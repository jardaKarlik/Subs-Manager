"""
local_sync.py - run email + wallet fetch for last 60 days, save locally.
Run from: C:/_dev/subscription_manager/
Usage:    python local_sync.py
"""
import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from database import init_db, AsyncSessionLocal, Subscription, SubscriptionEvent, FinancialRecord
from sqlalchemy import select, func

SINCE_DAYS  = 60
MAX_RESULTS = 500   # per source

async def show_db_state(label):
    async with AsyncSessionLocal() as db:
        subs   = (await db.execute(select(func.count(Subscription.id)))).scalar()
        events = (await db.execute(select(func.count(SubscriptionEvent.id)))).scalar()
        try:
            fr = (await db.execute(select(func.count(FinancialRecord.id)))).scalar()
        except Exception:
            fr = "n/a"
        print(f"\n[DB STATE — {label}]")
        print(f"  subscriptions      : {subs}")
        print(f"  subscription_events: {events}")
        print(f"  financial_records  : {fr}")

async def run_email_sync():
    print("\n" + "="*60)
    print(f"STEP 1 — EMAIL PARSE (last {SINCE_DAYS} days, max {MAX_RESULTS}/source)")
    print("="*60)
    try:
        from email_fetcher import EmailFetcher
        fetcher = EmailFetcher()
        async with AsyncSessionLocal() as db:
            results = await fetcher.process_emails(
                db=db,
                sources=None,
                max_results=MAX_RESULTS,
                since_days=SINCE_DAYS
            )
        print(f"\n  processed        : {results.get('processed', '?')}")
        print(f"  new_subscriptions: {results.get('new_subscriptions', '?')}")
        print(f"  skipped (dup)    : {results.get('skipped', '?')}")
        print(f"  failed           : {results.get('failed', '?')}")
        return results
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback; traceback.print_exc()
        return {}

async def run_wallet_sync():
    print("\n" + "="*60)
    print(f"STEP 2 — WALLET SYNC (last {SINCE_DAYS} days)")
    print("="*60)
    if not os.getenv("WALLET_API_TOKEN"):
        print("  WALLET_API_TOKEN not set — skipping")
        return {}
    try:
        from wallet_fetcher import WalletFetcher
        fetcher = WalletFetcher()
        results = await fetcher.sync(since_days=SINCE_DAYS)
        print(f"\n  fetched  : {results.get('fetched', '?')}")
        print(f"  upserted : {results.get('upserted', '?')}")
        print(f"  accounts : {results.get('accounts', '?')}")
        return results
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback; traceback.print_exc()
        return {}

async def show_top_subs():
    print("\n" + "="*60)
    print("TOP SUBSCRIPTIONS BY COST")
    print("="*60)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).order_by(Subscription.cost.desc()).limit(20)
        )
        subs = result.scalars().all()
        if not subs:
            print("  (none found)")
            return
        for s in subs:
            mo = s.cost/12 if s.billing_cycle == 'yearly' else s.cost
            print(f"  {s.service_name:<30} {s.category:<15} ${mo:>7.2f}/mo  [{s.status}]  src:{s.source}")

async def main():
    print("\nSUBS TERMINAL - LOCAL DATA SYNC")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    await init_db()
    await show_db_state("BEFORE")

    email_results  = await run_email_sync()
    wallet_results = await run_wallet_sync()

    await show_db_state("AFTER")
    await show_top_subs()

    summary = {
        "run_at": datetime.now().isoformat(),
        "since_days": SINCE_DAYS,
        "email": email_results,
        "wallet": wallet_results
    }
    out = r"C:\_temp\sync_summary.json"
    try:
        with open(out, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n  Summary saved to {out}")
    except Exception as e:
        print(f"  (could not save summary: {e})")

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Open http://localhost:8000 to see results.\n")

if __name__ == "__main__":
    asyncio.run(main())
