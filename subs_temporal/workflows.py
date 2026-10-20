"""Temporal workflows for Subscription Manager.

SubsSyncWorkflow replaces the three staggered APScheduler jobs (wallet 19:00,
email 19:05, match 19:15) with one deterministic sequence, preserving ordering:
wallet -> email -> match. DiscoverySweepWorkflow replaces the weekly Sunday
07:00 sweep.
"""

from datetime import timedelta

from temporalio import workflow

from . import activities

ACTIVITY_TIMEOUT = timedelta(minutes=30)
NOTIFY_TIMEOUT = timedelta(minutes=5)


@workflow.defn
class SubsSyncWorkflow:
    """Wallet sync -> email sync -> wallet match, then notify."""

    @workflow.run
    async def run(self, since_days: int = 5, max_results: int = 500) -> dict:
        started_at = workflow.now().isoformat() + "Z"
        steps: dict = {}

        wallet = await workflow.execute_activity(
            activities.wallet_sync_activity,
            since_days,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        steps["wallet_sync"] = wallet.get("result")

        email = await workflow.execute_activity(
            activities.email_sync_activity,
            args=[since_days, max_results],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        steps["email_sync"] = email.get("result")

        match = await workflow.execute_activity(
            activities.wallet_match_activity,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        steps["wallet_match"] = match

        await workflow.execute_activity(
            activities.notify_run_summary_activity,
            args=["subs_sync", "ok", steps, None, started_at, None],
            start_to_close_timeout=NOTIFY_TIMEOUT,
        )
        return steps


@workflow.defn
class DiscoverySweepWorkflow:
    """Weekly discovery sweep -> notify."""

    @workflow.run
    async def run(self, min_occurrences: int = 2) -> dict:
        started_at = workflow.now().isoformat() + "Z"

        result = await workflow.execute_activity(
            activities.discovery_sweep_activity,
            min_occurrences,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )

        await workflow.execute_activity(
            activities.notify_run_summary_activity,
            args=["discovery_sweep", "ok", result, None, started_at, None],
            start_to_close_timeout=NOTIFY_TIMEOUT,
        )
        return result


WORKFLOWS = [SubsSyncWorkflow, DiscoverySweepWorkflow]