"""Create a database on a Railway Postgres instance.

Usage:  ADMIN_URL=postgresql://... python scripts/pg_create_db.py <dbname>
"""
import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def main() -> None:
    url = os.environ.get("ADMIN_URL")
    if not url:
        sys.exit("ADMIN_URL is required")
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/pg_create_db.py <dbname>")

    name = sys.argv[1]
    conn = psycopg2.connect(url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,))
        if cur.fetchone():
            print(f"{name}: already exists")
        else:
            cur.execute(f'CREATE DATABASE "{name}"')
            print(f"{name}: created")


if __name__ == "__main__":
    main()
