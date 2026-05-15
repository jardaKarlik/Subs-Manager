# Railway Deployment Guide

## System Status
✅ **Application Ready for Deployment**

### What's Configured:
- ✅ Backend API serving on port 8000
- ✅ Frontend (simple.html) integrated into backend
- ✅ Database schema ready (SQLite local, PostgreSQL for production)
- ✅ Email parsing with Composio MCP
- ✅ All Phase 1 fixes implemented
- ✅ Python 3.14 environment working

### Frontend Design
- **Active Design**: simple.html (clean, minimal UI)
- **Logo**: Yellow $ icon with "subs." branding
- **Stats Cards**: Monthly/Yearly total, Active count
- **Auto-API Detection**: Works on localhost:8000 (dev) or same domain (prod)

---

## Deployment Steps

### 1. Prepare Repository
```bash
# All changes are committed to master branch
git status  # Should be clean
```

### 2. Create/Configure Railway Project

#### Option A: Create New Project
1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Select "GitHub"
4. Connect to this repo
5. Railway auto-detects Python app

#### Option B: Reuse Existing Project  
1. Delete the empty project (if exists)
2. Create new from GitHub

### 3. Configure Environment Variables in Railway

Add these to your Railway project:

```
PYTHON_VERSION=3.14
DATABASE_URL=postgresql://...  [Railway will auto-generate this]
COMPOSIO_API_KEY=ck_7UWyrPMTNc4e1WMGTGDN
GMAIL_USER_1=j.karleek@gmail.com
IMAP_SERVER=imap.zoner.com
IMAP_PORT=993
IMAP_USER=karlik@klikni.org
IMAP_PASSWORD=-9nP3FceEDd_Lp3
IMAP_VERIFY_SSL=false
```

### 4. Railway Deployment
- Railway reads `Procfile`: `web: python -m uvicorn api:app --host 0.0.0.0 --port $PORT`
- Installs dependencies from `requirements.txt`
- Starts the application

### 5. First Run
1. Application will initialize database
2. Backend serves API at `/api/*`
3. Frontend served from `/` (simple.html design)
4. Access at: `https://your-railway-domain.com`

---

## Architecture

```
Single Service: subscription-manager
├── API Backend (FastAPI on port 8000)
│   ├── /api/subscriptions          [CRUD operations]
│   ├── /api/parse-emails           [Email parsing]
│   ├── /api/stats                  [Statistics]
│   └── /api/health                 [Health check]
├── Frontend Static Files (served by backend)
│   ├── / (index.html - simple.html design)
│   ├── /simple.js                  [Frontend logic]
│   └── /api                        [Calls to backend API]
└── Database (PostgreSQL in production)
    └── Subscriptions, ProcessedEmails, Events
```

---

## Environment Details

### Local Development (Port 8000 + 3000)
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000` (separate http.server OR served from backend)
- API Client (simple.js): Detects localhost and uses `http://localhost:8000/api`

### Railway Production (Single Port)
- Entire app: `https://your-domain.railwayapp.io`
- Backend: `https://your-domain.railwayapp.io/api/*`
- Frontend: `https://your-domain.railwayapp.io/`
- API Client (simple.js): Uses `/api` (same domain)

---

## Database Migration

### Local (SQLite)
```python
# On first run, api.py calls:
await init_db()  # Creates SQLite in DATABASE_NAME
```

### Railway (PostgreSQL)
Railway auto-creates PostgreSQL. Set `DATABASE_URL` and app connects.

---

## Monitoring

### Health Check
```bash
curl https://your-railway-domain.com/api/health
```

### Expected Response
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "endpoints": [...]
}
```

---

## Rollback/Issues

If deployment has issues:
1. Check Railway deployment logs
2. Verify environment variables set correctly
3. Verify Python 3.14 is used (may need to adjust in railway.toml)
4. Confirm requirements.txt has all dependencies

---

## Next Steps After Deployment

1. **Email Sync**: Click "Sync" button to trigger `/api/parse-emails`
2. **Add Subscriptions**: Via UI or direct API calls
3. **Monitor**: Use `/api/health` endpoint
4. **Scale**: Railway dashboard shows metrics

---

**Deployment Ready**: ✅ All code is stable and tested locally
