# Dev Patterns & Feedback

Hard-won lessons from building this project. Read before touching anything.

## Always check Railway DB before assuming local DB is authoritative
The local `subscriptions.db` SQLite and the Railway PostgreSQL are separate. Railway has the live data.

**How to apply:** If a table "doesn't exist" locally, check Railway before concluding it's missing.

## Verify bank-sync records are genuine before using as anchor dates
When checking `recordDate.min` on Airbank accounts to set email fetch anchors, verify individual records have `source: "backend"` and `createdAt` matching bank-sync setup date — not today's date (which would indicate manual import).

**How to apply:** Always check `source` field and `createdAt` on the oldest records, not just the aggregate `recordDate.min`.

## Check both DB AND UI when auditing feature completeness
When asked to audit whether a feature is implemented, the answer has two parts: (1) is the backend writing data, and (2) is the frontend displaying it. A table with no UI is "DB only", not "done".

## frontend/simple.js is orphaned — index.html is the real frontend
`frontend/simple.js` is not loaded by `frontend/index.html`. All UI work happens in the inline `<script>` block in `index.html`.

**How to apply:** Always edit `frontend/index.html` for UI changes, never `simple.js`.

## frontend_glass/ is intentionally set aside
The React/Vite glass frontend exists but is not active. All UI work goes into `frontend/index.html` (terminal-style).

**How to apply:** Don't touch `frontend_glass/` unless explicitly asked.

## pip install broken on this machine (Python 3.13 SSL recursion bug)
`pip install` fails with `RecursionError: maximum recursion depth exceeded`. Packages cannot be installed locally.

**How to apply:** Don't attempt pip install locally. The app only runs on Railway.

## Don't use notes field to store plan_name
Early implementation stored `plan_name` in `notes` as "Plan: Premium". It's now a dedicated column.

**How to apply:** Use `sub.plan_name` directly, not `sub.notes`.

## wallet-spend-map returns `{"map": {...}}` — always access `resp.map`
The `/api/wallet-spend-map` endpoint wraps its payload in a `map` key. Accessing `resp` directly returns the wrapper object.

## subscription.cost is unreliable — wallet data is ground truth
`subscription.cost` is email-parser-derived (mode of subscription_events amounts) and can be wrong if bad emails were parsed. Wallet `total_czk` / `avg_monthly_czk` from service_costs is the real spend.

## After dropping DB tables: redeploy before recreating
Railway connection pool corruption can occur if you recreate tables in the same process that dropped them. Always trigger a fresh deploy between drop and recreate.

## Email parser: bulk sender domains are marketing, never transactional
Senders from subdomains like `bmail.`, `em.`, `enews.`, `promo.` are ESP bulk-mail sends. They get a -0.40 penalty in the classifier via `BULK_SENDER_SUBDOMAINS`. Example: `sonyeurope@bmail.sony-europe.com` is Sony marketing, not a subscription receipt.

## Email parser: amount extraction uses 3-tier context ranking
- Tier 2: subscription-specific keywords (předplatné, recurring, auto-renew) — strongest
- Tier 1: generic billing keywords (payment, invoice, platba)
- Tier 0: purchase-total keywords (total, celkem) — weakest; these appear in store receipts

When an email has both a subscription line (365 CZK) and an order total (1600 CZK), the subscription line wins because "předplatné" is Tier 2 and "celkem" is Tier 0.

## provider_aliases seeding: skip entries where canonical_name is None
Payment processors in PROVIDER_ALIASES have `name = None` (they resolve the payee from the email body). The seed-aliases endpoint skips these correctly — don't expect them to appear in the provider_aliases DB table.
