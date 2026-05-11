# 🎯 Subscription Manager

A beautiful, full-stack web application for tracking all your subscriptions across cloud services, dev tools, streaming platforms, and more. Features intelligent email parsing and a stunning dashboard interface.

## ✨ Features

- **📧 Smart Email Parsing**: Automatically scans 3 mailboxes (Gmail, Outlook, and IMAP) using Composio and direct IMAP.
- **🧠 Intelligent Detection**: Multi-layer `EmailClassifier` with confidence scoring, provider mapping, and payment processor support.
- **📊 Beautiful Dashboard**: Stunning visual interface with cost tracking, analytics, and time-based spend charts.
- **📱 Mobile-Friendly**: Responsive design built with React and Space Grotesk/JetBrains Mono fonts.
- **📈 Cost Analytics**: Track monthly/yearly costs with detailed category breakdowns.
- **🏷️ Smart Categories**: Organized by Cloud, Dev Tools, AI, Streaming, Music, Music Tools, Design, Productivity, Gaming, and Security.
- **➕ Manual Entry**: Add offline services and subscriptions not found in emails.
- **🔄 Incremental Sync**: Every-3-day sync job to keep your subscription data fresh.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Gmail/Outlook accounts with Composio access
- IMAP access for your 3rd mailbox (e.g., Zoner)

### Installation

1. **Clone and setup**:
```bash
git clone https://github.com/jardaKarlik/Subs-Manager.git
cd Subs-Manager
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials:
# - COMPOSIO_API_KEY
# - IMAP settings (server, port, user, password)
```

3. **Initialize database**:
```bash
python main.py
```

4. **Start the application**:
```bash
python start_app.py
```

## 🎮 Usage

### Initial Backfill
To populate your database with historical data from the last year, trigger the backfill via the API:
```bash
# Full 1-year backfill (default 1000 emails per source)
curl -X POST http://localhost:8000/api/parse-emails -H "Content-Type: application/json" -d '{"max_results": 2000, "since_days": 365}'
```

### Regular Sync
Run the incremental sync every 3 days to catch new invoices:
```bash
# Sync last 3 days
curl -X POST http://localhost:8000/api/sync-emails
```

## 🏗️ Architecture

### Backend (`api.py` & `email_fetcher.py`)
- **FastAPI**: REST API with async SQLAlchemy and SQLite/PostgreSQL support.
- **Composio**: Integration for Gmail and Outlook email fetching.
- **IMAP**: Direct connection for third-party mailboxes.
- **EmailClassifier**: Rule-based engine with multi-currency extraction and confidence scoring.

### Database (`database.py`)
- **Subscription**: Core service records.
- **SubscriptionEvent**: Historical payment records for charting.
- **ProcessedEmail**: Deduplication tracker.

## 📊 API Endpoints

- `GET /api/subscriptions` - Paginated subscription list
- `POST /api/parse-emails` - Full 1-year backfill
- `POST /api/sync-emails` - 3-day incremental sync
- `GET /api/events` - Historical spend data for charts
- `POST /api/cleanup` - Data retention management (2-year cap)
- `GET /api/stats` - Comprehensive cost analytics

## 📝 License
This project is for personal use. Feel free to modify and extend it for your own subscription tracking needs!
