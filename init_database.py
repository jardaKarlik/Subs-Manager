import asyncio
import sys
sys.path.insert(0, r'C:\_dev\subscription_manager')

from database import init_db, AsyncSessionLocal, Subscription

async def create_and_populate():
    await init_db()
    print("✅ Database created")
    
    async with AsyncSessionLocal() as session:
        subs = [
            Subscription(service_name="Netflix", cost=15.49, category="streaming", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Spotify", cost=16.99, category="music", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="AWS", cost=142.30, category="cloud", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="GitHub", cost=4.00, category="dev_tools", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Claude", cost=20.00, category="ai", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Vercel", cost=20.00, category="cloud", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Adobe Creative Cloud", cost=52.99, category="design", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Linear", cost=10.00, category="dev_tools", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Figma", cost=15.00, category="dev_tools", billing_cycle="monthly", status="active", source="manual"),
            Subscription(service_name="Notion", cost=10.00, category="productivity", billing_cycle="monthly", status="active", source="manual"),
        ]
        
        for sub in subs:
            session.add(sub)
        
        await session.commit()
        print(f"✅ Added {len(subs)} subscriptions")

asyncio.run(create_and_populate())
