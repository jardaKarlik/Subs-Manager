"""
Test the fixed email fetcher locally with SQLite database.
Data saved to: test_subscriptions_fixed.db
Results exported to: test_results/ folder
"""

import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func

# Force SQLite for local testing
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_subscriptions_fixed.db"

from database import init_db, AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from email_fetcher_fixed import EmailFetcherFixed

async def main():
    print("🧪 TESTING FIXED EMAIL FETCHER")
    print("=" * 60)
    print("📂 Data location: test_subscriptions_fixed.db")
    print("📂 Results folder: test_results/")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize fresh database
    await init_db()
    print("\n✅ Database initialized")
    
    # Create fixed fetcher
    fetcher = EmailFetcherFixed()
    
    print("\n📧 Starting email fetch and processing...")
    print("   - Fetching 50 emails total")
    print("   - Processing in batches of 20")
    print("   - Each batch waits for commit confirmation")
    print()
    
    # Process emails
    async with AsyncSessionLocal() as session:
        results = await fetcher.process_emails_safe(
            db=session,
            sources=["gmail"],  # Start with Gmail only
            max_results=50,
            since_days=30
        )
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    print(f"✉️  Emails processed: {results['processed']}")
    print(f"✅ New subscriptions: {results['new_subscriptions']}")
    print(f"⏭️  Skipped (duplicates): {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    
    # Query database to verify
    async with AsyncSessionLocal() as session:
        # Count everything
        sub_query = select(func.count(Subscription.id))
        sub_result = await session.execute(sub_query)
        total_subs = sub_result.scalar()
        
        email_query = select(func.count(ProcessedEmail.message_id))
        email_result = await session.execute(email_query)
        total_emails = email_result.scalar()
        
        event_query = select(func.count(SubscriptionEvent.id))
        event_result = await session.execute(event_query)
        total_events = event_result.scalar()
        
        print(f"\n💾 DATABASE VERIFICATION:")
        print(f"   Subscriptions in DB: {total_subs}")
        print(f"   Processed emails in DB: {total_emails}")
        print(f"   Events in DB: {total_events}")
        
        # Check data integrity
        if total_emails != results['processed']:
            print(f"\n⚠️  WARNING: Processed count mismatch!")
            print(f"   Expected: {results['processed']}")
            print(f"   Found in DB: {total_emails}")
        else:
            print(f"\n✅ Data integrity verified!")
        
        # Export subscriptions to JSON
        if total_subs > 0:
            print(f"\n📋 DETECTED SUBSCRIPTIONS:")
            subs_query = select(Subscription).order_by(Subscription.created_at.desc())
            subs = await session.execute(subs_query)
            
            subs_data = []
            for sub in subs.scalars():
                print(f"   - {sub.service_name}: {sub.cost} {sub.currency}/{sub.billing_cycle}")
                subs_data.append({
                    "service_name": sub.service_name,
                    "category": sub.category,
                    "cost": sub.cost,
                    "currency": sub.currency,
                    "billing_cycle": sub.billing_cycle,
                    "start_date": sub.start_date,
                    "notes": sub.notes,
                    "source": sub.source
                })
            
            # Save to JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = output_dir / f"subscriptions_{timestamp}.json"
            
            with open(json_file, 'w') as f:
                json.dump({
                    "summary": {
                        "total_subscriptions": total_subs,
                        "total_emails_processed": total_emails,
                        "total_events": total_events,
                        "test_date": timestamp
                    },
                    "subscriptions": subs_data
                }, f, indent=2)
            
            print(f"\n✅ Exported to: {json_file}")
        
        # Export processed emails sample
        emails_query = select(ProcessedEmail).limit(10)
        emails = await session.execute(emails_query)
        
        emails_data = []
        for email in emails.scalars():
            emails_data.append({
                "message_id": email.message_id,
                "source": email.source,
                "processed_date": email.processed_date.isoformat()
            })
        
        if emails_data:
            emails_file = output_dir / f"processed_emails_sample_{timestamp}.json"
            with open(emails_file, 'w') as f:
                json.dump(emails_data, f, indent=2)
    
    # Final summary
    print("\n" + "=" * 60)
    print("📂 OUTPUT FILES:")
    print("=" * 60)
    print(f"📁 Database: test_subscriptions_fixed.db")
    print(f"📁 Results: test_results/ folder")
    print(f"   - subscriptions_*.json")
    print(f"   - processed_emails_sample_*.json")
    
    print("\n💡 NEXT STEPS:")
    if total_subs > 0:
        print("✅ Success! Fixed fetcher is working")
        print("   1. Review test_results/subscriptions_*.json")
        print("   2. Compare with expected results")
        print("   3. If satisfied, update main email_fetcher.py with fixes")
        print("   4. Deploy to Railway")
    else:
        print("⚠️  No subscriptions detected")
        print("   Possible reasons:")
        print("   1. No subscription emails in the 50 fetched")
        print("   2. Classification threshold still too high")
        print("   3. Composio connection issue")
        print("\n   Try: python export_classifications.py")
        print("   To see confidence scores for all emails")

if __name__ == "__main__":
    asyncio.run(main())
