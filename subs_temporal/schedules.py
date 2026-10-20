"""Create the Temporal schedules that mirror the APScheduler jobs.

Run once after the worker is deployed:  python -m subs_temporal.schedules

Schedules are created PAUSED. Unpause each one once the new cluster is the
owner of the pipeline (see docs/railway-merge-runbook.md, section 8).

`task_queue` is per-schedule: the subscription workflows run on the
Python worker (`subs-manager`), while `musicReleaseScanWorkflow` is an
exported TS workflow served by the release-scanner worker
(`release-list-task-queue`). The schedule can be created from any client,
so it is registered here for convenience.
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
        "task_queue": TASK_QUEUE,
    },
    {
        "id": "subs-discovery-sweep",
        "cron": "0 7 * * 0",
        "workflow": DiscoverySweepWorkflow.run,
        "args": [2],
        "task_queue": TASK_QUEUE,
    },
    {
        "id": "music-release-scan-daily",
        "cron": "0 7 * * *",
        # Raw workflow name exported by the TS release scanner.
        "workflow": "musicReleaseScanWorkflow",
        "args": [],
        "task_queue": "release-list-task-queue",
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
                    task_queue=spec.get("task_queue", TASK_QUEUE),
                ),
                spec=ScheduleSpec(cron_expressions=[spec["cron"]]),
                policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
                state=ScheduleState(paused=True),
            ),
        )
        queue = spec.get("task_queue", TASK_QUEUE)
        print(f"created PAUSED schedule {spec['id']} ({spec['cron']}) on {queue}")


if __name__ == "__main__":
    asyncio.run(main())
