# 📊 Data Handling Analysis - Core Logic

## 1. How Data Flows from Email → Database

```
Email → EmailFetcher → EmailClassifier → Database
  ↓         ↓              ↓                ↓
fetch   batch of 20    classify       store if
         emails        each email     is_subscription
```

### The Process (email_fetcher.py)

**Line 371-420: `_process_email_batch()`**

1. **Dedupe:** Check if email already processed
2. **Classify:** `classifier.classify(subject, sender, body)`
3. **Mark processed:** INSERT into `processed_emails` table
4. **Store subscription:** INSERT into `subscriptions` table (if detected)
5. **Commit:** Save all changes to database

**THE PROBLEM:** Step 5 (commit) is failing silently or Step 4 (storage) isn't happening.

### Current Parsing Logic (email_parser.py)

**Decision rule:**
```python
is_subscription = (confidence >= 0.35)

confidence = 0.0
+ 0.25 if known provider (Spotify, Netflix, etc.)
+ 0.30 if keywords: invoice, receipt, subscription
+ 0.15 if amount detected: $15.99
+ 0.15 if subject has "receipt" or "invoice"
```

**Example:**
- Email: "Receipt for Your Payment to Spotify"
- Score: 0.25 (provider) + 0.15 (keywords) + 0.15 (subject) = 0.55
- Result: ✅ Stored as subscription

## 2. Why You Got 0 Subscriptions from 17k Emails

**Two possible causes:**

### A. Database writes are failing
- ProcessedEmail table is empty (17k emails not marked)
- Subscriptions table has only 14 rows (manual entries)
- Commit is failing silently

### B. Classification threshold too high
- Confidence < 0.35 for all emails
- Nothing triggers as subscription
- But ProcessedEmail table should still have 17k rows

## 3. What to Do Now

### Quick Test (5 minutes):
```bash
cd C:\_dev\subscription_manager
python test_local_parsing.py
```

This will:
- Process 50 emails locally
- Show if parsing works at all
- Tell you if it's a Railway issue or classification issue

### If it finds subscriptions locally:
→ Bug is in Railway database connection

### If it finds 0 subscriptions locally:
→ Bug is in classification threshold

## 4. The Fix

### If Railway connection issue:
**File:** `database.py` line 35
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Add this
    pool_recycle=3600,   # Add this
)
```

### If classification threshold issue:
**File:** `email_parser.py` line 400
```python
# Change from:
is_subscription = confidence >= 0.35

# To:
is_subscription = confidence >= 0.30
```

## 5. Processed Emails Table Issue

**Current state:** Railway has 0 rows in `processed_emails`

**Should have:** 17,510 rows (one per email)

**This table tracks:** Which emails we've already looked at (deduplication)

**The problem:** If this table is empty, it means database writes are failing completely.

## 6. Next Steps

1. **Run Railway queries** (see `analysis/railway_queries.sql`)
   - Check if `processed_emails` is truly empty
   - Check what the 14 subscriptions are

2. **Run local test** (`test_local_parsing.py`)
   - Proves if parsing works at all
   - Isolates Railway vs code issue

3. **Export classifications** (`export_classifications.py`)
   - Shows what confidence scores emails get
   - Helps tune threshold if needed

---

## Quick Reference

**Files that matter:**
- `email_fetcher.py` line 371-420: Batch processor (stores to DB)
- `email_parser.py` line 280-410: Classification logic
- `database.py` line 35-40: Database connection

**Tables:**
- `subscriptions`: Main data (14 rows)
- `processed_emails`: Dedup tracker (0 rows - BUG)
- `subscription_events`: Timeline (unknown rows)

**The bug is likely:** Line 415 in `email_fetcher.py` - `await db.commit()` is failing
