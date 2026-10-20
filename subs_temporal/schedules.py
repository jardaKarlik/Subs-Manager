"""Create the Temporal schedules that mirror the APScheduler jobs.

Run once after the worker is deployed:  python -m subs_temporal.schedules

Schedules are created PAUSED. The live APScheduler keeps owning execution until
we verify parity and set SCHEDULER_ENABLED=false on the web service. Unpause with
the Temporal UI or client once cut over.
"""

import asyncio
import os

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
)

from .workflows import DiscoverySweepWorkflow, SubsSyncWorkflow

TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "subs-manager")

SCHEDULES = [
    {
        "id": "subs-sync",
        "cron": "0 19 */3 * *",
        "workflow": SubsSyncWorkflow.run,
        "args": [5, 500],
    },
    {
        "id": "subs-discovery-sweep",
        "cron": "0 7 * * 0",
        "workflow": DiscoverySweepWorkflow.run,
        "args": [2],
    },
]


async def main() -> None:
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    for spec in SCHEDULES:
        handle = client.get_schedule_handle(spec["id"])
        try:
            await handle.describe()
            print(f"schedule {spec['id']} already exists - skipping")
            continue
        except Exception:
            pass
        await client.create_schedule(
            spec["id"],
            Schedule(
                action=ScheduleActionStartWorkflow(
                    spec["workflow"],
                    args=spec["args"],
                    id=spec["id"],
                    task_queue=TASK_QUEUE,
                ),
                spec=ScheduleSpec(cron_expressions=[spec["cron"]]),
                policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
                state=ScheduleState(paused=True),
            ),
        )
        print(f"created PAUSED schedule {spec['id']} ({spec['cron']})")


if __name__ == "__main__":
    asyncio.run(main())