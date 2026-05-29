# 📂 Data Storage Locations - Quick Reference

## Local Testing Files

### SQLite Databases
```
C:\_dev\subscription_manager\
├── test_subscriptions_fixed.db      ← Main test database (sequential batches)
├── test_subscriptions.db            ← Original test database
└── experimental_subs.db             ← Experimental branch database
```

**Schema (all databases):**
- `subscriptions` table: Your detected subscriptions
- `processed_emails` table: Dedup tracker (message IDs)
- `subscription_events` table: Payment timeline

**View with:**
```bash
sqlite3 test_subscriptions_fixed.db
sqlite> .tables
sqlite> SELECT COUNT(*) FROM subscriptions;
sqlite> SELECT * FROM subscriptions LIMIT 5;
sqlite> .quit
```

### Output Folder
```
C:\_dev\subscription_manager\test_results\
├── subscriptions_20260515_143022.json          ← Detected subscriptions
├── processed_emails_sample_20260515_143022.json ← Sample of processed emails
├── classifications_enhanced_20260515_143500.csv ← Full classification results
└── classifications_20260515_144000.csv          ← Original classifier results
```

### Analysis Folder
```
C:\_dev\subscription_manager\analysis\
├── QUICK_SUMMARY.md              ← Core logic explanation
├── DATA_FLOW_ANALYSIS.md         ← Complete technical deep-dive
└── railway_queries.sql           ← SQL queries for Railway database
```

## Railway Production Database

**Location:** Railway PostgreSQL (cloud)  
**Connection:** `railway connect postgres`

**Tables:**
- `subscriptions`: 14 rows currently
- `processed_emails`: 0 rows (bug - should be 17,510)
- `subscription_events`: Unknown (need to query)

## Test Scripts Output

### `test_local_with_fixes.py`
**Creates:**
- `test_subscriptions_fixed.db`
- `test_results/subscriptions_*.json`
- `test_results/processed_emails_sample_*.json`

**Console output:**
- Per-batch processing logs
- Commit confirmations
- Final verification

### `test_enhanced_parser.py`
**Creates:**
- `test_results/classifications_enhanced_*.csv`

**Console output:**
- Classification statistics
- Detection breakdown by type
- Top detected services

### `export_classifications.py` (original)
**Creates:**
- `classifications_*.csv` (in root folder)

**Console output:**
- Basic classification stats

## File Sizes (Approximate)

| File | Expected Size | Notes |
|------|---------------|-------|
| test_subscriptions_fixed.db | 50-100 KB | For 50 emails |
| subscriptions_*.json | 5-20 KB | Depends on detection count |
| classifications_*.csv | 50-200 KB | 100 emails = ~150 KB |
| railway_queries.sql | 5 KB | SQL query file |
| DATA_FLOW_ANALYSIS.md | 50 KB | Documentation |

## Quick Commands

### Run tests:
```bash
cd C:\_dev\subscription_manager

# Test fixed fetcher (creates DB + JSON)
python test_local_with_fixes.py

# Test enhanced parser (creates CSV)
python test_enhanced_parser.py

# Original export (creates CSV)
python export_classifications.py
```

### View results:
```bash
# Open database
sqlite3 test_subscriptions_fixed.db

# View JSON
cat test_results/subscriptions_*.json

# Open CSV in Excel
start test_results/classifications_enhanced_*.csv
```

### Clean up:
```bash
# Remove test databases
rm *.db

# Remove test results
rm -rf test_results/

# Keep only source code
git clean -fdx
```

## What Each File Contains

### Databases (*.db)
- Full relational data
- All three tables populated
- Can be queried with SQL
- Easy to inspect relationships

### JSON Files
- Subscription data export
- Human-readable
- Easy to share/compare
- Good for validation

### CSV Files  
- Individual email classifications
- Confidence scores per email
- Good for analysis in Excel
- Helps tune thresholds

## Data Flow Summary

```
Email → Fetcher → Classifier → Database → Export
  ↓        ↓          ↓           ↓          ↓
Gmail   Batch 20   Analyze    SQLite    JSON/CSV
        ↓                        ↓
    Commit confirmed        Verified
        ↓
    Next batch
```

## Important Notes

1. **Local databases are temporary** - For testing only
2. **test_results/ folder** - Safe to delete, regenerated on each run
3. **Railway database** - Production data, handle carefully
4. **CSV files** - Best for understanding what classifier decides
5. **JSON files** - Best for understanding final stored data

## Next Steps After Testing

If local test succeeds (finds subscriptions):
1. Review `test_results/subscriptions_*.json`
2. Compare with `test_results/classifications_*.csv`
3. Update main `email_fetcher.py` with fixes from `email_fetcher_fixed.py`
4. Update main `email_parser.py` with logic from `email_parser_enhanced.py`
5. Deploy to Railway

If local test fails (0 subscriptions):
1. Check `test_results/classifications_*.csv`
2. Look at confidence scores
3. Adjust threshold or keywords
4. Re-run test
