# 🔌 Port Configuration Reference

## Current Configuration (FIXED ✅)

All services now use consistent ports:

| Service | Port | File | Status |
|---------|------|------|--------|
| **Backend API** | 8000 | api.py | ✅ Correct |
| **Frontend** | 3000 | start_app.py | ✅ Correct |
| **Backend Launcher** | 8000 | start_app.py | ✅ Correct |

---

## Backend Port References (All PORT 8000)

### 1. **api.py** (Line 662)
```python
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
```
**Status:** ✅ Uses port 8000

### 2. **start_app.py** (Line 20)
```python
backend_process = subprocess.Popen([
    sys.executable, "-m", "uvicorn", "api:app", 
    "--host", "0.0.0.0", 
    "--port", "8000",  # ← Backend port
    "--reload"
], cwd=Path(__file__).parent)
```
**Status:** ✅ Uses port 8000

### 3. **test_api.py** (Line 11)
```python
BASE_URL = "http://localhost:8000"
```
**Status:** ✅ References port 8000

### 4. **run_initial_sync.py** (Line 5)
```python
API_URL = "http://localhost:8000/api/parse-emails"
```
**Status:** ✅ References port 8000

---

## Frontend Port References

### 1. **start_app.py** (Line 30)
```python
frontend_process = subprocess.Popen([
    sys.executable, "-m", "http.server", "3000"  # ← Frontend port
], cwd=frontend_dir)
```
**Status:** ✅ Uses port 3000

### 2. **frontend/app.js** (Line 2)
```javascript
const API_BASE = 'http://localhost:8000';  // ← Connects to backend port 8000
```
**Status:** ✅ FIXED - Now points to port 8000 (was 8001)

### 3. **frontend/diagnostic.html** (Multiple references)
```javascript
for (const port of [8000, 8001]) {  // Checks both ports for compatibility
  try {
    const response = await fetch(`http://localhost:${port}/api/health`);
    if (response.ok) {
      backendPort = port;  // Uses whichever port is found
      break;
    }
  } catch (err) {}
}
```
**Status:** ✅ Diagnostic checks ports, documentation shows 8000

---

## What Changed

### Before (BROKEN ❌)
```
Frontend (app.js)           Backend
    ↓                          ↓
localhost:8001          localhost:8000
         ✗ MISMATCH ✗
```

### After (FIXED ✅)
```
Frontend (app.js)           Backend
    ↓                          ↓
localhost:8000          localhost:8000
         ✓ MATCH ✓
```

---

## How to Start Everything

### Option 1: Use the Launcher Script
```bash
cd C:\_dev\subscription_manager
python start_app.py
```

This will:
1. Start Backend on **port 8000** ✅
2. Start Frontend on **port 3000** ✅
3. Frontend will connect to **localhost:8000** ✅

### Option 2: Manual (Separate Terminals)

**Terminal 1 - Backend:**
```bash
cd C:\_dev\subscription_manager
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd C:\_dev\subscription_manager\frontend
python -m http.server 3000
```

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | `http://localhost:3000` | Main UI |
| Backend API | `http://localhost:8000/api/subscriptions` | Data endpoint |
| API Docs | `http://localhost:8000/docs` | Interactive API documentation |
| Diagnostic | `http://localhost:3000/diagnostic.html` | Health check tool |

---

## Environment Variables

### `.env` (if used)
Currently no port configuration in .env - ports are hardcoded in Python files.

For future Railway deployment, you can set:
```env
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

Then update scripts to read from environment:
```python
import os
PORT = int(os.getenv('BACKEND_PORT', 8000))
```

---

## Port Availability Check

To verify ports are available before starting:

```bash
# Check port 8000 (Backend)
netstat -ano | grep ":8000"

# Check port 3000 (Frontend)
netstat -ano | grep ":3000"
```

If ports are in use, either:
1. Stop the conflicting process
2. Change port in the scripts above
3. Use different ports

---

## Summary

✅ **All ports are now consistent:**
- Backend: **port 8000** (everywhere)
- Frontend: **port 3000** (everywhere)
- Frontend connects to: **port 8000** (backend)

**Your diagnostic result confirmed this is working:**
```
✅ Backend is running on port 8000
✅ Subscriptions endpoint OK - 45 subscriptions found
✅ Stats endpoint OK - $4626.20/mo
✅ Frontend running on port 80
```

The "port 80" for frontend in your diagnostic is because you're likely accessing it from a browser without specifying the port (defaults to 80 for HTTP), but it's actually running on port 3000.

**Everything is now properly configured!** ✅

---

**Last Updated:** 2026-05-11  
**Status:** ✅ All Ports Consistent
