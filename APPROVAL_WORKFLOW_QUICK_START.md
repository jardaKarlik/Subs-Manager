# ⚡ Approval Workflow - Quick Start Guide

## What is it?

The **Approval Workflow** is a new page in mySUBZ that lets you review and manage subscriptions discovered from your wallet or other automated sources.

## Where to Find It

1. Open mySUBZ in your browser
2. Click the **"Approvals"** button in the header
3. You’ll see all pending subscriptions waiting for your review

## Navigation

```
Header Navigation:
[Dashboard] [Approvals] [Reports] [↻ Sync] [+ Add]
              ↑
         Click here to review
         pending subscriptions
```

## What You Can Do

### ✓ Approve Individual Subscriptions

1. Find a pending subscription card
2. Review the details:
   - Service name & category
   - Monthly/yearly cost
   - Billing cycle
   - Next billing date
3. Click **"Approve"** button (green)
4. Subscription is added to your main list

### ✗ Dismiss Individual Subscriptions

1. Find a pending subscription card
2. Click **"Dismiss"** button (red)
3. Subscription is hidden/cancelled
4. Card disappears from the pending list

### ⌛ Bulk Actions (Approve/Dismiss Multiple)

1. **Check boxes** on cards you want to process
2. Or click **"Select All"** for all pending subscriptions
3. Bulk action buttons appear:
   - **Approve (X)** - approve all selected
   - **Dismiss (X)** - dismiss all selected
4. Click the button
5. All selected subscriptions are processed

### 🔎 Sort by Different Criteria

Use the **Sort** dropdown to organize pending subscriptions:

- **Cost (High → Low)** - See expensive subscriptions first
- **Cost (Low → High)** - See cheap subscriptions first
- **Name (A-Z)** - Alphabetical order
- **Name (Z-A)** - Reverse alphabetical

## Example Workflow

### Scenario: You have 5 pending subscriptions

```
Pending Subscriptions: 5
Total Cost: $89.95

┌────────────────────────────┐
│ [ ] 💻 GitHub Enterprise                  │
│     $231 USD / yearly                  │
│     Next: 2025-03-15                  │
│     [Approve]      [Dismiss]         │
└────────────────────────────┘
┌────────────────────────────┐
│ [ ] 🎵 Spotify Premium                     │
│     $14.99 USD / monthly             │
│     Next: 2025-06-05                 │
│     [Approve]      [Dismiss]         │
└────────────────────────────┘
│ ... and 3 more
```

### Option 1: Approve Each One

1. Click "Approve" on GitHub Enterprise
   - Card disappears
   - Success message: "Subscription approved ✓"
2. Click "Approve" on Spotify Premium
   - Card disappears
   - Total cost updates
3. Repeat for others

### Option 2: Bulk Approve (Faster)

1. Click checkboxes on 2-3 cards you want to approve
2. "2 selected" appears in controls
3. Click **Approve (2)** button
4. Both approved at once
5. "2 subscriptions approved ✓" message

### Option 3: Mixed Actions

1. Approve some individually
2. Select others and bulk dismiss
3. Keep reviewing until:
   - "All caught up!"
   - No more pending subscriptions

## Status Indicators

### Pending (Yellow Badge)

Subscription is waiting for your decision

```
Status Badge: "Pending" (yellow)
```

### After Approval

- Goes to main Dashboard
- Shows in active subscriptions
- Counted in monthly/yearly totals

### After Dismissal

- Marked as cancelled
- Hidden from active list
- Not counted in totals

## Testing with Demo Data

### No pending subscriptions in demo mode?

Seed test data:

```bash
# Using curl
curl -X POST http://localhost:8000/api/seed-pending-candidates

# Response:
# {"status": "ok", "seeded": ["Steam", "Roblox", "IFTTT Pro", "Loopmasters"]}
```

**Test Subscriptions Created:**
- 🎮 Steam: 279 CZK/month
- 🎮 Roblox: 149 CZK/month
- 📊 IFTTT Pro: 89 CZK/month
- 🎵 Loopmasters: 199 CZK/month

## Tips & Tricks

### 📁 Review by Category

Each card shows:
- Icon: Category at a glance
- Label: Exact category name
- Gradient color: Visual distinction

### 💵 Watch the Total Cost

Header shows:
- Number of pending items
- Total cost of all pending

As you approve/dismiss, this updates in real-time

### ⚡ Quick Review

1. Sort by **Cost (High → Low)**
2. Review expensive subscriptions first
3. Approve obvious ones
4. Use bulk actions for multiple

### 🗑️ Cleanup Mode

To quickly dismiss unwanted subscriptions:

1. Click **Select All**
2. Review the highlighted subscriptions
3. Uncheck ones you want to keep
4. Click **Dismiss (X)**

## Keyboard Shortcuts (Future)

Currently: Click buttons

Planned features:
- [ ] Enter to approve selected
- [ ] Esc to deselect all
- [ ] ↑ ↓ arrow keys to navigate

## Help & Support

### Issue: Page is empty

You might not have any pending subscriptions. This is good! 🎆

- All pending items have been approved/dismissed
- Check the Dashboard to see your approved subscriptions
- Use seed test data to try the feature

### Issue: Buttons not responding

Check:
- Is your API server running? (port 8000)
- Is your frontend running? (port 5173 or 3000)
- Check browser console for errors (F12)

### Issue: Changes not saving

Refresh the page. The approval state should persist.

If it doesn’t:
1. Check API error in browser console
2. Verify backend is connected
3. Try a different subscription

## Performance Notes

### What happens when you approve?

```
You click "Approve"
      ⬇️
  API call sent
      ⬇️
  Backend updates database
      ⬇️
  Card disappears from UI
      ⬇️
  Success message shows
      ⬇️
  Main list refreshes (optional)
```

Typically takes 1-2 seconds

### Bulk Operations

Bulk operations are faster than individual:
- Individual: 5 subscriptions = 5 API calls
- Bulk: 5 subscriptions = 1 API call

## Summary

✅ **Approvals** page helps you manage subscription discoveries
✅ **Approve**: Add to your active subscriptions
✅ **Dismiss**: Mark as unwanted/cancelled
✅ **Bulk actions**: Process multiple at once
✅ **Sorting**: Find subscriptions your way

**Next Steps:**
1. Click "Approvals" in the header
2. Review any pending subscriptions
3. Approve or dismiss each one
4. Return to Dashboard to see your list

---

*Last Updated: May 29, 2026*
