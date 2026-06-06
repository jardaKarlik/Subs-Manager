# 🧠 Subscription Manager - Project Memory Bank

## 📋 Project Overview
Full-stack subscription management app with dual-context email classification.
Parses 3 mailboxes (Gmail, Outlook, IMAP) using weighted keyword decision model,
cross-references with BudgetBakers Wallet financial records for accurate cost tracking.

---

## ✅ Completed Features (V2 — June 2026)

### 1. Dual-Context Email Classification
- **Group A (Payment Confirmations)**: receipt, invoice, payment, billing, charge, purchas*, etc.
- **Group B (Account Creations)**: welcome, registration, subscription confirmed, your account, etc.
- Independent weight contexts — never mixed. A "Welcome + payment" email runs both contexts separately.
- Weighted keyword decision model with configurable thresholds (default 0.35)
- Negative keyword penalties for marketing/spam (offer, discount, sale, newsletter, etc.)
- Extended Czech language support (faktura, platba, úhrada, registrace, předplatné, etc.)

### 2. Email Fetching with Targeted Search
- **Group A queries**: subject:(receipt OR invoice OR payment OR billing OR purchas*)
- **Group B queries**: subject:("welcome to" OR "your account" OR registration OR "sign up")
- Results deduplicated across groups, each email tagged with its search_group
- Streaming batch processor (20 emails/batch, commits after each batch)

### 3. Provider Name Deduplication (200+ aliases)
- Matched via **full @domain** sender check (e.g., `sony@txn-email03.playstation.com` → Sony)
- Google → google, gmail, youtube, googlecloud, googleworkspace, googleone, googleplay
- Microsoft → microsoft, office, office365, azure, xbox, live, outlook, linkedin, skype
- Apple → apple, icloud, appleid, applemusic, appletv, appstore, itunes
- Amazon → amazon, aws, primevideo, audible, kindle, twitch, amazonpay, amazonmusic
- Payment processors (PayPal, Stripe) resolved to actual service from body text

### 4. Service Variant Detection
- Google → Google Cloud, Google One, YouTube Premium, YouTube Music, Google Workspace
- Microsoft → Microsoft 365, Azure, OneDrive, Xbox Game Pass, LinkedIn Premium
- Apple → iCloud, Apple Music, Apple TV, Apple Arcade, Apple One
- Amazon → AWS, Prime Video, Amazon Music, Audible, Kindle Unlimited

### 5. Amount Extraction
- Multi-currency (USD, EUR, GBP, CZK) with regex patterns
- Scores candidates by proximity to billing keywords (total, amount, charged)
- MAX_COST sanity caps per currency

### 6. Industry Detection (Google Places API V2)
- `industry_resolver.py` — queries `places:searchText` endpoint
- Maps Google Places types to subscription categories (cloud, streaming, ai, etc.)
- Results cached locally (`.industry_cache.json`, 30-day TTL)

### 7. Payment Type Detection (Wallet Recurrence)
- `detect_payment_type()` in `subscription_matcher.py`
- Analyzes wallet financial records: same amount at 25-35 day gaps → monthly
- 350-380 day gaps → yearly; otherwise → ad-hoc. No other variants.

### 8. Plan & Status Detection
- **Plan**: Premium, Professional, Enterprise, Free, Student, Family, Ultimate, Plus
- **Status**: active, cancelled, expired, trial — detected from email body signals

### 9. Database Schema (SQLAlchemy, SQLite/PostgreSQL)
- `Subscription` — service_name, category, cost, currency, billing_cycle, status, start_date, plan_name, etc.
- `FinancialRecord` — BudgetBakers Wallet transactions
- `ProcessedEmail` — deduplication tracker
- `SubscriptionEvent` — payment timeline
- `ServiceCost` — cumulative total + rolling 3-month sums
- `SyncMetadata` — sync run tracking per source
- `ProviderAlias` — extensible alias lookup table
- `ProviderIndustry` — cached Google Places results

### 10. Complete REST API (FastAPI)
| Method | Endpoint | Purpose |
|--------|----------|--------|
| GET | `/api/subscriptions` | Paginated, filterable, sortable |
| POST | `/api/subscriptions` | Create |
| PUT | `/api/subscriptions/{id}` | Update |
| DELETE | `/api/subscriptions/{id}` | Delete |
| GET | `/api/stats` | CZK-normalized statistics |
| GET | `/api/summary` | Backward-compatible summary |
| GET | `/api/categories` | Category breakdown |
| GET | `/api/events` | Payment timeline |
| POST | `/api/parse-emails` | Full email backfill |
| POST | `/api/sync-emails` | Incremental email sync |
| GET | `/api/monthly-trend` | Spend by month/category (top 8) |
| GET | `/api/service-costs/{id}` | Per-service rolling costs |
| GET | `/api/sync-status` | Last sync run info |
| POST | `/api/sync-wallet` | BudgetBakers Wallet sync |
| POST | `/api/match-wallet` | Cross-reference wallet → subscriptions |
| POST | `/api/subscriptions/{id}/approve` | Approve pending sub |
| POST | `/api/subscriptions/{id}/dismiss` | Dismiss pending sub |
| GET | `/api/health` | Health check |

### 11. Scheduled Jobs (APScheduler)
- Every 3 days at 19:00 UTC — wallet sync (5-day overlap)
- Every 3 days at 19:05 UTC — email sync (5-day overlap)
- Every 3 days at 19:15 UTC — wallet match + billing cycle inference
- Weekly Sunday 07:00 UTC — discovery sweep for unmatched payees

### 12. Frontend
- Dark theme with glass morphism, Space Grotesk + JetBrains Mono fonts
- Subscription grid with category gradients, hover effects
- Stats panel: monthly/yearly totals, active/idle counts, category allocation
- Approval workflow for pending wallet discoveries

---

## 📊 Mailbox Validation Results (June 2026)

### Gmail (115 emails, last 3 months)
| Category | Count | % |
|----------|-------|---|
| Group A (payments) | 99 | 86.1% |
| Group B (account creations) | 16 | 13.9% |
| Both | 0 | 0% |
| Skip (noise) | 0 | 0% |

Top senders: PayPal (50), Anthropic (14), Google (12), Facebook/Meta (10), PlayStation (8)

### Outlook (100 emails, last 3 months)
99% correctly filtered as marketing/newsletters. 1% purchase confirmation.

### Tuning Applied
Negative keywords added after discovery: "ads", "kredit" (refund), "vracena" (returned), "quota" (billing limits)

---

## 🗂️ File Structure (cleaned June 2026)

```
subs-manager/
├── api.py                    # FastAPI backend (all endpoints)
├── database.py               # SQLAlchemy models (8 tables)
├── email_fetcher.py          # Email fetching with Group A/B queries
├── email_parser.py           # Dual-context classifier (weighted keywords)
├── fx.py                     # Currency conversion (USD + CZK)
├── scheduler.py              # APScheduler cron jobs
├── subscription_matcher.py   # Wallet cross-reference + payment type detection
├── wallet_fetcher.py         # BudgetBakers API sync
├── notifier.py               # Email notification for job results
├── industry_resolver.py      # Google Places API V2 industry detection
├── keyword_validator.py      # Mailbox discovery tool
├── requirements.txt          # Python dependencies
├── Procfile                  # Railway deployment
├── railway.toml              # Railway config
├── alembic.ini / alembic/    # DB migrations
├── frontend/                 # Main UI (index.html + app.js)
├── frontend_glass/           # New glass-morphism UI
├── frontend_glass_dist/      # Built frontend for deployment
├── README.md                 # This file
└── PROJECT_MEMORY.md         # Extended project memory
```

---

## 🔧 Old/Removed Functionality (cleaned June 2026)

Removed ~105 files including:
- Old single-threshold classifier (`email_parser_enhanced.py`, `email_parser_relaxed.py`)
- Old SQLite-only manager (`db_manager.py`, `main.py`)
- One-time backfill/test scripts (40+ `.py` files)
- Planning/documentation artifacts (50+ `.md` files)
- Windows `.bat` files, screenshots, mockups
- Outdated architecture docs (all now in this file)

---

## 🚀 Deployment

**Railway**: Automatic deploy from GitHub master branch.
**Local**: `uvicorn api:app --host 0.0.0.0 --port 8000`

Environment required:
- `COMPOSIO_API_KEY` — Composio SDK key
- `GMAIL_ACCOUNT_ID` — Composio Gmail connection
- `OUTLOOK_ACCOUNT_ID` — Composio Outlook connection
- `IMAP_SERVER/USER/PASSWORD` — IMAP mailbox
- `WALLET_API_TOKEN` — BudgetBakers REST API token
- `GOOGLE_PLACES_API_KEY` — (optional) for industry resolver

---

*Last updated: 2026-06-06 | Pipeline overhaul V2 complete*
