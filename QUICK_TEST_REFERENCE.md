# 🚀 Quick Test Reference - 5 Minute Setup

## Start Here

### Terminal 1: Backend
```bash
cd /home/jaros/.cline/worktrees/1da01/subs-manager
python api.py
```
**Result**: http://localhost:8000 running

### Terminal 2: Frontend
```bash
cd /home/jaros/.cline/worktrees/1da01/subs-manager/frontend_glass
npm install    # First time only, takes 2-3 min
npm run dev
```
**Result**: http://localhost:5173 running

### Browser
```
Open: http://localhost:5173
```

---

## What to Look For (30 Seconds)

### ⚠️ Warning Badge (Top-Right)
- [ ] Amber badge if renewing in 1-7 days
- [ ] Red badge if expired
- [ ] Text: "⚠ Renews in Xd" or "🔴 Expired"

### 📊 Progress Bar (Below Cost)
- [ ] Thin bar showing % complete
- [ ] Color: Category color (normal) or amber/orange (expiring)
- [ ] Number like "65%" shown next to label

### 🔐 Countdown Text (Bottom)
- [ ] Gray: "Renews in XX days" (>7 days)
- [ ] Amber: "Renews in X days" (1-7 days)
- [ ] Yellow: "Renews today" or "Renews tomorrow"
- [ ] Red: "Expired"

### ⏸️ Pause Button (Bottom-Right)
- [ ] Circular button next to "Insights"
- [ ] Icon: ⏸
- [ ] Hover: Gets lighter

---

## Test Checklist (3 Minutes)

⚠️ **Warning Badges**
- [ ] Can see amber badge on some cards
- [ ] Can see red badge on expired cards
- [ ] Matches right colors

📊 **Progress Bar**
- [ ] Bar visible on all non-expired cards
- [ ] Shows percentage
- [ ] Color changes to amber when expiring soon
- [ ] Smooth, not jumpy

🔐 **Countdown**
- [ ] Text changes color based on days
- [ ] Says "today", "tomorrow", "X days", etc
- [ ] Red for expired

⏸️ **Pause Button**
- [ ] Button visible
- [ ] Can click it
- [ ] Gets lighter on hover
- [ ] No console errors

📶 **Mobile (F12 → iPhone)**
- [ ] Everything still fits
- [ ] No horizontal scroll
- [ ] Badge visible
- [ ] Progress bar still shows
- [ ] Buttons still work

---

## Expected Dates to Test

**In your database, look for subscriptions with:**

- **Today**: `next_billing_date = 2026-05-29`
  - Shows: "Renews today" (yellow)
  - Badge: "⚠ Renews in 0d" (amber)

- **3 days away**: `next_billing_date = 2026-06-01`
  - Shows: "Renews in 3 days" (amber)
  - Badge: "⚠ Renews in 3d" (amber)
  - Progress: ~90%

- **10 days away**: `next_billing_date = 2026-06-08`
  - Shows: "Renews in 10 days" (gray)
  - Badge: None
  - Progress: ~70%

- **Yesterday**: `next_billing_date = 2026-05-28`
  - Shows: "Expired" (red)
  - Badge: "🔴 Expired" (red)
  - Progress: Hidden

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| npm install fails | `rm -rf node_modules && npm install` |
| Port 5173 in use | Kill process or use different port |
| Backend not connecting | Check http://localhost:8000 in browser |
| Badges not showing | Verify subscription has next_billing_date |
| Colors look wrong | Press Ctrl+Shift+Delete (clear cache) |
| Console errors | Check terminal for traceback |

---

## Quick Success Indicators ✅

If you see these, it's working:

1. Dashboard loads without errors
2. Subscription cards display
3. At least one card shows a progress bar
4. At least one card shows a warning badge (if data allows)
5. Pause button visible on cards
6. Colors match expected values
7. Hover effects work
8. Mobile view responsive

---

## Command: Stop Everything

```bash
# Ctrl+C in both terminals
# Or killall:
pkill -f "python api.py"
pkill -f "vite"
```

---

## Next: Report Findings

If everything works:
- ✅ Component is ready for production
- ✅ All UI elements working as expected

If something doesn't work:
- Document what you see
- Get screenshot if possible
- Note browser and OS
- Check console errors

**Estimated time**: 5 minutes setup + 3 minutes testing = **8 minutes total**
