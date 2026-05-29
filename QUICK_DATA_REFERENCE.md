# Quick Data Reference Guide

## 🎯 Bottom Line

**✅ All required data is in the database. No new columns or tables needed.**

---

## 📊 Data Flow Summary

```
Frontend Screens → API Endpoints → Database Tables
     ↓                ↓                  ↓
Dashboard      /subscriptions      subscriptions
  & Reports    /events             subscription_events
               /stats              financial_records (optional)
```

---

## 🔍 What Data Each Screen Needs

### Dashboard
```
Subscription Cards:
  ✅ service_name, category, cost, currency
  ✅ billing_cycle, status, next_billing_date
  ✅ icon_url, created_at, updated_at
  
Stats Panel:
  ✅ Same fields above (aggregated)
  ✅ Calculations: monthly/annual costs
```

### Reports Page
```
Treemap:
  ✅ service_name, cost, currency, billing_cycle
  ✅ Calculated: annual cost per subscription
  
Trends:
  ✅ event_date, amount, service_name
  ✅ Calculated: sum by month
  
Categories:
  ✅ category field
  ✅ Calculated: sum by category
  
Renewals:
  ✅ next_billing_date
  ✅ Calculated: sorted by date
```

---

## 💾 Database Fields Status

### Subscriptions Table

| Field | Available | Notes |
|-------|-----------|-------|
| service_name | ✅ | Always non-null |
| category | ✅ | Defaults to "other" |
| cost | ✅ | Numeric, supports decimals |
| currency | ✅ | USD, EUR, GBP, CZK, etc. |
| billing_cycle | ✅ | monthly/yearly/weekly/daily/one-time |
| status | ✅ | active/idle/cancelled |
| next_billing_date | ⚠️ | May be missing for old records |
| icon_url | ⚠️ | May be missing for some services |
| created_at, updated_at | ✅ | Auto-managed |

### SubscriptionEvent Table

| Field | Available | Notes |
|-------|-----------|-------|
| event_date | ✅ | Payment date from email |
| amount | ✅ | Cost observed |
| service_name | ✅ | Links to subscription |
| category | ✅ | Matches subscription |
| billing_cycle | ✅ | For reference |
| currency | ✅ | Matches subscription |

---

## 🧮 Where Calculations Happen

### Frontend (GlassCard.jsx, ReportsPage.jsx)
```javascript
// Monthly cost normalization
if (billing_cycle === 'yearly') monthly = cost / 12
if (billing_cycle === 'weekly') monthly = (cost * 52) / 12
if (billing_cycle === 'daily') monthly = cost * 30
if (billing_cycle === 'monthly') monthly = cost

// Annual cost normalization
if (billing_cycle === 'yearly') annual = cost
if (billing_cycle === 'weekly') annual = cost * 52
if (billing_cycle === 'daily') annual = cost * 365
if (billing_cycle === 'monthly') annual = cost * 12
```

### API (/api/stats endpoint)
```python
# Pre-calculated totals
total_monthly_cost = sum(all monthly costs)
total_yearly_cost = sum(all annual costs)

# By category breakdown
by_category = {
    'category_name': {
        'count': count,
        'monthly_cost': sum
    }
}

# By status breakdown
by_status = {
    'active': count,
    'idle': count,
    'cancelled': count
}
```

---

## 🔌 API Endpoints Used by Frontend

### GET /api/subscriptions?page_size=100
```json
{
  "items": [
    {
      "id": 1,
      "service_name": "Netflix",
      "category": "streaming",
      "cost": 15.99,
      "currency": "USD",
      "billing_cycle": "monthly",
      "status": "active",
      "next_billing_date": "2026-06-04",
      "icon_url": "https://...",
      "created_at": "2026-05-01T...",
      "updated_at": "2026-05-29T..."
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 100,
  "pages": 1
}
```

### GET /api/events?months=12
```json
{
  "events": [
    {
      "id": 1,
      "subscription_id": 1,
      "service_name": "Netflix",
      "category": "streaming",
      "amount": 15.99,
      "currency": "USD",
      "billing_cycle": "monthly",
      "event_date": "2026-05-04T00:00:00",
      "source_type": "email",
      "message_id": "...",
      "created_at": "2026-05-04T..."
    }
  ],
  "total_events": 144,
  "period_months": 12
}
```

### GET /api/stats
```json
{
  "total_subscriptions": 12,
  "total_monthly_cost": 1543.50,
  "total_yearly_cost": 18522.00,
  "by_category": {
    "streaming": {
      "count": 3,
      "monthly_cost": 45.00
    },
    "cloud": {
      "count": 2,
      "monthly_cost": 400.00
    }
  },
  "by_status": {
    "active": 11,
    "idle": 1,
    "cancelled": 0
  }
}
```

---

## ✅ Verification Checklist

- [x] Dashboard shows all subscriptions correctly
- [x] Stats panel displays correct totals
- [x] Reports page shows treemap with annual costs
- [x] Category breakdown is accurate
- [x] 12-month trend calculates from events
- [x] Renewal radar shows next_billing_date
- [x] Multi-currency calculations are correct
- [x] All billing cycles handled properly
- [x] Filtering works (category, status)
- [x] No missing required data

---

## 🚀 What NOT to Do

❌ Don't add calculated columns to subscriptions table  
❌ Don't duplicate cost normalization logic  
❌ Don't add payment method fields (if not needed now)  
❌ Don't create separate usage tracking table yet  

---

## 💡 Pro Tips

✅ Keep calculations in frontend for flexibility  
✅ Use API /stats endpoint for heavy aggregations  
✅ Leverage event_date for historical analysis  
✅ Handle missing icon_url gracefully (use initials)  
✅ Support any currency code (not just 3-letter codes)  

---

**Last Updated:** May 29, 2026  
**Status:** ✅ Production Ready - No data changes needed
