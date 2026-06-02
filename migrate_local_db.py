"""
migrate_local_db.py — bring local subscriptions.db up to date with current data model.

Safe to run multiple times (checks before altering).

Changes applied:
  subscriptions   — add confirmed_by_wallet, last_payment_date, actual_cost, approval_status
  financial_records — create table if not exists
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "subscriptions.db"

def col_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())

def table_exists(cur, table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

def migrate():
    print(f"DB path: {DB_PATH}")
    if not DB_PATH.exists():
        print("✗ DB not found — run `python api.py` once first to create it")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    changes = 0

    # ── subscriptions: new wallet columns ─────────────────────────────────
    new_cols = [
        ("confirmed_by_wallet", "BOOLEAN DEFAULT 0"),
        ("last_payment_date",   "DATETIME"),
        ("actual_cost",         "FLOAT"),
        ("approval_status",     "VARCHAR(20) DEFAULT 'approved'"),
    ]
    for col, definition in new_cols:
        if not col_exists(cur, "subscriptions", col):
            cur.execute(f"ALTER TABLE subscriptions ADD COLUMN {col} {definition}")
            print(f"  ✓ subscriptions.{col} added")
            changes += 1
        else:
            print(f"  · subscriptions.{col} already exists")

    # ── financial_records: create if missing ──────────────────────────────
    if not table_exists(cur, "financial_records"):
        cur.execute("""
            CREATE TABLE financial_records (
                id                      VARCHAR(255) PRIMARY KEY,
                date                    DATETIME NOT NULL,
                amount                  FLOAT    NOT NULL,
                currency                VARCHAR(10) NOT NULL,
                payee                   VARCHAR(500),
                category_id             VARCHAR(255),
                category_name           VARCHAR(255),
                account_id              VARCHAR(255),
                account_name            VARCHAR(255),
                note                    VARCHAR(1000),
                labels                  JSON,
                record_type             VARCHAR(50),
                matched_subscription_id INTEGER,
                fetched_at              DATETIME
            )
        """)
        print("  ✓ financial_records table created")
        changes += 1
    else:
        print("  · financial_records already exists")

    conn.commit()
    conn.close()

    print(f"\n{'✓ Migration complete' if changes else '✓ Already up to date'} — {changes} change(s) applied")

    # show final schema
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("\nFinal tables:", tables)
    print("\nsubscriptions columns:")
    cur.execute("PRAGMA table_info(subscriptions)")
    for row in cur.fetchall():
        print(f"  {row[1]:35} {row[2]}")
    conn.close()

if __name__ == "__main__":
    migrate()
