# 🧪 Live.com Connection Test - Complete Checklist

## 📋 Pre-Test Requirements

### 1. Environment Setup
- [ ] `.env` file created with valid COMPOSIO_API_KEY
- [ ] All required Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Internet connection verified
- [ ] Composio account active and valid (https://app.composio.dev)

### 2. Live.com Account Setup in Composio
- [ ] Logged into https://app.composio.dev
- [ ] Clicked "Add Integration" or "Connect"
- [ ] Selected Microsoft Outlook or Microsoft 365 integration
- [ ] Signed in with jaroslav.karlik@live.com
- [ ] Authorized all requested permissions (email read access)
- [ ] Verified connection shows as "CONNECTED" or "ACTIVE"

### 3. Configuration Verification
```
✓ COMPOSIO_API_KEY = comp_[actual_key] (not placeholder)
✓ Email account = jaroslav.karlik@live.com
✓ Connection ID = [visible in Composio dashboard]
✓ Status = CONNECTED
```

---

## 🚀 Test Execution Steps

### Step 1: Quick Connectivity Check
```bash
python test_composio_unified.py --quick
```
**Expected Output:**
- Composio API: [OK]
- IMAP configured: [OK]

**Success Criteria:** Both show [OK]

---

### Step 2: Full Connection Test
```bash
python test_composio_unified.py
```
**Key Success Points:**
- ✅ Composio API: [OK]
- ✅ Gmail: [OK] with profile and 5 messages
- ✅ Outlook (Live.com): [OK] with 10 emails fetched
- ✅ IMAP: [OK] with INBOX count
- ✅ connection_report.json created

---

### Step 3: Specific Live.com Email Fetch Test
```bash
python test_outlook_composio.py
```
**Success Criteria:**
- ✅ Outlook account found in Composio
- ✅ Successfully fetched 1+ emails
- ✅ Email details displayed (From, Subject, Date)

---

## ✅ Verification Checklist

- [ ] API Key is valid (HTTP 200)
- [ ] Live.com account is connected
- [ ] Can fetch email list
- [ ] Emails have proper fields
- [ ] Reports generated
- [ ] No critical errors

---

## 📊 Success Metrics

| Component | Status | Notes |
|-----------|--------|-------|
| Composio API | ✅ | Connected and authenticated |
| Live.com Account | ✅ | Found and accessible |
| Email Fetch | ✅ | 10+ emails retrieved |
| IMAP Fallback | ✅ | Working as backup |
| Report Generation | ✅ | JSON reports created |

---

## 🚨 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| COMPOSIO_API_KEY error | Get key from https://app.composio.dev/settings |
| Live.com not connected | Visit https://app.composio.dev and add integration |
| HTTP 401 | API key expired, get new one |
| HTTP 404 | Action unavailable in this Composio version |
| Connection timeout | Check internet or Composio status |

---

## 📝 Next Steps

1. ✅ Run Quick Test: `python test_composio_unified.py --quick`
2. ✅ Run Full Test: `python test_composio_unified.py`
3. ✅ Run Outlook Test: `python test_outlook_composio.py`
4. ✅ Review Reports: Check connection_report.json
5. ✅ Proceed with Email Sync: `python run_initial_sync.py`

---

**Status: READY FOR TESTING** ✅
