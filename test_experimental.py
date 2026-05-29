"""
EXPERIMENTAL TEST - Maximum DB inserts for testing
Uses relaxed parser with lower threshold
"""

import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func

# Force SQLite for experimental branch
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///experimental_subscriptions.db"

from database import init_db, AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from email_fetcher_fixed import EmailFetcherFixed

# Import relaxed classifier
import sys
sys.path.insert(0, os.path.dirname(__file__))
from email_parser_relaxed import EmailClassifierRelaxed

# Monkey-patch the fixed fetcher to use relaxed classifier
original_init = EmailFetcherFixed.__init__
def patched_init(self):
    original_init(self)
    self.classifier = EmailClassifierRelaxed()
EmailFetcherFixed.__init__ = patched_init

async def main():
    print("🧪 EXPERIMENTAL BRANCH TEST")
    print("=" * 60)
    print("🎯 Goal: Maximum DB inserts for testing")
    print("📂 Database: experimental_subscriptions.db")
    print("📂 Results: experimental_results/")
    print("=" * 60)
    print("\n⚙️  Configuration:")
    print("   - Confidence threshold: 0.25 (was 0.35)")
    print("   - Body analysis: First 5 sentences (was 2)")
    print("   - Spam filter: Less aggressive")
    print("   - Sequential batches: 2-second delay")
    print()
    
    # Create output directory
    output_dir = Path("experimental_results")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize fresh database
    await init_db()
    print("✅ Database initialized\n")
    
    # Create fetcher with relaxed classifier
    fetcher = EmailFetcherFixed()
    
    print("📧 Starting email fetch...")
    print("   Source: Gmail")
    print("   Max emails: 100")
    print("   Time range: Last 30 days")
    print()
    
    # Process emails
    async with AsyncSessionLocal() as session:
        results = await fetcher.process_emails_safe(
            db=session,
            sources=["gmail"],
            max_results=100,  # More emails for testing
            since_days=30
        )
    
    print("\n" + "=" * 60)
    print("📊 EXPERIMENTAL RESULTS")
    print("=" * 60)
    print(f"✉️  Emails processed: {results['processed']}")
    print(f"✅ New subscriptions: {results['new_subscriptions']}")
    print(f"⏭️  Skipped (duplicates): {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    
    # Verify database
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
        print(f"   Subscriptions: {total_subs}")
        print(f"   Processed emails: {total_emails}")
        print(f"   Events: {total_events}")
        
        # Data integrity check
        if total_emails == results['processed']:
            print(f"\n✅ INTEGRITY CHECK PASSED")
            print(f"   All {total_emails} emails stored in database")
        else:
            print(f"\n⚠️  INTEGRITY CHECK FAILED")
            print(f"   Expected: {results['processed']}")
            print(f"   Found: {total_emails}")
        
        # Export everything
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export subscriptions
        if total_subs > 0:
            print(f"\n📋 DETECTED SUBSCRIPTIONS:")
            subs_query = select(Subscription).order_by(Subscription.cost.desc())
            subs = await session.execute(subs_query)
            
            subs_data = []
            for sub in subs.scalars():
                print(f"   - {sub.service_name}: {sub.cost} {sub.currency}/{sub.billing_cycle} "
                      f"({sub.source})")
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
            
            # Save subscriptions
            json_file = output_dir / f"subscriptions_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump({
                    "summary": {
                        "total_subscriptions": total_subs,
                        "total_emails_processed": total_emails,
                        "total_events": total_events,
                        "detection_rate": f"{(total_subs/total_emails*100):.1f}%",
                        "test_date": timestamp,
                        "threshold": 0.25,
                        "body_sentences": 5
                    },
                    "subscriptions": subs_data
                }, f, indent=2)
            
            print(f"\n✅ Exported to: {json_file}")
        
        # Export all processed emails (sample)
        emails_query = select(ProcessedEmail).limit(20)
        emails = await session.execute(emails_query)
        
        emails_data = []
        for email in emails.scalars():
            emails_data.append({
                "message_id": email.message_id,
                "source": email.source,
                "processed_date": email.processed_date.isoformat()
            })
        
        if emails_data:
            emails_file = output_dir / f"processed_emails_{timestamp}.json"
            with open(emails_file, 'w') as f:
                json.dump({
                    "sample_count": len(emails_data),
                    "total_count": total_emails,
                    "emails": emails_data
                }, f, indent=2)
    
    # Detection rate analysis
    detection_rate = (total_subs / total_emails * 100) if total_emails > 0 else 0
    
    print("\n" + "=" * 60)
    print("📈 DETECTION ANALYSIS")
    print("=" * 60)
    print(f"Detection rate: {detection_rate:.1f}%")
    
    if detection_rate >= 10:
        print("✅ EXCELLENT: >10% detection rate")
    elif detection_rate >= 5:
        print("✅ GOOD: 5-10% detection rate")
    elif detection_rate >= 2:
        print("⚠️  LOW: 2-5% detection rate")
    else:
        print("❌ VERY LOW: <2% detection rate")
    
    print("\n" + "=" * 60)
    print("📂 OUTPUT FILES")
    print("=" * 60)
    print(f"📁 Database: experimental_subscriptions.db")
    print(f"📁 Results: experimental_results/")
    print(f"   - subscriptions_{timestamp}.json")
    print(f"   - processed_emails_{timestamp}.json")
    
    print("\n💡 NEXT STEPS:")
    if total_subs > 5:
        print("✅ Success! Relaxed parser is working")
        print("\n   Compare with previous run:")
        print("   1. Check if more subscriptions detected")
        print("   2. Review false positives in JSON")
        print("   3. Tune threshold between 0.25-0.35 if needed")
        print("\n   If satisfied with results:")
        print("   1. Merge changes to main email_parser.py")
        print("   2. Update email_fetcher.py with sequential logic")
        print("   3. Test on Railway with small batch (200 emails)")
        print("   4. Deploy to production")
    else:
        print("⚠️  Still low detection")
        print("\n   Debug steps:")
        print("   1. Run: python test_enhanced_parser.py")
        print("   2. Check CSV for confidence scores")
        print("   3. Lower threshold to 0.20 if needed")
        print("   4. Check if emails actually contain subscriptions")

if __name__ == "__main__":
    asyncio.run(main())
