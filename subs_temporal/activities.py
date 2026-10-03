"""Temporal activities for Subscription Manager.

Each activity calls the same module the APScheduler job in scheduler.py calls,
so there is a single source of truth for the pipeline logic. The operations are
idempotent (wallet/financial upserts + processed_emails dedup gate), which makes
Temporal retries safe.
"""

import asyncio
import logging
from typing import Any, Optional

from temporalio import activity

logger = logging.getLogger("temporal.activities")


def _primitive(value: Any) -> Any:
    """Coerce results to JSON/JSON-safe types for Temporal payloads."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_primitive(v) for v in value]
    return str(value)


@activity.defn
async def wallet_sync_activity(since_days: int = 5) -> dict:
    """Pull BudgetBakers Wallet records -> financial_records (scheduler.job_wallet_sync)."""
    from wallet_fetcher import WalletFetcher

    result = await WalletFetcher().sync(since_days=since_days)
    return {"result": _primitive(result)}


@activity.defn
async def email_sync_activity(since_days: int = 5, max_results: int = 500) -> dict:
    """Gmail + Outlook + IMAP -> subscriptions (scheduler.job_email_sync)."""
    from database import AsyncSessionLocal
    from email_fetcher import EmailFetcher

    async with AsyncSessionLocal() as db:
        result = await EmailFetcher().process_emails(
            db=db, since_days=since_days, max_results=max_results
        )
    return {"result": _primitive(result)}


@activity.defn
async def wallet_match_activity() -> dict:
    """Cross-reference wallet records vs subscriptions (scheduler.job_wallet_match).

    `infer_billing_cycles` is called by scheduler.py but is not defined in
    subscription_matcher.py on master, so it is guarded and reported rather than
    allowed to fail the activity.
    """
    from subscription_matcher import SubscriptionMatcher

    matcher = SubscriptionMatcher()
    result = await matcher.match_all()
    payload: dict = {"matching": _primitive(result)}

    infer = getattr(matcher, "infer_billing_cycles", None)
    if callable(infer):
        try:
            payload["cycles"] = _primitive(await infer())
        except Exception as exc:  # pragma: no cover - defensive
            payload["cycles_error"] = f"{type(exc).__name__}: {exc}"
    else:
        payload["cycles"] = None
        payload["cycles_note"] = "infer_billing_cycles not implemented on this revision"
    return payload


@activity.defn
async def discovery_sweep_activity(min_occurrences: int = 2) -> dict:
    """Surface new recurring payees (scheduler.job_discovery_sweep)."""
    from subscription_matcher import SubscriptionMatcher

    matcher = SubscriptionMatcher()
    candidates = await matcher.find_unmatched_recurring(min_occurrences=min_occurrences)
    candidates = candidates or []
    high_confidence = [c for c in candidates if (c or {}).get("score", 0) >= 70]
    return {"candidates": len(candidates), "high_confidence": len(high_confidence)}


@activity.defn
async def notify_run_summary_activity(
    job_name: str,
    status: str,
    stats: dict,
    error: Optional[str] = None,
    started_at: Optional[str] = None,
    duration_s: Optional[float] = None,
) -> bool:
    """Send the Gmail run summary (notifier.send_run_summary, blocking -> thread)."""
    from notifier import send_run_summary

    try:
        await asyncio.to_thread(
            send_run_summary,
            job_name,
            status,
            _primitive(stats),
            error,
            started_at,
            duration_s,
        )
        return True
    except Exception as exc:
        logger.warning("notify_run_summary failed: %s", exc)
        return False


ALL_ACTIVITIES = [
    wallet_sync_activity,
    email_sync_activity,
    wallet_match_activity,
    discovery_sweep_activity,
    notify_run_summary_activity,
]