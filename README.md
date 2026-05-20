# 🎯 Subscription Manager

A beautiful, full-stack web application for tracking all your subscriptions across cloud services, dev tools, streaming platforms, and more. Features intelligent email parsing from Gmail, Outlook, and IMAP, with a stunning glass-morphism dashboard interface.

## ✨ Features

- **📧 Multi-Source Email Parsing**: Automatically scans 3 mailboxes (Gmail via Composio, Outlook via Composio, and direct IMAP).
- **🧠 Intelligent Detection**: Multi-layer `EmailClassifier` with confidence scoring, provider mapping (70+ known services), payment processor support (PayPal, Google Pay), and multi-currency extraction.
- **📊 Beautiful Dashboard**: Glass-morphism visual interface with cost tracking, category analytics, and time-based spend charts.
- **📱 Mobile-Friendly**: Responsive React frontend with Space Grotesk / JetBrains Mono typography.
- **📈 Cost Analytics**: Track monthly/yearly costs with detailed breakdowns by category (Cloud, AI, Streaming, Music, Dev Tools, Design, Gaming, Security, Productivity).
- **🏷️ Smart Categories**: Auto-categorizes subscriptions with 70+ known provider mappings.
- **➕ Manual Entry**: Add offline services and subscriptions not found in emails.
- **🔄 Incremental Sync**: Configurable sync jobs to keep subscription data fresh.
- **🗄️ Dual Database Support**: SQLite for local development, PostgreSQL for production.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Gmail/Outlook accounts with Composio OAuth connected
- IMAP access for third-party mailboxes (e.g., Zoner)

### Local Development

1. **Clone and setup**:
```bash
git clone https://github.com/jardaKarlik/Subs-Manager.git
cd Subs-Manager
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials (see Environment Variables below)
```

3. **Initialize database**:
```bash
python main.py
```

4. **Start the application**:
```bash
python start_app.py
# Or directly:
uvicorn api:app --host 0.0.0.0 --port 8000
```

The app will be available at `http://localhost:8000`.

---

## 🌐 Deployment (Railway)

This project is configured for one-click deployment on [Railway](https://railway.app/).

### Required Environment Variables

Configure these in your Railway dashboard before deploying:

| Variable | Description | Example |
|----------|-------------|---------|
| `COMPOSIO_API_KEY` | Your Composio API key | `ak_xxxxx` |
| `COMPOSIO_USER_ID` | Composio user identifier | `pg-test-xxxxx` |
| `GMAIL_ACCOUNT_ID` | Connected Gmail account ID from Composio | `gmail_xxxxx` |
| `GMAIL_USER_EMAIL` | Gmail address | `you@gmail.com` |
| `OUTLOOK_ACCOUNT_ID` | Connected Outlook account ID from Composio | `outlook_xxxxx` |
| `OUTLOOK_USER_EMAIL` | Outlook address | `you@live.com` |
| `IMAP_SERVER` | IMAP server hostname | `imap.zoner.com` |
| `IMAP_PORT` | IMAP port | `993` |
| `IMAP_USER` | IMAP username | `you@domain.com` |
| `IMAP_PASSWORD` | IMAP password | `xxxxx` |
| `IMAP_VERIFY_SSL` | Enable SSL verification | `false` (for self-signed certs) |
| `DATABASE_URL` *(optional)* | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `SYNC_MAX_RESULTS` *(optional)* | Default max emails per sync | `50000` |
| `SYNC_SINCE_DAYS` *(optional)* | Default lookback days | `365` |

> **Note:** If `DATABASE_URL` is not set, the app uses SQLite stored at `./subscriptions.db`.

### Deploy
```bash
railway up
```

---

## 🎮 Usage

### Initial Backfill
Populate your database with historical data from the last year:

```bash
# Full 1-year backfill (up to 50,000 emails per source)
curl -X POST https://your-app.up.railway.app/api/parse-emails -H "Content-Type: application/json" -d '{"max_results": 50000, "since_days": 365}'
```

### Incremental Sync
Run a smaller sync to catch recent invoices (default: last 3 days):

```bash
curl -X POST https://your-app.up.railway.app/api/sync-emails -H "Content-Type: application/json" -d '{"max_results": 500, "since_days": 3}'
```

### Check Status
```bash
curl https://your-app.up.railway.app/api/webhook/status
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│         Glass-morphism UI • Charts • Responsive             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend (api.py)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Subscription│  │ Email Fetcher│  │ Email Classifier│   │
│  │    CRUD     │  │  (3 sources) │  │ (Rule-based AI) │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQLAlchemy Async
┌────────────────────────▼────────────────────────────────────┐
│              SQLite (dev)  /  PostgreSQL (prod)              │
│    subscriptions  •  subscription_events  •  processed_emails│
└─────────────────────────────────────────────────────────────┘
```

### Backend Stack
- **FastAPI**: Async REST API with automatic OpenAPI docs (`/docs`)
- **SQLAlchemy 2.0**: Async ORM with declarative models
- **Composio SDK v2**: OAuth-based Gmail and Outlook email fetching
- **IMAPlib**: Direct IMAP for third-party mailboxes
- **EmailClassifier**: Rule-based engine with:
  - 70+ known provider mappings
  - Payment processor detection (PayPal, Google Pay, Apple Pay)
  - Czech bank support (ČSOB, Komerční banka, Fio, Airbank, Moneta, Raiffeisen)
  - Multi-currency extraction (USD, EUR, GBP, CZK)
  - Billing cycle detection (monthly/yearly/weekly/daily/one-time)
  - Confidence scoring (0.0–1.0)

### Database Schema

| Table | Purpose |
|-------|---------|
| `subscriptions` | Core subscription records with cost, billing cycle, category |
| `subscription_events` | Historical payment events for timeline charts |
| `processed_emails` | Deduplication tracker (message_id per source) |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check + endpoint list |
| `GET` | `/api/subscriptions` | Paginated subscription list (filter by category, status, search) |
| `POST` | `/api/subscriptions` | Add manual subscription |
| `GET` | `/api/subscriptions/{id}` | Get single subscription |
| `PUT` | `/api/subscriptions/{id}` | Update subscription |
| `DELETE` | `/api/subscriptions/{id}` | Delete subscription |
| `POST` | `/api/parse-emails` | **Full backfill** — parse emails from all sources |
| `POST` | `/api/sync-emails` | **Incremental sync** — recent emails only |
| `GET` | `/api/events` | Historical payment events for charts |
| `GET` | `/api/stats` | Aggregated cost statistics by category & status |
| `GET` | `/api/summary` | Summary with cost calculations |
| `GET` | `/api/categories` | List all categories in use |
| `GET` | `/api/webhook/status` | Status message for Discord/Make.com |
| `POST` | `/api/cleanup?days=730` | Delete old data (retention) |
| `POST` | `/api/add-test-data` | Seed test subscriptions |

---

## 🔧 Project Structure

```
subscription_manager/
├── api.py                  # FastAPI app + endpoints
├── email_fetcher.py        # Gmail/Outlook/IMAP fetching + batch processing
├── email_parser.py         # EmailClassifier — detection engine
├── database.py             # SQLAlchemy models + session management
├── main.py                 # CLI entry point (init + test)
├── start_app.py            # Development server launcher
├── requirements.txt        # Python dependencies
├── railway.toml            # Railway deployment config
├── .env.example            # Environment variable template
├── frontend/               # React frontend (legacy)
├── frontend_glass/         # Glass-morphism React frontend
├── alembic/                # Database migrations
└── memory/                 # Self-improving agent memory (experimental)
```

---

## 🐛 Troubleshooting

### Emails show 0 processed / 0 amount detected
- Check that Composio OAuth is connected for Gmail/Outlook
- Verify IMAP credentials in environment variables
- Check app logs: `railway logs`

### Duplicate subscriptions appearing
- The deduplication relies on `ProcessedEmail` table. If using SQLite, ensure the app has write permissions.
- Each email source uses a unique `message_id` format: `gmail:{id}`, `outlook:{id}`, `imap:{id}`.

### Database shows 0 emails processed but events exist
- The `total_emails_processed` counter in `/api/webhook/status` counts `ProcessedEmail` records.
- If deduplication fails (see above), emails are re-processed and events are created, but the processed counter does not increment.

### Sync request times out
- Large backfills (50k emails / 365 days) can take several minutes.
- The API request may timeout at 30s, but the worker continues processing in the background.
- Monitor progress via `/api/events` and `/api/stats`.

### Currency not detected
- Supported currencies: USD (`$`), EUR (`€`), GBP (`£`), CZK (`Kč`)
- Amount patterns expect formats like `$15.99`, `€19,00`, `Kč209,00`

---

## 📝 License

This project is for personal use. Feel free to modify and extend it for your own subscription tracking needs!
