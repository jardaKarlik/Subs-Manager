"""
Test email parsing locally with SQLite database.
This avoids hitting Railway on every test.
"""

import asyncio
import os
from sqlalchemy import select, func

# Force SQLite for local testing (before importing database)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_subscriptions.db"

from database import init_db, AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from email_fetcher import EmailFetcher

async def main():
    print("🧪 Local Testing Environment")
    print("=" * 60)
    
    # Initialize fresh database
    await init_db()
    print("✅ Database initialized: test_subscriptions.db")
    
    # Create fetcher
    fetcher = EmailFetcher()
    
    # Test on small sample first
    print("\n📧 Fetching 50 emails from Gmail...")
    async with AsyncSessionLocal() as session:
        results = await fetcher.process_emails(
            db=session,
            sources=["gmail"],  # Just Gmail for now
            max_results=50,
            since_days=30  # Last 30 days only
        )
    
    print("\n📊 RESULTS:")
    print(f"   Processed: {results['processed']}")
    print(f"   New subscriptions: {results['new_subscriptions']}")
    print(f"   Skipped: {results['skipped']}")
    print(f"   Failed: {results['failed']}")
    
    # Query the local database
    async with AsyncSessionLocal() as session:
        # Count subscriptions
        sub_query = select(func.count(Subscription.id))
        sub_result = await session.execute(sub_query)
        total_subs = sub_result.scalar()
        
        # Count processed emails
        email_query = select(func.count(ProcessedEmail.message_id))
        email_result = await session.execute(email_query)
        total_emails = email_result.scalar()
        
        # Count events
        event_query = select(func.count(SubscriptionEvent.id))
        event_result = await session.execute(event_query)
        total_events = event_result.scalar()
        
        print(f"\n💾 DATABASE CONTENTS:")
        print(f"   Subscriptions: {total_subs}")
        print(f"   Processed emails: {total_emails}")
        print(f"   Events: {total_events}")
        
        # Show subscriptions
        if total_subs > 0:
            print(f"\n📋 DETECTED SUBSCRIPTIONS:")
            subs = await session.execute(select(Subscription).limit(10))
            for sub in subs.scalars():
                print(f"   - {sub.service_name}: {sub.cost} {sub.currency}/{sub.billing_cycle}")
        else:
            print("\n⚠️  NO SUBSCRIPTIONS DETECTED!")
            print("    This suggests:")
            print("    1. Classification threshold is too high, OR")
            print("    2. No subscription emails in the sample, OR")
            print("    3. Composio connection is not working")
            
            # Show what WAS processed
            if total_emails > 0:
                print(f"\n📧 But {total_emails} emails were marked as processed")
                print("    Run: python export_classifications.py")
                print("    to see what confidence scores they got")

if __name__ == "__main__":
    asyncio.run(main())
