"""
Database configuration and SQLAlchemy models.
Supports both SQLite (local development) and PostgreSQL (production).
"""

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Boolean, Integer, JSON, select, delete, update, func, ForeignKey
from dotenv import load_dotenv

load_dotenv()

# Always use the DB in the subscription_manager folder, regardless of CWD
_DB_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_DB_DIR, "subscriptions.db")

# Database URL configuration
# SQLite: sqlite+aiosqlite:///path/to/subscriptions.db
# PostgreSQL: postgresql+asyncpg://user:pass@host/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{_DB_PATH}"
)

# Fix Railway's auto-generated URL: asyncpg driver required for SQLAlchemy async
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    future=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


class Subscription(Base):
    """Subscription model with enhanced fields for production use."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="other")
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    status: Mapped[str] = mapped_column(String(20), default="active")
    start_date: Mapped[str] = mapped_column(String(10), nullable=True)
    next_billing_date: Mapped[str] = mapped_column(String(10), nullable=True)
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(100), default="manual")
    icon_url: Mapped[str] = mapped_column(String(500), nullable=True)
    # Wallet cross-reference fields
    confirmed_by_wallet: Mapped[bool] = mapped_column(Boolean, default=False)
    last_payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=True)
    # Approval workflow: pending (wallet_discovery) → approved | dismissed
    approval_status: Mapped[str] = mapped_column(String(20), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def _iso(self, v):
        """Coerce datetime/string/None to an ISO-8601 string for JSON."""
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)  # already a string from the DB

    def to_dict(self):
        """Convert model to dictionary for JSON serialization.

        Defensive against bad data: last_payment_date / created_at / updated_at
        may occasionally be stored as strings (e.g. from a previous bug) — we
        coerce to ISO string instead of raising.
        """
        return {
            "id": self.id,
            "service_name": self.service_name,
            "category": self.category,
            "cost": self.cost,
            "currency": self.currency,
            "billing_cycle": self.billing_cycle,
            "status": self.status,
            "start_date": self.start_date,
            "next_billing_date": self.next_billing_date,
            "notes": self.notes,
            "source": self.source,
            "icon_url": self.icon_url,
            "confirmed_by_wallet": self.confirmed_by_wallet,
            "last_payment_date": self._iso(self.last_payment_date),
            "actual_cost": self.actual_cost,
            "approval_status": self.approval_status or "approved",
            "created_at": self._iso(self.created_at),
            "updated_at": self._iso(self.updated_at),
        }


class FinancialRecord(Base):
    """Financial transactions from BudgetBakers Wallet for cross-referencing."""
    __tablename__ = "financial_records"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Wallet record UUID
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    payee: Mapped[str] = mapped_column(String(500), nullable=True)
    category_id: Mapped[str] = mapped_column(String(255), nullable=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=True)
    account_id: Mapped[str] = mapped_column(String(255), nullable=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=True)
    note: Mapped[str] = mapped_column(String(1000), nullable=True)
    labels: Mapped[list] = mapped_column(JSON, default=list)
    record_type: Mapped[str] = mapped_column(String(50), nullable=True)  # expense / income
    matched_subscription_id: Mapped[int] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "amount": self.amount,
            "currency": self.currency,
            "payee": self.payee,
            "category_name": self.category_name,
            "account_name": self.account_name,
            "note": self.note,
            "labels": self.labels,
            "record_type": self.record_type,
            "matched_subscription_id": self.matched_subscription_id,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }


class ProcessedEmail(Base):
    """Track processed emails to avoid duplicates."""
    __tablename__ = "processed_emails"

    message_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SubscriptionEvent(Base):
    """Track subscription payment events over time for charting."""
    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(nullable=False)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="other")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    event_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="email")
    message_id: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "service_name": self.service_name,
            "category": self.category,
            "amount": self.amount,
            "currency": self.currency,
            "billing_cycle": self.billing_cycle,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "source_type": self.source_type,
            "message_id": self.message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


async def init_db():
    """Initialize database - create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for FastAPI to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
