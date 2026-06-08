# Subscription Manager — Architecture

## Stack
- **Backend**: FastAPI + SQLAlchemy async, Python 3.13
- **DB**: PostgreSQL on Railway (production), SQLite locally
- **Frontend**: Terminal-style UI — `frontend/index.html` (single file, inline JS ~900 lines). `frontend/simple.js` is orphaned — not loaded by index.html.
- **Glass UI**: `frontend_glass/` (React/Vite) — exists but deliberately set aside; only `frontend/` is active
- **Email sources**: Gmail + Outlook via Composio SDK v2, IMAP direct (Zoner/karlik@klikni.org)
- **Wallet**: BudgetBakers Wallet REST API via `wallet_fetcher.py`
- **Scheduler**: APScheduler cron — every 3 days at 19:00 UTC

## Key Files
| File | Role |
|---|---|
| `api.py` | FastAPI app, all endpoints, startup hooks |
| `database.py` | All SQLAlchemy models |
| `email_fetcher.py` | Email fetch + batch processing pipeline |
| `email_parser.py` | EmailClassifier, Group A/B scoring, keyword lists, PROVIDER_ALIASES |
| `subscription_matcher.py` | Wallet cross-reference, reconciliation flag, service_costs writer, provider_aliases seeder |
| `wallet_fetcher.py` | BudgetBakers API → financial_records upsert |
| `industry_resolver.py` | Google Places API V2 category lookup, JSON cache + DB sync |
| `scheduler.py` | APScheduler cron jobs — wallet_sync, email_sync, wallet_match, discovery_sweep |
| `notifier.py` | Gmail summary notification after each cron run |
| `fx.py` | Currency exchange rates |
| `keyword_validator.py` | Keyword validation tooling |

## Data Pipeline

```
EMAIL SOURCES (Gmail A/B groups, Outlook, IMAP)
  → email_fetcher._stream_fetch_and_process_gmail/outlook()
    → _process_email_batch()
      → EmailClassifier.classify()  [email_parser.py]
        → Group A (payment keywords) score
        → Group B (account creation keywords) score
        → Wallet cross-reference boost +0.10
        → Provider alias resolution (PROVIDER_ALIASES dict)
        → Industry resolution (Google Places API → .industry_cache.json)
      → INSERT/UPDATE: subscriptions (plan_name, status, billing_cycle, start_date)
      → INSERT: subscription_events
      → INSERT: processed_emails (dedup gate)
      → INSERT: batch_processes (per-batch telemetry)
    → UPDATE: sync_metadata (per-source run stats)
    → CALL: _recalculate_costs() → UPDATE subscriptions.cost (mode of events)
    → CALL: SubscriptionMatcher.update_service_costs() → UPSERT service_costs

WALLET (BudgetBakers MCP or REST API)
  → wallet_fetcher.WalletFetcher.sync()
    → UPSERT: financial_records
  → SubscriptionMatcher.match_all()
    → UPDATE: financial_records.matched_subscription_id
    → UPDATE: subscriptions (confirmed_by_wallet, last_payment_date, actual_cost, reconciliation_flag)
    → CALL: update_service_costs()
  → SubscriptionMatcher.detect_all_payment_types()
    → UPDATE: subscriptions.billing_cycle (monthly/yearly/adhoc from gap analysis)
```

## DB Tables (all 9)
| Table | Writer | Status |
|---|---|---|
| `subscriptions` | email_fetcher, matcher, API | ✅ core table |
| `financial_records` | wallet_fetcher | ✅ wired |
| `processed_emails` | email_fetcher | ✅ dedup gate |
| `subscription_events` | email_fetcher | ✅ payment timeline |
| `service_costs` | subscription_matcher.update_service_costs() | ✅ 3-month rolling |
| `sync_metadata` | email_fetcher.process_emails() | ✅ per-source run log |
| `batch_processes` | email_fetcher._process_email_batch() | ✅ per-batch telemetry |
| `provider_aliases` | startup seed from PROVIDER_ALIASES dict | ✅ seeded on start |
| `provider_industries` | startup sync from .industry_cache.json | ✅ synced on start |

## Subscription Model Key Fields
- `plan_name` — detected from email body (Premium, Pro, Free, Standard…)
- `reconciliation_flag` — True when |cost - actual_cost| / cost > 20%
- `confirmed_by_wallet` — 1 when matched to a financial_record
- `actual_cost` — wallet-derived flat fee (mode of matched records)
- `cost` — email-derived, recalculated as mode of subscription_events amounts
- `approval_status` — pending (wallet_discovery) → approved | dismissed

## Email Classification
- **Group A** (payment/receipt): receipt, invoice, platba, faktura, daňový doklad, etc.
- **Group B** (account creation): welcome, subscription confirmed, registrace, předplatné, etc.
- **Negative**: newsletter, discount, promo, offer, etc.
- **Score threshold**: 0.35 per group; `is_subscription = is_payment OR is_account_creation`
- **Wallet boost**: +0.10 if sender domain seen in financial_records
- **Bulk sender penalty**: -0.40 if sender subdomain is in BULK_SENDER_SUBDOMAINS (bmail., em., enews., etc.)

## API Endpoint Map (key ones)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/subscriptions` | List with pagination, filtering, sort |
| GET | `/api/stats` | Aggregated stats |
| GET | `/api/wallet-spend-map` | sub_id → spend data (sparklines) |
| GET | `/api/monthly-trend?months=3` | 3-month category spend chart data |
| GET | `/api/sync-status` | Last N sync runs from sync_metadata |
| GET | `/api/service-costs/{id}` | Rolling 3-month costs for one subscription |
| GET | `/api/events` | Subscription payment events (filterable by service_name, months) |
| POST | `/api/parse-emails` | Full backfill (since_days, max_results) |
| POST | `/api/sync-emails` | Incremental sync (default 3 days) |
| POST | `/api/sync-wallet` | Pull wallet records |
| POST | `/api/match-wallet` | Cross-reference wallet vs subscriptions |
| POST | `/api/recalculate-costs` | Rebuild cost mode + service_costs |
| POST | `/api/admin/reset-db` | DROP ALL + recreate schema |
| POST | `/api/admin/reset-batch-table` | Drop + recreate batch_processes |
| POST | `/api/admin/sync-industry-cache` | Sync .industry_cache.json → provider_industries |
| POST | `/api/admin/seed-aliases` | Seed provider_aliases from hardcoded dict |

## Frontend (index.html) Key Functions
- `loadAll()` — fetches subscriptions, wallet-spend-map, monthly-trend, sync-status in parallel
- `renderTable()` — builds the main subscription register table
- `extractPlan(sub)` — reads `sub.plan_name`, falls back to parsing `sub.notes`
- `renderMonthlyTrend(data)` — 3-month category bars in right aside (hidden until data)
- `renderSyncStatus(data)` — last 6 sync runs in right aside (hidden until data)
- `renderBurnRate()` — top 10 bar chart
- `renderAllocation()` — category allocation bars
- `recon-flag` ⚠ badge — shown on service name when `reconciliation_flag=true`

## Scheduled Jobs (APScheduler)
| Job | Schedule | What it does |
|---|---|---|
| wallet_sync | Every 3 days 19:00 UTC | Pull last 5 days of wallet records |
| email_sync | Every 3 days 19:05 UTC | Pull last 5 days of emails |
| wallet_match | Every 3 days 19:15 UTC | Cross-reference + infer billing cycles |
| discovery_sweep | Weekly Sun 07:00 UTC | Surface new recurring payees as candidates |

## Airbank Anchor Date
Earliest Airbank bank-sync record: **2026-02-24** (Air Bank v2.0 Hlavni účet).
Financial records backfill covers 2026-02-24 → today.
