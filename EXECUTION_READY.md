# ✅ Subscription Manager - Live.com Connection Test EXECUTION READY

**Generated:** May 12, 2026 | **Status:** 🟢 READY FOR TESTING

---

## 🎯 Quick Start - Connection Test

### Phase 1: Verify Environment (2 minutes)
```bash
# 1. Create .env from template
cp .env.example .env

# 2. Edit .env - add COMPOSIO_API_KEY from https://app.composio.dev/settings
# COMPOSIO_API_KEY=comp_xxxxx
```

### Phase 2: Run Quick Check (1 minute)
```bash
python test_composio_unified.py --quick
```
**Expected:** Composio API [OK] + IMAP configured [OK]

### Phase 3: Full Integration Test (5 minutes)
```bash
python test_composio_unified.py
```
**Validates:** API, Gmail, Outlook/Live.com, IMAP

### Phase 4: Outlook-Specific Test (2 minutes)
```bash
python test_outlook_composio.py
```
**Expected:** Live.com account found + 10 emails listed

---

## 📋 Pre-Test Checklist

- [ ] `.env` file created from `.env.example`
- [ ] `COMPOSIO_API_KEY` filled with valid key
- [ ] Internet connection verified
- [ ] Python 3.8+ installed
- [ ] Dependencies installed
- [ ] Live.com account connected in Composio

---

## 🚨 Quick Troubleshooting

| Error | Solution |
|-------|----------|
| COMPOSIO_API_KEY error | Get key from https://app.composio.dev/settings |
| Live.com not connected | Add integration at https://app.composio.dev |
| HTTP 401 | API key expired, get new one |
| Cannot reach Composio | Check internet or Composio status |

---

## 📊 Success Metrics

| Test | Pass Criteria |
|------|------------------|
| API Connectivity | HTTP 200 response |
| Gmail Account | Found and accessible |
| Live.com Account | Found and accessible |
| Email Fetch | 5+ emails per account |
| IMAP Connection | Direct connection OK |
| Report Generated | connection_report.json created |

---

## ⏱️ Time Estimate

- Setup: 5 min
- Quick Test: 1 min
- Full Test: 5 min
- Outlook Test: 2 min
- **Total:** ~13 minutes

---

## 📁 Key Files

- `test_composio_unified.py` - Main test suite
- `test_outlook_composio.py` - Outlook-specific test
- `LIVE_COM_TEST_CHECKLIST.md` - Detailed guide
- `PROJECT_MEMORY.md` - Full documentation

---

## 🟢 Status: READY

✅ All preparation complete
✅ Test scripts verified
✅ Documentation comprehensive

**Next Command:**
```bash
python test_composio_unified.py --quick
```

---

*Prepared by: Cline AI Agent | Date: 2026-05-12 ✅*
