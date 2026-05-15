"""
Quick database initializer - creates subscriptions.db with sample data
Run this from the subscription_manager directory
"""
import asyncio
from database import init_db, AsyncSessionLocal, Subscription

async def main():
    print("🔧 Creating database...")
    await init_db()
    print("✅ Database tables created")
    
    print("\n📦 Adding sample subscriptions...")
    async with AsyncSessionLocal() as session:
        subs = [
            Subscription(service_name="Netflix", cost=15.49, category="streaming", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Spotify", cost=16.99, category="music", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="AWS", cost=142.30, category="cloud", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="GitHub Pro", cost=4.00, category="dev_tools", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Claude Pro", cost=20.00, category="ai", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Vercel Pro", cost=20.00, category="cloud", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Adobe Creative Cloud", cost=52.99, category="design", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Linear", cost=10.00, category="dev_tools", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Figma Professional", cost=15.00, category="dev_tools", billing_cycle="monthly", status="active", currency="USD", source="manual"),
            Subscription(service_name="Notion Plus", cost=10.00, category="productivity", billing_cycle="monthly", status="active", currency="USD", source="manual"),
        ]
        
        for sub in subs:
            session.add(sub)
        
        await session.commit()
        
        total = sum(s.cost for s in subs)
        print(f"✅ Added {len(subs)} subscriptions")
        print(f"💰 Total monthly cost: ${total:.2f}")
        print(f"💰 Total yearly cost: ${total * 12:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
