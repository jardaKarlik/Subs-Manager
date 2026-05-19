"""Local deterministic test for serialized batch orchestration.

This test does not call Composio. It builds 400 dummy emails and processes them
in 8 batches of 50 to validate serialization, status logging, and DB inserts.
"""

import asyncio
import os
from typing import List, Dict

from sqlalchemy import delete, func, select

from batch_orchestrator import BatchOrchestrator, EmailBatch
from database import (
    AsyncSessionLocal,
    BatchProcess,
    ProcessedEmail,
    Subscription,
    SubscriptionEvent,
    init_db,
)
from email_fetcher import EmailFetcher


class DummyFetcher(EmailFetcher):
    def __init__(self, emails: List[Dict]):
        super().__init__()
        self.emails = emails

    async def _stream_fetch_batches_gmail(
        self,
        max_results: int,
        since_days: int,
        batch_size: int = 50,
        start_batch_number: int = 1,
        page_token: str = None,
    ):
        start_index = int(page_token or "0")
        gmail = [e for e in self.emails if e["source"] == "gmail"]
        batch_number = start_batch_number
        yielded = 0
        for idx in range(start_index, len(gmail), batch_size):
            if yielded >= max_results:
                break
            chunk = gmail[idx:idx + batch_size]
            chunk = chunk[:max_results - yielded]
            if not chunk:
                break
            yield EmailBatch(
                source="gmail",
                batch_number=batch_number,
                emails=chunk,
                page_token=str(idx),
                next_page_token=str(idx + len(chunk)),
            )
            yielded += len(chunk)
            batch_number += 1

    async def _stream_fetch_batches_outlook(
        self,
        max_results: int,
        since_days: int,
        batch_size: int = 50,
        start_batch_number: int = 1,
        skip: int = 0,
    ):
        outlook = [e for e in self.emails if e["source"] == "outlook"]
        batch_number = start_batch_number
        yielded = 0
        for idx in range(skip, len(outlook), batch_size):
            if yielded >= max_results:
                break
            chunk = outlook[idx:idx + batch_size]
            chunk = chunk[:max_results - yielded]
            if not chunk:
                break
            yield EmailBatch(
                source="outlook",
                batch_number=batch_number,
                emails=chunk,
                page_token=str(idx),
                next_page_token=str(idx + len(chunk)),
            )
            yielded += len(chunk)
            batch_number += 1


class FailingAfterBatchesOrchestrator(BatchOrchestrator):
    def __init__(self, fetcher, fail_after_completed: int):
        super().__init__(fetcher)
        self.fail_after_completed = fail_after_completed
        self.completed_seen = 0

    async def _process_single_batch(self, db, batch, process_type, results):
        record = await super()._process_single_batch(db, batch, process_type, results)
        self.completed_seen += 1
        if self.completed_seen >= self.fail_after_completed:
            raise RuntimeError("Simulated crash after completed batch")
        return record


def build_dummy_emails() -> List[Dict]:
    emails = []

    subscription_templates = [
        ("Netflix", "receipts@netflix.com", "Your Netflix Premium Subscription Receipt", "Thank you for subscribing. You paid $22.99 USD for your monthly Netflix Premium plan."),
        ("Spotify", "billing@spotify.com", "Spotify Family Plan Payment Confirmation", "Your payment was successful. We charged $16.99 USD for your monthly Spotify Premium Family subscription."),
        ("OpenAI", "billing@openai.com", "Welcome to ChatGPT Plus", "Your subscription is confirmed. Amount paid: $20.00 USD. Billed monthly."),
        ("GitHub", "noreply@github.com", "GitHub Pro receipt", "Receipt for your payment. You paid $4.00 USD for GitHub Pro monthly plan."),
        ("Notion", "team@notion.so", "Welcome to Notion", "Thank you for joining Notion. Your account is active."),
    ]

    # 80 subscription-like emails, split evenly across gmail/outlook.
    for i in range(80):
        service, sender, subject, body = subscription_templates[i % len(subscription_templates)]
        source = "gmail" if i < 40 else "outlook"
        emails.append({
            "message_id": f"sub-{i:03d}",
            "source": source,
            "subject": subject,
            "sender": sender,
            "date": "2026-05-15T10:00:00Z",
            "body": body,
            "raw": {},
        })

    # 300 non-subscription emails.
    for i in range(300):
        source = "gmail" if i < 150 else "outlook"
        emails.append({
            "message_id": f"noise-{i:03d}",
            "source": source,
            "subject": f"Newsletter update #{i}",
            "sender": "news@example.com",
            "date": "2026-05-14T08:30:00Z",
            "body": "Weekly digest with marketing updates, promo news, and unsubscribe footer.",
            "raw": {},
        })

    # 20 duplicates using existing IDs, split evenly across gmail/outlook.
    duplicate_indexes = list(range(10)) + list(range(40, 50))
    for idx in duplicate_indexes:
        duplicate = dict(emails[idx])
        emails.append(duplicate)

    # Keep deterministic ordering by source so each provider has 200 emails.
    return sorted(emails, key=lambda item: (item["source"], item["message_id"]))


async def reset_db():
    await init_db()
    async with AsyncSessionLocal() as db:
        await db.execute(delete(BatchProcess))
        await db.execute(delete(SubscriptionEvent))
        await db.execute(delete(ProcessedEmail))
        await db.execute(delete(Subscription))
        await db.commit()


async def count_rows(db, model):
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar() or 0


async def run_happy_path():
    await reset_db()
    emails = build_dummy_emails()
    fetcher = DummyFetcher(emails)
    orchestrator = BatchOrchestrator(fetcher)

    async with AsyncSessionLocal() as db:
        # Pre-seed 10 processed subscription messages to prove skip logic.
        for i in range(10):
            db.add(ProcessedEmail(message_id=f"gmail:sub-{i:03d}", source="gmail"))
        await db.commit()

        results = await orchestrator.run_full_backfill(
            db=db,
            sources=["gmail", "outlook"],
            max_results=200,
            since_days=730,
            batch_size=50,
        )

        completed = await db.execute(
            select(func.count(BatchProcess.id)).where(BatchProcess.status == "completed")
        )
        completed_batches = completed.scalar() or 0
        processed_count = await count_rows(db, ProcessedEmail)
        event_count = await count_rows(db, SubscriptionEvent)
        subscription_count = await count_rows(db, Subscription)

    assert len(emails) == 400, f"Expected 400 dummy emails, got {len(emails)}"
    assert completed_batches == 8, f"Expected 8 completed batches, got {completed_batches}"
    assert processed_count == 380, f"Expected 380 unique processed emails, got {processed_count}"
    assert event_count >= 70, f"Expected at least 70 subscription events, got {event_count}"
    assert subscription_count >= 5, f"Expected at least 5 subscriptions, got {subscription_count}"
    assert results["processed"] == 370, f"Expected 370 newly processed emails, got {results['processed']}"
    assert results["skipped"] == 30, f"Expected 30 skipped emails, got {results['skipped']}"

    print("[OK] Happy path passed")
    print(f"   Batches completed: {completed_batches}")
    print(f"   New processed emails: {results['processed']}")
    print(f"   Skipped emails: {results['skipped']}")
    print(f"   Subscription rows: {subscription_count}")
    print(f"   Event rows: {event_count}")


async def run_resume_path():
    await reset_db()
    emails = build_dummy_emails()
    fetcher = DummyFetcher(emails)

    async with AsyncSessionLocal() as db:
        try:
            await FailingAfterBatchesOrchestrator(fetcher, fail_after_completed=3).run_full_backfill(
                db=db,
                sources=["gmail", "outlook"],
                max_results=200,
                since_days=730,
                batch_size=50,
            )
        except RuntimeError:
            pass

        completed_before = await db.execute(
            select(func.count(BatchProcess.id)).where(BatchProcess.status == "completed")
        )
        assert completed_before.scalar() == 3, "Expected simulated crash after 3 completed batches"

        results = await BatchOrchestrator(fetcher).run_full_backfill(
            db=db,
            sources=["gmail", "outlook"],
            max_results=200,
            since_days=730,
            batch_size=50,
        )

        completed_after = await db.execute(
            select(func.count(BatchProcess.id)).where(BatchProcess.status == "completed")
        )
        processed_count = await count_rows(db, ProcessedEmail)
        event_count = await count_rows(db, SubscriptionEvent)

    assert completed_after.scalar() == 8, "Expected resume to finish all 8 batches"
    assert processed_count == 380, f"Expected 380 unique processed emails, got {processed_count}"
    assert event_count == 80, f"Expected 80 events without preseed, got {event_count}"
    assert results["processed"] == 230, f"Expected resumed run to process 230 emails, got {results['processed']}"
    print("[OK] Resume path passed")


async def main():
    # Force local file DB unless caller explicitly supplied DATABASE_URL.
    os.environ.setdefault("SYNC_MAX_RESULTS", "400")
    await run_happy_path()
    await run_resume_path()


if __name__ == "__main__":
    asyncio.run(main())
