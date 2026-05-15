"""
Run initial email sync to populate database
Fetches from Gmail (Composio), Outlook (Composio), and IMAP (Zoner)
"""
import asyncio
from database import init_db
from email_fetcher import EmailFetcher
from database import AsyncSessionLocal

async def main():
    print("🚀 Starting initial email sync...")
    print("=" * 60)
    
    # Create database if it doesn't exist
    print("\n1️⃣  Initializing database...")
    await init_db()
    print("✅ Database ready")
    
    # Create fetcher
    fetcher = EmailFetcher()
    
    print("\n2️⃣  Starting email sync from 3 sources...")
    print("   - Gmail (via Composio): j.karleek@gmail.com")
    print("   - Outlook (via Composio)")
    print("   - IMAP: karlik@klikni.org")
    print()
    
    async with AsyncSessionLocal() as session:
        # Sync last year's emails, up to 1000 per source
        results = await fetcher.process_emails(
            db=session,
            sources=None,  # All sources
            max_results=1000,
            since_days=365
        )
    
    print("\n" + "=" * 60)
    print("📊 SYNC RESULTS:")
    print("=" * 60)
    print(f"✉️  Emails processed: {results['processed']}")
    print(f"✅ New subscriptions found: {results['new_subscriptions']}")
    print(f"⏭️  Skipped (duplicates): {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    
    if results['new_subscriptions'] > 0:
        print(f"\n💰 Run 'python api.py' and visit http://localhost:8000/api/stats to see totals")
    else:
        print(f"\n⚠️  No subscriptions found - check email filters or try manual entry")

if __name__ == "__main__":
    asyncio.run(main())
