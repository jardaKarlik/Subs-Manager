# UI Enhancements - Testing Guide

**Status**: Ready for testing  
**Component**: GlassCard.jsx  
**Date**: May 29, 2026

---

## Quick Start: How to Test in 5 Minutes

### Step 1: Navigate to Frontend Directory
```bash
cd /home/jaros/.cline/worktrees/1da01/subs-manager/frontend_glass
```

### Step 2: Install Dependencies (if not done)
```bash
npm install
```
This will take 2-3 minutes first time.

### Step 3: Start Backend (in separate terminal)
```bash
cd /home/jaros/.cline/worktrees/1da01/subs-manager
python api.py
```
Backend will run on http://localhost:8000

### Step 4: Start Frontend Development Server
```bash
# Still in frontend_glass directory
npm run dev
```
Frontend will start on http://localhost:5173

### Step 5: Open in Browser
```
http://localhost:5173
```

---

## Visual Testing Checklist

### Test 1: Expiration Warning Badges ✅

**Objective**: Verify warning badges appear correctly

**Steps**:
1. Open dashboard in browser
2. Look for subscriptions with `next_billing_date` 1-7 days away
3. **Verify**:
   - [ ] Amber badge appears in top-right
   - [ ] Badge shows "⚠ Renews in Xd" text
   - [ ] Badge has semi-transparent amber background
   - [ ] Badge position doesn't overlap with annual cost

**Expected Result**: Amber badges visible on cards expiring soon

---

### Test 2: Expired Subscriptions Badge ✅

**Objective**: Check expired subscription display

**Steps**:
1. Find a subscription with `next_billing_date` in the past
2. **Verify**:
   - [ ] Red badge appears "🔴 Expired"
   - [ ] Badge has semi-transparent red background
   - [ ] Billing progress bar is hidden
   - [ ] Countdown text shows "Expired" in red

**Expected Result**: Red expired badge clearly visible

---

### Test 3: Billing Cycle Progress Bar ✅

**Objective**: Test progress bar animation and styling

**Steps**:
1. Select a subscription expiring in 14+ days
2. **Verify**:
   - [ ] Progress bar visible below cost
   - [ ] Shows percentage label (e.g., "55%")
   - [ ] Bar width matches percentage
   - [ ] Bar color is category gradient (not amber)
   - [ ] Smooth, not jumpy animation

3. Find a subscription expiring in 1-7 days
4. **Verify**:
   - [ ] Progress bar changes to amber/orange gradient
   - [ ] Visual warning through color change

**Expected Result**: Progress bars show and update smoothly

---

### Test 4: Enhanced Next Billing Text ✅

**Objective**: Verify color-coded countdown display

**Steps**:
1. Check subscriptions with different renewal dates:

**More than 7 days away**:
   - [ ] Text color is gray
   - [ ] Shows "Renews in XX days"

**1-7 days away**:
   - [ ] Text color is amber
   - [ ] Shows "Renews in X day(s)"

**Tomorrow**:
   - [ ] Text color is yellow
   - [ ] Shows "Renews tomorrow"

**Today**:
   - [ ] Text color is yellow
   - [ ] Shows "Renews today"

**Expired**:
   - [ ] Text color is red
   - [ ] Shows "Expired"

**Expected Result**: Color-coded text changes based on days until renewal

---

### Test 5: Pause Button ✅

**Objective**: Test pause button appearance and hover effects

**Steps**:
1. Locate action buttons in bottom-right of card
2. **Verify**:
   - [ ] Pause button (⏸) visible next to Insights
   - [ ] Button is circular (32px)
   - [ ] Icon clearly visible
   - [ ] "Pause subscription" tooltip shows on hover

3. Hover over pause button
4. **Verify**:
   - [ ] Button background becomes lighter
   - [ ] Icon becomes brighter
   - [ ] Smooth transition (not instant)

**Expected Result**: Pause button visible with working hover effects

---

### Test 6: Responsive Design ✅

**Objective**: Verify layout works on all screen sizes

#### Mobile (375px)
1. Press F12 (DevTools)
2. Click device toggle (mobile icon)
3. Select iPhone (375px width)
4. **Verify**:
   - [ ] Warning badge visible
   - [ ] Progress bar fits without overflow
   - [ ] Buttons stack or align properly
   - [ ] No horizontal scroll
   - [ ] Text readable

#### Tablet (768px)
1. Change device to iPad (768px)
2. **Verify**:
   - [ ] All elements properly spaced
   - [ ] Badges don't overlap annual cost
   - [ ] Progress bar full width
   - [ ] Buttons side-by-side

#### Desktop (1200px+)
1. Return to normal view
2. **Verify**:
   - [ ] Full spacing maintained
   - [ ] No overlapping elements
   - [ ] All features visible
   - [ ] Professional appearance

**Expected Result**: Layout adapts correctly to all screen sizes

---

### Test 7: Functional Testing ✅

**Objective**: Check button functionality and interactions

**Steps**:
1. Click "Insights" button
   - [ ] Opens insights modal/view
   - [ ] Card styling remains intact

2. Click Pause button
   - Note: This won't actually pause yet (backend integration needed)
   - [ ] Button is clickable (no JS errors)
   - [ ] No console errors

3. Hover over card
   - [ ] Parallax effect still works (if enabled)
   - [ ] Card slightly elevates
   - [ ] Light glow follows cursor
   - [ ] Progress bar visible during hover

**Expected Result**: All interactions work smoothly

---

## Advanced Testing

### Browser Console Checks

1. Press F12 to open DevTools
2. Go to "Console" tab
3. **Verify**:
   - [ ] No red error messages
   - [ ] No yellow warnings
   - [ ] Component renders without issues

### Network Tab

1. Go to "Network" tab
2. Reload page
3. **Verify**:
   - [ ] No failed API calls (status 200)
   - [ ] All subscriptions load
   - [ ] No excessive requests

### Performance

1. Go to "Performance" tab
2. Click record, wait 3 seconds, stop
3. **Verify**:
   - [ ] No excessive redraws
   - [ ] FPS stays above 30
   - [ ] No jank/stuttering

---

## Edge Case Testing

### Test: Missing next_billing_date

**Setup**: Edit a subscription to remove next_billing_date

**Verify**:
- [ ] Progress bar hidden
- [ ] Warning badge hidden
- [ ] Countdown text hidden
- [ ] Other card elements display normally
- [ ] No errors in console

### Test: Expiring Today (daysLeft = 0)

**Setup**: Create/edit subscription with next_billing_date = today

**Verify**:
- [ ] Shows "Renews today" in yellow
- [ ] Amber badge shows "⚠ Renews in 0d"
- [ ] Progress bar at ~95%

### Test: Expired (daysLeft < 0)

**Setup**: Set next_billing_date to yesterday

**Verify**:
- [ ] Shows "Expired" in red
- [ ] Red badge shows "🔴 Expired"
- [ ] Progress bar hidden
- [ ] Card styling indicates issue

### Test: Far Future (daysLeft > 365)

**Setup**: Set next_billing_date to 1+ year away

**Verify**:
- [ ] Shows "Renews in XXX days" in gray
- [ ] No warning badge
- [ ] Progress bar at low %
- [ ] Normal card styling

---

## Data Requirements for Testing

To see all features, subscriptions need:

```javascript
{
  id: 1,
  service_name: "Netflix",
  category: "streaming",
  cost: 15.99,
  currency: "USD",
  billing_cycle: "monthly",
  status: "active",
  next_billing_date: "2026-06-05T00:00:00",  // Required!
  icon_url: "https://..."
}
```

**Key requirement**: `next_billing_date` must be set and valid ISO date format

---

## Common Issues & Solutions

### Issue: Progress bar not showing
**Solution**: Check that subscription has valid `next_billing_date`

### Issue: Warning badges not visible
**Solution**: 
1. Check browser console for errors
2. Verify subscription status is "active"
3. Confirm next_billing_date is within 7 days

### Issue: Color not correct
**Solution**: 
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh (Ctrl+Shift+R)
3. Check console for CSS errors

### Issue: Button not clickable
**Solution**:
1. Check console for JS errors
2. Verify React is loaded
3. Try in different browser

### Issue: Responsive layout broken
**Solution**:
1. Clear browser cache
2. Close and reopen DevTools
3. Try different screen size

---

## Quick Test Command Sequence

Copy and paste these commands in order:

```bash
# Terminal 1: Backend
cd /home/jaros/.cline/worktrees/1da01/subs-manager
python api.py

# Terminal 2: Frontend (in new terminal)
cd /home/jaros/.cline/worktrees/1da01/subs-manager/frontend_glass
npm install
npm run dev

# Then open browser:
# http://localhost:5173
```

---

## Test Report Template

Use this to document your testing:

```
=== TEST REPORT ===
Date: [Date]
Tester: [Name]
Browser: [Chrome/Firefox/Safari/Edge]
OS: [Windows/Mac/Linux]

UI Elements Tested:
- [ ] Expiration warning badges
- [ ] Billing cycle progress bar
- [ ] Enhanced next billing display
- [ ] Pause subscription button
- [ ] Days until billing logic

Responsive Sizes:
- [ ] Mobile (375px)
- [ ] Tablet (768px)
- [ ] Desktop (1200px+)

Issues Found:
1. [Issue description]
2. [Issue description]

Status: [PASS / FAIL]
```

---

## Next Steps After Testing

If all tests pass ✅:
1. Note any minor visual tweaks needed
2. Document any browser-specific issues
3. Approve for production deployment

If tests fail ❌:
1. Document exact issue and steps to reproduce
2. Check browser console for errors
3. Report findings

---

**Happy Testing! 🎉**
