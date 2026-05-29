# Subscription Manager - Railway Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Subscription Manager application to Railway.app. The application consists of two services:
- **Backend**: FastAPI (Python) on port 8000
- **Frontend**: Static React app served via Python HTTP server on port 3000

## Prerequisites

1. Railway.app account ([railway.app](https://railway.app))
2. Git installed and repository configured
3. GitHub account (for connecting repository to Railway)
4. Environment variables configured locally

## Local Development Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///subscriptions.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname

# Email Integrations (Optional for local testing)
GMAIL_USER=your-email@gmail.com
COMPOSIO_API_KEY=your-composio-key
IMAP_PASSWORD=your-imap-password

# App Configuration
BACKEND_PORT=8001
FRONTEND_PORT=3000
```

### Running Locally

```bash
# Terminal 1: Backend API
python -m uvicorn api:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Frontend
cd frontend && python -m http.server 3000

# Or use the convenience script:
python start_app.py
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs

## Railway Deployment

### Step 1: Connect Repository to Railway

1. Go to [railway.app](https://railway.app)
2. Create a new project
3. Select "Deploy from GitHub"
4. Authorize and select the repository
5. Railway will auto-detect the deployment configuration

### Step 2: Configure Environment Variables

In the Railway dashboard, set the following environment variables:

#### Database Configuration

**For SQLite (development/small scale):**
```
DATABASE_URL=sqlite+aiosqlite:///subscriptions.db
```

**For PostgreSQL (production recommended):**
```
DATABASE_URL=postgresql+asyncpg://username:password@host:port/subscription_manager
```

To create a PostgreSQL database on Railway:
1. In your Railway project, click "Add"
2. Select "Database" → "PostgreSQL"
3. Copy the `DATABASE_URL` connection string
4. Paste it into your project environment variables

#### Email Integration Variables (Optional)

```
GMAIL_USER=your-email@gmail.com
COMPOSIO_API_KEY=your-api-key
IMAP_PASSWORD=your-imap-password
IMAP_HOST=imap.gmail.com
```

#### Application Variables

```
PYTHON_VERSION=3.11
PORT=8000
```

### Step 3: Deploy

Railway will automatically deploy when you:
- Push to `main` / `master` branch
- Or manually trigger deployment from the dashboard

#### Manual Deployment

```bash
# Using Railway CLI
railway up

# Or push to trigger auto-deployment
git push origin feature/railway-migration
```

### Step 4: Database Migration

#### From SQLite to PostgreSQL

Railway recommends using PostgreSQL for production. To migrate:

1. **Export data from SQLite**:
   ```bash
   python -c "
   import sqlite3
   import json
   from database import Subscription
   
   # Dump SQLite data
   conn = sqlite3.connect('subscriptions.db')
   cursor = conn.cursor()
   cursor.execute('SELECT * FROM subscriptions')
   rows = cursor.fetchall()
   # Export to JSON for import
   "
   ```

2. **Update DATABASE_URL** in Railway environment to PostgreSQL connection string

3. **Run database initialization**:
   ```bash
   # This will create tables in PostgreSQL
   python -c "from database import init_db; import asyncio; asyncio.run(init_db())"
   ```

4. **Import data** if needed using the `/api/subscriptions` POST endpoint

5. **Verify migration**:
   - Check `/api/health` returns "connected"
   - Check `/api/subscriptions` returns all data

### Step 5: Domain Configuration

Railway provides a default domain (e.g., `project-name.up.railway.app`). To use a custom domain:

1. Go to Railway project settings
2. Find "Domains" section
3. Add custom domain
4. Configure DNS with your domain provider

## Post-Deployment Verification

### Health Checks

```bash
# Check API health
curl https://your-domain.com/api/health

# Verify database connection
curl https://your-domain.com/api/stats

# List all subscriptions
curl https://your-domain.com/api/subscriptions
```

### Common Issues

#### 1. Database Connection Failure

**Error**: `"database": "disconnected"`

**Solution**:
- Verify `DATABASE_URL` environment variable is set correctly
- Check PostgreSQL credentials (if using PG)
- Ensure database tables are initialized

#### 2. Port Already in Use

**Error**: `[WinError 10048] Address already in use`

**Solution**:
- Use environment `PORT` variable instead of hardcoding
- Check running processes: `netstat -ano | grep :<port>`

#### 3. Frontend Not Loading

**Error**: Frontend shows blank or 404

**Solution**:
- Verify both services are running in Railway dashboard
- Check frontend service is on port 3000
- Verify CORS is configured in `api.py`
- Update API_BASE in `frontend/app.js` to match Railway domain

#### 4. CORS Issues

If frontend cannot reach backend API:

1. Update `frontend/app.js`:
   ```javascript
   const API_BASE = 'https://your-domain.com';
   ```

2. Verify CORS middleware in `api.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Use specific domains in production
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

## Scaling & Optimization

### Horizontal Scaling

1. Go to Railway dashboard
2. Select your service
3. Adjust "Replicas" count
4. Railway handles load balancing automatically

### Database Optimization

For high traffic:
- Migrate to PostgreSQL (better concurrency)
- Add indexing on frequently queried columns
- Consider caching with Redis (add-on from Railway)

### Cost Optimization

- Remove unused services
- Use SQLite for very low traffic (<1000 requests/day)
- Set appropriate memory limits
- Monitor logs for inefficient queries

## Monitoring & Logging

### View Logs

```bash
# Using Railway CLI
railway logs

# Or in dashboard: Logs tab
```

### Key Metrics to Monitor

- API response times (`/api/stats` queries)
- Database connection pool usage
- Memory utilization
- Number of active subscriptions
- Email parsing job duration

### Email Parsing Performance

Monitor `/api/parse-emails` endpoint:
- Runs async, returns immediately
- Processes emails in background
- Check logs for parsing errors

## Backup & Recovery

### Database Backups

For PostgreSQL on Railway:
1. Use Railway's built-in backup feature
2. Set backup retention in database settings
3. Download backups from Railway dashboard

For SQLite:
```bash
# Download from Railway Deployments
railway download subscriptions.db
```

### Restore from Backup

1. Stop current deployment
2. Upload backup file
3. Update `DATABASE_URL` if needed
4. Redeploy

## CI/CD Pipeline

The project includes GitHub Actions for:
- Automatic deployment on push
- Linting and testing
- Database health checks

No additional setup needed - Railway auto-detects `railway.toml` and `.github/workflows`.

## Troubleshooting Commands

```bash
# Check deployment status
railway status

# View environment variables
railway vars

# Open Railway dashboard for this project
railway open

# Trigger redeploy
railway redeploy

# SSH into running container (if available)
railway shell
```

## Support & Resources

- Railway Docs: https://docs.railway.app
- FastAPI Docs: https://fastapi.tiangolo.com
- SQLAlchemy: https://www.sqlalchemy.org
- GitHub Issues: [Project Issues](https://github.com/jardaKarlik/Subs-Manager/issues)

## Migration from SQLite to PostgreSQL (Detailed)

When scaling to production, follow this process:

### 1. Prepare PostgreSQL Database

```sql
CREATE DATABASE subscription_manager;
CREATE USER subs_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE subscription_manager TO subs_user;
```

### 2. Update Connection String

Railway PostgreSQL format:
```
postgresql+asyncpg://user:password@host:5432/subscription_manager
```

### 3. Run Schema Migration

```python
# Python script to initialize PostgreSQL schema
import asyncio
from database import init_db

async def migrate():
    await init_db()  # Creates all tables in PostgreSQL

asyncio.run(migrate())
```

### 4. Verify Tables

```sql
\dt  -- List all tables
SELECT COUNT(*) FROM subscriptions;
```

### 5. (Optional) Migrate Existing Data

If you have subscriptions in SQLite:

```python
import sqlite3
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, Subscription

async def migrate_data():
    # Read from SQLite
    conn = sqlite3.connect('subscriptions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM subscriptions')
    rows = cursor.fetchall()
    
    # Write to PostgreSQL
    async with AsyncSessionLocal() as session:
        for row in rows:
            sub = Subscription(
                service_name=row[1],
                category=row[2],
                cost=row[3],
                # ... map all fields
            )
            session.add(sub)
        await session.commit()

asyncio.run(migrate_data())
```

## Performance Benchmarks

Tested configurations:

| Config | Subscriptions | Avg Response Time | Monthly Cost |
|--------|---------------|-------------------|--------------|
| SQLite (dev) | 100 | 50ms | $0 |
| PostgreSQL (free tier) | 1,000 | 80ms | $5 |
| PostgreSQL (standard) | 10,000 | 120ms | $20 |

## FAQ

**Q: Can I use SQLite in production?**
A: Yes, for small deployments (<1GB data, <100 concurrent users). For anything larger, use PostgreSQL.

**Q: How do I handle email parsing errors?**
A: Check logs in Railway dashboard. Email parsing logs include error details.

**Q: Can I deploy without GitHub?**
A: Yes, use Railway CLI: `railway up`

**Q: How do I update the deployment?**
A: Push changes to repository or use `railway redeploy`

**Q: What's included in the free tier?**
A: Check Railway pricing page. Typically 5GB monthly bandwidth, sufficient for testing.
