# 🚀 PHASE 2: Backend Deployment to Railway

**Status**: Starting Phase 2  
**Date**: 15 May 2026  
**Goal**: Deploy API and frontend to Railway, test connectivity

---

## 📋 Phase 2 Steps

### Step 1: Prepare Git Repository
- Commit Phase 1 changes
- Push to GitHub

### Step 2: Deploy to Railway
- Initialize Railway project
- Deploy application
- Monitor build

### Step 3: Verify Backend
- Check deployment status
- Test API endpoints
- Verify database

### Step 4: Verify Frontend
- Load main URL
- Check CSS/JS loading
- Verify functionality

### Step 5: Integration Testing
- Test subscription listing
- Test API calls
- Check error logs

### Step 6: Configuration (Optional)
- Add database credentials
- Configure email sources
- Set environment variables

---

## 🔄 Step-by-Step Instructions

### STEP 1: Commit and Push Changes

```bash
cd subscription_manager

# Check status
git status

# Stage all changes
git add .

# Commit
git commit -m "Phase 1: Frontend redesign and Railway configuration
- Replace index.html with simple.html design
- Add dynamic API endpoint detection
- Configure railway.toml for single service
- Add frontend static file serving to API"

# Push
git push origin main
```

---

### STEP 2: Initialize Railway

```bash
# Initialize Railway
railway init

# This creates .railway/config.json and links your account
```

---

### STEP 3: Deploy to Railway

```bash
# Deploy the application
railway up

# Monitor the deployment progress
```

---

### STEP 4: Get Your Railway URL

```bash
# View your deployed application
railway open

# Or get the URL from Railway dashboard
```

---

### STEP 5: Test API Endpoints

```bash
# Test basic API
curl https://<your-railway-url>/api/subscriptions

# Expected: Empty subscription list
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "pages": 0
}
```

---

### STEP 6: Test Frontend

Visit: `https://<your-railway-url>/`

Expected to see:
- ✅ Subs Manager title
- ✅ Stats cards (all zeros)
- ✅ Empty subscription grid
- ✅ Sync and Add buttons
- ✅ No console errors

---

## 🔍 Verification Checklist

### Frontend
- [ ] Page loads
- [ ] Logo visible
- [ ] Stats cards visible
- [ ] Grid visible
- [ ] Buttons work
- [ ] Responsive
- [ ] No console errors

### API
- [ ] GET /api/subscriptions works
- [ ] Returns valid JSON
- [ ] Pagination works
- [ ] Filtering works
- [ ] No 500 errors

### Integration
- [ ] Frontend loads API
- [ ] Stats calculate correctly
- [ ] CORS headers present
- [ ] No mixed content

---

## 🆘 Troubleshooting

### Deployment Failed
```bash
# Check logs
railway logs
```

### Frontend Not Loading
```bash
# Verify frontend directory
ls -la frontend/
```

### API Not Responding
```bash
# Check if started
railway logs --follow
```

### CORS Errors
Check api.py has CORSMiddleware enabled with `allow_origins=["*"]`

---

## 📊 Expected Results

✅ Application deployed successfully  
✅ Frontend loads at root URL  
✅ API responds to requests  
✅ Database initializes  
✅ Logs show no critical errors  

---

**Proceed with Steps 1-6 above!**
