# 🌿 EXPERIMENTAL BRANCH GUIDE

## Created Branch: experimental/local-db-output

### Purpose
Test email parsing with local database output, avoiding Railway pollution during development.

## 🎯 Key Changes

### 1. Relaxed Parser (`email_parser_relaxed.py`)
- **Threshold:** 0.25 (was 0.35) → More matches
- **Body analysis:** First 5 sentences (was 2) → Better context
- **Spam filter:** Needs 2+ spam keywords (was 1) → Less aggressive
- **Bonuses:** More combination bonuses → Higher scores

### 2. Sequential Fetcher (`email_fetcher_fixed.py`)
- Waits for commit confirmation before next batch
- 2-second delay between batches (was 0.5s)
- Detailed per-batch logging
- Verifies data stored

### 3. Output Locations
```
experimental_subscriptions.db       ← SQLite database
experimental_results/
  ├── subscriptions_*.json         ← All detected subscriptions
  └── processed_emails_*.json      ← Sample of processed emails
```

## 🚀 Run Experiment

```bash
cd C:\_dev\subscription_manager

# Create branch (if not done yet)
git checkout -b experimental/local-db-output

# Run test
python test_experimental.py
```

## 📊 What It Does

1. Fetches 100 emails from Gmail (last 30 days)
2. Processes in batches of 20
3. Uses relaxed classifier (threshold 0.25)
4. Saves to local SQLite database
5. Exports results to JSON
6. Shows detection rate statistics

## ✅ Success Criteria

**Good result:** 5-15 subscriptions from 100 emails (5-15% detection rate)

**Expected output:**
```
📊 EXPERIMENTAL RESULTS
═══════════════════════════════════
✉️  Emails processed: 100
✅ New subscriptions: 12
⏭️  Skipped: 0
❌ Failed: 0

💾 DATABASE VERIFICATION:
   Subscriptions: 12
   Processed emails: 100
   Events: 12

✅ INTEGRITY CHECK PASSED
   All 100 emails stored in database

📈 DETECTION ANALYSIS
═══════════════════════════════════
Detection rate: 12.0%
✅ EXCELLENT: >10% detection rate
```

## 🔧 Threshold Tuning

If detection rate is:
- **>20%:** Too many false positives → Increase threshold to 0.30
- **10-20%:** Perfect range → Keep at 0.25
- **5-10%:** Good → Keep at 0.25
- **2-5%:** Low → Lower to 0.22
- **<2%:** Very low → Check if emails actually contain subscriptions

## 📝 Comparison Table

| Setting | Original | Enhanced | Relaxed (Experimental) |
|---------|----------|----------|------------------------|
| Threshold | 0.35 | 0.30 | **0.25** |
| Body analysis | Full | 2 sentences | **5 sentences** |
| Spam filter | 1 keyword | 1 keyword | **2+ keywords** |
| Combo bonus | None | 0.15 | **0.20** |
| Expected rate | 5-8% | 8-12% | **10-15%** |

## 🔄 Iteration Process

1. **Run test:** `python test_experimental.py`
2. **Check results:** Open `experimental_results/subscriptions_*.json`
3. **Review quality:** Are subscriptions real or false positives?
4. **Adjust threshold:** Edit `email_parser_relaxed.py` line 169
5. **Repeat:** Run test again with new threshold

## 📂 Files on This Branch

**New files:**
- `email_parser_relaxed.py` - Lower threshold parser
- `email_fetcher_fixed.py` - Sequential batch processor
- `test_experimental.py` - Main test runner
- `experimental_subscriptions.db` - Test database
- `experimental_results/` - Output folder

**Keep from main:**
- `database.py` - Same schema
- `email_fetcher.py` - Original (for reference)
- `email_parser.py` - Original (for reference)

## 🎯 When to Merge Back

Merge to main when:
1. ✅ Detection rate is 5-15%
2. ✅ False positive rate < 20%
3. ✅ No database commit failures
4. ✅ Processed emails table populates correctly

## 🔀 Merge Process

```bash
# Test passes on experimental branch
git add email_parser_relaxed.py email_fetcher_fixed.py
git commit -m "feat: relaxed parser + sequential batches"

# Switch to main
git checkout main

# Merge changes
git merge experimental/local-db-output

# Update main files
cp email_parser_relaxed.py email_parser.py
cp email_fetcher_fixed.py email_fetcher.py

# Test on Railway with small batch
# POST /api/parse-emails {"max_results": 200, "since_days": 30}

# If successful, deploy
git push origin main
```

## 🗑️ Clean Up

Remove experimental files:
```bash
# Delete database
rm experimental_subscriptions.db

# Delete results
rm -rf experimental_results/

# Keep branch for future experiments
git checkout main
```

## 📊 Expected Files After Run

```
C:\_dev\subscription_manager\
├── experimental_subscriptions.db (50-100 KB)
└── experimental_results/
    ├── subscriptions_20260515_150022.json (10-30 KB)
    └── processed_emails_20260515_150022.json (5-10 KB)
```

## 🎓 Key Learnings

**First 2 vs 5 sentences:**
- 2 sentences: Good for "Welcome to X" emails
- 5 sentences: Better for "Receipt from PayPal for X" emails
- **Recommendation:** Use 5 for testing, tune to 3-4 for production

**Threshold impact:**
- 0.35: Very strict, <5% detection
- 0.30: Balanced, ~8% detection
- 0.25: Relaxed, ~12% detection
- 0.20: Very relaxed, 15-20% detection (many false positives)

**Sequential batches:**
- Critical for Railway PostgreSQL
- Prevents connection pool exhaustion
- Ensures data integrity
- Slightly slower but reliable

---

Created: 2026-05-15  
Branch: experimental/local-db-output  
Purpose: Safe testing without Railway pollution
