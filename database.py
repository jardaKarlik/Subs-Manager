"""
Database configuration and SQLAlchemy models.
Supports both SQLite (local development) and PostgreSQL (production).
"""

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Integer, Text, select, delete, update, func
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

# Railway injects postgresql:// but SQLAlchemy async requires postgresql+asyncpg://
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    confirmed_by_wallet: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    last_payment_date: Mapped[str] = mapped_column(String(10), nullable=True)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(20), nullable=True)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "confirmed_by_wallet": self.confirmed_by_wallet,
            "last_payment_date": self.last_payment_date,
            "actual_cost": self.actual_cost,
            "approval_status": self.approval_status,
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


class FinancialRecord(Base):
    """Wallet transaction records from BudgetBakers."""
    __tablename__ = "financial_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[str] = mapped_column(String(20), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    payee: Mapped[str] = mapped_column(String(255), nullable=True)
    category_id: Mapped[str] = mapped_column(String(100), nullable=True)
    category_name: Mapped[str] = mapped_column(String(100), nullable=True)
    account_id: Mapped[str] = mapped_column(String(100), nullable=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    labels: Mapped[str] = mapped_column(Text, nullable=True)
    record_type: Mapped[str] = mapped_column(String(50), nullable=True)
    matched_subscription_id: Mapped[int] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[str] = mapped_column(String(30), nullable=True)


async def init_db():
    """Initialize database - create all tables and apply one-time migrations."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create migrations tracking table
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS _migrations "
            "(id VARCHAR(64) PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))

        # Each migration runs exactly once, tracked by id
        pending = [
            ("001_subscriptions_wallet_cols",
             "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS confirmed_by_wallet INTEGER DEFAULT 0"),
            ("002_subscriptions_last_payment",
             "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS last_payment_date VARCHAR(10)"),
            ("003_subscriptions_actual_cost",
             "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS actual_cost FLOAT"),
            ("004_subscriptions_approval_status",
             "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20)"),
            ("005_financial_records_matched_sub",
             "ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS matched_subscription_id INTEGER"),
            ("006_financial_records_fetched_at",
             "ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS fetched_at VARCHAR(30)"),
            ("007_financial_records_id_to_varchar",
             "ALTER TABLE financial_records ALTER COLUMN id TYPE VARCHAR(64) USING id::VARCHAR(64)"),
        ]

        for migration_id, sql in pending:
            try:
                exists = await conn.execute(
                    text("SELECT 1 FROM _migrations WHERE id = :id"),
                    {"id": migration_id}
                )
                if exists.fetchone():
                    continue
                await conn.execute(text(sql))
                await conn.execute(
                    text("INSERT INTO _migrations (id) VALUES (:id)"),
                    {"id": migration_id}
                )
            except Exception:
                pass  # SQLite skips PostgreSQL-only syntax gracefully


async def get_db():
    """Dependency for FastAPI to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
