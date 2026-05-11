import asyncio
import os
from datetime import datetime
from email_fetcher import EmailFetcher
from database import init_db, AsyncSessionLocal

async def run_backfill():
    print("Initializing database...")
    await init_db()
    
    fetcher = EmailFetcher()
    
    print("\nStarting full 1-year backfill (Direct Script)...")
    print("This will fetch up to 2000 emails per source from the last 365 days.")
    
    async with AsyncSessionLocal() as db:
        try:
            # Process all sources: gmail, outlook, imap
            results = await fetcher.process_emails(
                db=db,
                sources=["gmail", "outlook", "imap"],
                max_results=2000,
                since_days=365
            )
            
            print(f"\nBackfill completed!")
            print(f"Processed: {results['processed']}")
            print(f"New Subscriptions: {results['new_subscriptions']}")
            print(f"Skipped (Duplicates): {results['skipped']}")
            print(f"Errors: {results['errors']}")
            print("\nBreakdown by source:")
            for source, count in results['sources'].items():
                print(f" - {source}: {count} emails found")
                
        except Exception as e:
            print(f"\nBackfill failed with error: {e}")

if __name__ == "__main__":
    # Load environment variables if needed (should be handled by database/fetcher imports)
    asyncio.run(run_backfill())
