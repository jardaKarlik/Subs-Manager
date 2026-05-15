"""Check database status and populate if empty"""
import asyncio
import sqlite3
from database import init_db, AsyncSessionLocal, Subscription
from sqlalchemy import select, func

async def check_and_populate():
    # Initialize database (creates tables if they don't exist)
    print("🔧 Initializing database...")
    await init_db()
    print("✅ Database tables created/verified")
    
    async with AsyncSessionLocal() as session:
        # Check current count
        result = await session.execute(select(func.count(Subscription.id)))
        count = result.scalar()
        print(f"\n📊 Current subscriptions in database: {count}")
        
        if count == 0:
            print("\n❌ Database is empty! Adding sample data...")
            
            sample_subs = [
                Subscription(service_name="Last.fm", cost=108.91, currency="CZK", category="music", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="Anthropic", cost=12.02, currency="EUR", category="ai", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="Google Cloud", cost=280.0, currency="CZK", category="cloud", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="Cline", cost=8.75, currency="USD", category="ai", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="Netflix", cost=136.0, currency="CZK", category="streaming", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="Spotify", cost=150.0, currency="CZK", category="music", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="GitHub Pro", cost=4.0, currency="USD", category="dev_tools", billing_cycle="monthly", status="active", source="manual"),
                Subscription(service_name="Beatport", cost=200.0, currency="CZK", category="music", billing_cycle="monthly", status="active", source="manual"),
            ]
            
            for sub in sample_subs:
                session.add(sub)
            
            await session.commit()
            print(f"✅ Added {len(sample_subs)} sample subscriptions")
        else:
            print("\n📋 Listing current subscriptions:")
            result = await session.execute(select(Subscription))
            for sub in result.scalars():
                print(f"  - {sub.service_name}: {sub.cost} {sub.currency} ({sub.category})")

if __name__ == "__main__":
    asyncio.run(check_and_populate())
