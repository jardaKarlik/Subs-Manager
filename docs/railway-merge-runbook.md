# Railway merge runbook — one project for Subscription Manager + Temporal

Status: **planned, not executed**
Prepared: 2026-10-20
Target project name: `subs-temporal`
Domains: `subs.klikni.org` (site), `temporal.klikni.org` (UI behind basic auth)

---

## 0. Why / target state

Today the system is split across two Railway projects:

- `subscription-manager` — web app + app Postgres + a worker that reaches Temporal over a **public TCP proxy**
- `temporal` — template-derived Temporal cluster + `Client` hello-world sample + the music-release worker

Target: **one project**, one private network, no public Temporal TCP proxy, no sample services.

```
                     Internet
                        |
        +---------------+----------------+
        |                                |
  subs.klikni.org          temporal.klikni.org
        |                                |
   +----v----+                   +-------v--------+
   |   web   |                   | temporal-auth  |  (Caddy basic auth)
   | FastAPI |                   |   :8080        |
   +----+----+                   +-------+--------+
        |                                |
        |                        +-------v--------+
        |                        |  temporal-ui   |  (no public domain)
        |                        +-------+--------+
        |                                |
        |                    +-----------v-----------+
        +-------------------->  temporal  :7233      |
                             +-----------+-----------+
                                         |
        +------------------+-------------+-------------+------------------+
        |                  |                           |                  |
  +-----v-----+     +------v------+             +------v------+    +------v------+
  |subs-worker|     | music-worker|             |  Postgres   |    |  ReleaseS   |
  | subs_     |     | TS release  |             | temporal +  |    |  project DB |
  | temporal  |     | scanner     |             | temporal_   |    | (external)  |
  +-----------+     +-------------+             | visibility  |    +-------------+
                                                | + subs      |
                                                +-------------+
```

Services to create (7):

| Name | Kind | Source |
|---|---|---|
| `Postgres` | database | Railway Postgres |
| `temporal` | image | `temporalio/auto-setup:1.29.7` |
| `temporal-ui` | image | `temporalio/ui:2.56.0` |
| `temporal-auth` | image | `ghcr.io/brody192/railway-caddy-basic-auth:main` |
| `web` | repo | `jardaKarlik/Subs-Manager` @ `master` |
| `subs-worker` | repo | same repo, Dockerfile `subs_temporal/Dockerfile` |
| `music-worker` | repo | same repo, `music_worker/` (exported from old container) |

---

## 1. Decisions already made

- Music-release worker **is included** in the new project.
- Website gets a **custom domain**.
- Temporal UI is reachable **only through the basic-auth proxy** (no direct domain).
- **One Postgres service, two databases**: `subs` (app) + `temporal`/`temporal_visibility` (Temporal).
- Old projects stay alive until validation, then are deleted.

---

## 2. Pre-flight (do not skip)

### 2.1 Back up the app database

Use the old project's `DATABASE_PUBLIC_URL` (already available as the old `DATABASE_URL` variable).

```powershell
# Run from C:\_dev\subscription_manager (psycopg2 is installed for Python 3.14)
$old = railway variable list -s subscription-manager -e production -p adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 --json |
  ConvertFrom-Json
$env:SRC_URL = $old.DATABASE_URL
python scripts/pg_backup.py   # creates backups/subs-YYYYMMDD-HHMM.json (all 9 tables)
```

If `scripts/pg_backup.py` does not exist yet, create it (see Appendix A) before executing.

### 2.2 Freeze the old schedulers

The old Temporal cluster currently owns all scheduling. Pause it so the dump is consistent:

```powershell
railway ssh -p adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 -e production -s subs-temporal-worker `
  "python -m subs_temporal.run_once pause subs-sync"
railway ssh -p adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 -e production -s subs-temporal-worker `
  "python -m subs_temporal.run_once pause subs-discovery-sweep"
```

Pause `music-release-scan-daily` in the old Temporal UI as well (or via a one-off script).
Wait for any in-flight workflow to finish (Temporal UI → Workflows → Running).

### 2.3 Export the music-release worker source

The code exists **only in the old container** (`/app/src`, 8 TS files). It is not in this repo.

```powershell
$tmp = "$env:TEMP\music_worker_src"
$b64 = railway ssh -p 67092547-2bdc-40cb-b267-850a1a839e86 -e production -s 9317f18b-624c-44b0-a341-dcc84cd23c24 `
  "cd /app && tar -czf - src package.json package-lock.json tsconfig.json Dockerfile railway.json .env.example README.md tools.md .dockerignore 2>/dev/null | base64 -w0"
[IO.File]::WriteAllBytes("$tmp.tar.gz", [Convert]::FromBase64String($b64))
tar -xzf "$tmp.tar.gz" -C $tmp
```

Then copy it into the repo as `music_worker/`, review for secrets (there should be none), and commit:

```powershell
New-Item -ItemType Directory -Force music_worker | Out-Null
Copy-Item "$tmp\*" music_worker\ -Recurse -Force
git add music_worker && git commit -m "chore(music-worker): preserve release scanner source from deployed container"
git push origin master
```

Notes:
- `package.json` has an unnecessary `@railway/cli` dependency. Optional cleanup, but keep parity for the first deploy.
- Do **not** commit `.env` — only `.env.example` exists.

### 2.4 Update the local-preview fallback

`frontend/index.html:552` hardcodes `https://mysubz.up.railway.app` for localhost/file preview. After cutover it will point at a dead project. Change it to the new domain (or an env-injected value) **before** the final commit:

```js
? 'https://subs.klikni.org'
```

Same-origin requests on the real domain are unaffected (`API` is `''`).

---

## 3. Create the project and database

```powershell
railway init --name subs-temporal --json          # capture id + production environment id
$P = "<NEW_PROJECT_ID>"
railway link -p $P -e production
railway add --database postgres --service Postgres --json
```

Then create the app database `subs` (Temporal's auto-setup will create `temporal` and
`temporal_visibility` itself):

```powershell
$pg = railway variable list -s Postgres -e production -p $P --json | ConvertFrom-Json
$env:ADMIN_URL = $pg.DATABASE_PUBLIC_URL
python scripts/pg_create_db.py subs
```

If the Postgres addon has no public URL, open a tunnel and use the private URL:

```powershell
railway connect Postgres --tunnel-only -p $P -e production
# use the printed localhost connection string for ADMIN_URL
```

Postgres notes:
- Choose the same region as the old project (check the dashboard; likely EU West).
- Keep public networking only for the migration window; disable it afterwards.
- One instance hosts `subs`, `temporal`, `temporal_visibility` — no extra cost, shared blast radius.

---

## 4. Deploy Temporal

### 4.1 `temporal` service

```powershell
railway add --image temporalio/auto-setup:1.29.7 --service temporal --json
```

Variables (Railway reference syntax):

| Key | Value |
|---|---|
| `DB` | `postgres12` |
| `DB_PORT` | `${{Postgres.PGPORT}}` |
| `DBNAME` | `temporal` |
| `VISIBILITY_DBNAME` | `temporal_visibility` |
| `POSTGRES_SEEDS` | `${{Postgres.PGHOST}}` |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` |
| `POSTGRES_PWD` | `${{Postgres.PGPASSWORD}}` |
| `PORT` | `7233` |
| `BIND_ON_IP` | `0.0.0.0` |
| `TEMPORAL_BROADCAST_ADDRESS` | `127.0.0.1` |

Do **not** create a public domain or a TCP proxy. All clients are in-project.

Verify from another service later with `nc -z temporal.railway.internal 7233`
(or simply watch the UI).

### 4.2 `temporal-ui` (no public domain)

```powershell
railway add --image temporalio/ui:2.56.0 --service temporal-ui --json
```

| Key | Value |
|---|---|
| `PORT` | `8080` |
| `TEMPORAL_ADDRESS` | `${{temporal.RAILWAY_PRIVATE_DOMAIN}}:7233` |
| `TEMPORAL_CORS_ORIGINS` | `https://temporal.klikni.org` |
| `TEMPORAL_AUTH_ENABLED` | `true` |

**Do not generate a Railway domain for this service.** The current UI is readable by anyone who knows its URL; do not repeat that.

### 4.3 `temporal-auth` (public, basic auth)

```powershell
railway add --image ghcr.io/brody192/railway-caddy-basic-auth:main --service temporal-auth --json
```

| Key | Value |
|---|---|
| `USERNAME` | `<pick-a-username>` |
| `PASSWORD` | `<openssl rand -base64 32>` |
| `PROXY_PASS` | `http://${{temporal-ui.RAILWAY_PRIVATE_DOMAIN}}:8080` |

Then attach the custom domain:

```powershell
railway domain temporal.klikni.org --service temporal-auth -p 8080
```

Railway prints **two** records to add in Cloudflare — a `CNAME` and a `TXT`
verification record. Both are required; see Appendix D for the exact Cloudflare steps.

Optional hardening: replace the unpinned `:main` proxy image with `caddy:2-alpine`
and a committed Caddyfile if you want a fully pinned dependency chain.

---

## 5. Deploy the app

### 5.1 `web`

```powershell
railway add --repo jardaKarlik/Subs-Manager --branch master --service web --json
```

Builder: RAILPACK (auto-detects `Procfile` → `uvicorn api:app --host 0.0.0.0 --port $PORT`).

Variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/subs` |
| `SCHEDULER_ENABLED` | `false` |
| `PYTHON_VERSION` | `3.13` |
| `WALLET_API_BASE` | copy from old `web` |
| `WALLET_API_TOKEN` | copy from old `web` |
| `COMPOSIO_API_KEY` | copy |
| `COMPOSIO_USER_ID` | copy |
| `GMAIL_ACCOUNT_ID` | copy |
| `GMAIL_USER_EMAIL` | copy |
| `OUTLOOK_ACCOUNT_ID` | copy |
| `OUTLOOK_USER_EMAIL` | copy |
| `IMAP_SERVER` | copy |
| `IMAP_PORT` | copy |
| `IMAP_USER` | copy |
| `IMAP_PASSWORD` | copy |
| `IMAP_VERIFY_SSL` | copy |
| `SYNC_SINCE_DAYS` | copy |
| `SYNC_MAX_RESULTS` | copy |

`DATABASE_URL` must start with `postgresql://`; `database.py` rewrites it to `postgresql+asyncpg://`.

Do **not** copy `RAILWAY_*` variables, and do **not** copy the old literal `DATABASE_URL`.

Secrets copy pattern (values never printed):

```powershell
$src = railway variable list -s subscription-manager -e production -p adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 --json | ConvertFrom-Json
$keys = @('WALLET_API_BASE','WALLET_API_TOKEN','COMPOSIO_API_KEY','COMPOSIO_USER_ID',
          'GMAIL_ACCOUNT_ID','GMAIL_USER_EMAIL','OUTLOOK_ACCOUNT_ID','OUTLOOK_USER_EMAIL',
          'IMAP_SERVER','IMAP_PORT','IMAP_USER','IMAP_PASSWORD','IMAP_VERIFY_SSL',
          'SYNC_SINCE_DAYS','SYNC_MAX_RESULTS')
foreach ($k in $keys) {
  $src.$k | railway variable set $k --stdin --skip-deploys -s web -e production -p $P
}
# non-secret literals can be set directly:
railway variable set 'SCHEDULER_ENABLED=false' 'PYTHON_VERSION=3.13' --skip-deploys -s web -e production -p $P
railway variable set 'DATABASE_URL=postgresql://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/subs' --skip-deploys -s web -e production -p $P
```

First boot creates the 9 tables, seeds `provider_aliases`, and syncs the industry cache.
Wait for `GET https://<generated-domain>/api/health` to return 200 **before** migrating data.

Attach the custom domain after data verification:

```powershell
railway domain subs.klikni.org --service web -p 8080
```

Copy the two printed records (`CNAME` + `TXT`) into Cloudflare — see Appendix D.

### 5.2 `subs-worker`

```powershell
railway add --repo jardaKarlik/Subs-Manager --branch master --service subs-worker --json
```

Settings (dashboard or `railway` MCP `update_service`):

- Root directory: `/` (repo root)
- Dockerfile path: `subs_temporal/Dockerfile`
- Builder: DOCKERFILE

Variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | same composed value as `web` |
| `TEMPORAL_ADDRESS` | `${{temporal.RAILWAY_PRIVATE_DOMAIN}}:7233` |
| `TEMPORAL_TASK_QUEUE` | `subs-manager` |
| plus all app secrets from §5.1 except `PYTHON_VERSION` / `SCHEDULER_ENABLED` | copy |

Do **not** set `SCHEDULER_ENABLED` on the worker — it has no FastAPI startup.

### 5.3 `music-worker`

```powershell
railway add --repo jardaKarlik/Subs-Manager --branch master --service music-worker --json
```

Settings:

- Root directory: `music_worker`
- Builder: DOCKERFILE (the recovered `Dockerfile`)

Variables (copy from the old `Worker` service):

| Key | Value |
|---|---|
| `TEMPORAL_ADDRESS` | `${{temporal.RAILWAY_PRIVATE_DOMAIN}}:7233` |
| `RELEASES_PROJECT_ID` | copy |
| `RELEASES_ENVIRONMENT_ID` | copy |
| `RELEASES_ENV` | copy |
| `RELEASES_PROD_SERVICE_ID` | copy |
| `RELEASES_STAGING_SERVICE_ID` | copy |
| `RELEASES_DATABASE_URL` | copy (external ReleaseS DB) |
| `TEKNO_PROD_URL` | copy |
| `TEKNO_STAGING_URL` | copy |
| `RAILWAY_RELEASES_TOKEN` | copy |
| `DISCORD_WEBHOOK_URL` | copy |
| `COMPOSIO_API_KEY` | copy |
| `COMPOSIO_USER_ID` | copy |
| `COMPOSIO_OUTLOOK_ACCOUNT_ID` | copy |
| `SOUNDCLOUD_CLIENT_ID` | copy |
| `SOUNDCLOUD_OAUTH_TOKEN` | copy |
| `BANDCAMP_LOOKBACK_DAYS` | copy |

Expected log line: `Worker state changed { state: 'RUNNING' }` for `release-list-task-queue`.

---

## 6. Migrate the app data

Only after `web` has created the schema.

```powershell
$old = railway variable list -s subscription-manager -e production -p adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 --json | ConvertFrom-Json
$pg  = railway variable list -s Postgres -e production -p $P --json | ConvertFrom-Json

$env:SRC_URL = $old.DATABASE_URL
$u = [uri]$pg.DATABASE_PUBLIC_URL
$env:DST_URL = $u.GetLeftPart([System.UriPartial]::Authority) + '/subs'
python scripts/pg_copy.py
```

`scripts/pg_copy.py` (Appendix B) is schema-aware:
- copies the intersection of source/target columns,
- reports source-only and target-only columns,
- truncates the target table first,
- resets each `id` sequence,
- prints a per-table source/target count.

Expected tables: `subscriptions`, `financial_records`, `processed_emails`,
`subscription_events`, `service_costs`, `sync_metadata`, `batch_processes`,
`provider_aliases`, `provider_industries`.

Verification:

```powershell
curl.exe https://<generated-web-domain>/api/stats
curl.exe "https://<generated-web-domain>/api/subscriptions?page_size=1"
```

Counts must match the pre-flight snapshot. If a target-only column appears, check
`database.py` models vs the old DB before proceeding.

---

## 7. Recreate Temporal schedules (paused)

The new cluster starts empty. Create all three schedules **paused**, then confirm
they exist before unpausing at cutover.

`subs_temporal/schedules.py` currently defines only the two subscription schedules and
hardcodes one task queue. Make two small changes:

1. Allow a per-schedule queue and add the music entry:

```python
SCHEDULES = [
    {
        "id": "subs-sync",
        "cron": "0 19 */3 * *",
        "workflow": SubsSyncWorkflow.run,
        "args": [5, 500],
        "task_queue": TASK_QUEUE,
    },
    {
        "id": "subs-discovery-sweep",
        "cron": "0 7 * * 0",
        "workflow": DiscoverySweepWorkflow.run,
        "args": [2],
        "task_queue": TASK_QUEUE,
    },
    {
        "id": "music-release-scan-daily",
        "cron": "0 7 * * *",
        "workflow": "musicReleaseScanWorkflow",   # raw name exported by the TS worker
        "args": [],
        "task_queue": "release-list-task-queue",
    },
]
```

2. Use the per-schedule queue when creating the action:

```python
action=ScheduleActionStartWorkflow(
    spec["workflow"],
    args=spec["args"],
    id=spec["id"],
    task_queue=spec.get("task_queue", TASK_QUEUE),
),
```

The live cluster stores calendar specs, but the cron equivalents used by `schedules.py`
produce the same firing times:

- `subs-sync`: `0 19 */3 * *` (day-of-month 1,4,7,…,31 at 19:00)
- `subs-discovery-sweep`: `0 7 * * 0` (Sunday 07:00)
- `music-release-scan-daily`: `0 7 * * *` (daily 07:00)

Run the bootstrap inside `subs-worker` (it has `temporalio`):

```powershell
railway ssh -s subs-worker -e production -p $P "python -m subs_temporal.schedules"
railway ssh -s subs-worker -e production -p $P "python -m subs_temporal.run_once check"
```

Expected: three schedules, `paused=True`, next times shown.

---

## 8. Cutover

1. Pause old schedules (already done in §2.2), confirm no running workflows in the old UI.
2. Re-run the backup + copy (§2.1, §6) one final time to capture any last writes.
3. Unpause the new schedules:
   ```powershell
   foreach ($s in @('subs-sync','subs-discovery-sweep','music-release-scan-daily')) {
     railway ssh -s subs-worker -e production -p $P "python -m subs_temporal.run_once unpause $s"
   }
   ```
4. Run one manual end-to-end sync against the new stack:
   ```powershell
   railway ssh -s subs-worker -e production -p $P "python -m subs_temporal.run_once start 5 500"
   ```
   Watch the Temporal UI → `SubsSyncWorkflow` → Activity results.
5. Point DNS in Cloudflare (Appendix D): add the `CNAME` **and** `TXT` records Railway
   printed for each of `subs.klikni.org` and `temporal.klikni.org`.
   ```powershell
   railway domain status subs.klikni.org -s web -p $P
   railway domain status temporal.klikni.org -s temporal-auth -p $P
   ```
   Wait for `certificateStatus: VALID` on both.
6. Open `https://subs.klikni.org` and verify:
   - table renders the expected number of subscriptions,
   - `TOTAL PAID` / wallet numbers match the old UI,
   - sync status block shows recent runs,
   - approval/dismiss actions work.
7. Open `https://temporal.klikni.org` behind basic auth:
   - all 3 schedules listed and unpaused,
   - both workers (`subs-manager`, `release-list-task-queue`) show as pollers,
   - trigger `music-release-scan-daily` once and confirm `music-worker` logs.

Acceptance checks:

- `GET /api/health` → 200
- `GET /api/stats` counts equal old values
- No public domain exists on `temporal-ui`
- No TCP proxy exists on `temporal`
- `web` has `SCHEDULER_ENABLED=false`
- `subs-worker` and `music-worker` log "started/RUNNING"

---

## 9. Rollback

Before deleting anything:

1. Pause the new schedules.
2. Re-point `subs.klikni.org` DNS to the old service (or use `mysubz.up.railway.app`).
3. Unpause the old schedules:
   ```powershell
   railway ssh -p adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 -e production -s subs-temporal-worker `
     "python -m subs_temporal.run_once unpause subs-sync"
   ```
4. The old project still owns its own Postgres, so no data restore is needed — any
   writes made against `subs` after cutover would be lost, so roll back quickly.

Keep both old projects for **7 days** after a successful cutover.

---

## 10. Decommission

Only after 7 days of clean operation:

```powershell
railway service delete --service subscription-manager --project adcb3b41-6d7d-485f-97ac-2b6b95d99cb2 --yes
# then delete the old subscription-manager project and the old temporal project
```

Also:

- Delete the old Temporal TCP proxy (`turntable.proxy.rlwy.net:51514`) when the old cluster is deleted.
- Disable public networking on the new Postgres.
- Rotate the Temporal UI basic-auth password if it was ever shared.
- Update `memory/project_deploy.md`, `CLAUDE.md` URLs, and any bookmarks.

---

## 11. Gotchas specific to this repo

- `api.py` mounts `frontend/` at `/` **after** all API routes; the FastAPI service *is* the website. Do not add a separate static-site service.
- `SCHEDULER_ENABLED=false` on `web` is mandatory. Temporal owns scheduling; otherwise APScheduler double-runs.
- `DATABASE_URL` must point at the `subs` database, not Railway's default `railway` DB (that one holds Temporal).
- `wallet-spend-map` returns `{"map": {...}}` — unchanged.
- `subscription.cost` is parser-derived; wallet `total_czk` / `avg_monthly_czk` remains ground truth.
- After a DB wipe/recreate, redeploy before recreating (connection-pool corruption).
- `subs_temporal/Dockerfile` expects `requirements.txt` at the **repo root**; keep the service root directory `/` and set only the Dockerfile path.
- The music worker source was never in git. Committing `music_worker/` is part of this migration, not optional cleanup.
- The TS worker uses workflow **function exports** (`musicReleaseScanWorkflow`), so the schedule action references the raw workflow name, not a class name.
- `temporalio/auto-setup` will create `temporal` + `temporal_visibility`; the same Postgres user must be superuser (Railway's `postgres` is).
- Do not expose `temporal-ui` directly. The old deployment's UI answered 200 with no auth.
- Pin images (`1.29.7`, `2.56.0`). `:main` on the Caddy auth proxy is the only unpinned dependency; acceptable short-term, better replaced with a pinned Caddyfile.

---

## Appendix A — `scripts/pg_backup.py`

```python
"""Dump all app tables to JSON. Usage: SRC_URL=... python scripts/pg_backup.py"""
import json, os, pathlib
from datetime import datetime
import psycopg2

TABLES = [
    "provider_aliases", "provider_industries", "subscriptions",
    "financial_records", "processed_emails", "subscription_events",
    "service_costs", "sync_metadata", "batch_processes",
]

out_dir = pathlib.Path("backups")
out_dir.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d-%H%M")
conn = psycopg2.connect(os.environ["SRC_URL"])
conn.autocommit = True
payload = {}
with conn.cursor() as cur:
    for table in TABLES:
        try:
            cur.execute(f'SELECT * FROM "{table}"')
            cols = [d[0] for d in cur.description]
            payload[table] = [dict(zip(cols, row)) for row in cur.fetchall()]
            print(f"{table}: {len(payload[table])}")
        except Exception as exc:
            conn.rollback()
            print(f"{table}: SKIP ({exc})")

path = out_dir / f"subs-{stamp}.json"
path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
print(f"wrote {path}")
```

## Appendix B — `scripts/pg_copy.py`

```python
"""Copy app tables source -> target, schema-aware.
Usage: SRC_URL=... DST_URL=... python scripts/pg_copy.py
"""
import io, os
import psycopg2

TABLES = [
    "provider_aliases", "provider_industries", "subscriptions",
    "financial_records", "processed_emails", "subscription_events",
    "service_costs", "sync_metadata", "batch_processes",
]

src = psycopg2.connect(os.environ["SRC_URL"])
dst = psycopg2.connect(os.environ["DST_URL"])
src.autocommit = True
dst.autocommit = True

def columns(conn, table):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema='public' AND table_name=%s
               ORDER BY ordinal_position""",
            (table,),
        )
        return [r[0] for r in cur.fetchall()]

with src.cursor() as sc, dst.cursor() as dc:
    for table in TABLES:
        s_cols, d_cols = columns(src, table), columns(dst, table)
        if not s_cols or not d_cols:
            print(f"SKIP {table}: missing on {'source' if not s_cols else 'target'}")
            continue
        common = [c for c in s_cols if c in d_cols]
        dropped = [c for c in s_cols if c not in d_cols]
        added = [c for c in d_cols if c not in s_cols]
        if dropped:
            print(f"WARN {table}: source-only columns dropped: {dropped}")
        if added:
            print(f"WARN {table}: target-only columns defaulted: {added}")

        collist = ", ".join(f'"{c}"' for c in common)
        buf = io.StringIO()
        sc.copy_expert(f'COPY "{table}" ({collist}) TO STDOUT WITH CSV', buf)
        buf.seek(0)

        dc.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
        dc.copy_expert(f'COPY "{table}" ({collist}) FROM STDIN WITH CSV', buf)

        dc.execute("SELECT pg_get_serial_sequence(%s, 'id')",
                   (f'public."{table}"',))
        seq = dc.fetchone()[0]
        if seq:
            dc.execute(
                f'SELECT setval(%s, COALESCE((SELECT MAX(id) FROM "{table}"), 1), '
                f'(SELECT COUNT(*) > 0 FROM "{table}"))',
                (seq,),
            )

        sc.execute(f'SELECT COUNT(*) FROM "{table}"'); n_src = sc.fetchone()[0]
        dc.execute(f'SELECT COUNT(*) FROM "{table}"'); n_dst = dc.fetchone()[0]
        status = "OK" if n_src == n_dst else "MISMATCH"
        print(f"{table}: source={n_src} target={n_dst} {status}")
```

## Appendix C — `scripts/pg_create_db.py`

```python
"""Create a database on Railway Postgres. Usage: ADMIN_URL=... python scripts/pg_create_db.py subs"""
import os, sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

name = sys.argv[1]
conn = psycopg2.connect(os.environ["ADMIN_URL"])
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,))
    if cur.fetchone():
        print(f"{name}: already exists")
    else:
        cur.execute(f'CREATE DATABASE "{name}"')
        print(f"{name}: created")
```

## Appendix D — DNS on Cloudflare for `klikni.org`

### D.1 Current state (verified 2026-10-20)

| Fact | Value |
|---|---|
| Nameservers | `jewel.ns.cloudflare.com`, `guy.ns.cloudflare.com` — **already Cloudflare** |
| Registrar of record | joker.com (CSL Computer Service Langenbach GmbH) |
| Registered | 2024-12-16 |
| Expires | **2026-12-16** (~8 weeks) |
| DNSSEC | not signed (`delegationSigned: false`) — no blocker for any change |
| Apex A | `185.158.133.1` (old Czech host; serves the portfolio site) |
| www | `185.158.133.1` (same) |
| MX | `relay.zoner.com`, `10mx.zoner.com`, `15mx.zoner.com` (Zoner Mail) |
| TXT | `v=spf1 include:spf-zoner-zmail.zoner.com ~all` |

### D.2 Access — confirmed, nothing to transfer

Verified 2026-10-20 via the official Cloudflare CLI (`cf`, v1.0.0-beta.20):

| Fact | Value |
|---|---|
| Zone ID | `e4c99d7555f0cf00e2704acbb2095820` |
| Account ID | `0b6949aa75b1a4b3f9b2008b1814475a` |
| Account name | `J.karleek@gmail.com's Account` |
| Original nameservers | `ns1.regzone.cz`, `ns1.regzone.de`, `ns1.regzone.info` |
| Moved to Cloudflare | 2026-05-29 |
| Existing records | 13 (see D.4) |

The domain was moved off Regzone (the "obscure Czech host") to Cloudflare in May.
**Nothing needs transferring.** Access is via API token, not a dashboard login.

Setup already done on this machine:

- API token in GCP Secret Manager as `cloudflare` (project `master4all`),
  also mirrored to the user env var `CLOUDFLARE_API_TOKEN`.
- `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_ZONE_ID` set as user env vars.
- `CF_SEND_TELEMETRY=false` set.
- `cf` installed globally (`npm install --global cf`).

Token permissions include `#dns_records:edit`, `#dns_records:read`, `#zone:read`.

**PowerShell quoting gotcha:** `cf`'s `--body` takes raw JSON, and PowerShell 5.1
mangles embedded double quotes when shelling out. Always backslash-escape:

```powershell
$json = '{"type":"CNAME","name":"subs","content":"x.up.railway.app","proxied":false,"ttl":1}'
& cf dns records create --zone klikni.org --body ($json.Replace('"','\"'))
```

This is verified working (`--dry-run` returns the correct parsed body).

### D.3 Records to add — Cloudflare CLI

For each custom domain Railway prints **two** records. Both are mandatory — with only
the CNAME, the domain verifies but every request 404s, because Railway uses the TXT to
prove ownership before routing.

Read current state:

```powershell
cf zones list --name klikni.org
cf dns records list --zone klikni.org
cf dns records list --zone klikni.org --name subs.klikni.org
```

**`subs.klikni.org`** → service `web`, target port **8080**

```powershell
# CNAME — proxied:false = grey cloud, ttl:1 = automatic
$body = '{"type":"CNAME","name":"subs","content":"<RAILWAY TARGET>","proxied":false,"ttl":1}'
& cf dns records create --zone klikni.org --body ($body.Replace('"','\"'))

# TXT — ownership verification
$body = '{"type":"TXT","name":"<_railway.subs>","content":"<RAILWAY VALUE>","ttl":1}'
& cf dns records create --zone klikni.org --body ($body.Replace('"','\"'))
```

**`temporal.klikni.org`** → service `temporal-auth`, target port **8080**

```powershell
$body = '{"type":"CNAME","name":"temporal","content":"<RAILWAY TARGET>","proxied":false,"ttl":1}'
& cf dns records create --zone klikni.org --body ($body.Replace('"','\"'))

$body = '{"type":"TXT","name":"<RAILWAY NAME>","content":"<RAILWAY VALUE>","ttl":1}'
& cf dns records create --zone klikni.org --body ($body.Replace('"','\"'))
```

Copy the exact Name/Target/Content values from Railway — do not guess them from these
placeholders. Add `--dry-run` to any `create` to preview the request without writing.

Verify:

```powershell
cf dns records list --zone klikni.org --name subs.klikni.org
Resolve-DnsName subs.klikni.org -Type CNAME
Resolve-DnsName temporal.klikni.org -Type CNAME
```

Rollback — delete a record by the ID returned at creation:

```powershell
cf dns records delete <RECORD_ID> --zone klikni.org --force
```

`--force` is required: in a non-interactive session a delete prints `Aborted.`, makes no
change, **and still exits 0**, so a script cannot detect the skip from the exit code.

**Why grey cloud (`proxied:false`):** Railway already provisions and renews its own TLS
certificate for each custom domain. Proxied (orange cloud) puts a second TLS layer in
front and needs Cloudflare SSL mode set to *Full (strict)*, plus `_acme-challenge`
handling. Grey cloud is the low-risk default; switch to proxied later if you want
Cloudflare caching/WAF on the app.

### D.4 Existing records — do not touch

Full inventory as of 2026-10-20 (13 records):

| Type | Name | Proxied | Content |
|---|---|---|---|
| A | `klikni.org` | no | `185.158.133.1` |
| A | `www.klikni.org` | no | `185.158.133.1` |
| A | `ftp.klikni.org` | **yes** | `217.198.114.187` |
| AAAA | `ftp.klikni.org` | **yes** | `2a00:19a0:3:72:0:d9c6:72bb:1` |
| CNAME | `autoconfig.klikni.org` | **yes** | `autoconfig.zoner.com` |
| CNAME | `kanbanos.klikni.org` | **yes** | `8ad38f9d-....cfargotunnel.com` |
| MX | `klikni.org` | no | `relay.zoner.com` |
| MX | `klikni.org` | no | `10mx.zoner.com` |
| MX | `klikni.org` | no | `15mx.zoner.com` |
| SRV | `_autodiscover._tcp.klikni.org` | no | `0 443 autodiscover.zoner.com` |
| TXT | `_lovable.klikni.org` | no | `lovable_verify=010d96...` |
| TXT | `_lovable.www.klikni.org` | no | `lovable_verify=ea1ef9...` |
| TXT | `klikni.org` | no | `v=spf1 include:spf-zoner-zmail.zoner.com ~all` |

Notes:

- Apex + `www` A records serve the portfolio site (`C:\_dev\klikni.org`).
- `ftp.*` points at a **second host** (`217.198.114.187`) — separate from the web origin.
- `kanbanos.*` runs on a **Cloudflare Tunnel**, not an A record.
- `autoconfig` + `_autodiscover` + all three MX records are Zoner Mail. Moving them
  breaks `karlik@klikni.org`.
- The two `_lovable` TXT records are Lovable site-verification tokens.

Adding `subs` and `temporal` touches none of these — different names, no apex changes.

### D.5 Optional: transfer the registrar to Cloudflare

Separate from DNS, and optional. Because the zone already uses Cloudflare NS, you are
eligible for Cloudflare Registrar.

Why bother: renewals at cost (~$10.44/yr for `.org`), one bill, no reseller markup,
WHOIS privacy included.

Steps:

1. At joker.com, unlock `klikni.org` and request the **EPP / auth code**.
2. Cloudflare dashboard → **Domain Registration** → **Transfer a domain** →
   `klikni.org`.
3. Enter the EPP code. Cloudflare confirms the current registrar by email.
4. Approve the transfer email. It completes in 1–5 days; the site and email stay up.

Requirements: registered ≥60 days ago (yours is, since 2024-12-16), not transferred in
the last 60 days, unlocked, no legal dispute. DNSSEC must be off — it is.

⚠️ **Do it now, not in December.** Expiry is 2026-12-16. A transfer started in early
December can collide with renewal, and a failed transfer so close to expiry risks the
domain. Starting in October leaves ample margin.

If you only want DNS control and not registrar ownership, do nothing — you already have
full DNS control via the API token. joker.com keeps billing you for the domain.
