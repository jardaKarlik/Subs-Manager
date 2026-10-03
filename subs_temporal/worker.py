"""Temporal worker entrypoint.

Run as:  python -m subs_temporal.worker
Env:
  TEMPORAL_ADDRESS     Temporal frontend (default localhost:7233)
  TEMPORAL_TASK_QUEUE  Task queue name (default subs-manager)
"""

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import ALL_ACTIVITIES
from .workflows import WORKFLOWS

TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "subs-manager")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(address)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=WORKFLOWS,
        activities=ALL_ACTIVITIES,
    )
    logging.info(
        "Subscription Manager Temporal worker started (queue=%s, address=%s)",
        TASK_QUEUE,
        address,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())