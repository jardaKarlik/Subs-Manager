# 📋 Backlog Task: Fail-Proof Batch Email Orchestrator

**Task ID:** SUB-MANAGER-BATCH-ORCH-01  
**Priority:** HIGH  
**Status:** 📋 READY TO IMPLEMENT  
**Branch:** `feature/sdk-v2-migration` (or new branch `feature/batch-orchestrator`)  
**Estimated Time:** 4–5 hours  

---

## 🎯 Objective

Implement a **fail-proof, serialized batch processing pipeline** for email fetch → parse → classify → DB insert. The system must guarantee that:

1. One batch is **fully fetched, parsed, inserted, and verified** before the next batch starts.
2. A crash at any point can be **resumed** without re-processing already-completed batches.
3. Every batch has **explicit verification** that DB rows were actually written.
4. The entire flow can be **tested locally** with dummy data before hitting live Composio APIs.

---

## 📐 Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Gmail/Outlook  │────▶│  BatchExtractor │────▶│  EmailBatch #N  │
│    API (v2)     │     │  (generator)    │     │  (50 emails)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                    ┌────────────────────────────────────┘
                    ▼
         ┌─────────────────────┐
         │   BatchOrchestrator │
         │  ┌───────────────┐  │
         │  │ 1. FETCH      │  │◄── Create BatchProcess record (status="fetching")
         │  │ 2. PARSE      │  │◄── Update status="parsing"
         │  │ 3. DEDUP      │  │◄── Check ProcessedEmail table
         │  │ 4. INSERT     │  │◄── Transaction: Sub + Event + ProcessedEmail
         │  │ 5. VERIFY     │  │◄── SELECT COUNT(*) to confirm rows landed
         │  │ 6. COMMIT     │  │◄── Update status="completed"
         │  └───────────────┘  │
         └─────────────────────┘
                    │
                    ▼ (ONLY IF batch N completed)
         ┌─────────────────────┐
         │   EmailBatch #N+1   │
         └─────────────────────┘
```

**Rule:** Batch N+1 is never started until Batch N status = `completed`.

---

## 🗄️ Database Schema Changes

### New Table: `batch_processes`

```sql
CREATE TABLE batch_processes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_type VARCHAR(20) NOT NULL,      -- 'full_backfill' | 'incremental'
    source VARCHAR(50) NOT NULL,              -- 'gmail' | 'outlook' | 'imap'
    batch_number INTEGER NOT NULL,
    page_token VARCHAR(500),                 -- Gmail nextPageToken or Outlook skip
    emails_fetched INTEGER DEFAULT 0,
    emails_processed INTEGER DEFAULT 0,
    emails_skipped INTEGER DEFAULT 0,
    new_subscriptions INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',    -- pending → fetching → parsing → inserting → verifying → completed | failed
    error_message VARCHAR(2000),
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE INDEX idx_batch_resume 
ON batch_processes(source, process_type, status, batch_number);
```

### Existing Tables (unchanged)
- `subscriptions`
- `processed_emails` — **remains the global dedup source of truth**
- `subscription_events`

---

## 📁 Files to Create / Modify

| File | Action | Description |
|------|--------|-------------|
| `database.py` | **Modify** | Add `BatchProcess` SQLAlchemy model |
| `batch_orchestrator.py` | **Create** | Core orchestrator + `EmailBatch` dataclass + verification logic |
| `email_fetcher.py` | **Modify** | Refactor stream methods to yield `EmailBatch` objects; enhance `_process_email_batch` with verification |
| `api.py` | **Modify** | Wire `BatchOrchestrator` into `/api/parse-emails` and `/api/sync-emails`; add `/api/batch-status` endpoint |
| `test_batch_orchestrator.py` | **Create** | Local test script with 400 dummy emails, 8 batches, crash/resume simulations |


---

## 🔧 Implementation Steps

### Phase 1: Schema (30 min)
1. Add `BatchProcess` model to `database.py`
2. Add composite index for resume queries
3. Run `init_db()` to create table (SQLite auto-migration)

### Phase 2: Core Orchestrator (90 min)
1. Create `batch_orchestrator.py`:
   - `EmailBatch` dataclass (`batch_number`, `page_token`, `emails[]`, `source`)
   - `BatchOrchestrator` class:
     - `_create_batch_record(db, source, process_type, batch_number, page_token)`
     - `_process_single_batch(db, batch, classifier)` → fetch → parse → dedup → insert → verify → mark complete
     - `_verify_batch_inserted(db, message_ids)` → SELECT COUNT(*) FROM processed_emails WHERE message_id IN (...)
     - `_get_resume_point(db, source, process_type)` → returns last `completed` batch + page_token
     - `_mark_failed_and_rewind(db, batch_id, error)`
     - `run_full_backfill(db, sources, max_results, since_days, batch_size=100)`
     - `run_incremental_sync(db, sources, max_results, since_days, batch_size=100)`

### Phase 3: Fetcher Refactor (45 min)
1. Modify `email_fetcher.py`:
   - `_stream_fetch_batches_gmail(max_results, since_days)` → yields `EmailBatch`
   - `_stream_fetch_batches_outlook(max_results, since_days)` → yields `EmailBatch`
   - `_process_email_batch()` → add `verify=True` flag; after commit, count inserted rows and assert match
   - Keep all existing parsing/classification/insert logic intact

### Phase 4: API Wiring (30 min)
1. Update `/api/parse-emails` → call `orchestrator.run_full_backfill()`
2. Update `/api/sync-emails` → call `orchestrator.run_incremental_sync()`
3. Add `/api/batch-status` → return latest batch processes per source with counts and status

### Phase 5: Local Testing (60 min)
1. Create `test_batch_orchestrator.py`:
   - Use in-memory or file-based SQLite (`sqlite+aiosqlite:///./test_batch.db`)
   - Generate **400 dummy emails** with realistic distribution:
     - 80 subscription emails (mix of Gmail/Outlook sources, various providers)
     - 20 duplicate emails (same message_id repeated — tests dedup)
     - 300 non-subscription emails (marketing, social, newsletters)
     - Pre-seed `ProcessedEmail` with 10 IDs (tests skip logic)
   - Set `batch_size=50` → expect **8 batches**
   - Test cases:
     - **Test 1 (Happy Path):** Run all 8 batches. Assert all `completed`, 70 new subscriptions (80 − 10 pre-seeded), 0 duplicates.
     - **Test 2 (Crash & Resume):** Simulate crash after batch 3. Restart orchestrator. Assert resumes at batch 4, final counts identical to Test 1.
     - **Test 3 (DB Commit Failure):** Mock commit to raise on batch 2. Assert batch 2 status=`failed`, batches 3+ never created, counts reflect only batch 1.
     - **Test 4 (Verification Mismatch):** Mock verification to return wrong count. Assert batch status=`failed`, pipeline halts.
     - **Test 5 (Incremental Sync):** Run full backfill on 100 emails. Add 20 new emails. Run incremental. Assert only 20 processed, 100 skipped.


---

## 🧪 Test Data Specification

The local test script must generate deterministic dummy emails. Example structure:

```python
DUMMY_EMAILS = [
    {
        "message_id": f"gmail-msg-{i:03d}",
        "source": "gmail",
        "subject": "Your Netflix Premium Subscription Receipt",
        "sender": "receipts@netflix.com",
        "date": "2026-05-15T10:00:00Z",
        "body": "Thank you for subscribing. You paid $22.99 USD for your monthly Netflix Premium plan.",
    },
    # ... 400 total
]
```

**Distribution per 400 emails:**

| Type | Count | Purpose |
|------|-------|---------|
| Subscription (paid) | 50 | Core detection logic |
| Subscription (free) | 20 | Free service keywords |
| Payment processor | 10 | PayPal/Stripe body extraction |
| Non-subscription | 300 | Negative keyword filtering |
| Duplicates | 20 | Same message_id as above |
| Pre-seeded in DB | 10 | Already in `ProcessedEmail` |

---

## 🔄 Resume Logic Detail

```python
async def _get_resume_point(db, source, process_type):
    """
    Find the last successfully completed batch for this source.
    If the latest batch is NOT 'completed', mark it failed and return
    the previous batch's page_token. (Option A: safe rewind)
    """
    latest = await db.execute(
        select(BatchProcess)
        .where(BatchProcess.source == source)
        .where(BatchProcess.process_type == process_type)
        .order_by(BatchProcess.batch_number.desc())
        .limit(1)
    )
    latest_batch = latest.scalar_one_or_none()

    if not latest_batch:
        return None  # Fresh start

    if latest_batch.status == "completed":
        return latest_batch.page_token  # Resume from here

    # Latest batch is incomplete (crashed). Mark failed, return previous.
    latest_batch.status = "failed"
    latest_batch.error_message = (
        "Recovered from previous crash — rewinding to re-process"
    )
    await db.commit()

    previous = await db.execute(
        select(BatchProcess)
        .where(BatchProcess.source == source)
        .where(BatchProcess.process_type == process_type)
        .where(BatchProcess.status == "completed")
        .order_by(BatchProcess.batch_number.desc())
        .limit(1)
    )
    prev_batch = previous.scalar_one_or_none()
    return prev_batch.page_token if prev_batch else None
```


---

## 📊 Success Criteria

- [ ] `BatchProcess` table created and queryable
- [ ] 400 dummy emails processed in exactly 8 batches of 50
- [ ] All 8 batches show `completed` status with correct counts
- [ ] Crash after batch 3 → resume from batch 4 → final counts identical
- [ ] DB commit failure on batch 2 → batch 2 status=`failed`, batches 3+ untouched
- [ ] Verification mismatch → batch status=`failed`, pipeline halts
- [ ] Incremental sync processes only new emails, skips existing
- [ ] `/api/batch-status` returns real-time progress per source
- [ ] All existing tests (`test_fetch_classify.py`, etc.) still pass

---

## 🚀 Rollout Checklist

| Step | Action | Validation |
|------|--------|------------|
| 1 | Run `test_batch_orchestrator.py` locally | All 5 tests pass |
| 2 | Run `python sync_emails_now.py` with small limit (200 emails) | Real Composio fetch works, batches log correctly |
| 3 | Run full backfill (`/api/parse-emails`, max_results=50k) | Production DB populates, all batches `completed` |
| 4 | Verify `/api/batch-status` during run | Shows live progress |
| 5 | Set up incremental sync schedule (cron / Railway scheduler) | Runs every 3 days, only processes new emails |

---

## 📝 Notes

- **Deduplication rationale:** `ProcessedEmail` remains the global dedup source. Even though API pagination returns unique emails per batch, a crash mid-batch causes re-fetch of the same batch on resume. The PRIMARY KEY on `message_id` guarantees idempotency.
- **Batch size:** Default 50 for testing; production can use 100 (current default) or configure via env var.
- **Option A vs B:** This task implements **Option A (safe rewind)** — simpler, bulletproof, slightly slower but guaranteed correct.
- **No new dependencies:** Uses existing SQLAlchemy, asyncpg/aiosqlite, no Celery/RQ needed.

---

**Created:** May 20, 2026  
**Ready for implementation:** ✅ YES  
**Assignee:** TBD
