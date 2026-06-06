# Subscription Manager

Tracks all subscriptions by parsing emails from Gmail, Outlook, and IMAP, then cross-referencing against real bank transactions from BudgetBakers Wallet (Airbank, Raiffeisenbank, PayPal). Deployed on Railway with PostgreSQL.

**Live**: https://mysubz.up.railway.app

---

## Architecture

```
EMAIL SOURCES                    WALLET (BudgetBakers)
Gmail (Composio)                 Airbank / RB / PayPal
Outlook (Composio)               via REST API
IMAP (Zoner/klikni.org)
        │                                │
        ▼                                ▼
email_fetcher.py              wallet_fetcher.py
  Group A queries                  paginated sync
  (payment/receipt)                    │
  Group B queries              financial_records
  (account creation)                   │
        │                    subscription_matcher.py
        ▼                      fuzzy payee match
   EmailClassifier              reconciliation flag
   email_parser.py              billing cycle inference
        │                       service_costs update
        ▼                                │
   subscriptions ◄───────────────────────┘
   subscription_events
   processed_emails
   batch_processes
   sync_metadata
        │
        ▼
  FastAPI (api.py)
  frontend/index.html
```

---

## Database Tables

| Table | Purpose | Writer |
|---|---|---|
| `subscriptions` | Core subscription records | email_fetcher, matcher, API |
| `financial_records` | Bank transactions from Wallet | wallet_fetcher |
| `processed_emails` | Dedup gate — prevents reprocessing | email_fetcher |
| `subscription_events` | Per-payment events for timeline/cost calc | email_fetcher |
| `service_costs` | Rolling 3-month spend per subscription | subscription_matcher |
| `sync_metadata` | Per-source sync run log | email_fetcher |
| `batch_processes` | Per-batch telemetry (20 emails/batch) | email_fetcher |
| `provider_aliases` | Service name normalization | seeded from code on startup |
| `provider_industries` | Google Places API category cache | synced from JSON cache on startup |

### Subscription fields
- `plan_name` — detected from email (Premium, Pro, Free, Standard…)
- `reconciliation_flag` — True when email cost vs bank cost diverge >20%
- `confirmed_by_wallet` — matched to a bank transaction
- `actual_cost` — wallet-derived flat fee
- `cost` — email-derived, recalculated as mode of all events
- `billing_cycle` — monthly/yearly/adhoc, inferred from payment gaps

---

## Email Classification

Emails are fetched in two groups, each with its own scoring context:

**Group A — Payment/Receipt** (`receipt`, `invoice`, `platba`, `faktura`, `daňový doklad`, …)
- Score threshold: 0.35 → `is_payment = True`

**Group B — Account Creation** (`welcome`, `subscription confirmed`, `registrace`, `předplatné`, …)
- Score threshold: 0.35 → `is_account_creation = True`

`is_subscription = is_payment OR is_account_creation`

Wallet cross-reference boost: +0.10 if sender domain appears in `financial_records`.

---

## Scheduled Jobs

| Job | Schedule | What |
|---|---|---|
| wallet_sync | Every 3 days 19:00 UTC | Pull last 5 days of wallet records |
| email_sync | Every 3 days 19:05 UTC | Pull last 5 days of emails |
| wallet_match | Every 3 days 19:15 UTC | Cross-reference + infer billing cycles |
| discovery_sweep | Weekly Sun 07:00 UTC | Surface unmatched recurring payees |

---

## Key API Endpoints

```
GET  /api/subscriptions          List (pagination, filter, sort)
GET  /api/stats                  Aggregated totals
GET  /api/monthly-trend          3-month spend by category
GET  /api/sync-status            Last sync run history
GET  /api/wallet-spend-map       Bank spend per subscription
GET  /api/service-costs/{id}     Rolling 3-month costs
GET  /api/wallet-candidates      Unmatched recurring payees

POST /api/parse-emails           Full/incremental email backfill
POST /api/sync-emails            Incremental email sync
POST /api/sync-wallet            Pull wallet records
POST /api/match-wallet           Cross-reference wallet vs subscriptions
POST /api/recalculate-costs      Rebuild cost mode + service_costs
POST /api/scheduler/run/{job_id} Trigger a cron job manually

POST /api/admin/reset-db         ⚠ DROP ALL + recreate schema
POST /api/admin/reset-batch-table Recreate batch_processes
POST /api/admin/sync-industry-cache Sync .industry_cache.json → DB
POST /api/admin/seed-aliases     Re-seed provider_aliases
```

---

## Full Backfill Sequence

After a clean deploy or DB wipe, run in order:

```bash
# 1. Wipe and recreate all tables
curl -X POST https://mysubz.up.railway.app/api/admin/reset-db

# 2. Pull all wallet records (Airbank anchor: 2026-02-24)
curl -X POST https://mysubz.up.railway.app/api/sync-wallet

# 3. Full email parse from anchor date
curl -X POST https://mysubz.up.railway.app/api/parse-emails \
  -H "Content-Type: application/json" \
  -d '{"since_days": 102, "max_results": 50000}'

# 4. Cross-reference wallet vs subscriptions
curl -X POST https://mysubz.up.railway.app/api/match-wallet

# 5. Rebuild costs and rolling sums
curl -X POST https://mysubz.up.railway.app/api/recalculate-costs
```

After this, the scheduler runs incremental updates every 3 days automatically.

---

## Environment Variables

```env
DATABASE_URL            # Auto-set by Railway from Postgres service
COMPOSIO_API_KEY        # Composio SDK v2
COMPOSIO_USER_ID        # default
GMAIL_ACCOUNT_ID        # Gmail account ID in Composio
OUTLOOK_ACCOUNT_ID      # Outlook account ID in Composio
OUTLOOK_USER_EMAIL      # e.g. user@outlook.com
IMAP_HOST               # e.g. mail.zoner.com
IMAP_USER               # e.g. user@klikni.org
IMAP_PASSWORD           # IMAP password
WALLET_API_TOKEN        # BudgetBakers REST API bearer token
GOOGLE_PLACES_API_KEY   # Industry detection (optional)
```

See `.env.example` for the full template.

---

## Deployment

Railway auto-deploys on push to `master`.

```bash
git push origin master
```

Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

---

## Local Development

```bash
git clone https://github.com/jardaKarlik/Subs-Manager.git
cd Subs-Manager
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
uvicorn api:app --reload
```

For frontend-only preview (no backend needed):
```bash
python -m http.server 8080 --directory frontend
# open http://localhost:8080
```
