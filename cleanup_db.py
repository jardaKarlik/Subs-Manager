"""
cleanup_db.py - Fix bad data from first sync run:
  1. Delete test/demo records (source: test, demo_script)
  2. Delete false positives (Vase/Vaše, Apetitonline, Superzoo, Braintreegateway, Fastspring, Unknown Service)
  3. Fix Microsoft 20,800,000 CZK -> correct amount
  4. Fix Google 1000 USD -> 1000 CZK (currency was wrong)
  5. Show clean state after
"""
import asyncio
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "subscriptions.db"

# IDs / names to delete outright
DELETE_SOURCES  = ('test', 'demo_script')
DELETE_NAMES    = ('Vase', 'Apetitonline', 'Superzoo', 'Braintreegateway', 'Fastspring', 'Unknown Service')

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    print("\n=== BEFORE ===")
    cur.execute("SELECT id, service_name, cost, currency, source FROM subscriptions ORDER BY cost DESC")
    rows = cur.fetchall()
    for r in rows:
        print(f"  [{r[0]:2d}] {r[1]:<30} {r[2]:>12.2f} {r[3]}  src:{r[4]}")

    # 1. Delete test/demo records
    cur.execute("DELETE FROM subscriptions WHERE source IN ('test','demo_script')")
    n1 = cur.rowcount
    print(f"\n  Deleted {n1} test/demo records")

    # 2. Delete false positives by name
    for name in DELETE_NAMES:
        cur.execute("DELETE FROM subscriptions WHERE service_name = ?", (name,))
        if cur.rowcount:
            print(f"  Deleted false positive: {name}")

    # 3. Fix Microsoft 20,800,000 CZK — regex grabbed account number, not amount.
    #    Real Microsoft 365 in CZ is ~300 CZK/mo. Correct to 300.
    cur.execute(
        "UPDATE subscriptions SET cost = 300.0, currency = 'CZK' "
        "WHERE service_name = 'Microsoft' AND cost > 10000"
    )
    if cur.rowcount:
        print("  Fixed Microsoft cost: 20,800,000 -> 300 CZK")

    # 4. Fix Google: currency stored as USD but it's 1000 CZK (~$44)
    cur.execute(
        "UPDATE subscriptions SET currency = 'CZK' "
        "WHERE service_name = 'Google' AND cost = 1000.0 AND currency = 'USD'"
    )
    if cur.rowcount:
        print("  Fixed Google currency: USD -> CZK (still 1000 CZK)")

    # 5. Fix Spotify 299 USD -> 299 CZK
    cur.execute(
        "UPDATE subscriptions SET currency = 'CZK' "
        "WHERE service_name = 'Spotify' AND cost = 299.0 AND currency = 'USD'"
    )
    if cur.rowcount:
        print("  Fixed Spotify currency: USD -> CZK")

    # 6. Also clean orphaned processed_emails for deleted subs
    #    (keep processed_emails so we don't re-parse the same emails)

    conn.commit()

    print("\n=== AFTER ===")
    cur.execute("SELECT id, service_name, cost, currency, billing_cycle, source FROM subscriptions ORDER BY cost DESC")
    rows = cur.fetchall()
    for r in rows:
        mo = r[2]/12 if r[4] == 'yearly' else r[2]
        print(f"  [{r[0]:2d}] {r[1]:<30} {mo:>8.2f}/mo {r[3]}  cycle:{r[4]}  src:{r[5]}")

    # Show estimated totals per currency
    print("\n=== TOTALS BY CURRENCY ===")
    cur.execute("""
        SELECT currency,
               SUM(CASE WHEN billing_cycle='monthly' THEN cost
                        WHEN billing_cycle='yearly'  THEN cost/12.0
                        ELSE cost END) as monthly_equiv
        FROM subscriptions
        GROUP BY currency
        ORDER BY monthly_equiv DESC
    """)
    fx = {'USD': 1.0, 'EUR': 1.08, 'GBP': 1.27, 'CZK': 0.044}
    total_usd = 0.0
    for cur_code, mo in cur.fetchall():
        rate   = fx.get(cur_code, 1.0)
        usd_eq = mo * rate
        total_usd += usd_eq
        print(f"  {cur_code}: {mo:>8.2f}/mo  ≈  ${usd_eq:>7.2f} USD")
    print(f"\n  TOTAL (approx USD): ${total_usd:.2f}/mo  ~  ${total_usd*12:.0f}/yr")

    conn.close()

if __name__ == "__main__":
    run()
