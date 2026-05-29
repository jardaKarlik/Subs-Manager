# New Rule: Composio is the Universal Data Integration Layer

> **Applies to:** Any project (current & future) that needs to pull data from
> email services (Gmail, Live.com, IMAP), social platforms (Reddit, LinkedIn),
> or any other third-party API.

---

## The Rule

**Composio is the tool of choice** for fetching data from ALL of the following
sources. Do NOT use direct API calls, IMAP, or any other library unless
Composio is unavailable for that specific source.

| Source               | How to access via Composio            | Notes                          |
|----------------------|----------------------------------------|--------------------------------|
| **Gmail**            | `GMAIL_FETCH_EMAILS` / `gmail_get_profile` / `gmail_fetch_emails` | OAuth handled by Composio      |
| **Live.com / Outlook** | `OUTLOOK_QUERY_EMAILS` / `outlook_list_messages` | Live.com accounts work via Outlook integration |
| **klikni.org (IMAP)** | `imap_list_mailboxes` / Direct IMAP via `imaplib` | Use Composio IMAP first; fallback to direct IMAP with `ssl.CERT_NONE` if certs fail |
| **Reddit**           | `reddit_get_identity`, subreddit actions | Connect via Composio dashboard |
| **LinkedIn**         | `linkedin_get_profile`, feed actions    | Connect via Composio dashboard |

---

## Why Composio?

1. **Single API key** (`COMPOSIO_API_KEY`) – one auth for all integrations.
2. **OAuth is handled** by Composio – no refresh tokens, no scopes to manage.
3. **Unified response format** – `POST /api/v1/actions/execute` works the same
   for every integration.
4. **Connection management** – `GET /api/v1/connectedAccounts` lists everything.
5. **Extensible** – adding a new source is just a 1-click connect in the
   Composio dashboard.

---

## API Pattern

```python
import requests

API_BASE = "https://backend.composio.dev/api/v1"
headers = {
    "X-API-Key": os.getenv("COMPOSIO_API_KEY"),
    "Content-Type": "application/json",
}

# 1. List connected accounts
resp = requests.get(f"{API_BASE}/connectedAccounts", headers=headers)

# 2. Execute an action
resp = requests.post(
    f"{API_BASE}/actions/execute",
    headers=headers,
    json={
        "connectedAccountId": "<connection-id>",
        "actionName": "<action_slug>",
        "input": { ... },
    },
)
```

---

## .env Configuration Template

```ini
COMPOSIO_API_KEY=comp_your_api_key_here

# Gmail
GMAIL_USER_1=j.karleek@gmail.com
GMAIL_USER_2=

# Outlook / Live.com
OUTLOOK_USER=jaroslav.karlik@live.com
OUTLOOK_USER_2=

# IMAP (klikni.org)
IMAP_SERVER=imap.zoner.com
IMAP_PORT=993
IMAP_USER=karlik@klikni.org
IMAP_PASSWORD=your_app_password
IMAP_VERIFY_SSL=true

# Reddit
REDDIT_USER=

# LinkedIn
LINKEDIN_USER=
```

---

## Quick Test

```bash
# Full test of all sources
python test_composio_unified.py

# Quick connectivity check only
python test_composio_unified.py --quick

# List connected sources only
python test_composio_unified.py --sources
```

---

## Integration Status (Subscription Manager)

| Source              | Email              | Composio Status | Last Verified |
|---------------------|--------------------|-----------------|---------------|
| Gmail               | j.karleek@gmail.com  | Active (80k msgs) | 2026-05-11  |
| Outlook / Live.com  | jaroslav.karlik@live.com | Active (10 msgs) | 2026-05-11  |
| IMAP / Zoner        | karlik@klikni.org     | Active (363 msgs) | 2026-05-11  |
| Reddit              | TBD                | Not connected   | –             |
| LinkedIn            | TBD                | Not connected   | –             |

> **Next step:** Connect Reddit & LinkedIn in [Composio Dashboard](https://app.composio.dev),
> then run `python test_composio_unified.py` again.
