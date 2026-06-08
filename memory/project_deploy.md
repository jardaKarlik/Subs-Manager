# Deploy & Backfill Playbook

## Railway Setup
- **Project**: subscription-manager (id: adcb3b41-6d7d-485f-97ac-2b6b95d99cb2)
- **App service**: subscription-manager (id: bab29cc5-c298-427e-a8c2-19a56cbb47a1)
- **Postgres service**: Postgres-f5H6 (id: 5dbe9a85-009c-4758-892c-3d270627f40b)
- **Environment**: production (id: 3301a5f3-37be-41e6-892e-81a44bb99a6a)
- **Public URL**: https://mysubz.up.railway.app
- **DB public URL**: postgresql://postgres:…@yamabiko.proxy.rlwy.net:16839/railway
- **Start command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- **Builder**: nixpacks

## Deploy Flow
```bash
git push origin master   # triggers Railway auto-deploy
# Wait ~2 min for nixpacks build + startup
```

On startup, `api.py` automatically:
1. Creates all DB tables (`init_db()`)
2. Seeds `provider_aliases` from hardcoded `PROVIDER_ALIASES` dict
3. Syncs `.industry_cache.json` → `provider_industries` table
4. Starts APScheduler cron jobs

## Full DB Wipe + Backfill Sequence
Run these in order after a clean deploy:

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

## Post-Deploy Checklist (after parser/alias changes)
```bash
# Re-seed provider_aliases after PROVIDER_ALIASES changes in email_parser.py
POST https://mysubz.up.railway.app/api/admin/seed-aliases

# Recompute all subscription costs after parser/alias changes
POST https://mysubz.up.railway.app/api/recalculate-costs
```

## Monitoring After Backfill
```
GET /api/sync-status          — check sync run history
GET /api/stats                — overall counts
GET /api/wallet-spend-map     — wallet coverage
GET /api/service-costs/{id}   — rolling 3-month for a subscription
```

## Admin Endpoints (one-time use)
| Endpoint | Purpose |
|---|---|
| `POST /api/admin/reset-db` | DROP ALL tables + recreate schema |
| `POST /api/admin/reset-batch-table` | Drop + recreate batch_processes only |
| `POST /api/admin/sync-industry-cache` | Sync .industry_cache.json → provider_industries |
| `POST /api/admin/seed-aliases` | Re-seed provider_aliases from code dict |

## Environment Variables (required)
```
DATABASE_URL          # Set by Railway automatically from Postgres service
COMPOSIO_API_KEY      # Composio SDK v2 key
COMPOSIO_USER_ID      # default
GMAIL_ACCOUNT_ID      # Gmail account ID in Composio
OUTLOOK_ACCOUNT_ID    # Outlook account ID in Composio
OUTLOOK_USER_EMAIL    # e.g. user@outlook.com
IMAP_HOST             # e.g. mail.zoner.com
IMAP_USER             # e.g. karlik@klikni.org
IMAP_PASSWORD         # IMAP password
WALLET_API_TOKEN      # BudgetBakers REST API bearer token
GOOGLE_PLACES_API_KEY # For industry resolution (optional)
```

## Local Dev (broken due to Python 3.13 SSL bug)
Python 3.13 has an SSL recursion bug that breaks pip downloads locally.
Packages cannot be installed via pip on this machine.
The app runs on Railway only — local preview uses static file server on port 8080.

**Workaround for local preview:**
```bash
python -m http.server 8080 --directory frontend
# Then open http://localhost:8080 (API calls will 404 — that's expected)
```
