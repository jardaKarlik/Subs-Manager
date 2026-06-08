# Transaction Modal Feature Implementation Summary

## Overview
This implementation adds clickable service icons that open a transaction history modal showing all payment events for that subscription, with mailbox source and bank record confirmation columns.

## Changes Made

### PART 1: Database Model (database.py)

✓ Added `mailbox` column to `SubscriptionEvent` class:
  - Type: `Mapped[str] = mapped_column(String(50), nullable=True)`
  - Positioned after `source_type` field
  - Nullable with no default, ensuring backward compatibility
  - Updated `to_dict()` method to include mailbox field

### PART 2: Migration Script (migrate_add_mailbox.py)

✓ Created standalone migration script supporting both SQLite and PostgreSQL:
  - Auto-detects database type from DATABASE_URL
  - Gracefully handles "column already exists" errors
  - Prints clear success/failure messages
  - Usage: `python migrate_add_mailbox.py`

### PART 3: Email Fetcher (email_fetcher.py)

✓ Updated SubscriptionEvent constructor at line 552:
  - Added `mailbox=source` parameter
  - Source values: "gmail", "outlook", "imap" (already in function scope)
  - No other changes to email_fetcher logic

### PART 4: API Endpoint (api.py)

✓ Added new endpoint: `GET /api/subscriptions/{subscription_id}/transactions`
  - Fetches all SubscriptionEvent records for the subscription
  - Fetches all FinancialRecord rows matched to the subscription
  - Implements bank confirmation matching:
    * Checks YYYY-MM month alignment
    * 30% amount tolerance: abs(bank_amt - event_amt) / max(event_amt, 1) <= 0.30
    * Fallback: zero-amount events confirmed by any same-month bank record
  - Returns comprehensive transaction history with:
    * Event details (date, amount, currency, mailbox, source_type)
    * Bank confirmation status
    * Bank details (amount, payee, account, note)
    * CZK conversion using fixed rates (CZK:1.0, EUR:25.0, USD:23.0, GBP:29.0)
  - Endpoint added to /api/health endpoint list

### PART 5: Frontend (frontend/index.html)

✓ Added modal HTML structure:
  - Full-screen overlay: `id="txn-modal"`
  - Fixed position with blur backdrop
  - Modal box with header, summary, scrollable table, footer
  - Table columns: #, DATE, AMOUNT, MAILBOX, BANK REC, PAYEE/NOTE

✓ Added CSS styling:
  - Modal overlay and visibility classes
  - Mailbox source badges (gmail red, outlook blue, imap green)
  - Bank confirmation indicators
  - Responsive table styling with hover effects

✓ Added JavaScript functions:
  - `openTransactionModal(subId, serviceName)` - Opens modal and fetches data
  - `renderTransactionModal(data)` - Renders transaction table with formatting
  - `closeTransactionModal()` - Closes modal
  - Overlay click handler - Close on background click
  - Escape key handler - Close on ESC key

✓ Updated `logoHtml()` function:
  - Added `onclick` handler on outer span element
  - Passes subscription ID and service name to modal function
  - Added `cursor:pointer` style for visual feedback
  - Properly escapes single quotes in service names

## Backward Compatibility

✓ All changes are fully backward compatible:
  - New `mailbox` column is nullable with no default
  - Existing SubscriptionEvent rows unaffected
  - New endpoint doesn't affect existing APIs
  - Email fetcher maintains all existing logic
  - Frontend changes are additive only

## Testing Checklist

After implementation, verify:

1. **Database Migration**
   - [ ] Run: `python migrate_add_mailbox.py`
   - [ ] Should show success message or "column already exists"
   - [ ] On SQLite and PostgreSQL

2. **API Endpoint**
   - [ ] Start server: `uvicorn api:app --reload`
   - [ ] Test endpoint: `curl http://localhost:8000/api/subscriptions/1/transactions`
   - [ ] Verify JSON response structure
   - [ ] Check /api/health includes new endpoint

3. **Frontend Modal**
   - [ ] Open http://localhost:8080
   - [ ] Click any service icon/logo
   - [ ] Modal should appear with loading state
   - [ ] Modal populates with transaction data
   - [ ] Close button works
   - [ ] Escape key closes modal
   - [ ] Clicking overlay closes modal
   - [ ] Date range displays correctly
   - [ ] Mailbox badges show correct colors
   - [ ] Bank confirmation indicators render

4. **Existing Features**
   - [ ] Service table renders normally
   - [ ] Filters still work
   - [ ] Sorting still works
   - [ ] Ticker still animates
   - [ ] Burn rate calculations unchanged

5. **Database**
   - [ ] New SubscriptionEvent records include mailbox field
   - [ ] Existing records unaffected
   - [ ] Bank matching logic works correctly

## Files Modified

1. `/database.py` - Added mailbox field to SubscriptionEvent
2. `/email_fetcher.py` - Pass mailbox parameter to SubscriptionEvent
3. `/api.py` - New transactions endpoint and health check update
4. `/frontend/index.html` - Modal HTML, CSS, JavaScript, and logo onclick
5. `/migrate_add_mailbox.py` - NEW: Migration script

## Deployment Notes

### Local Development
```bash
python migrate_add_mailbox.py
uvicorn api:app --reload
```

### Production (Railway)
```bash
git push origin feature/transaction-modal
railway run python migrate_add_mailbox.py
```

The migration will run against the PostgreSQL database and create the mailbox column if needed.

