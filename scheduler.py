"""
Scheduled sync jobs for Subscription Manager.

Jobs (every 3 days at 19:00 UTC):
  - 19:00 UTC — wallet sync (last 5 days)
  - 19:05 UTC — email sync  (last 5 days)
  - 19:15 UTC — wallet match (cross-reference + billing cycle inference)
  - Weekly  Sun 07:00 — wallet candidates refresh (discovery sweep)

Uses interval=3 days (not cron) so the schedule is independent of the day
of week it was first started. Initial deployment triggers a one-time backfill
via /api/parse-emails and /api/sync-wallet manually; subsequent runs are
incremental with a 2-day overlap buffer (since_days=5) to guarantee no
transactions or emails are missed across the 3-day gap.

Integrates with FastAPI lifecycle via startup/shutdown hooks.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

# Singleton — created once, shared across the app
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


# ── Job functions ─────────────────────────────────────────────────────────────

async def _run_with_notification(job_name: str, coro_factory):
    """Run a job coroutine factory, capture result/error/duration, send Gmail summary.

    `coro_factory` is a no-arg callable returning a coroutine — it runs inside
    a try/except so a single failing job never breaks the scheduler loop.
    Notification failures are logged but never raised.
    """
    import time
    from notifier import send_run_summary

    started = datetime.utcnow()
    t0 = time.monotonic()
    error_msg = None
    stats: dict = {}

    logger.info("[cron] %s start", job_name)
    try:
        result = await coro_factory()
        if isinstance(result, dict):
            stats = {k: v for k, v in result.items() if isinstance(v, (int, float, str))}
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error("[cron] %s failed: %s", job_name, error_msg)
    finally:
        duration = time.monotonic() - t0
        status = "ok" if error_msg is None else "error"
        try:
            send_run_summary(
                job_name=job_name,
                status=status,
                stats=stats,
                error=error_msg,
                started_at=started.isoformat(timespec="seconds") + "Z",
                duration_s=duration,
            )
        except Exception as notif_exc:
            logger.warning("[cron] %s notification failed: %s", job_name, notif_exc)
        if error_msg is None:
            logger.info("[cron] %s done in %.1fs: %s", job_name, duration, stats)


async def job_wallet_sync():
    """Every 3 days: pull last 5 days of wallet records.

    2-day overlap buffer over the 3-day cycle guarantees that no transactions
    slip through due to timezone shifts or processing delays.
    """

    async def _run():
        from wallet_fetcher import WalletFetcher
        return await WalletFetcher().sync(since_days=5)

    await _run_with_notification("wallet_sync", _run)


async def job_email_sync():
    """Every 3 days: pull last 5 days of emails from all sources.

    2-day overlap buffer over the 3-day cycle guarantees that no emails
    slip through due to timezone shifts or processing delays.
    """

    async def _run():
        from email_fetcher import EmailFetcher
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await EmailFetcher().process_emails(db=db, since_days=5, max_results=500)

    await _run_with_notification("email_sync", _run)


async def job_wallet_match():
    """Every 3 days: cross-reference wallet records against subscriptions."""

    async def _run():
        from subscription_matcher import SubscriptionMatcher
        matcher = SubscriptionMatcher()
        match_result = await matcher.match_all()
        cycle_result = await matcher.infer_billing_cycles()
        return {"matched": match_result, "cycles": cycle_result}

    await _run_with_notification("wallet_match", _run)


async def job_discovery_sweep():
    """Weekly: surface new recurring payees as pending candidates."""

    async def _run():
        from subscription_matcher import SubscriptionMatcher
        matcher = SubscriptionMatcher()
        candidates = await matcher.find_unmatched_recurring(min_occurrences=2)
        high_confidence = [c for c in candidates if c["score"] >= 70]
        return {
            "candidates": len(candidates),
            "high_confidence": len(high_confidence),
        }

    await _run_with_notification("discovery_sweep", _run)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler():
    """Register all jobs and start the scheduler. Call from FastAPI startup."""
    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler already running — skipping start")
        return

    # Every 3 days at 19:00 UTC — wallet sync
    scheduler.add_job(
        job_wallet_sync,
        CronTrigger(hour=19, minute=0, day="*/3"),
        id="wallet_sync",
        replace_existing=True,
        misfire_grace_time=3600,  # 1h grace — long ops can take time
    )

    # Every 3 days at 19:05 UTC — email sync (5 min after wallet)
    scheduler.add_job(
        job_email_sync,
        CronTrigger(hour=19, minute=5, day="*/3"),
        id="email_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Every 3 days at 19:15 UTC — wallet match (10 min after email start)
    scheduler.add_job(
        job_wallet_match,
        CronTrigger(hour=19, minute=15, day="*/3"),
        id="wallet_match",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly discovery sweep — Sunday 07:00 UTC (unchanged)
    scheduler.add_job(
        job_discovery_sweep,
        CronTrigger(day_of_week="sun", hour=7, minute=0),
        id="discovery_sweep",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.start()
    _log_schedule()


def stop_scheduler():
    """Gracefully stop the scheduler. Call from FastAPI shutdown."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def _log_schedule():
    scheduler = get_scheduler()
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info("  %-20s next run: %s", job.id, job.next_run_time)
