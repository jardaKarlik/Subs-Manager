"""
Migration script to add 'mailbox' column to subscription_events table.
Supports both SQLite (local development) and PostgreSQL (production).
Handles the case where the column already exists gracefully.

Usage:
    python migrate_add_mailbox.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment or construct default SQLite path
_DB_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_DB_DIR, "subscriptions.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DB_PATH}"
)

# Fix Railway's auto-generated URL: use standard sqlite driver for migration
if DATABASE_URL.startswith("sqlite+aiosqlite"):
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

# Fix Railway's auto-generated PostgreSQL URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def run_migration():
    """Run the migration based on database type."""
    print(f"Using DATABASE_URL: {DATABASE_URL}")
    
    if "postgresql" in DATABASE_URL:
        run_postgres_migration()
    elif "sqlite" in DATABASE_URL:
        run_sqlite_migration()
    else:
        print(f"❌ Unknown database type in: {DATABASE_URL}")
        sys.exit(1)


def run_sqlite_migration():
    """Add mailbox column to SQLite subscription_events table."""
    try:
        import sqlite3
        
        # Extract path from SQLite URL
        db_path = DATABASE_URL.replace("sqlite:///", "")
        
        print(f"Connecting to SQLite: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Try to add the column
            cursor.execute(
                "ALTER TABLE subscription_events ADD COLUMN mailbox VARCHAR(50)"
            )
            conn.commit()
            print("✓ Successfully added 'mailbox' column to subscription_events (SQLite)")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠ Column 'mailbox' already exists in subscription_events (SQLite) — skipping")
            else:
                raise
        finally:
            conn.close()
    except Exception as e:
        print(f"❌ SQLite migration failed: {e}")
        sys.exit(1)


def run_postgres_migration():
    """Add mailbox column to PostgreSQL subscription_events table."""
    try:
        import psycopg2
        
        # Parse PostgreSQL connection string
        # Format: postgresql://user:password@host:port/dbname
        parts = DATABASE_URL.replace("postgresql://", "").split("@")
        if len(parts) == 2:
            user_pass, host_db = parts
            user, password = user_pass.split(":", 1)
            host, dbname = host_db.split("/", 1)
            if ":" in host:
                host, port = host.split(":", 1)
                port = int(port)
            else:
                port = 5432
        else:
            print(f"❌ Could not parse PostgreSQL URL: {DATABASE_URL}")
            sys.exit(1)
        
        print(f"Connecting to PostgreSQL: {host}:{port}/{dbname}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname
        )
        cursor = conn.cursor()
        
        try:
            # Try to add the column
            cursor.execute(
                "ALTER TABLE subscription_events ADD COLUMN mailbox VARCHAR(50)"
            )
            conn.commit()
            print("✓ Successfully added 'mailbox' column to subscription_events (PostgreSQL)")
        except psycopg2.errors.DuplicateColumn:
            print("⚠ Column 'mailbox' already exists in subscription_events (PostgreSQL) — skipping")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"❌ PostgreSQL migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 70)
    print("Migration: Add 'mailbox' column to subscription_events")
    print("=" * 70)
    run_migration()
    print("=" * 70)
    print("✓ Migration complete!")
    print("=" * 70)
