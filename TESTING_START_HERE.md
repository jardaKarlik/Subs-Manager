# 🏧 Testing Guide - START HERE

## What to Test

You're testing 5 new UI elements added to subscription cards:

1. ⚠️ **Expiration Warning Badges** - Amber/Red badges in top-right
2. 📊 **Billing Cycle Progress Bar** - Visual timeline of cycle completion
3. 🔐 **Enhanced Countdown Text** - Color-coded "Renews in X days" text
4. ⏸️ **Pause Button** - New action button for subscriptions
5. 💪 **Calculation Logic** - Smart date/billing calculations

---

## Option A: 5-Minute Quick Test 🚀

**Perfect if you just want to verify it works**

### Step 1: Open 2 Terminals

**Terminal 1 - Backend:**
```bash
cd /home/jaros/.cline/worktrees/1da01/subs-manager
python api.py
```
Wait for: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - Frontend:**
```bash
cd /home/jaros/.cline/worktrees/1da01/subs-manager/frontend_glass
npm install
npm run dev
```
Wait for: `VITE v... ready in ... ms`

### Step 2: Open Browser
```
http://localhost:5173
```

### Step 3: Look for These (30 seconds)

- ✅ **Progress bars** on cards (thin bars showing %)
- ✅ **Badges** in top-right (amber " ⚠️" or red "🔴")
- ✅ **Pause button** (⏸) next to Insights button
- ✅ **Colored text** like "Renews in 5 days" at bottom

### Done! ✅

If you see all these = **Everything works!**

---

## Option B: 10-Minute Full Test 📝

**Better if you want to verify everything thoroughly**

Open: **TESTING_GUIDE_UI_ENHANCEMENTS.md**

It has:
- Detailed checklist for each element
- Step-by-step verification
- Mobile/tablet/desktop testing
- Edge case scenarios
- Troubleshooting guide

---

## Option C: Quick Reference 🔍

**Quick lookup if something doesn't look right**

Open: **QUICK_TEST_REFERENCE.md**

It has:
- What each element should look like
- What colors to expect
- Common problems & fixes
- Success indicators

---

## What Should You See?

### 📊 Progress Bar (Below Cost)
```
Billing cycle progress         55%
[###############################  ]
```
- Thin line showing % complete
- Shows number like "55%"
- Color: Category gradient (blue, purple, etc.)
- OR amber/orange if renewing soon

### ⚠️ Warning Badge (Top-Right)
```
⚠ Renews in 3d     <- Amber, renewing soon (1-7 days)
OR
🔴 Expired          <- Red, already expired
```

### 🔐 Countdown Text (Bottom)
```
Renews in 5 days     <- Amber (1-7 days away)
Renews today         <- Yellow (renews today)
Expired              <- Red (overdue)
Renews in 45 days    <- Gray (normal, >7 days)
```

### ⏸️ Pause Button (Bottom-Right)
```
[⏸] [Insights] <- Small circular button
```

---

## Troubleshooting

### "I don't see any badges or progress bars"

**Fix**: 
Your subscriptions need `next_billing_date` set. 
Without this field, the new features won't show (which is correct behavior).

Check:
1. Database has subscriptions with `next_billing_date` populated
2. Format must be ISO: `2026-06-05T00:00:00`
3. Refresh browser (Ctrl+F5)

### "Colors look wrong"

**Fix**:
```bash
# Clear cache completely:
# Windows: Ctrl+Shift+Delete
# Mac: Cmd+Shift+Delete
# Then hard refresh: Ctrl+Shift+R
```

### "npm install fails"

**Fix**:
```bash
rm -rf node_modules
npm cache clean --force
npm install
```

### "Port 5173 already in use"

**Fix**:
```bash
# Kill existing process:
pkill -f vite

# Then try npm run dev again
```

### "Backend not responding"

**Fix**:
1. Verify Terminal 1 shows `Uvicorn running on http://0.0.0.0:8000`
2. Try visiting http://localhost:8000 directly
3. Check for error messages in terminal

---

## Expected Behavior

| Scenario | What You'll See |
|----------|----------------|
| Renews in 3 days | Amber badge + amber text + progress bar |
| Renews in 15 days | No badge + gray text + progress bar |
| Renews today | Yellow "Renews today" + amber badge |
| Expired | Red "Expired" + red badge + no progress |
| No renewal date | No badges, no progress, no countdown |

---

## Mobile Testing

Press **F12** (open DevTools)

Click **device toggle** (phone icon) at top

Select **iPhone** to see mobile view

**Verify**:
- Badge still visible
- Progress bar doesn't overflow
- Buttons still clickable
- Text readable
- No horizontal scroll

---

## Success Checklist ✅

If you can check all these:

- [ ] Dashboard loads without errors
- [ ] Cards display subscription info
- [ ] At least one card shows progress bar
- [ ] Badge visible on some cards (if data allows)
- [ ] Pause button visible
- [ ] Colors make sense
- [ ] Hover effects work (button gets lighter)
- [ ] Mobile view works
- [ ] No errors in console (F12 > Console)

**All checked?** ✅ **Everything is working!**

---

## Next Steps

### If Testing Passes ✅
1. Component is ready for production
2. Can deploy with confidence
3. All 5 UI elements functional

### If Testing Fails ❌
1. Check the troubleshooting section above
2. Try the fixes
3. Take a screenshot
4. Note the browser and OS you're using
5. Check browser console for errors (F12)

---

## Need More Help?

- **Quick reference**: QUICK_TEST_REFERENCE.md
- **Detailed guide**: TESTING_GUIDE_UI_ENHANCEMENTS.md
- **Visual guide**: UI_ELEMENTS_VISUAL_GUIDE.md
- **Technical docs**: UI_ENHANCEMENTS_SUMMARY.md

---

## Quick Stop Commands

```bash
# Stop backend (in Terminal 1):
Ctrl+C

# Stop frontend (in Terminal 2):
Ctrl+C

# OR kill both:
pkill -f "python api.py"
pkill -f "vite"
```

---

**You're ready! Happy testing! 🎉**
