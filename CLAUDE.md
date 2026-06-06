# Subscription Manager — Claude Session Guide

## ⚡ SESSION START PROTOCOL (mandatory, every session)

Before writing a single line of code or answering any question, run these three checks:

```bash
# 1. Pull latest code
git pull origin master

# 2. Confirm API is live
curl -sk https://mysubz.up.railway.app/api/subscriptions?page_size=1

# 3. Check sync status
curl -sk https://mysubz.up.railway.app/api/sync-status
```

Then tell the user:
> "Confirmed: [N] subs in DB, API live. Last sync: [date]. What are we working on?"

If `git pull` shows new commits — read `memory/CODEBASE_STRUCTURE.md` before touching anything. State may have changed since your training context.

---

## 📍 Key References

| What | Where |
|---|---|
| **Live app** | https://mysubz.up.railway.app |
| **Frontend** | `frontend/index.html` (single-file SPA, no build step) |
| **Git remote** | https://github.com/jardaKarlik/Subs-Manager |
| **Local path** | `C:\_dev\subscription_manager` |
| **Deploy** | Railway auto-deploys on push to `master` |
| **DB** | Railway PostgreSQL (`Postgres-f5H6`), accessed via `DATABASE_PUBLIC_URL` from local |
| **Memory** | `C:\Users\jaros\.claude\projects\C---dev-subscription-manager\memory\` |

---

## 🛠 Available Toolset (MCP servers connected in this project)

| Tool | What it gives you | MCP ID prefix |
|---|---|---|
| **BudgetBakers** | Wallet records (accounts, categories, records, aggregations, standing orders) | `mcp__db891e28` |
| **Gmail** | Read/search emails, create drafts, manage labels | `mcp__fa8af5c8` |
| **Google Calendar** | Events, scheduling | `mcp__fb531c06` |
| **Desktop Commander** | File ops, process management, terminal | `mcp__Desktop_Commander` |
| **Chrome** | Browser automation, page reading | `mcp__Claude_in_Chrome` |
| **Computer use** | Full desktop control | `mcp__computer-use` |

> Composio is used server-side (in `email_fetcher.py`) for Outlook. Direct Outlook access from Claude is via Composio actions triggered through the API endpoints, not a direct MCP.

---

## 🔄 Key Operational Commands

```bash
# Trigger background email backfill (returns immediately, runs async on Railway)
curl -sk -X POST "https://mysubz.up.railway.app/api/admin/backfill?since_days=30&max_results=50000"

# Watch backfill progress
curl -sk https://mysubz.up.railway.app/api/sync-status

# Re-run wallet matching (after importing new wallet records)
curl -sk -X POST https://mysubz.up.railway.app/api/match-wallet

# Recalculate all subscription costs from events
curl -sk -X POST https://mysubz.up.railway.app/api/recalculate-costs

# Seed provider aliases (run after code changes to PAYEE_ALIASES)
curl -sk -X POST https://mysubz.up.railway.app/api/admin/seed-aliases

# Fix a specific subscription (example: set billing_cycle to yearly)
curl -sk -X PUT https://mysubz.up.railway.app/api/subscriptions/4 \
  -H "Content-Type: application/json" -d '{"billing_cycle":"yearly"}'

# Create DB tables from outside Railway (uses DATABASE_PUBLIC_URL)
python init_db_remote.py
```

---

## 💰 FX Rates (keep backend + frontend in sync!)

```
CZK: 1   EUR: 25   USD: 23   GBP: 29
```
- Backend: `api.py` → `_FX_TO_CZK`
- Frontend: `frontend/index.html` → `FX_TO_CZK`

**Change both together or amounts will diverge.**

---

## 🏗 Architecture in One Paragraph

Single-file frontend (`frontend/index.html`) talks to a FastAPI backend (`api.py`) deployed on Railway. The backend uses async SQLAlchemy with a Railway PostgreSQL DB. Email ingestion runs via `email_fetcher.py` (Gmail via Gmail MCP, Outlook via Composio). Wallet data comes from BudgetBakers export, matched to subscriptions by `subscription_matcher.py`. The frontend's `monthly()` function prefers wallet-sourced `avg_monthly_czk`; falls back to parser cost × FX. The `TOTAL PAID` column uses actual wallet `total_czk` (real sum of payments), with `~estimate` for non-wallet subs.

---

## 📋 Memory Files (always read before major changes)

| File | Contents |
|---|---|
| `memory/CODEBASE_STRUCTURE.md` | Files, endpoints, DB schema, frontend functions |
| `memory/NEXT_STEPS.md` | Current state, known issues, roadmap |
| `memory/WORKING_PATTERNS.md` | Debugging patterns, anti-patterns, data flow |
| `memory/feedback_structured_workflow.md` | Work block-by-block rule |
| `memory/feedback_multi_computer_workflow.md` | Multi-computer git workflow |
| `memory/user_shorthand.md` | "subs" = subscriptions, etc. |

---

## ⚠️ Anti-Patterns (hard-won — do not repeat)

- **Never** rename an API response field without grepping all frontend consumers first
- **Never** stash-pop into a diverged master — pull clean, re-apply manually
- **Never** use `railway run python3 script.py` from Windows — it targets the internal DB hostname
- `wallet-spend-map` returns `{"map": {...}}` — always access `resp.map`, not `resp` directly
- `provider_aliases` seeding: skip entries where `canonical_name is None` (payment processors)
- `subscription.cost` is unreliable (parser-sourced); wallet `total_czk` / `avg_monthly_czk` is ground truth
- After dropping DB tables: **redeploy before recreating** (Railway connection pool corruption)
