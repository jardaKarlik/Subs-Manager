# Data Requirements Review - Frontend vs Database

**Date:** May 29, 2026  
**Status:** ✅ **COMPLETE - All required data is available in the database**

---

## Executive Summary

After reviewing all frontend screens and their data requirements against the current database schema and API endpoints, **all necessary data is available or can be calculated from existing fields**. No new database tables or columns are required at this time.

---

## 1. Frontend Screens & Data Requirements

### 1.1 Dashboard View (Main Screen)

**Screen Component:** `GlassSubscriptionGrid.jsx` + `StatsPanel.jsx`

#### Data Required:
| Field | Source | Status |
|-------|--------|--------|
| `service_name` | Subscription.service_name | ✅ Available |
| `category` | Subscription.category | ✅ Available |
| `cost` | Subscription.cost | ✅ Available |
| `currency` | Subscription.currency | ✅ Available |
| `billing_cycle` | Subscription.billing_cycle | ✅ Available |
| `status` | Subscription.status | ✅ Available |
| `next_billing_date` | Subscription.next_billing_date | ✅ Available |
| `icon_url` | Subscription.icon_url | ✅ Available |
| `created_at` | Subscription.created_at | ✅ Available |
| `updated_at` | Subscription.updated_at | ✅ Available |

#### Calculated Fields:
| Metric | Calculation | Status |
|--------|-----------|--------|
| Monthly Cost | `cost / 12` (if yearly), `cost * 52 / 12` (if weekly), `cost * 30` (if daily), `0` (if one-time), else `cost` | ✅ Done in Frontend |
| Annual Cost | `cost` (if yearly), `cost * 52` (if weekly), `cost * 365` (if daily), `cost` (if one-time), else `cost * 12` | ✅ Done in Frontend |
| Total Monthly | Sum of all monthly costs | ✅ Done in Frontend |
| Total Yearly | Sum of all annual costs | ✅ Done in Frontend |
| Active Count | Count where status = 'active' | ✅ Done in Frontend |
| Total Subscriptions | Count all | ✅ Available via API |

**Frontend Location:** `/frontend_glass/src/components/StatsPanel.jsx` & `GlassCard.jsx`  
**API Endpoint:** `GET /api/subscriptions?page_size=100`  
**Data Availability:** ✅ **COMPLETE**

---

### 1.2 Reports Page (Insights View)

**Screen Component:** `ReportsPage.jsx`

#### Data Required from Subscriptions:
| Field | Source | Status |
|-------|--------|--------|
| `id` | Subscription.id | ✅ Available |
| `service_name` | Subscription.service_name | ✅ Available |
| `category` | Subscription.category | ✅ Available |
| `cost` | Subscription.cost | ✅ Available |
| `currency` | Subscription.currency | ✅ Available |
| `billing_cycle` | Subscription.billing_cycle | ✅ Available |
| `status` | Subscription.status | ✅ Available |
| `next_billing_date` | Subscription.next_billing_date | ✅ Available |

#### Data Required from Events:
| Field | Source | Status |
|-------|--------|--------|
| `event_date` | SubscriptionEvent.event_date | ✅ Available |
| `amount` | SubscriptionEvent.amount | ✅ Available |
| `service_name` | SubscriptionEvent.service_name | ✅ Available |
| `category` | SubscriptionEvent.category | ✅ Available |
| `billing_cycle` | SubscriptionEvent.billing_cycle | ✅ Available |
| `currency` | SubscriptionEvent.currency | ✅ Available |

#### Calculated Metrics in Report:
| Metric | Calculation | Status |
|--------|-----------|--------|
| Annual Spend (Per Sub) | Sum of annual costs | ✅ Done in Frontend |
| Monthly Spend (Per Sub) | Sum of monthly costs | ✅ Done in Frontend |
| Category Breakdown | Group by category, sum annual/monthly | ✅ Done in Frontend |
| Billing Cycle Distribution | Count subscriptions by cycle | ✅ Done in Frontend |
| Biggest Cost Driver | Subscription with highest annual cost | ✅ Done in Frontend |
| Top 5 Concentration | (Top 5 annual / Total annual) * 100 | ✅ Done in Frontend |
| 12-Month Trend | Sum of event amounts by month | ✅ Done in Frontend |
| Upcoming Renewals | Filter next_billing_date, sort by date | ✅ Done in Frontend |

**Frontend Location:** `/frontend_glass/src/components/ReportsPage.jsx`  
**API Endpoints:**
- `GET /api/subscriptions?page_size=100` → Subscription list
- `GET /api/events?months=12` → Historical events

**Data Availability:** ✅ **COMPLETE**

---

## 2. Database Schema Coverage

### 2.1 Subscription Table - All Required Fields Present

```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    service_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    cost FLOAT,
    currency VARCHAR(10),
    billing_cycle VARCHAR(20),
    status VARCHAR(20),
    start_date VARCHAR(10),
    next_billing_date VARCHAR(10),
    notes VARCHAR(1000),
    source VARCHAR(100),
    icon_url VARCHAR(500),
    confirmed_by_wallet BOOLEAN,
    last_payment_date DATETIME,
    actual_cost FLOAT,
    approval_status VARCHAR(20),
    created_at DATETIME,
    updated_at DATETIME
)
```

**Coverage:** ✅ **100%** - All required fields present

### 2.2 SubscriptionEvent Table - All Timeline Fields Present

```sql
CREATE TABLE subscription_events (
    id INTEGER PRIMARY KEY,
    subscription_id INTEGER,
    service_name VARCHAR(255),
    category VARCHAR(100),
    amount FLOAT,
    currency VARCHAR(10),
    billing_cycle VARCHAR(20),
    event_date DATETIME,
    source_type VARCHAR(50),
    message_id VARCHAR(255),
    created_at DATETIME
)
```

**Coverage:** ✅ **100%** - All required fields for timeline/trend analysis

---

## 3. API Endpoints & Response Coverage

### 3.1 Subscriptions Endpoint - Complete

**Endpoint:** `GET /api/subscriptions?page_size=100`

All required fields returned with proper formatting:
- ✅ `id`, `service_name`, `category`
- ✅ `cost`, `currency`, `billing_cycle`
- ✅ `status`, `start_date`, `next_billing_date`
- ✅ `icon_url`, `source`
- ✅ `created_at`, `updated_at`
- ✅ `total_spent` (aggregated from FinancialRecord)

**Status:** ✅ **COMPLETE**

### 3.2 Events Endpoint - Complete

**Endpoint:** `GET /api/events?months=12`

All timeline fields returned:
- ✅ `event_date`, `amount`, `currency`
- ✅ `service_name`, `category`, `billing_cycle`
- ✅ `source_type`, `message_id`

**Status:** ✅ **COMPLETE**

### 3.3 Stats Endpoint - Complete

**Endpoint:** `GET /api/stats`

All aggregated statistics returned:
- ✅ `total_subscriptions`, `total_monthly_cost`, `total_yearly_cost`
- ✅ `by_category`, `by_status`
- ✅ Wallet enrichment: `confirmed_count`, `actual_monthly_spend`

**Status:** ✅ **COMPLETE**

---

## 4. Calculations Location Analysis

### 4.1 Frontend Calculations (✅ Correct Implementation)

The application **correctly** performs normalization in the frontend:

**In `GlassCard.jsx`:**
- Monthly cost normalization (billing cycle → monthly)
- Annual cost normalization (billing cycle → annual)
- Currency formatting with symbols

**In `ReportsPage.jsx`:**
- Category breakdown with grouping and summing
- Annual spend concentration calculation
- Billing cycle distribution
- 12-month trend aggregation
- Top 5 concentration percentage

**Benefits:**
- ✅ Simple database schema (no calculated columns)
- ✅ Flexible calculations (easy to change business logic)
- ✅ Efficient (no database overhead)

### 4.2 Backend Pre-Aggregation (✅ Efficient)

The API smartly pre-aggregates expensive calculations:

**In `/api/stats` endpoint:**
- Total monthly/yearly costs (billing-cycle aware)
- Category cost breakdown
- Status distribution
- Wallet-enriched metrics (confirmed count, actual spend)

**Benefits:**
- ✅ Reduces frontend complexity
- ✅ Leverages database aggregation
- ✅ Integrates wallet data seamlessly

---

## 5. Data Quality Assessment

### Current Field Coverage

| Field | Status | Notes |
|-------|--------|-------|
| `service_name` | ✅ Essential | Always required, non-null |
| `category` | ✅ Good | Defaults to "other", well-populated |
| `cost` | ✅ Good | Numeric, defaults to 0.0 |
| `currency` | ✅ Good | Defaults to USD, multi-currency support |
| `billing_cycle` | ✅ Good | Validated enum (monthly/yearly/weekly/daily/one-time) |
| `status` | ✅ Good | Validated enum (active/idle/cancelled) |
| `next_billing_date` | ⚠️ Partial | Extracted from emails, may be missing for older subs |
| `icon_url` | ⚠️ Partial | Clearbit integration, some may be missing |
| `start_date` | ⚠️ Partial | Extracted from emails, may be missing |
| `notes` | ✅ Good | Optional but useful for context |
| `created_at`/`updated_at` | ✅ Essential | Auto-managed timestamps |

---

## 6. Summary: All Required Data is Available

### Dashboard Completeness
| Component | Data Needed | Available | Source |
|-----------|-------------|-----------|--------|
| Stats Panel | Costs, counts | ✅ | API aggregation |
| Subscription Cards | Service details | ✅ | Subscription table |
| Status indicators | Status field | ✅ | Subscription table |
| Icons | icon_url field | ✅ | Subscription table |

### Reports Page Completeness
| Component | Data Needed | Available | Source |
|-----------|-------------|-----------|--------|
| Treemap | Annual costs | ✅ | Calculated from cost + billing_cycle |
| Category pressure | Breakdown by category | ✅ | Subscription.category |
| Renewal radar | Next billing dates | ✅ | Subscription.next_billing_date |
| 12-month trend | Event amounts | ✅ | SubscriptionEvent.amount |
| Billing rhythm | Cycle distribution | ✅ | Subscription.billing_cycle |

---

## 7. Conclusion

### ✅ NO NEW DATABASE FIELDS REQUIRED

The current database schema provides **100% coverage** of all data needed by the frontend.

### ✅ CALCULATIONS ARE PROPERLY PLACED

- Raw data stored in database ✅
- Presentation calculations in frontend ✅
- Stats pre-aggregation in API ✅

### ✅ MULTI-CURRENCY & FLEXIBLE BILLING SUPPORTED

- Currency field handles USD, EUR, GBP, CZK ✅
- Billing cycle enum supports all common patterns ✅
- Calculations handle all cycles correctly ✅

### Future Enhancements (Not Required Now)

If you want to add later:
- Payment method tracking → New table
- Usage analytics → New table
- Price history → New table
- Renewal notifications → Feature flag only

---

**Recommendation:** Proceed with current implementation. No schema changes needed.

---

**Document Version:** 1.0  
**Last Updated:** May 29, 2026  
**Created by:** Cline AI
