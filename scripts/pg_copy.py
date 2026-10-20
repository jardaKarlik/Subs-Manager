"""Copy app tables source -> target, schema-aware.

Usage:  SRC_URL=... DST_URL=... python scripts/pg_copy.py

Copies the intersection of source/target columns, truncates the target first,
resets each `id` sequence, and prints a per-table source/target count.

Exit code 1 if any table count mismatches.
"""
import io
import os
import sys

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


def columns(conn, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema='public' AND table_name=%s
               ORDER BY ordinal_position""",
            (table,),
        )
        return [r[0] for r in cur.fetchall()]


def main() -> None:
    src_url = os.environ.get("SRC_URL")
    dst_url = os.environ.get("DST_URL")
    if not src_url or not dst_url:
        sys.exit("SRC_URL and DST_URL are both required")

    src = psycopg2.connect(src_url)
    dst = psycopg2.connect(dst_url)
    src.autocommit = True
    dst.autocommit = True

    problems = 0
    with src.cursor() as sc, dst.cursor() as dc:
        for table in TABLES:
            s_cols, d_cols = columns(src, table), columns(dst, table)
            if not s_cols or not d_cols:
                side = "source" if not s_cols else "target"
                print(f"SKIP  {table}: table missing on {side}")
                continue

            common = [c for c in s_cols if c in d_cols]
            dropped = [c for c in s_cols if c not in d_cols]
            added = [c for c in d_cols if c not in s_cols]
            if dropped:
                print(f"WARN  {table}: source-only columns dropped: {dropped}")
            if added:
                print(f"WARN  {table}: target-only columns defaulted: {added}")

            collist = ", ".join(f'"{c}"' for c in common)
            buf = io.StringIO()
            sc.copy_expert(f'COPY "{table}" ({collist}) TO STDOUT WITH CSV', buf)
            buf.seek(0)

            dc.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
            dc.copy_expert(f'COPY "{table}" ({collist}) FROM STDIN WITH CSV', buf)

            dc.execute("SELECT pg_get_serial_sequence(%s, 'id')",
                       (f'public."{table}"',))
            seq = dc.fetchone()[0]
            if seq:
                dc.execute(
                    f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM \"{table}\"), 1), "
                    f"(SELECT COUNT(*) > 0 FROM \"{table}\"))",
                    (seq,),
                )

            sc.execute(f'SELECT COUNT(*) FROM "{table}"')
            n_src = sc.fetchone()[0]
            dc.execute(f'SELECT COUNT(*) FROM "{table}"')
            n_dst = dc.fetchone()[0]
            ok = n_src == n_dst
            if not ok:
                problems += 1
            print(f"{'OK  ' if ok else 'FAIL'} {table}: source={n_src} target={n_dst}")

    print(f"\n{'all tables copied' if not problems else f'{problems} MISMATCH(ES)'}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
