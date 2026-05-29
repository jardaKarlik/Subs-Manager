# 🚀 QUICK START - Experimental Test

## For Windows Users

### Option 1: Double-Click (Easiest)
1. Navigate to `C:\_dev\subscription_manager\`
2. Double-click `RUN_EXPERIMENTAL.bat`
3. Press any key when prompted
4. Wait for test to complete

### Option 2: Command Prompt
```cmd
cd C:\_dev\subscription_manager
python run_experimental.py
```

### Option 3: PowerShell
```powershell
cd C:\_dev\subscription_manager
python run_experimental.py
```

## What It Does

1. ✅ Creates git branch: `experimental/local-db-output`
2. ✅ Fetches 100 emails from Gmail
3. ✅ Classifies with relaxed threshold (0.25)
4. ✅ Saves to `experimental_subscriptions.db`
5. ✅ Exports to `experimental_results/subscriptions_*.json`

## Expected Output

```
🧪 EXPERIMENTAL BRANCH TEST
════════════════════════════════════════
🎯 Goal: Maximum DB inserts for testing
📂 Database: experimental_subscriptions.db
📂 Results: experimental_results/
════════════════════════════════════════

⚙️  Configuration:
   - Confidence threshold: 0.25 (was 0.35)
   - Body analysis: First 5 sentences (was 2)
   - Spam filter: Less aggressive
   - Sequential batches: 2-second delay

📧 Starting email fetch...
   Source: Gmail
   Max emails: 100
   Time range: Last 30 days

📦 Batch #1: Processing 20 emails
  After deduplication: 20 unique emails
  ✅ Netflix: 15.99 USD (conf=0.75)
  ✅ Spotify: 9.99 USD (conf=0.70)
  💾 Committing to database...
  ✅ Commit successful! Verified 20/20 emails stored

... (continues for all batches)

📊 EXPERIMENTAL RESULTS
════════════════════════════════════════
✉️  Emails processed: 100
✅ New subscriptions: 12
⏭️  Skipped: 0
❌ Failed: 0

💾 DATABASE VERIFICATION:
   Subscriptions: 12
   Processed emails: 100
   Events: 12

✅ INTEGRITY CHECK PASSED
```

## Output Files

After running, check these locations:

```
C:\_dev\subscription_manager\
├── experimental_subscriptions.db       (Your test database)
└── experimental_results\
    ├── subscriptions_20260515_150022.json
    └── processed_emails_20260515_150022.json
```

## Open Results

### View JSON (Windows)
```cmd
notepad experimental_results\subscriptions_*.json
```

### View Database (if you have sqlite3)
```cmd
sqlite3 experimental_subscriptions.db
sqlite> SELECT * FROM subscriptions;
sqlite> .quit
```

### Open in Excel
- Right-click `subscriptions_*.json`
- Open with Excel (it can import JSON)

## Troubleshooting

### "Not a git repository"
This is OK! The script will initialize git automatically.

### "Python not found"
Make sure Python is in your PATH or use full path:
```cmd
C:\Users\jaros\AppData\Local\Python\pythoncore-3.14-64\python.exe run_experimental.py
```

### "No module named 'database'"
You're in the wrong directory. Make sure you're in:
```cmd
cd C:\_dev\subscription_manager
```

### "Composio connection failed"
Check your `.env` file has:
```
COMPOSIO_API_KEY=ak_3IvGhy75...
GMAIL_USER_EMAIL=j.karleek@gmail.com
```

## Next Steps

### If you get 10+ subscriptions:
✅ Success! The fixes work.

1. Review `experimental_results/subscriptions_*.json`
2. Check for false positives
3. If quality is good, merge to main
4. Deploy to Railway

### If you get 0-5 subscriptions:
⚠️ Need more tuning.

1. Run: `python test_enhanced_parser.py`
2. Open the CSV, check confidence scores
3. Lower threshold to 0.22 in `email_parser_relaxed.py`
4. Run test again

## Return to Main Branch

```cmd
cd C:\_dev\subscription_manager
git checkout main
```

Or just delete the experimental files:
```cmd
del experimental_subscriptions.db
rmdir /s experimental_results
```

---

**Created:** 2026-05-15  
**For:** Windows users  
**Purpose:** Easy experimental testing
