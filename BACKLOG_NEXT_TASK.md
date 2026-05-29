# 📋 BACKLOG TASK: Execute Live.com Connection Test & Email Sync

**Task ID:** SUB-MANAGER-V1-02  
**Status:** 🔄 READY FOR BACKLOG  
**Priority:** HIGH  
**Sprint:** V1 Launch  
**Estimated Time:** 2-3 hours

---

## 🎯 Objective

Execute Live.com/Outlook connection test, validate email sync, and confirm V1 production readiness.

---

## 📝 Task Description

### Phase 1: Connection Test Execution (30 min)

**Goal:** Validate all 3 email integrations

**Steps:**
1. Setup environment
   ```bash
   cd C:/_dev/subscription_manager
   cp .env.example .env
   # Add COMPOSIO_API_KEY to .env
   ```

2. Quick connectivity check
   ```bash
   python test_composio_unified.py --quick
   ```
   Expected: Composio API [OK] + IMAP [OK]

3. Full integration test
   ```bash
   python test_composio_unified.py
   ```
   Expected: Gmail ✅ + Outlook ✅ + IMAP ✅

4. Outlook-specific test
   ```bash
   python test_outlook_composio.py
   ```
   Expected: Live.com account + 10+ emails

5. Review connection report
   ```bash
   cat connection_report.json
   ```
   Verify all 3 sources connected

**Success Criteria:**
- ✅ Composio API responds with 200 OK
- ✅ Gmail: 5+ emails fetched
- ✅ Outlook: 10+ emails fetched
- ✅ IMAP: Connection established
- ✅ connection_report.json generated

---

### Phase 2: Email Sync Validation (45 min)

**Goal:** Validate email fetching and subscription parsing

**Steps:**
1. Run initial email sync
   ```bash
   python run_initial_sync.py
   ```

2. Check database for subscriptions
   ```bash
   python -c "from database import Subscription, SessionLocal; \
   db = SessionLocal(); \
   subs = db.query(Subscription).all(); \
   print(f'Total: {len(subs)}'); \
   [print(f'  - {s.service_name} (${s.monthly_cost}/mo)') for s in subs[:10]]"
   ```

3. Start API server
   ```bash
   python api.py
   ```

4. Test API endpoints
   ```bash
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/subscriptions
   curl http://localhost:8000/api/stats
   ```

5. Test frontend
   - Open http://localhost:3000
   - Verify subscriptions display
   - Check mobile responsiveness

**Success Criteria:**
- ✅ Initial sync completes
- ✅ Database contains 10+ subscriptions
- ✅ Cost calculations correct
- ✅ API endpoints return 200 OK
- ✅ Frontend displays data

---

### Phase 3: Data Quality Validation (30 min)

**Goal:** Ensure parsing accuracy and cost tracking

**Steps:**
1. Review parsed subscriptions
   - Check for duplicates
   - Verify costs
   - Confirm categories

2. Test manual entry
   - Add subscription via UI
   - Verify save
   - Check totals updated

3. Test cost calculations
   - Verify monthly total
   - Verify yearly total
   - Check category breakdown

**Success Criteria:**
- ✅ No duplicates
- ✅ Costs accurate
- ✅ Categories correct
- ✅ Manual entry works
- ✅ Calculations correct

---

### Phase 4: Documentation & Handoff (15 min)

**Goal:** Document results and update project memory

**Steps:**
1. Create test results report
2. Update PROJECT_MEMORY.md
3. Create deployment checklist
4. Commit changes

---

## ⏱️ Time Breakdown

| Phase | Time |
|-------|------|
| Connection Test | 30 min |
| Email Sync | 45 min |
| Data Quality | 30 min |
| Documentation | 15 min |
| **Total** | **120 min** |

---

## ✅ Acceptance Criteria

- [ ] All connection tests pass
- [ ] 20+ subscriptions in database
- [ ] API endpoints responsive
- [ ] Frontend displays correctly
- [ ] Mobile UI works
- [ ] Cost calculations accurate
- [ ] No duplicates
- [ ] All changes committed

---

## 📚 Related Documentation

- EXECUTION_READY.md
- LIVE_COM_TEST_CHECKLIST.md
- LIVE_COM_READY_TO_TEST.md
- PROJECT_MEMORY.md
- TESTING_GUIDE.md

---

**Created:** May 12, 2026  
**Status:** Ready for Backlog  
**Priority:** HIGH - V1 Launch Path
