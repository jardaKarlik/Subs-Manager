# 📊 Subscription Manager - Data Architecture & Mapping

## Executive Summary

This document maps the complete data flow from email sources → email parser → database → frontend UI. It identifies gaps between what's available and what's needed, providing a blueprint for proper implementation.

---

## 1. Data Sources & What They Provide

### 1.1 Email Sources (via Composio MCP)

**Gmail (Primary & Secondary)**
- Method: Composio MCP `GMAIL_FETCH_EMAILS` + `GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID`
- Available fields:
  - `subject`: Email subject line
  - `sender`: From address
  - `date`: Email date
  - `body`: Email body text (extracted from text/plain or text/html)
  - `message_id`: Gmail message ID

**Outlook (via Composio)**
- Method: Composio MCP `OUTLOOK_FETCH_EMAILS`
- Same fields as Gmail

**IMAP (Third mailbox)**
- Method: Direct IMAP protocol
- Same fields as above

---

## 2. Email Parser Output

### 2.1 Classification Result

The `EmailClassifier.classify()` method returns:

```python
{
    "is_subscription": bool,           # Confidence >= 0.35
    "confidence": float,                # 0.0 to 1.0
    "service_name": str,                # Extracted or matched name
    "category": str,                    # cloud, dev_tools, ai, streaming, music, design, productivity, security, other
    "cost": float,                      # Extracted amount or 0
    "currency": str,                    # USD, EUR, etc (defaults to USD)
    "billing_cycle": str,               # monthly, yearly, or extracted value
    "is_free": bool,                    # Free service indicator
    "source_type": str,                 # email, payment_processor, czech_bank
    "reasons": list,                    # Debug reasons for classification
}
```

### 2.2 Data Extraction

The parser extracts from emails:
- ✅ Service name (from sender domain or body)
- ✅ Category (from KNOWN_PROVIDERS mapping)
- ✅ Cost (regex: extracts currency amounts)
- ✅ Currency (defaults to USD)
- ✅ Billing cycle (monthly/yearly detection from text)

**Missing/Not Extracted:**
- ❌ `plan_name` (e.g., "Pro", "Standard", "Family")
- ❌ `start_date` (subscription start date)
- ❌ `next_billing_date` (next charge date)
- ❌ `icon_url` (service icon)
- ❌ `notes` (additional info)

---

## 3. Database Schema

### 3.1 Subscriptions Table

```python
class Subscription(Base):
    id: int                          # Primary key, auto-increment
    service_name: str                # e.g., "Netflix", "GitHub Pro"
    category: str                    # cloud, dev_tools, etc.
    cost: float                      # Monthly/yearly amount
    currency: str                    # USD, EUR, etc. (default: USD)
    billing_cycle: str               # monthly, yearly, or other
    status: str                      # active, idle, cancelled (default: active)
    start_date: str                  # ISO format YYYY-MM-DD (nullable)
    next_billing_date: str           # ISO format YYYY-MM-DD (nullable)
    notes: str                       # Free text (nullable)
    source: str                      # gmail, outlook, imap, manual, test
    icon_url: str                    # URL to service icon (nullable)
    created_at: datetime             # Auto-timestamp
    updated_at: datetime             # Auto-timestamp
```

**Status:** Database schema supports all needed fields ✅

### 3.2 Supporting Tables

**ProcessedEmail** - Deduplication tracking
```python
message_id: str                      # Unique identifier per source
source: str                          # gmail, outlook, imap
processed_date: datetime             # When it was processed
```

**SubscriptionEvent** - Time-series tracking for spending trends
```python
subscription_id: int
service_name: str
category: str
amount: float
currency: str
billing_cycle: str
event_date: datetime
source_type: str
message_id: str
created_at: datetime
```

---

## 4. Frontend UI Data Requirements

### 4.1 Service Data Structure (from b751b547-0f44-4986-958a-35765ec7e457.js)

```javascript
{
  id: string,                        // Unique identifier
  name: string,                      // Display name (service_name)
  mono: string,                      // 2-char abbreviation (e.g., "NF" for Netflix)
  color: string,                     // Hex color (#7aa9ff, #ff6b1a, etc.)
  cat: string,                       // Category (cloud, dev_tools, ai, etc.)
  plan: string,                      // Plan type (Pro, Standard, Family, etc.)
  monthly: float,                    // Monthly cost in USD
  billing: string,                   // Capitalized (Monthly, Yearly)
  usage: float,                      // 0-1 range (how much is being used)
  since: string,                     // YYYY-MM format (subscription start)
  status: string                     // active, idle
}
```

### 4.2 UI Expectations vs Database Reality

| UI Field | DB Source | Current Status | Issue |
|----------|-----------|-----------------|-------|
| `id` | subscription.id | ✅ Available | Direct mapping |
| `name` | subscription.service_name | ✅ Available | Direct mapping |
| `mono` | Generated from name | ✅ Works | `service_name.substring(0,2).toUpperCase()` |
| `color` | Category-based mapping | ✅ Available | Hardcoded in app.js `getServiceColor()` |
| `cat` | subscription.category | ✅ Available | Direct mapping |
| `plan` | ❌ NOT IN DB | ❌ **MISSING** | Hardcoded to "Standard" in app.js |
| `monthly` | subscription.cost | ⚠️ Partial | Needs billing_cycle conversion |
| `billing` | subscription.billing_cycle | ✅ Available | Need capitalization |
| `usage` | ❌ NOT TRACKED | ❌ **MISSING** | Currently random 0.2-1.0 |
| `since` | subscription.start_date | ❌ Not populated | Parser doesn't extract |
| `status` | subscription.status | ✅ Available | Direct mapping |

---

## 5. Data Flow Gaps & Solutions

### Gap 1: Plan Type Not Available
**Problem:** UI expects `plan` field (Pro, Standard, Family, etc.), but:
- Email parser doesn't extract plan from emails
- Database has no plan_name field
- UI hardcodes to "Standard"

**Solution Options:**
1. **Add `plan_name` field to Subscription table** (recommended for future)
2. **Update email parser** to extract plan from body text (e.g., "Spotify Family", "GitHub Pro")
3. **Keep hardcoded** for now, but mark as TODO

**Recommended Action:** Extract from email body when available, fallback to "Standard"

---

### Gap 2: Monthly Cost Calculation
**Problem:** Database stores cost + billing_cycle separately, UI needs calculated monthly amount

**Current Transformation:**
```javascript
monthly: parseFloat(sub.cost) || 0,  // Takes cost as-is, ignores billing_cycle
```

**Issue:** If billing_cycle is "yearly", cost should be divided by 12 for monthly display

**Solution:**
```javascript
function calculateMonthly(cost, billing_cycle) {
  if (billing_cycle === 'yearly') {
    return cost / 12;
  } else if (billing_cycle === 'monthly') {
    return cost;
  } else {
    return cost; // Default to cost as-is
  }
}

// In transformSubscriptionData:
monthly: calculateMonthly(sub.cost, sub.billing_cycle)
```

---

### Gap 3: Start Date Not Populated from Emails
**Problem:**
- Email parser doesn't extract start date from email content
- Database field exists but remains NULL
- UI fallback: `'2023-01'` (hardcoded)
- Result: All subscriptions show same generic start date

**Solution:**
1. **Extract from email headers:** Email date ≈ notification date (use as start_date)
   ```python
   # In email_fetcher.py process_emails():
   start_date = datetime.fromisoformat(email['date']).strftime('%Y-%m-%d')
   new_sub.start_date = start_date
   ```

2. **Or: Extract from body text** (pattern matching for "since date")
3. **Or: Manual entry** via UI for imported subscriptions

**Recommended:** Use email date as start_date for email-sourced subscriptions

---

### Gap 4: Usage Tracking Not Implemented
**Problem:**
- UI expects `usage` field (0-1 range)
- Database has no usage tracking
- Currently generates random value (Math.random() * 0.8 + 0.2)

**Solution:**
1. **Track via SubscriptionEvent table:** Count events per month
2. **Calculate usage:** % of expected usage based on billing cycle
3. **Or: Skip for MVP:** Keep random for demo purposes

**Recommended for MVP:** Keep random, plan SubscriptionEvent tracking for v2

---

### Gap 5: No Icon URLs
**Problem:**
- UI displays service icons (colorful "NF", "SP", etc.)
- Database has icon_url field but never populated
- UI currently uses category color + text abbreviation

**Solution:**
1. **Manual mapping:** Create icon_url mapping in frontend
2. **CDN icons:** Host icons for each service (FontAwesome, custom SVGs)
3. **Service logos API:** Use service's own logo where available

**Recommended:** Use category colors (working now) + text abbreviations

---

## 6. Revised Data Transformation Pipeline

### 6.1 Email → Database

```python
# In email_fetcher.py process_emails()

classification = self.classifier.classify(...)

# Extract/enhance data
start_date = datetime.fromisoformat(email['date']).strftime('%Y-%m-%d')
plan_name = extract_plan_from_body(email['body']) or 'Standard'

# Create subscription
new_sub = Subscription(
    service_name=classification["service_name"],
    category=classification["category"],
    cost=classification["cost"],
    currency=classification["currency"],
    billing_cycle=classification["billing_cycle"],
    status="active",
    start_date=start_date,           # NEW: From email date
    notes=f"Plan: {plan_name}",      # NEW: Store plan info
    source=email["source"],
)
```

### 6.2 Database → Frontend

```javascript
// In frontend/app.js transformSubscriptionData()

function calculateMonthly(cost, billing_cycle) {
  if (billing_cycle?.toLowerCase() === 'yearly') {
    return cost / 12;
  }
  return cost || 0;
}

function extractPlan(notes) {
  // Parse plan from notes field if available
  // e.g., "Plan: Pro" → "Pro"
  if (!notes) return 'Standard';
  const match = notes.match(/Plan:\s*(\w+)/);
  return match ? match[1] : 'Standard';
}

function transformSubscriptionData(backendSubs) {
  return backendSubs.map(sub => ({
    id: sub.id.toString(),
    name: sub.service_name,
    mono: sub.service_name.substring(0, 2).toUpperCase(),
    color: getServiceColor(sub.category),
    cat: sub.category,
    plan: extractPlan(sub.notes),           // NEW: Extract from notes
    monthly: calculateMonthly(sub.cost, sub.billing_cycle),  // NEW: Calculate
    billing: (sub.billing_cycle || 'monthly').charAt(0).toUpperCase() + 
             (sub.billing_cycle || 'monthly').slice(1),
    usage: Math.random() * 0.8 + 0.2,       // TODO: Implement proper tracking
    since: sub.start_date || '2023-01',     // NEW: Use actual start_date
    status: sub.status || 'active'
  }));
}
```

---

## 7. Implementation Roadmap

### Phase 1: Quick Fix (Today)
- ✅ Fix port mismatch (8000 vs 8001)
- ✅ Verify API endpoints work
- ✅ Fix transformSubscriptionData() mapping
- ✅ Test with existing test data

### Phase 2: Data Enrichment (This Week)
- Add start_date extraction from email date
- Add plan extraction from email body
- Update database records with historical data
- Test email parsing with real emails

### Phase 3: Composio Integration (Next)
- Verify Composio MCP tools work
- Test email fetching from all 3 sources
- Implement classification scoring review
- Process real email backfill

### Phase 4: Advanced Features (Later)
- Usage tracking via SubscriptionEvent
- Icon URL mapping/CDN integration
- next_billing_date extraction
- Payment history analytics

---

## 8. Testing Checklist

### Backend Tests
- [ ] Email parser classifies test emails correctly
- [ ] Database stores all required fields
- [ ] /api/subscriptions returns proper schema
- [ ] /api/stats calculates correctly with monthly vs yearly costs

### Frontend Tests
- [ ] transformSubscriptionData() handles all fields
- [ ] calculateMonthly() returns correct values
- [ ] Services display with correct start dates
- [ ] Plan names appear correctly
- [ ] Stats match database totals

### Integration Tests
- [ ] Add test subscription via manual entry
- [ ] Parse test email with known subscription
- [ ] Verify UI displays matching data
- [ ] Cost calculations match stats endpoint

---

## 9. Database Field Reference

### Current Fields (Populated)
```
id, service_name, category, cost, currency, billing_cycle, status, source, created_at, updated_at
```

### Optional Fields (Nullable)
```
start_date - To be populated from email date
next_billing_date - For future billing reminders
notes - For plan info, special notes
icon_url - For service icons
```

### Not Currently Used
```
None - all fields have a purpose
```

---

## 10. Composio MCP Integration Points

### Current Usage in email_fetcher.py

```python
# Line 42-54: GMAIL_FETCH_EMAILS
result = await use_mcp_tool(
    "COMPOSIO_MULTI_EXECUTE_TOOL",
    {
        "tools": [{
            "tool_slug": "GMAIL_FETCH_EMAILS",
            "arguments": {
                "max_results": max_results,
                "query": f"after:{self._format_gmail_date(since_days)}"
            }
        }],
        "sync_response_to_workbench": False
    }
)

# Line 62-71: GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID
detail = await use_mcp_tool(
    "COMPOSIO_MULTI_EXECUTE_TOOL",
    {
        "tools": [{
            "tool_slug": "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
            "arguments": {"message_id": message_id}
        }],
        "sync_response_to_workbench": False
    }
)
```

### What's Available from Composio
- ✅ Email list fetching (subject, sender, date, ID)
- ✅ Full message content (body, headers)
- ✅ Multi-source (Gmail, Outlook)
- ✅ Date-based filtering
- ✅ Message search

### What's NOT Available
- ❌ Plan type detection (raw email only)
- ❌ Payment processing details (unless in email body)
- ❌ Billing cycle certainty (must infer from patterns)

---

## 11. Next Steps

1. **Run Diagnostic Dashboard** (`http://localhost:3000/diagnostic.html`)
   - Verify backend connectivity
   - Check database status
   - Identify any immediate issues

2. **Test Current Data Flow**
   - Add test data via `/api/add-test-data`
   - View in frontend at `/index.html`
   - Check console for errors

3. **Implement Enhancements**
   - Update transformSubscriptionData() with Gap fixes
   - Add start_date extraction in email parser
   - Test with sample emails

4. **Verify with Real Data**
   - Configure .env with real email credentials
   - Run initial email parsing
   - Review detected subscriptions
   - Adjust detection confidence thresholds if needed

5. **Schedule Recurring Sync**
   - Set up daily/weekly email sync job
   - Implement incremental updates
   - Add error handling for edge cases

---

## Appendix: Service Categories

```python
CATEGORIES = {
    'cloud': ['AWS', 'Google Cloud', 'Azure', 'Vercel', 'Heroku', ...],
    'dev_tools': ['GitHub', 'Linear', 'Figma', 'Notion', 'Docker', ...],
    'ai': ['OpenAI', 'Anthropic', 'Midjourney', 'ElevenLabs', ...],
    'streaming': ['Netflix', 'Disney+', 'Apple TV+', 'Max', ...],
    'music': ['Spotify', 'Apple Music', 'Tidal', 'Bandcamp', ...],
    'design': ['Adobe', 'Figma', 'Canva', ...],
    'productivity': ['Notion', 'Slack', 'Linear', ...],
    'security': ['1Password', 'Bitwarden', ...],
    'music_tools': ['Ableton', 'Serato', 'Traktor', ...],
    'gaming': [Games & gaming services],
    'other': [Everything else]
}
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-11  
**Status:** Ready for Implementation
