"""
Subscription Manager API - Enhanced with SQLAlchemy ORM, full CRUD,
pagination, filtering, and async support.

To switch to PostgreSQL (production), set DATABASE_URL env var:
  postgresql+asyncpg://user:password@host:port/dbname
"""

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uvicorn
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from database import (
    init_db, get_db, AsyncSessionLocal,
    Subscription, ProcessedEmail, SubscriptionEvent
)

from email_fetcher import EmailFetcher

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
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup():
    await init_db()


# ============================================================================
# Subscription CRUD Endpoints
# ============================================================================

@app.get("/api/subscriptions", response_model=PaginatedSubscriptions)
async def get_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    billing_cycle: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(service_name|cost|created_at|category|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated subscriptions with filtering and sorting."""
    
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
    
    pages = (total + page_size - 1) // page_size
    
    return {
        "items": [item.to_dict() for item in items],
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
    """Get comprehensive subscription statistics."""
    result = await db.execute(select(Subscription))
    subs = result.scalars().all()
    
    total_monthly = 0.0
    total_yearly = 0.0
    by_category = {}
    by_status = {}
    
    for s in subs:
        cost = s.cost or 0
        
        # Category breakdown
        by_category[s.category] = by_category.get(s.category, {"count": 0, "monthly_cost": 0})
        by_category[s.category]["count"] += 1
        
        # Status breakdown
        by_status[s.status] = by_status.get(s.status, 0) + 1
        
        # Cost calculations
        if s.billing_cycle == "monthly":
            total_monthly += cost
            total_yearly += cost * 12
            by_category[s.category]["monthly_cost"] += cost
        elif s.billing_cycle == "yearly":
            total_yearly += cost
            total_monthly += cost / 12
            by_category[s.category]["monthly_cost"] += cost / 12
        else:
            # For other cycles, count as monthly
            total_monthly += cost
            by_category[s.category]["monthly_cost"] += cost
    
    return {
        "total_subscriptions": len(subs),
        "total_monthly_cost": round(total_monthly, 2),
        "total_yearly_cost": round(total_yearly, 2),
        "by_category": by_category,
        "by_status": by_status
    }


@app.get("/api/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Get simplified summary (backward compatible)."""
    result = await db.execute(select(Subscription))
    subs = result.scalars().all()
    
    total_monthly = 0
    total_yearly = 0
    
    for s in subs:
        cost = s.cost or 0
        if s.billing_cycle == "monthly":
            total_monthly += cost
            total_yearly += cost * 12
        elif s.billing_cycle == "yearly":
            total_yearly += cost
            total_monthly += cost / 12
    
    return {
        "total_subscriptions": len(subs),
        "estimated_monthly_cost": round(total_monthly, 2),
        "estimated_yearly_cost": round(total_yearly, 2)
    }


# ============================================================================
# Email Parsing & Sync
# ============================================================================

class ParseEmailsRequest(BaseModel):
    sources: Optional[List[str]] = None
    max_results: int = Field(default=1000, ge=1, le=2000)
    since_days: int = Field(default=730, ge=1, le=730)


class SyncEmailsRequest(BaseModel):
    sources: Optional[List[str]] = None
    max_results: int = Field(default=100, ge=1, le=1000)
    since_days: int = Field(default=3, ge=1, le=30)


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
            "/api/add-test-data",
            "/api/health"
        ]
    }


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
