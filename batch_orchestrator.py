"""
Serialized batch orchestration for email backfill and incremental sync.

The orchestrator enforces this rule: batch N+1 is never fetched/processed until
batch N has been inserted, verified, and marked completed in the database.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Callable, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import BatchProcess, ProcessedEmail


@dataclass
class EmailBatch:
    source: str
    batch_number: int
    emails: List[Dict]
    page_token: Optional[str] = None
    next_page_token: Optional[str] = None


BatchFactory = Callable[..., AsyncIterator[EmailBatch]]


class BatchOrchestrator:
    """Run email processing batches sequentially with persistent status."""

    def __init__(self, fetcher):
        self.fetcher = fetcher

    async def run_full_backfill(
        self,
        db: AsyncSession,
        sources: Optional[List[str]] = None,
        max_results: int = 1000,
        since_days: int = 30,
        batch_size: int = 10,
    ) -> Dict:
        return await self._run(
            db=db,
            process_type="full_backfill",
            sources=sources,
            max_results=max_results,
            since_days=since_days,
            batch_size=batch_size,
        )

    async def run_incremental_sync(
        self,
        db: AsyncSession,
        sources: Optional[List[str]] = None,
        max_results: int = 100,
        since_days: int = 3,
        batch_size: int = 10,
    ) -> Dict:
        return await self._run(
            db=db,
            process_type="incremental",
            sources=sources,
            max_results=max_results,
            since_days=since_days,
            batch_size=batch_size,
        )

    async def _run(
        self,
        db: AsyncSession,
        process_type: str,
        sources: Optional[List[str]],
        max_results: int,
        since_days: int,
        batch_size: int,
    ) -> Dict:
        if sources is None:
            sources = ["gmail", "outlook", "imap"]

        results = {
            "processed": 0,
            "new_subscriptions": 0,
            "skipped": 0,
            "failed": 0,
            "sources": {},
            "batches": {"completed": 0, "failed": 0},
        }

        for source in sources:
            resume = await self._get_resume_point(db, source, process_type)
            source_fetched = 0

            async for batch in self._iter_batches(
                source=source,
                max_results=max_results,
                since_days=since_days,
                batch_size=batch_size,
                resume_batch_number=resume["batch_number"],
                resume_token=resume["page_token"],
            ):
                source_fetched += len(batch.emails)
                await self._process_single_batch(db, batch, process_type, results)
                results["batches"]["completed"] += 1
                print(
                    f"  {source.title()} batch #{batch.batch_number}: "
                    f"{len(batch.emails)} fetched -> total processed: {results['processed']}"
                )

            results["sources"][source] = source_fetched

        return results

    async def _iter_batches(
        self,
        source: str,
        max_results: int,
        since_days: int,
        batch_size: int,
        resume_batch_number: int,
        resume_token: Optional[str],
    ) -> AsyncIterator[EmailBatch]:
        remaining = max_results - (resume_batch_number * batch_size)
        if remaining <= 0:
            return

        if source == "gmail":
            async for batch in self.fetcher._stream_fetch_batches_gmail(
                max_results=remaining,
                since_days=since_days,
                batch_size=batch_size,
                start_batch_number=resume_batch_number + 1,
                page_token=resume_token,
            ):
                yield batch
        elif source == "outlook":
            outlook_skip = int(resume_token or (resume_batch_number * batch_size))
            async for batch in self.fetcher._stream_fetch_batches_outlook(
                max_results=remaining,
                since_days=since_days,
                batch_size=batch_size,
                start_batch_number=resume_batch_number + 1,
                skip=outlook_skip,
            ):
                yield batch
        elif source == "imap":
            emails = await self.fetcher.fetch_imap(max_results, since_days)
            if resume_batch_number > 0:
                emails = emails[resume_batch_number * batch_size:]
            batch_number = resume_batch_number + 1
            for start in range(0, len(emails), batch_size):
                chunk = emails[start:start + batch_size]
                if chunk:
                    yield EmailBatch(
                        source="imap",
                        batch_number=batch_number,
                        emails=chunk,
                        page_token=str(start),
                        next_page_token=str(start + len(chunk)),
                    )
                    batch_number += 1

    async def _process_single_batch(
        self,
        db: AsyncSession,
        batch: EmailBatch,
        process_type: str,
        results: Dict,
    ) -> BatchProcess:
        batch_record = await self._create_batch_record(db, batch, process_type)
        before = results.copy()

        try:
            batch_record.status = "parsing"
            await db.commit()

            message_ids = self._unique_message_ids(batch.emails)

            batch_record.status = "inserting"
            batch_record.emails_fetched = len(batch.emails)
            await db.commit()

            await self.fetcher._process_email_batch(db, batch.emails, results)

            batch_record.status = "verifying"
            await db.commit()

            await self._verify_batch_inserted(db, message_ids)

            batch_record.emails_processed = results["processed"] - before["processed"]
            batch_record.emails_skipped = results["skipped"] - before["skipped"]
            batch_record.new_subscriptions = (
                results["new_subscriptions"] - before["new_subscriptions"]
            )
            batch_record.status = "completed"
            batch_record.completed_at = datetime.utcnow()
            await db.commit()
            return batch_record
        except Exception as exc:
            await db.rollback()
            fresh = await db.get(BatchProcess, batch_record.id)
            if fresh:
                fresh.status = "failed"
                fresh.error_message = str(exc)[:2000]
                fresh.completed_at = datetime.utcnow()
                await db.commit()
            results["batches"]["failed"] += 1
            raise RuntimeError(
                f"Batch {batch.source} #{batch.batch_number} failed: {exc}"
            ) from exc

    async def _create_batch_record(
        self,
        db: AsyncSession,
        batch: EmailBatch,
        process_type: str,
    ) -> BatchProcess:
        existing = await db.execute(
            select(BatchProcess).where(
                BatchProcess.source == batch.source,
                BatchProcess.process_type == process_type,
                BatchProcess.batch_number == batch.batch_number,
                BatchProcess.status == "completed",
            )
        )
        if existing.scalar_one_or_none():
            raise RuntimeError(
                f"Refusing to re-process completed batch {batch.source} #{batch.batch_number}"
            )

        record = BatchProcess(
            process_type=process_type,
            source=batch.source,
            batch_number=batch.batch_number,
            page_token=batch.next_page_token or batch.page_token,
            emails_fetched=len(batch.emails),
            status="fetching",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def _verify_batch_inserted(
        self,
        db: AsyncSession,
        message_ids: List[str],
    ) -> None:
        if not message_ids:
            return
        result = await db.execute(
            select(func.count(ProcessedEmail.message_id)).where(
                ProcessedEmail.message_id.in_(message_ids)
            )
        )
        actual = result.scalar() or 0
        expected = len(set(message_ids))
        if actual != expected:
            raise RuntimeError(
                f"Batch verification failed: expected {expected} ProcessedEmail rows, got {actual}"
            )

    async def _get_resume_point(
        self,
        db: AsyncSession,
        source: str,
        process_type: str,
    ) -> Dict:
        latest_result = await db.execute(
            select(BatchProcess)
            .where(
                BatchProcess.source == source,
                BatchProcess.process_type == process_type,
            )
            .order_by(BatchProcess.batch_number.desc())
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        if latest and latest.status != "completed":
            latest.status = "failed"
            latest.error_message = "Recovered from previous incomplete run; safe rewind"
            latest.completed_at = datetime.utcnow()
            await db.commit()

        completed_result = await db.execute(
            select(BatchProcess)
            .where(
                BatchProcess.source == source,
                BatchProcess.process_type == process_type,
                BatchProcess.status == "completed",
            )
            .order_by(BatchProcess.batch_number.desc())
            .limit(1)
        )
        completed = completed_result.scalar_one_or_none()

        if not completed:
            return {"batch_number": 0, "page_token": None}
        return {
            "batch_number": completed.batch_number,
            "page_token": completed.page_token,
        }

    def _unique_message_ids(self, emails: List[Dict]) -> List[str]:
        seen = set()
        ids = []
        for email in emails:
            uid = f"{email['source']}:{email['message_id']}"
            if uid not in seen:
                seen.add(uid)
                ids.append(uid)
        return ids
