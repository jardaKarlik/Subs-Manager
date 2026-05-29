"""
Scheduled sync jobs for Subscription Manager.

Jobs:
  - Daily   06:00 UTC  — wallet sync (last 7 days)
  - Daily   06:10 UTC  — email sync  (last 3 days)
  - Daily   06:20 UTC  — wallet match (cross-reference + billing cycle inference)
  - Weekly  Sun 07:00  — wallet candidates refresh (discovery sweep)

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

async def job_wallet_sync():
    """Daily: pull last 7 days of wallet records."""
    logger.info("[cron] wallet sync start")
    try:
        from wallet_fetcher import WalletFetcher
        result = await WalletFetcher().sync(since_days=7)
        logger.info("[cron] wallet sync done: %s", result)
    except Exception as exc:
        logger.error("[cron] wallet sync failed: %s", exc)


async def job_email_sync():
    """Daily: pull last 3 days of emails from all sources."""
    logger.info("[cron] email sync start")
    try:
        from email_fetcher import EmailFetcher
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await EmailFetcher().process_emails(db=db, since_days=3, max_results=200)
        logger.info("[cron] email sync done: %s", result)
    except Exception as exc:
        logger.error("[cron] email sync failed: %s", exc)


async def job_wallet_match():
    """Daily: cross-reference wallet records against subscriptions."""
    logger.info("[cron] wallet match start")
    try:
        from subscription_matcher import SubscriptionMatcher
        matcher = SubscriptionMatcher()
        match_result = await matcher.match_all()
        cycle_result = await matcher.infer_billing_cycles()
        logger.info("[cron] wallet match done: %s %s", match_result, cycle_result)
    except Exception as exc:
        logger.error("[cron] wallet match failed: %s", exc)


async def job_discovery_sweep():
    """Weekly: surface new recurring payees as pending candidates."""
    logger.info("[cron] discovery sweep start")
    try:
        from subscription_matcher import SubscriptionMatcher
        matcher = SubscriptionMatcher()
        candidates = await matcher.find_unmatched_recurring(min_occurrences=2)
        high_confidence = [c for c in candidates if c["score"] >= 70]
        logger.info("[cron] discovery sweep done: %d candidates, %d high-confidence",
                    len(candidates), len(high_confidence))
    except Exception as exc:
        logger.error("[cron] discovery sweep failed: %s", exc)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler():
    """Register all jobs and start the scheduler. Call from FastAPI startup."""
    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler already running — skipping start")
        return

    # Daily wallet sync at 06:00 UTC
    scheduler.add_job(
        job_wallet_sync,
        CronTrigger(hour=6, minute=0),
        id="wallet_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Daily email sync at 06:10 UTC
    scheduler.add_job(
        job_email_sync,
        CronTrigger(hour=6, minute=10),
        id="email_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Daily cross-reference at 06:20 UTC (after both syncs finish)
    scheduler.add_job(
        job_wallet_match,
        CronTrigger(hour=6, minute=20),
        id="wallet_match",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Weekly discovery sweep — Sunday 07:00 UTC
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
