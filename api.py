"""
Subscription Manager API - Enhanced with SQLAlchemy ORM, full CRUD,
pagination, filtering, and async support.

To switch to PostgreSQL (production), set DATABASE_URL env var:
  postgresql+asyncpg://user:password@host:port/dbname
"""

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uvicorn
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, update as sql_update
from sqlalchemy.orm import selectinload

from database import (
    init_db, get_db, AsyncSessionLocal,
    Subscription, ProcessedEmail, SubscriptionEvent
)

from email_fetcher import EmailFetcher
from fx import to_usd, format_money, format_compact

# Global fetcher instance
email_fetcher = EmailFetcher()

app = FastAPI(
    title="Subscription Manager API",
    description="Track and manage subscriptions from multiple email sources",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class SubscriptionCreate(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(default="other", max_length=100)
    cost: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", max_length=10)
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly|weekly|daily|one-time)$")
    status: Optional[str] = Field(default="active", pattern="^(active|idle|cancelled)$")
    start_date: Optional[str] = None
    next_billing_date: Optional[str] = None
    notes: Optional[str] = None
    source: str = Field(default="manual", max_length=100)
    icon_url: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    service_name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    cost: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    billing_cycle: Optional[str] = Field(None, pattern="^(monthly|yearly|weekly|daily|one-time)$")
    status: Optional[str] = Field(None, pattern="^(active|idle|cancelled)$")
    start_date: Optional[str] = None
    next_billing_date: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)
    icon_url: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: int
    service_name: str
    category: str
    cost: float
    currency: str
    billing_cycle: str
    status: str
    start_date: Optional[str]
    next_billing_date: Optional[str]
    notes: Optional[str]
    source: str
    icon_url: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class PaginatedSubscriptions(BaseModel):
    items: List[SubscriptionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class StatsResponse(BaseModel):
    total_subscriptions: int
    total_monthly_cost: float
    total_yearly_cost: float
    by_category: dict
    by_status: dict


# ============================================================================
# Startup / Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup():
    await init_db()
    from scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    from scheduler import stop_scheduler
    stop_scheduler()


# ============================================================================
# Subscription CRUD Endpoints
# ============================================================================

@app.get("/api/subscriptions", response_model=PaginatedSubscriptions)
async def get_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    billing_cycle: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None, description="Filter by approval_status: pending|approved|dismissed"),
    sort_by: str = Query("created_at", pattern="^(service_name|cost|created_at|category|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated subscriptions with filtering and sorting."""
    from database import FinancialRecord

    # Build base query
    query = select(Subscription)
    count_query = select(func.count(Subscription.id))

    # Apply filters
    if category:
        query = query.where(Subscription.category == category)
        count_query = count_query.where(Subscription.category == category)

    if status:
        query = query.where(Subscription.status == status)
        count_query = count_query.where(Subscription.status == status)

    if billing_cycle:
        query = query.where(Subscription.billing_cycle == billing_cycle)
        count_query = count_query.where(Subscription.billing_cycle == billing_cycle)

    if search:
        search_term = f"%{search}%"
        query = query.where(Subscription.service_name.ilike(search_term))
        count_query = count_query.where(Subscription.service_name.ilike(search_term))

    if approval_status:
        query = query.where(Subscription.approval_status == approval_status)
        count_query = count_query.where(Subscription.approval_status == approval_status)
    # NOTE: We do NOT add a default "exclude dismissed" filter here because
    # all 62 existing rows have approval_status = NULL (legacy data).
    # The COALESCE workaround (treating NULL as "not dismissed") was returning
    # 500s on Railway for page_size >= 30. New rows will have an explicit
    # approval_status set; the filter can be re-enabled once all data
    # is backfilled with a non-NULL value.

    # Apply sorting
    sort_column = getattr(Subscription, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    # total_spent enrichment is disabled here — it was causing 500s
    # on Railway for page_size >= 23 (likely a JSON/JSONB indexing issue
    # with the labels column on financial_records). The UI can fetch
    # per-subscription spend from /api/wallet-spend instead.
    total_spent_map: dict[int, float] = {}

    pages = (total + page_size - 1) // page_size

    items_out = []
    for item in items:
        # to_dict() is defensive — returns a full payload even for
        # rows with bad data (e.g. last_payment_date as string).
        d = item.to_dict()
        d["total_spent"] = total_spent_map.get(item.id)
        items_out.append(d)

    return {
        "items": items_out,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@app.get("/api/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(subscription_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single subscription by ID."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return sub.to_dict()


@app.post("/api/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def add_subscription(sub: SubscriptionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new subscription."""
    new_sub = Subscription(**sub.model_dump())
    db.add(new_sub)
    await db.commit()
    await db.refresh(new_sub)
    return new_sub.to_dict()


@app.put("/api/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    sub: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing subscription."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update only provided fields
    update_data = sub.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(existing, field, value)
    
    await db.commit()
    await db.refresh(existing)
    return existing.to_dict()


@app.delete("/api/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(subscription_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a subscription."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    await db.delete(sub)
    await db.commit()
    return None


# ============================================================================
# Statistics & Summary
# ============================================================================

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get comprehensive subscription statistics including wallet-enriched data."""
    from database import FinancialRecord
    result = await db.execute(select(Subscription))
    subs = result.scalars().all()

    # Monthly-equivalent cost per sub, in the sub's own currency.
    # one-time purchases are NOT counted as monthly (they're a one-off hit).
    # daily is treated as a small recurring charge.
    def _monthly_equiv(s):
        cost = s.cost or 0
        if s.billing_cycle == "yearly":  return cost / 12
        if s.billing_cycle == "weekly":  return cost * 52 / 12
        if s.billing_cycle == "daily":   return cost * 30
        if s.billing_cycle == "one-time":return 0  # excluded from monthly
        return cost  # monthly or unknown

    total_monthly = 0.0
    total_yearly = 0.0
    by_category = {}
    by_status = {}
    by_currency = {}   # {"CZK": {"count": N, "monthly": X}, "USD": {...}, ...}
    total_monthly_usd = 0.0
    confirmed_count = 0
    recurring_count = 0  # excludes one-time

    for s in subs:
        cost = s.cost or 0
        cur = (s.currency or "USD").upper()

        by_category[s.category] = by_category.get(s.category, {"count": 0, "monthly_cost": 0})
        by_category[s.category]["count"] += 1
        by_status[s.status] = by_status.get(s.status, 0) + 1

        mo = _monthly_equiv(s)
        yr = mo * 12

        by_category[s.category]["monthly_cost"] += mo
        total_monthly += mo
        total_yearly += yr
        total_monthly_usd += to_usd(mo, cur)

        by_currency[cur] = by_currency.get(cur, {"count": 0, "monthly": 0.0})
        by_currency[cur]["count"] += 1
        by_currency[cur]["monthly"] += mo

        if s.billing_cycle != "one-time":
            recurring_count += 1
        if s.confirmed_by_wallet:
            confirmed_count += 1

    # Wallet stats
    wallet_record_count = 0
    wallet_sync_last = None
    actual_monthly_spend = 0.0
    try:
        wcount = await db.execute(select(func.count(FinancialRecord.id)))
        wallet_record_count = wcount.scalar() or 0

        wlast = await db.execute(select(func.max(FinancialRecord.fetched_at)))
        wallet_sync_last = wlast.scalar()

        # Actual monthly spend: sum of matched expense records in last 30 days
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        wspend = await db.execute(
            select(func.sum(FinancialRecord.amount)).where(
                FinancialRecord.matched_subscription_id != None,  # noqa: E711
                FinancialRecord.record_type == "expense",
                FinancialRecord.date >= thirty_days_ago,
            )
        )
        raw_spend = wspend.scalar() or 0.0
        actual_monthly_spend = round(abs(raw_spend), 2)
    except Exception:
        pass

    return {
        "total_subscriptions": len(subs),
        "recurring_count": recurring_count,
        "one_time_count": len(subs) - recurring_count,
        "total_monthly_cost": round(total_monthly, 2),  # mixed-currency (for reference)
        "total_monthly_usd": round(total_monthly_usd, 2),  # normalized to USD
        "total_yearly_cost": round(total_yearly, 2),
        "by_category": by_category,
        "by_status": by_status,
        "by_currency": by_currency,
        "base_currency": "USD",
        "data_as_of": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        # Wallet-enriched fields
        "confirmed_count": confirmed_count,
        "unconfirmed_count": len(subs) - confirmed_count,
        "actual_monthly_spend": actual_monthly_spend,
        "wallet_record_count": wallet_record_count,
        "wallet_sync_last": wallet_sync_last.isoformat() if wallet_sync_last else None,
    }


@app.get("/api/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Get simplified summary (backward compatible)."""
    result = await db.execute(select(Subscription))
    subs = result.scalars().all()
    
    total_monthly = 0.0
    total_yearly = 0.0
    total_monthly_usd = 0.0
    by_currency = {}
    recurring = 0

    for s in subs:
        cost = s.cost or 0
        cur = (s.currency or "USD").upper()
        if s.billing_cycle == "yearly":   mo = cost / 12
        elif s.billing_cycle == "weekly": mo = cost * 52 / 12
        elif s.billing_cycle == "daily":  mo = cost * 30
        elif s.billing_cycle == "one-time": mo = 0
        else:                              mo = cost

        total_monthly += mo
        total_yearly += mo * 12
        total_monthly_usd += to_usd(mo, cur)
        if s.billing_cycle != "one-time":
            recurring += 1
        by_currency[cur] = by_currency.get(cur, 0.0) + mo

    return {
        "total_subscriptions": len(subs),
        "recurring_count": recurring,
        "one_time_count": len(subs) - recurring,
        # Mixed-currency total (legacy) — sum of raw values across currencies.
        # Kept for backward compatibility; prefer total_monthly_usd for display.
        "estimated_monthly_cost": round(total_monthly, 2),
        "estimated_monthly_usd": round(total_monthly_usd, 2),
        "estimated_yearly_cost": round(total_yearly, 2),
        "by_currency": {k: round(v, 2) for k, v in by_currency.items()},
        "base_currency": "USD",
        "data_as_of": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


# ============================================================================
# Email Parsing & Sync
# ============================================================================

class ParseEmailsRequest(BaseModel):
    sources: Optional[List[str]] = None
    max_results: int = Field(default=1000, ge=1, le=50000)
    since_days: int = Field(default=730, ge=1, le=730)


class SyncEmailsRequest(BaseModel):
    sources: Optional[List[str]] = None
    max_results: int = Field(default=100, ge=1, le=50000)
    since_days: int = Field(default=3, ge=1, le=365)


@app.post("/api/parse-emails")
async def parse_emails(
    req: ParseEmailsRequest = ParseEmailsRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Full backfill: Parse emails from all configured sources and detect subscriptions.
    Default: 1 year back, 50 emails per source.
    """
    try:
        results = await email_fetcher.process_emails(
            db=db,
            sources=req.sources,
            max_results=req.max_results,
            since_days=req.since_days
        )
        return {
            "success": True,
            "message": f"Processed {results['processed']} emails, found {results['new_subscriptions']} new subscriptions",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email parsing failed: {str(e)}")


@app.post("/api/sync-emails")
async def sync_emails(
    req: SyncEmailsRequest = SyncEmailsRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Incremental sync: Parse only recent emails (default: last 3 days).
    Run this on a schedule (e.g., every 3 days) to keep subscriptions up to date.
    """
    try:
        results = await email_fetcher.process_emails(
            db=db,
            sources=req.sources,
            max_results=req.max_results,
            since_days=req.since_days
        )
        return {
            "success": True,
            "message": f"Sync complete: {results['processed']} processed, {results['new_subscriptions']} new, {results['skipped']} skipped",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sync failed: {str(e)}")


@app.get("/api/sync-emails")
async def sync_emails_get(
    sources: Optional[str] = Query(None, description="Comma-separated source names"),
    max_results: int = Query(100, ge=1, le=50000),
    since_days: int = Query(3, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    GET version: Incremental sync with query params.
    Use this for simple curl calls without JSON body.
    """
    try:
        source_list = [s.strip() for s in sources.split(",")] if sources else None
        results = await email_fetcher.process_emails(
            db=db,
            sources=source_list,
            max_results=max_results,
            since_days=since_days
        )
        return {
            "success": True,
            "message": f"Sync complete: {results['processed']} processed, {results['new_subscriptions']} new, {results['skipped']} skipped",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sync failed: {str(e)}")


@app.get("/api/parse-emails")
async def parse_emails_get(
    sources: Optional[str] = Query(None, description="Comma-separated source names"),
    max_results: int = Query(1000, ge=1, le=50000),
    since_days: int = Query(730, ge=1, le=730),
    db: AsyncSession = Depends(get_db)
):
    """
    GET version: Full backfill with query params.
    Use this for simple curl calls without JSON body.
    """
    try:
        source_list = [s.strip() for s in sources.split(",")] if sources else None
        results = await email_fetcher.process_emails(
            db=db,
            sources=source_list,
            max_results=max_results,
            since_days=since_days
        )
        return {
            "success": True,
            "message": f"Processed {results['processed']} emails, found {results['new_subscriptions']} new subscriptions",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email parsing failed: {str(e)}")


@app.get("/api/events")
async def get_events(
    service_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db)
):
    """Get subscription payment events for time-based spend tracking."""
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    query = select(SubscriptionEvent).where(SubscriptionEvent.event_date >= cutoff)

    if service_name:
        query = query.where(SubscriptionEvent.service_name.ilike(f"%{service_name}%"))
    if category:
        query = query.where(SubscriptionEvent.category == category)

    query = query.order_by(SubscriptionEvent.event_date.desc())
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [e.to_dict() for e in events],
        "total_events": len(events),
        "period_months": months
    }


@app.post("/api/add-test-data")
async def add_test_data(db: AsyncSession = Depends(get_db)):
    """Add test subscription data for demonstration."""
    test_data = [
        # Streaming
        SubscriptionCreate(
            service_name="Netflix",
            category="streaming",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            start_date="2023-01-10",
            notes="Plan: Standard",
            source="test"
        ),
        SubscriptionCreate(
service_name="Disney+",
            category="streaming",
            cost=10.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Hulu",
            category="streaming",
            cost=7.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Music
        SubscriptionCreate(
            service_name="Spotify Premium",
            category="music",
            cost=120.00,
            currency="USD",
            billing_cycle="yearly",
            start_date="2022-06-15",
            notes="Plan: Family",
            source="test"
        ),
        SubscriptionCreate(
service_name="Apple Music",
            category="music",
            cost=10.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Dev Tools
        SubscriptionCreate(
            service_name="GitHub Pro",
            category="dev_tools",
            cost=4.00,
            currency="USD",
            billing_cycle="monthly",
            start_date="2021-11-20",
            notes="Plan: Pro",
            source="test"
        ),
        SubscriptionCreate(
service_name="JetBrains All Products",
            category="dev_tools",
            cost=149.00,
            currency="USD",
            billing_cycle="yearly",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Vercel Pro",
            category="dev_tools",
            cost=20.00,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Design
        SubscriptionCreate(
            service_name="Adobe Creative Cloud",
            category="design",
            cost=600.00,
            currency="USD",
            billing_cycle="yearly",
            start_date="2023-03-05",
            notes="Plan: All Apps",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Figma Professional",
            category="design",
            cost=12.00,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Cloud
        SubscriptionCreate(
            service_name="AWS",
            category="cloud",
            cost=127.45,
            currency="USD",
            billing_cycle="monthly",
            start_date="2024-01-01",
            notes="Plan: Pay-as-you-go",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Google Cloud Platform",
            category="cloud",
            cost=89.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # AI
        SubscriptionCreate(
            service_name="ChatGPT Plus",
            category="ai",
            cost=20.00,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Anthropic Claude API",
            category="ai",
            cost=0.00,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Productivity
        SubscriptionCreate(
            service_name="Notion Personal",
            category="productivity",
            cost=10.00,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Slack Pro",
            category="productivity",
            cost=8.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
    ]

    count = 0
    for sub_data in test_data:
        sub = Subscription(**sub_data.model_dump())
        db.add(sub)
        count += 1

    await db.commit()

    return {
        "success": True,
        "message": f"Added {count} test subscriptions",
        "count": count
    }


# ============================================================================
# Categories
# ============================================================================

@app.get("/api/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all unique categories with counts."""
    result = await db.execute(
        select(Subscription.category, func.count(Subscription.id))
        .group_by(Subscription.category)
        .order_by(func.count(Subscription.id).desc())
    )
    categories = result.all()
    
    return {
        "categories": [
            {"name": cat, "count": count} for cat, count in categories
        ]
    }


# ============================================================================
# Health Check
# ============================================================================

@app.post("/api/cleanup")
async def cleanup_old_data(days: int = Query(730, ge=90, le=1095), db: AsyncSession = Depends(get_db)):
    """
    Cleanup old processed emails and events to keep DB lean.
    Default: 2 years (730 days). Minimum: 90 days. Maximum: 3 years.
    """
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Delete old processed emails
    del_emails = await db.execute(
        delete(ProcessedEmail).where(ProcessedEmail.processed_date < cutoff)
    )
    emails_deleted = del_emails.rowcount

    # Delete old subscription events
    del_events = await db.execute(
        delete(SubscriptionEvent).where(SubscriptionEvent.event_date < cutoff)
    )
    events_deleted = del_events.rowcount

    await db.commit()

    return {
        "success": True,
        "message": f"Cleanup complete: {emails_deleted} processed emails, {events_deleted} events deleted",
        "retention_days": days,
        "cutoff_date": cutoff.isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": "connected",
        "endpoints": [
            "/api/subscriptions",
            "/api/subscriptions/{id}",
            "/api/stats",
            "/api/summary",
            "/api/categories",
            "/api/parse-emails",
            "/api/sync-emails",
            "/api/events",
            "/api/cleanup",
            "/api/webhook/status",
            "/api/add-test-data",
            "/api/health"
        ]
    }


@app.get("/api/webhook/status")
async def webhook_status(db: AsyncSession = Depends(get_db)):
    """Simple status endpoint for Discord/Make.com integrations."""
    from database import ProcessedEmail, SubscriptionEvent

    # Get total subscriptions
    sub_query = select(func.count(Subscription.id))
    sub_result = await db.execute(sub_query)
    total_subs = sub_result.scalar() or 0

    # Get total cost
    cost_query = select(Subscription.cost, Subscription.billing_cycle)
    cost_result = await db.execute(cost_query)
    subs = cost_result.all()

    monthly_cost = 0.0
    for cost, cycle in subs:
        if cycle == "monthly":
            monthly_cost += cost
        elif cycle == "yearly":
            monthly_cost += cost / 12

    # Get processed emails count
    # Primary: count ProcessedEmail records (exact dedup tracker)
    total_emails = 0
    try:
        email_query = select(func.count(ProcessedEmail.message_id))
        email_result = await db.execute(email_query)
        total_emails = email_result.scalar() or 0
    except Exception:
        pass

    # Fallback: count distinct source emails from subscription_events
    # (useful when ProcessedEmail is empty, e.g. ephemeral SQLite on Railway)
    if total_emails == 0:
        try:
            event_query = select(func.count(func.distinct(SubscriptionEvent.message_id)))
            event_result = await db.execute(event_query)
            total_emails = event_result.scalar() or 0
        except Exception:
            pass

    message = f"📊 **Subscription Manager Status**\n\nDatabase contains **{total_subs}** active subscriptions totaling **${monthly_cost:.2f}/month**.\nWe have processed **{total_emails}** emails to find these."

    return {
        "content": message,
        "total_subscriptions": total_subs,
        "estimated_monthly_cost": round(monthly_cost, 2),
        "total_emails_processed": total_emails
    }


# ============================================================================
# Wallet (BudgetBakers) Endpoints
# ============================================================================

@app.post("/api/sync-wallet")
async def sync_wallet(since_days: int = Query(120, ge=1, le=730)):
    """Fetch financial records from BudgetBakers Wallet and store them."""
    from wallet_fetcher import WalletFetcher
    fetcher = WalletFetcher()
    result = await fetcher.sync(since_days=since_days)
    return {"status": "ok", **result}


@app.get("/api/sync-wallet")
async def sync_wallet_get(since_days: int = Query(120, ge=1, le=730)):
    """GET version of wallet sync (browser-friendly)."""
    from wallet_fetcher import WalletFetcher
    fetcher = WalletFetcher()
    result = await fetcher.sync(since_days=since_days)
    return {"status": "ok", **result}


@app.get("/api/wallet-records")
async def get_wallet_records(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    unmatched_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Return stored financial records, optionally filtered to unmatched ones."""
    from database import FinancialRecord
    from sqlalchemy import select, func

    q = select(FinancialRecord).order_by(FinancialRecord.date.desc())
    if unmatched_only:
        q = q.where(FinancialRecord.matched_subscription_id == None)  # noqa: E711
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    records = result.scalars().all()

    count_q = select(func.count(FinancialRecord.id))
    if unmatched_only:
        count_q = count_q.where(FinancialRecord.matched_subscription_id == None)  # noqa: E711
    total = (await db.execute(count_q)).scalar() or 0

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [r.to_dict() for r in records],
    }


@app.get("/api/wallet-spend")
async def wallet_spend(db: AsyncSession = Depends(get_db)):
    """Total historical spend per service from wallet financial records."""
    from database import FinancialRecord
    rows = await db.execute(
        select(
            Subscription.id,
            Subscription.service_name,
            Subscription.currency,
            func.count(FinancialRecord.id).label("payments"),
            func.sum(FinancialRecord.amount).label("total_amount"),
            func.avg(FinancialRecord.amount).label("avg_amount"),
            func.min(FinancialRecord.date).label("first_payment"),
            func.max(FinancialRecord.date).label("last_payment"),
        )
        .join(FinancialRecord, FinancialRecord.matched_subscription_id == Subscription.id)
        .where(FinancialRecord.record_type == "expense")
        .group_by(Subscription.id)
        .order_by(func.sum(FinancialRecord.amount))  # most expensive first (amounts are negative)
    )
    items = rows.all()
    return {
        "count": len(items),
        "services": [
            {
                "id": r.id,
                "service_name": r.service_name,
                "payments": r.payments,
                "total_spent": round(abs(r.total_amount or 0), 2),
                "avg_payment": round(abs(r.avg_amount or 0), 2),
                "currency": r.currency,
                "first_payment": r.first_payment.isoformat() if r.first_payment else None,
                "last_payment": r.last_payment.isoformat() if r.last_payment else None,
            }
            for r in items
        ],
    }


@app.post("/api/match-wallet")
async def match_wallet():
    """Cross-reference financial records against subscriptions."""
    from subscription_matcher import SubscriptionMatcher
    matcher = SubscriptionMatcher()
    match_result = await matcher.match_all()
    cycle_result = await matcher.infer_billing_cycles()
    return {"status": "ok", **match_result, **cycle_result}


@app.get("/api/wallet-candidates")
async def wallet_candidates(min_occurrences: int = Query(2, ge=2), min_score: int = Query(0, ge=0)):
    """Return unmatched recurring wallet payees scored by subscription likelihood."""
    from subscription_matcher import SubscriptionMatcher
    matcher = SubscriptionMatcher()
    candidates = await matcher.find_unmatched_recurring(min_occurrences=min_occurrences)
    if min_score > 0:
        candidates = [c for c in candidates if c["score"] >= min_score]
    return {"count": len(candidates), "candidates": candidates}


class PromoteCandidateRequest(BaseModel):
    payee: str
    service_name: str
    category: str = "other"


@app.post("/api/wallet-candidates/promote")
async def promote_candidate(req: PromoteCandidateRequest):
    """Promote a wallet payee to a confirmed subscription."""
    from subscription_matcher import SubscriptionMatcher
    matcher = SubscriptionMatcher()
    result = await matcher.promote_candidate(
        payee=req.payee,
        service_name=req.service_name,
        category=req.category,
    )
    return {"status": "ok", **result}


@app.get("/api/wallet-accounts")
async def get_wallet_accounts():
    """Return live account list from BudgetBakers API."""
    from wallet_fetcher import WalletFetcher
    fetcher = WalletFetcher()
    accounts = await fetcher.fetch_accounts()
    return {"accounts": accounts}


# ============================================================================
# Approval Workflow
# ============================================================================

@app.post("/api/subscriptions/{subscription_id}/approve")
async def approve_subscription(subscription_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a pending subscription (wallet_discovery or manual)."""
    result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.approval_status = "approved"
    sub.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "approved", "id": subscription_id, "service_name": sub.service_name}


@app.post("/api/subscriptions/{subscription_id}/dismiss")
async def dismiss_subscription(subscription_id: int, db: AsyncSession = Depends(get_db)):
    """Dismiss a pending subscription (hides it from main listing)."""
    result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.approval_status = "dismissed"
    sub.status = "cancelled"
    sub.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "dismissed", "id": subscription_id, "service_name": sub.service_name}


@app.post("/api/subscriptions/bulk-approve")
async def bulk_approve(ids: List[int], db: AsyncSession = Depends(get_db)):
    """Approve multiple pending subscriptions at once."""
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(Subscription)
        .where(Subscription.id.in_(ids))
        .values(approval_status="approved", updated_at=datetime.utcnow())
    )
    await db.commit()
    return {"status": "ok", "approved_count": len(ids)}


@app.post("/api/subscriptions/bulk-dismiss")
async def bulk_dismiss(ids: List[int], db: AsyncSession = Depends(get_db)):
    """Dismiss multiple pending subscriptions at once."""
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(Subscription)
        .where(Subscription.id.in_(ids))
        .values(approval_status="dismissed", status="cancelled", updated_at=datetime.utcnow())
    )
    await db.commit()
    return {"status": "ok", "dismissed_count": len(ids)}


@app.post("/api/seed-pending-candidates")
async def seed_pending_candidates(db: AsyncSession = Depends(get_db)):
    """Seed test pending candidates (Steam, Roblox, IFTTT Pro, Loopmasters) for UI testing."""
    candidates = [
        {"service_name": "Steam", "category": "gaming", "cost": 279.0, "currency": "CZK", "billing_cycle": "monthly"},
        {"service_name": "Roblox", "category": "gaming", "cost": 149.0, "currency": "CZK", "billing_cycle": "monthly"},
        {"service_name": "IFTTT Pro", "category": "productivity", "cost": 89.0, "currency": "CZK", "billing_cycle": "monthly"},
        {"service_name": "Loopmasters", "category": "music_tools", "cost": 199.0, "currency": "CZK", "billing_cycle": "monthly"},
    ]
    added = []
    for c in candidates:
        # Skip if already exists by name
        existing = await db.execute(
            select(Subscription).where(Subscription.service_name == c["service_name"])
        )
        if existing.scalar_one_or_none():
            continue
        sub = Subscription(
            **c,
            status="active",
            source="wallet_discovery",
            approval_status="pending",
        )
        db.add(sub)
        added.append(c["service_name"])
    await db.commit()
    return {"status": "ok", "seeded": added}


# ============================================================================

# Scheduler Management Endpoints
# ============================================================================

@app.get("/api/scheduler/jobs")
async def list_jobs():
    """List all scheduled jobs and their next run times."""
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"running": scheduler.running, "jobs": jobs}


@app.post("/api/scheduler/run/{job_id}")
async def run_job_now(job_id: str):
    """Manually trigger a scheduled job by ID."""
    from scheduler import get_scheduler, job_wallet_sync, job_email_sync, job_wallet_match, job_discovery_sweep
    valid_jobs = {
        "wallet_sync": job_wallet_sync,
        "email_sync": job_email_sync,
        "wallet_match": job_wallet_match,
        "discovery_sweep": job_discovery_sweep,
    }
    if job_id not in valid_jobs:
        raise HTTPException(status_code=404, detail=f"Unknown job '{job_id}'. Valid: {list(valid_jobs)}")
    import asyncio
    asyncio.create_task(valid_jobs[job_id]())
    return {"status": "triggered", "job_id": job_id}


# ============================================================================
# Mount Frontend Static Files (AFTER all API routes to avoid route capture)
# Prefer frontend/ (simple UI with wallet features), fall back to glass dist.
# ============================================================================

_base = Path(__file__).parent
_frontend_candidates = [_base / "frontend", _base / "frontend_glass_dist"]
for frontend_dir in _frontend_candidates:
    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
        break


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
