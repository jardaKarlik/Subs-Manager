"""Dump all app tables to a JSON snapshot.

Usage:  SRC_URL=postgresql://... python scripts/pg_backup.py [output_dir]
"""
import json
import os
import pathlib
import sys
from datetime import datetime

import psycopg2

TABLES = [
    "provider_aliases",
    "provider_industries",
    "subscriptions",
    "financial_records",
    "processed_emails",
    "subscription_events",
    "service_costs",
    "sync_metadata",
    "batch_processes",
]


def main() -> None:
    url = os.environ.get("SRC_URL")
    if not url:
        sys.exit("SRC_URL is required")

    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "backups")
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    conn = psycopg2.connect(url)
    conn.autocommit = True
    payload: dict[str, list] = {}

    with conn.cursor() as cur:
        for table in TABLES:
            try:
                cur.execute(f'SELECT * FROM "{table}"')
                cols = [d[0] for d in cur.description]
                payload[table] = [dict(zip(cols, row)) for row in cur.fetchall()]
                print(f"{table}: {len(payload[table])}")
            except Exception as exc:
                conn.rollback()
                print(f"{table}: SKIP ({type(exc).__name__}: {exc})")

    path = out_dir / f"subs-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {path}  ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
