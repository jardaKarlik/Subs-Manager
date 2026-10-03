"""Manual control + status for the Subscription Manager Temporal workflows.

Usage (run inside the worker container or anywhere with TEMPORAL_ADDRESS set):

  python -m subs_temporal.run_once start [since_days] [max_results]
  python -m subs_temporal.run_once status <workflow_id>
  python -m subs_temporal.run_once terminate <workflow_id>
  python -m subs_temporal.run_once discovery [min_occurrences]
"""

import asyncio
import os
import sys
import time

from temporalio.client import Client

from .workflows import DiscoverySweepWorkflow, SubsSyncWorkflow

TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "subs-manager")


def _addr() -> str:
    return os.getenv("TEMPORAL_ADDRESS", "localhost:7233")


async def _start(kind: str, nums: list[int]) -> None:
    client = await Client.connect(_addr())
    if kind == "discovery":
        wf, args = DiscoverySweepWorkflow.run, [nums[0]]
    else:
        wf, args = SubsSyncWorkflow.run, nums
    wf_id = f"{kind}-manual-{int(time.time())}"
    handle = await client.start_workflow(wf, args=args, id=wf_id, task_queue=TASK_QUEUE)
    print(f"STARTED {handle.id}")


async def _status(wf_id: str) -> None:
    client = await Client.connect(_addr())
    handle = client.get_workflow_handle(wf_id)
    desc = await handle.describe()
    print(f"status: {desc.status}")
    hist = handle.fetch_history()
    if not hasattr(hist, "__aiter__"):
        hist = await hist
    for ev in hist.events:
        if ev.HasField("activity_task_scheduled_event_attributes"):
            print("SCHEDULED", ev.activity_task_scheduled_event_attributes.activity_type.name)
        if ev.HasField("activity_task_completed_event_attributes"):
            payloads = ev.activity_task_completed_event_attributes.result.payloads
            data = payloads[0].data.decode("utf-8", "replace")[:240] if payloads else ""
            print("COMPLETED", data)
        if ev.HasField("activity_task_failed_event_attributes"):
            print("FAILED", ev.activity_task_failed_event_attributes.failure.message[:240])


async def _terminate(wf_id: str) -> None:
    client = await Client.connect(_addr())
    await client.get_workflow_handle(wf_id).terminate()
    print(f"terminated {wf_id}")


async def _schedules() -> None:
    client = await Client.connect(_addr())
    it = client.list_schedules()
    if not hasattr(it, "__aiter__"):
        it = await it
    async for s in it:
        paused = s.schedule.state.paused if s.schedule and s.schedule.state else None
        nxt = [t.isoformat() for t in (s.info.next_action_times or [])][:1] if s.info else []
        print(f"{s.id}  paused={paused}  next={nxt}")


async def _set_paused(sid: str, paused: bool) -> None:
    client = await Client.connect(_addr())
    handle = client.get_schedule_handle(sid)
    if paused:
        await handle.pause()
    else:
        await handle.unpause()
    print(f"{'paused' if paused else 'unpaused'} {sid}")


async def _check() -> None:
    client = await Client.connect(_addr())
    for sid in ("subs-sync", "subs-discovery-sweep", "music-release-scan-daily"):
        d = await client.get_schedule_handle(sid).describe()
        st = d.schedule.state
        nxt = [t.isoformat() for t in (d.info.next_action_times or [])] if d.info else []
        print(sid, "paused=", st.paused, "next=", nxt)


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "help"
    if cmd == "start":
        nums = [int(x) for x in argv[1:3]] or [5, 500]
        asyncio.run(_start("sync", nums))
    elif cmd == "discovery":
        nums = [int(argv[1])] if len(argv) > 1 else [2]
        asyncio.run(_start("discovery", nums))
    elif cmd == "status" and len(argv) > 1:
        asyncio.run(_status(argv[1]))
    elif cmd == "terminate" and len(argv) > 1:
        asyncio.run(_terminate(argv[1]))
    elif cmd == "schedules":
        asyncio.run(_schedules())
    elif cmd == "pause" and len(argv) > 1:
        asyncio.run(_set_paused(argv[1], True))
    elif cmd == "unpause" and len(argv) > 1:
        asyncio.run(_set_paused(argv[1], False))
    elif cmd == "check":
        asyncio.run(_check())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()