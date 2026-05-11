# 🎯 Subscription Manager

A beautiful, full-stack web application for tracking all your subscriptions across cloud services, dev tools, streaming platforms, and more. Features intelligent email parsing and a stunning dashboard interface.

## ✨ Features

- **📧 Smart Email Parsing**: Automatically scans 3 mailboxes using Composio + Gmail API and IMAP
- **🧠 Intelligent Detection**: AI-powered logic to differentiate real subscriptions from ads
- **📊 Beautiful Dashboard**: Stunning visual interface with cost tracking and analytics
- **📱 Mobile-Friendly**: Responsive design that works on all devices
- **🎨 Cool Visuals**: Modern dark theme with gradients and smooth animations
- **📈 Cost Analytics**: Track monthly/yearly costs with detailed breakdowns
- **🏷️ Smart Categories**: Organize by Cloud, Dev Tools, AI, Streaming, Music, etc.
- **➕ Manual Entry**: Add offline services and subscriptions not found in emails

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Gmail account with API access
- Composio account (for advanced email parsing)

### Installation

1. **Clone and setup**:
```bash
cd c:\_dev\subscription_manager
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials:
# - COMPOSIO_API_KEY
# - Gmail credentials
# - IMAP settings for 3rd mailbox
```

3. **Initialize database**:
```bash
python main.py
```

4. **Start the application**:
```bash
python start_app.py
```

The app will automatically:
- Start the FastAPI backend on `http://localhost:8000`
- Start the frontend server on `http://localhost:3000`
- Open your browser to the dashboard

## 🎮 Usage

### Email Parsing
1. Click **"Parse Emails"** button in the top-right
2. The system will scan your configured mailboxes
3. AI logic identifies subscription emails vs. promotional content
4. New subscriptions are automatically added to your dashboard

### Manual Entry
1. Click **"+ Add Subscription"** button
2. Fill in service details (name, category, cost, etc.)
3. Subscription appears immediately in your dashboard

### Dashboard Navigation
- **Overview**: See all subscriptions with total costs
- **Categories**: Browse by Cloud, Dev Tools, AI, Streaming, etc.
- **Layout Toggle**: Switch between "Command center" and "Editorial bento" views

## 🏗️ Architecture

### Backend (`api.py`)
- **FastAPI** REST API with automatic documentation
- **SQLite** database for subscription storage
- **Composio** integration for Gmail parsing
- **IMAP** client for additional mailbox support
- **AI-powered** subscription detection logic

### Frontend (`frontend/`)
- **React** components with modern JSX
- **Beautiful UI** with Space Grotesk fonts and custom styling
- **Real-time** data fetching from backend API
- **Responsive** design for mobile and desktop

### Key Files
```
subscription_manager/
├── api.py              # FastAPI backend server
├── main.py             # Database initialization
├── imap_fetcher.py     # IMAP email client
├── start_app.py        # Application launcher
├── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html      # Main UI (React app)
│   ├── app.js          # Backend integration
│   └── *.js            # UI components
└── subscriptions.db    # SQLite database
```

## 🔧 Configuration

### Email Sources
The app supports 3 mailbox types:

1. **Primary Gmail** (via Composio)
   - Uses Gmail API for reliable access
   - Handles OAuth authentication
   - Best for personal Gmail accounts

2. **Secondary Gmail** (via Composio)
   - Second Gmail account support
   - Useful for business/work accounts

3. **IMAP Mailbox** (direct connection)
   - Any IMAP-compatible email provider
   - Outlook, Yahoo, custom domains
   - Configure in `.env` file

### Subscription Detection Logic
The AI logic identifies subscriptions by:
- **Email patterns**: "invoice", "receipt", "subscription", "billing"
- **Sender analysis**: Known service providers vs. marketing emails
- **Content analysis**: Actual charges vs. promotional offers
- **Frequency**: Regular billing cycles vs. one-time promotions

## 📊 API Endpoints

- `GET /subscriptions` - List all subscriptions
- `POST /subscriptions` - Add new subscription
- `PUT /subscriptions/{id}` - Update subscription
- `DELETE /subscriptions/{id}` - Delete subscription
- `POST /parse-emails` - Trigger email parsing
- `GET /stats` - Get cost statistics
- `GET /health` - Health check

Full API documentation available at `http://localhost:8000/docs`

## 🎨 Customization

### Adding Categories
Edit the `CATEGORIES` array in the frontend JavaScript files to add new subscription categories.

### Styling
The app uses a modern dark theme with:
- **Space Grotesk** font for headings
- **JetBrains Mono** for code/data
- **Custom gradients** and animations
- **Responsive** breakpoints

### Email Parsing Rules
Modify the subscription detection logic in `api.py` to customize how emails are classified as subscriptions vs. advertisements.

## 🚨 Troubleshooting

### Common Issues

**Email parsing not working?**
- Check your `.env` file has correct credentials
- Verify Composio API key is valid
- Test IMAP connection settings

**Frontend not loading?**
- Ensure both servers are running (backend:8000, frontend:3000)
- Check browser console for JavaScript errors
- Verify `app.js` is loading correctly

**Database errors?**
- Run `python main.py` to reinitialize the database
- Check file permissions on `subscriptions.db`

## 📝 License

This project is for personal use. Feel free to modify and extend for your own subscription tracking needs!

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome! The codebase is designed to be easily extensible for additional email providers, subscription services, and UI enhancements.