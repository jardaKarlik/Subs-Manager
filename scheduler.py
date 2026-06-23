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
    """Every 3 days: pull last 5 days of wallet records, run matching, and auto-discover."""
    async def _run():
        from wallet_fetcher import WalletFetcher
        from subscription_matcher import SubscriptionMatcher

        # 1. Fetch wallet records
        sync_res = await WalletFetcher().sync(since_days=5)

        # 2. Run matching, payment type detection, and auto-discovery
        matcher = SubscriptionMatcher()
        match_res = await matcher.match_all()
        detect_res = await matcher.detect_all_payment_types()
        discover_res = await matcher.auto_discover_new_subscriptions()

        return {
            "sync": sync_res,
            "matching": match_res,
            "payment_type_detection": detect_res,
            "auto_discovery": discover_res
        }

    await _run_with_notification("wallet_sync", _run)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler():
    """Register all jobs and start the scheduler. Call from FastAPI startup."""
    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler already running — skipping start")
        return

    # Every 3 days at 19:00 UTC — wallet sync (full pipeline)
    scheduler.add_job(
        job_wallet_sync,
        CronTrigger(hour=19, minute=0, day="*/3"),
        id="wallet_sync",
        replace_existing=True,
        misfire_grace_time=3600,  # 1h grace
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
