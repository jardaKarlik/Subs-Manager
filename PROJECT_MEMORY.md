# 🧠 Subscription Manager - Project Memory Bank

## 📋 Project Overview
Full-stack subscription management app with dual-context email classification.
Parses 3 mailboxes (Gmail, Outlook, IMAP) using weighted keyword decision model,
cross-references with BudgetBakers Wallet financial records for accurate cost tracking.

---

## 🔑 Data Access — Prefer the Live API (default for queries)

**Rule of thumb:** When the user asks about backend data (subscriptions, events,
wallet spend, stats, health, single-record lookups), query the deployed REST API
instead of the local SQLite file or the Railway Postgres directly.

**Base URL:** `https://mysubz.up.railway.app`
**CORS:** open (`allow_origins=["*"]` in `api.py`), no auth required
**DB driver note:** The app uses `postgresql+asyncpg://` against Railway Postgres
(see `database.py:28-31`); the API normalizes everything for you.

### Quick reference — key endpoints

| Need | Endpoint | Notes |
|---|---|---|
| List/search subs | `GET /api/subscriptions?search=<q>&limit=<n>` | `search` is ILIKE on `service_name` |
| One sub by id | `GET /api/subscriptions/{id}` | |
| Update a sub | `PUT /api/subscriptions/{id}` | JSON body, partial updates |
| Payment events | `GET /api/events?service_name=<name>` | Last 12 months by default |
| Portfolio stats | `GET /api/stats` | CZK-normalized, has `data_as_of` |
| Monthly trend chart | `GET /api/monthly-trend?months=3` | Category bars for sparkline |
| Per-service rolling costs | `GET /api/service-costs/{id}` | 3-month rolling window |
| Wallet spend per service | `GET /api/wallet-spend` | Confirmed matches only |
| Wallet spend map (all) | `GET /api/wallet-spend-map` | Keyed by sub id, **access `resp.map`** |
| Last sync runs | `GET /api/sync-status` | Per-source run history |
| Health / DB status | `GET /api/health` | Confirms DB connectivity |

### Operational endpoints (POST)

| Action | Endpoint | Notes |
|---|---|---|
| Recompute all costs | `POST /api/recalculate-costs` | Mode of subscription_events amounts |
| Run wallet matching | `POST /api/match-wallet` | After pulling new wallet records |
| Backfill (admin) | `POST /api/admin/backfill?since_days=N&max_results=50000` | Async, returns immediately |
| Re-seed provider aliases | `POST /api/admin/seed-aliases` | After editing `PROVIDER_ALIASES` in code |
| Sync industry cache | `POST /api/admin/sync-industry-cache` | `.industry_cache.json` → DB |
| Wipe + recreate all tables | `POST /api/admin/reset-db` | **Redeploy between drop and recreate** |
| Reset batch_processes only | `POST /api/admin/reset-batch-table` | |

### Workflow

```bash
# 1. Always start with /api/health to confirm the DB is connected
curl -sS --max-time 30 https://mysubz.up.railway.app/api/health

# 2. Confirm DB has rows
curl -sS 'https://mysubz.up.railway.app/api/subscriptions?page_size=1'

# 3. For "show me data for X" → use the search filter
curl -sS 'https://mysubz.up.railway.app/api/subscriptions?search=sony&limit=50'

# 4. For full context → also pull stats + events + wallet-spend
curl -sS https://mysubz.up.railway.app/api/stats
curl -sS 'https://mysubz.up.railway.app/api/events?service_name=Sony'
curl -sS https://mysubz.up.railway.app/api/wallet-spend
```

### When to use the API vs. direct DB

- **Use the live API** for: any read-only query, "show me data for X", portfolio
  overviews, single-record lookups, confirming record counts, dashboards.
  Cheaper, safer, no creds to manage, always reflects the latest deployed state.
- **Fall back to direct DB** only when the API is missing the needed field
  (e.g., raw `created_at` microsecond precision, or `notes` joins). The Railway
  PostgreSQL is reachable at:
  - `postgresql://postgres:<password>@yamabiko.proxy.rlwy.net:16839/railway`
  - Password is in the Railway dashboard (not in the repo).
  - Project: `adcb3b41-6d7d-485f-97ac-2b6b95d99cb2` (was previously
    `a33c422a-3fbf-4858-8e67-bd5b1c3491d1` — see `memory/project_deploy.md`)
- **Don't bother with local SQLite** — `subscriptions.db` is not in the worktree
  and the local repro uses different data than the deployed DB.

### Discovered 2026-06-08 via Sony lookup session
The current ~62 subs live in Railway Postgres; the local repo has no
`.env`/`subscriptions.db` and no `psql`/`railway` CLI installed, so the deployed
API is the only frictionless read path.

---

## 📚 Memory Files (in-repo, canonical cross-client knowledge)

The `memory/` directory is the **source of truth** for project knowledge shared
across all Claude clients and workstations. **Read these before making non-trivial
changes.** This file (`PROJECT_MEMORY.md`) is a working memory bank built on top.

| File | What it contains |
|---|---|
| `CLAUDE.md` | Mandatory session-start protocol, MCP toolset, FX rates, anti-patterns |
| `memory/project_architecture.md` | Stack, files, 9 DB tables, data pipeline, API endpoints, scheduler |
| `memory/project_deploy.md` | Railway IDs, deploy flow, 5-step backfill sequence, env vars |
| `memory/feedback.md` | Hard-won patterns, anti-patterns, parser quirks, what to avoid |

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

### 9. Database Schema (SQLAlchemy, 9 tables — see `database.py`)

| Table | Writer | Role |
|---|---|---|
| `subscriptions` | email_fetcher, matcher, API | Core sub records |
| `financial_records` | wallet_fetcher | BudgetBakers Wallet transactions |
| `processed_emails` | email_fetcher | Dedup gate (blocks re-parse) |
| `subscription_events` | email_fetcher | Per-email payment timeline |
| `service_costs` | subscription_matcher.update_service_costs() | 3-month rolling sums per sub |
| `sync_metadata` | email_fetcher.process_emails() | Per-source run log |
| `batch_processes` | email_fetcher._process_email_batch() | Per-batch telemetry |
| `provider_aliases` | startup seed from `PROVIDER_ALIASES` dict | Alias lookup (skip canonical_name=None) |
| `provider_industries` | startup sync from `.industry_cache.json` | Google Places cache |

### 9a. Subscription Model Key Fields (gotchas)

- `plan_name` — **dedicated column now** (don't write to `notes` like the old days)
- `reconciliation_flag` — `True` when `|cost - actual_cost| / cost > 20%`
- `confirmed_by_wallet` — `1` when matched to a `financial_record`
- `actual_cost` — wallet-derived flat fee (mode of matched records); **ground truth**
- `cost` — email-derived, recalculated as mode of `subscription_events` amounts; **unreliable**
- `approval_status` — `pending` (wallet_discovery) → `approved` | `dismissed`
- `icon_url`, `next_billing_date`, `notes` — nullable, often empty

### 10. Complete REST API (FastAPI)
| Method | Endpoint | Purpose |
|--------|----------|--------|
| GET | `/api/subscriptions` | Paginated, filterable, sortable (params: `search`, `category`, `status`, `billing_cycle`, `approval_status`, `sort_by`, `sort_order`, `page`, `page_size`) |
| POST | `/api/subscriptions` | Create |
| PUT | `/api/subscriptions/{id}` | Update (partial JSON body) |
| DELETE | `/api/subscriptions/{id}` | Delete |
| GET | `/api/stats` | CZK-normalized statistics |
| GET | `/api/summary` | Backward-compatible summary |
| GET | `/api/categories` | Category breakdown |
| GET | `/api/events` | Payment timeline (params: `service_name`, `category`, `months`) |
| GET | `/api/service-costs/{id}` | Rolling 3-month costs for one sub |
| GET | `/api/monthly-trend` | Spend by month/category (top 8) |
| GET | `/api/wallet-spend` | Confirmed wallet matches per service |
| GET | `/api/wallet-spend-map` | sub_id → spend data for sparklines (**access `resp.map`**) |
| GET | `/api/sync-status` | Last sync run info per source |
| POST | `/api/parse-emails` | Full email backfill (params: `since_days`, `max_results`) |
| POST | `/api/sync-emails` | Incremental email sync (default 3 days) |
| POST | `/api/sync-wallet` | BudgetBakers Wallet sync |
| POST | `/api/match-wallet` | Cross-reference wallet → subscriptions |
| POST | `/api/recalculate-costs` | Recompute all costs from `subscription_events` mode |
| POST | `/api/subscriptions/{id}/approve` | Approve pending sub |
| POST | `/api/subscriptions/{id}/dismiss` | Dismiss pending sub |
| POST | `/api/subscriptions/bulk-approve` | Approve multiple |
| POST | `/api/subscriptions/bulk-dismiss` | Dismiss multiple |
| GET | `/api/health` | Health check |
| POST | `/api/admin/reset-db` | DROP ALL + recreate schema (**redeploy between drop and recreate**) |
| POST | `/api/admin/reset-batch-table` | Drop + recreate `batch_processes` only |
| POST | `/api/admin/sync-industry-cache` | Sync `.industry_cache.json` → `provider_industries` |
| POST | `/api/admin/seed-aliases` | Re-seed `provider_aliases` from `PROVIDER_ALIASES` dict |
| POST | `/api/admin/backfill` | Background full backfill (params: `since_days`, `max_results`) |

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

### 13. Frontend Status (which file is the real one)
- **`frontend/index.html`** — ACTIVE. Single-file SPA with inline `<script>` block (~900 lines). Edit this for all UI work.
- **`frontend/simple.js`** — **ORPHANED**. Not loaded by `index.html`. Do not edit.
- **`frontend_glass/`** — React/Vite glass UI. **Intentionally set aside.** Don't touch unless explicitly asked.
- **`frontend_glass_dist/`** — Built glass UI bundle. Inert artifact.

---

## 💰 FX Rates (KEEP IN SYNC — backend + frontend)

```
CZK: 1   EUR: 25   USD: 23   GBP: 29
```

- Backend: `api.py` → `_FX_TO_CZK`
- Frontend: `frontend/index.html` → `FX_TO_CZK`

**Change both together or amounts will silently diverge between API and UI.** The frontend's `monthly()` function prefers wallet-sourced `avg_monthly_czk`; falls back to parser `cost × FX`. The `TOTAL PAID` column uses actual wallet `total_czk` (real sum of payments), with `~estimate` for non-wallet subs.

---

## 🏗 Railway Resources (for quick dashboard navigation)

| Resource | ID |
|---|---|
| Project | `adcb3b41-6d7d-485f-97ac-2b6b95d99cb2` |
| App service | `bab29cc5-c298-427e-a8c2-19a56cbb47a1` |
| Postgres service (`Postgres-f5H6`) | `5dbe9a85-009c-4758-892c-3d270627f40b` |
| Environment (`production`) | `3301a5f3-37be-41e6-892e-81a44bb99a6a` |
| Public app URL | `https://mysubz.up.railway.app` |
| DB public URL | `postgresql://postgres:…@yamabiko.proxy.rlwy.net:16839/railway` |
| Builder | nixpacks |
| Start command | `uvicorn api:app --host 0.0.0.0 --port $PORT` |
| Deploy trigger | `git push origin master` (~2 min build) |

---

## 🔁 5-Step Backfill Sequence (after a clean deploy or DB wipe)

Run these in order:

```bash
# 1. Wipe all tables and recreate schema
POST https://mysubz.up.railway.app/api/admin/reset-db

# 2. Pull Airbank + all wallet records (covers 2026-02-24 onward)
POST https://mysubz.up.railway.app/api/sync-wallet

# 3. Full email backfill from Airbank anchor date
POST https://mysubz.up.railway.app/api/parse-emails
Body: {"since_days": <days_since_2026-02-24>, "max_results": 50000}

# 4. Cross-reference wallet records against detected subscriptions
POST https://mysubz.up.railway.app/api/match-wallet

# 5. Rebuild cost mode + service_costs rolling sums
POST https://mysubz.up.railway.app/api/recalculate-costs
```

After this, the regular scheduler handles incremental updates (every 3 days).
**Why wipe?** Existing `processed_emails` rows block re-processing. A clean DB + full re-parse applies all current parser rules to all historical emails.

**Post-parser-change variant** (don't wipe, just recompute):
```bash
POST /api/admin/seed-aliases     # re-seed after editing PROVIDER_ALIASES
POST /api/recalculate-costs     # recompute all subscription costs
```

---

## 🗓 Airbank Anchor Date

Earliest Airbank bank-sync record: **2026-02-24** (Air Bank v2.0 Hlavni účet).
Financial records backfill covers **2026-02-24 → today**.

Always verify bank-sync records are genuine before using as anchor dates:
- Check `source == "backend"` and `createdAt` matches bank-sync setup date
- Don't just trust aggregate `recordDate.min` (could be from manual import)

---

## 🛑 Local Dev Limitation (intentionally broken)

Python 3.13 has an SSL recursion bug on this machine that **breaks `pip install`**:
```
RecursionError: maximum recursion depth exceeded
```

**Workaround for local preview only** (no API):
```bash
python -m http.server 8080 --directory frontend
# Then open http://localhost:8080 (API calls will 404 — that's expected)
```

**Do not attempt `pip install` locally.** The app only runs on Railway. For any real testing, push to `master` and use the live API at `https://mysubz.up.railway.app`.

---

## 🚨 Anti-Patterns (do not repeat — from `memory/feedback.md`)

- **Never** rename an API response field without grepping all frontend consumers first
- **Never** stash-pop into a diverged master — pull clean, re-apply manually
- **Never** use `railway run python3 script.py` from Windows — targets the internal DB hostname, not the public one
- **Never** recreate DB tables in the same Railway process that dropped them — connection pool corruption. **Always redeploy between drop and recreate**
- **Never** write `plan_name` into the `notes` field — it's a dedicated column now
- **Never** trust `subscription.cost` for ground truth — wallet `total_czk` / `avg_monthly_czk` is ground truth
- **Never** access `wallet-spend-map` response directly — it wraps in `{"map": {...}}`, use `resp.map`
- **Never** expect payment-processor aliases (PayPal, Stripe) in `provider_aliases` DB table — they have `canonical_name=None` and are correctly skipped at seed time
- **Never** treat bulk-sender subdomains (`bmail.`, `em.`, `enews.`, `promo.`) as transactional — they get a -0.40 penalty. Example: `sonyeurope@bmail.sony-europe.com` is Sony **marketing**, not a subscription receipt
- **Always** check both DB and UI when auditing feature completeness — a table with no UI is "DB only", not "done"
- **Always** check Railway DB before assuming local SQLite is authoritative — Railway has the live data

### Email parser gotchas
- **Amount extraction uses 3-tier context ranking**: Tier 2 (subscription-specific: `předplatné`, recurring, auto-renew) > Tier 1 (generic billing: payment, invoice, platba) > Tier 0 (purchase-total: total, celkem)
- When an email has both a subscription line (365 CZK) and an order total (1600 CZK), the subscription line wins
- Negative keywords after discovery tuning: `ads`, `kredit` (refund), `vracena` (returned), `quota` (billing limits)

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
├── database.py               # SQLAlchemy models (9 tables)
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
├── frontend/                 # Main UI — index.html is ACTIVE, simple.js is ORPHANED
├── frontend_glass/           # React/Vite glass UI — set aside, do not touch
├── frontend_glass_dist/      # Built glass UI bundle (inert)
├── memory/                   # Cross-client knowledge (CANONICAL)
│   ├── project_architecture.md   # Stack, files, 9 DB tables, data pipeline
│   ├── project_deploy.md         # Railway IDs, deploy flow, 5-step backfill
│   └── feedback.md               # Hard-won patterns, anti-patterns, parser quirks
├── CLAUDE.md                 # Mandatory session-start protocol, MCP toolset, FX, anti-patterns
├── README.md                 # Project readme
└── PROJECT_MEMORY.md         # This file — working memory bank on top of memory/
```

---

## 🔧 Old/Removed Functionality (cleaned June 2026)

Removed ~105 files including:
- Old single-threshold classifier (`email_parser_enhanced.py`, `email_parser_relaxed.py`)
- Old SQLite-only manager (`db_manager.py`, `main.py`)
- One-time backfill/test scripts (40+ `.py` files)
- Planning/documentation artifacts (50+ `.md` files)
- Windows `.bat` files, screenshots, mockups
- Outdated architecture docs (now in `memory/`)

---

## 🚀 Deployment

**Railway**: Automatic deploy from GitHub master branch (~2 min nixpacks build).
**Local**: ⚠️ **broken** (Python 3.13 SSL recursion bug) — see "Local Dev Limitation" above.

**Environment variables (all required except `GOOGLE_PLACES_API_KEY`):**

| Var | Source |
|---|---|
| `DATABASE_URL` | Auto-set by Railway from Postgres-f5H6 service |
| `COMPOSIO_API_KEY` | Composio SDK v2 key |
| `COMPOSIO_USER_ID` | default |
| `GMAIL_ACCOUNT_ID` | Gmail account ID in Composio |
| `OUTLOOK_ACCOUNT_ID` | Outlook account ID in Composio |
| `OUTLOOK_USER_EMAIL` | e.g. `jaroslav.karlik@live.com` |
| `IMAP_HOST` | e.g. `imap.zoner.com` |
| `IMAP_USER` | e.g. `karlik@klikni.org` |
| `IMAP_PASSWORD` | IMAP password |
| `WALLET_API_TOKEN` | BudgetBakers REST API bearer token |
| `GOOGLE_PLACES_API_KEY` | (optional) for industry resolver |
| `PYTHON_VERSION` | `3.13` |
| `PORT` | Auto-set by Railway |

**On startup `api.py` automatically:**
1. Creates all DB tables (`init_db()`)
2. Seeds `provider_aliases` from hardcoded `PROVIDER_ALIASES` dict
3. Syncs `.industry_cache.json` → `provider_industries` table
4. Starts APScheduler cron jobs

---

*Last updated: 2026-06-08 | Pulled `memory/` + `CLAUDE.md` from remote; added 9-table schema, full API map, Railway IDs, FX rates, 5-step backfill, Airbank anchor, local-dev limitation, anti-patterns*
*Pipeline overhaul V2 complete (2026-06-06)*
