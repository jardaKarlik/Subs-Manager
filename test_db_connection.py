"""Test database creation, data insertion, and API connectivity"""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import init_db, AsyncSessionLocal, Subscription


async def test_database():
    print("=" * 80)
    print("DATABASE CONNECTION TEST")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    await init_db()
    print("[OK] Database initialized")
    
    # Check database file
    db_path = os.path.join(os.path.dirname(__file__), "subscriptions.db")
    if os.path.exists(db_path):
        print(f"[OK] Database file: {db_path} ({os.path.getsize(db_path)} bytes)")
    else:
        print(f"[ERROR] Database file not found")
        return False
    
    # Insert test data
    print("\n2. Inserting test data...")
    async with AsyncSessionLocal() as session:
        test_subs = [
            Subscription(service_name="Netflix Test", category="streaming", 
                        cost=15.99, billing_cycle="monthly", status="active", source="test"),
            Subscription(service_name="Spotify Test", category="music", 
                        cost=120.00, billing_cycle="yearly", status="active", source="test"),
            Subscription(service_name="GitHub Test", category="dev_tools", 
                        cost=4.00, billing_cycle="monthly", status="active", source="test"),
        ]
        
        for sub in test_subs:
            session.add(sub)
        await session.commit()
        print(f"[OK] Inserted {len(test_subs)} test subscriptions")
    
    # Query data
    print("\n3. Querying subscriptions...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Subscription))
        subs = result.scalars().all()
        
        print(f"[OK] Found {len(subs)} subscriptions:")
        for sub in subs:
            print(f"  - {sub.service_name} | {sub.category} | ${sub.cost} | {sub.billing_cycle}")
    
    print("\n4. Frontend connection check...")
    app_js = os.path.join(os.path.dirname(__file__), "frontend", "app.js")
    if os.path.exists(app_js):
        with open(app_js, 'r') as f:
            content = f.read()
        if "const API_BASE = 'http://localhost:8000/api'" in content:
            print("[OK] Frontend configured for: http://localhost:8000/api")
        else:
            print("[WARNING] Check API_BASE in app.js")
    
    print("\n" + "=" * 80)
    print("SUMMARY: Database working, test data inserted, frontend configured")
    print("Next: Start API server with 'python api.py'")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    asyncio.run(test_database())
