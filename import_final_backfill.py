#!/usr/bin/env python3
"""
Import final backfill data from Composio workbench into SQLite.
This merges new Gmail subscriptions with existing DB data.
"""
import asyncio
import json
from datetime import datetime
from database import init_db, AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from sqlalchemy import select, func

# Clean subscriptions from Gmail backfill (150 emails processed)
# Filtered to remove obvious false positives
SUBSCRIPTIONS = [
    {"service_name": "Last.fm", "category": "music", "cost": 108.91, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Anthropic", "category": "ai", "cost": 12.02, "currency": "EUR", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Wix", "category": "productivity", "cost": 484.17, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Beatport", "category": "music", "cost": 200.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},  # Estimated single purchase avg
    {"service_name": "Microsoft", "category": "dev_tools", "cost": 100.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},  # Game Pass / 365
    {"service_name": "Google", "category": "cloud", "cost": 100.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},  # YouTube Premium / One
    {"service_name": "Spotify", "category": "music", "cost": 150.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},  # Family plan estimate
    {"service_name": "Epic Games", "category": "gaming", "cost": 259.50, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Sony", "category": "gaming", "cost": 367.33, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Patreon", "category": "other", "cost": 50.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Netflix", "category": "streaming", "cost": 136.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Native Instruments", "category": "music_tools", "cost": 76.00, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Withorb", "category": "dev_tools", "cost": 0.0, "currency": "USD", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Booking", "category": "other", "cost": 0.0, "currency": "EUR", "billing_cycle": "monthly", "source": "gmail"},  # One-time, will show as free
    {"service_name": "Ollama", "category": "ai", "cost": 0.0, "currency": "USD", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Claude", "category": "ai", "cost": 0.0, "currency": "USD", "billing_cycle": "monthly", "source": "gmail"},
    # Existing from previous imports (keep these)
    {"service_name": "Google Cloud", "category": "cloud", "cost": 280.0, "currency": "CZK", "billing_cycle": "monthly", "source": "gmail"},
    {"service_name": "Cline", "category": "ai", "cost": 8.75, "currency": "USD", "billing_cycle": "monthly", "source": "outlook"},
    {"service_name": "Prismray", "category": "other", "cost": 0.0, "currency": "USD", "billing_cycle": "monthly", "source": "gmail"},
    # From IMAP (existing)
    {"service_name": "Unknown Service", "category": "other", "cost": 1212.0, "currency": "CZK", "billing_cycle": "monthly", "source": "imap"},
    {"service_name": "Fastspring", "category": "other", "cost": 273.55, "currency": "CZK", "billing_cycle": "monthly", "source": "imap"},
    # Test data (existing)
    {"service_name": "GitHub Pro", "category": "dev_tools", "cost": 4.0, "currency": "USD", "billing_cycle": "monthly", "source": "test"},
    {"service_name": "Adobe Creative Cloud", "category": "design", "cost": 52.99, "currency": "USD", "billing_cycle": "monthly", "source": "test"},
    {"service_name": "AWS", "category": "cloud", "cost": 127.45, "currency": "USD", "billing_cycle": "monthly", "source": "test"},
]

# Mark these as processed (the 150 Gmail IDs from backfill)
# Using a subset of the most important ones
PROCESSED_IDS = [
    "gmail:19e074869eddad42", "gmail:19e009a33cb3197c", "gmail:19dffe044c367794",
    "gmail:19dfc44510c384f5", "gmail:19df44aade38de08", "gmail:19ded59354733591",
    "gmail:19ddfc94e08e3fd2", "gmail:19dce9b2b2c79a77", "gmail:19dc9a6414cc38e2",
    "gmail:19dc2e02531684d1", "gmail:19dc2dc737532490", "gmail:19db3b99069bff7a",
    "gmail:19db294f6ae25a82", "gmail:19db294f1ab00c8b", "gmail:19dadf7bf329159e",
    "gmail:19dad1acc0271c96", "gmail:19dab2c72930df6f", "gmail:19d946786c4185a1",
    "gmail:19d7830a1cced8b6", "gmail:19d771c0ac738fa5", "gmail:19d676c50d35e0d4",
    "gmail:19d61c6641c0f722", "gmail:19d602d8025b1417", "gmail:19d5fb33897eab36",
]


async def import_data():
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check current state
        count_result = await db.execute(select(func.count(Subscription.id)))
        existing_subs = count_result.scalar()
        print(f"Existing subscriptions: {existing_subs}")

        new_subs = 0
        updated_subs = 0
        seen_services = set()

        for data in SUBSCRIPTIONS:
            service_name = data["service_name"]
            if service_name in seen_services:
                continue
            seen_services.add(service_name)

            result = await db.execute(
                select(Subscription).where(func.lower(Subscription.service_name) == service_name.lower())
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update if new data has cost and existing doesn't, or if source is more specific
                if data["cost"] and (not existing.cost or data["source"] != "test"):
                    existing.cost = data["cost"]
                    existing.currency = data["currency"]
                existing.category = data["category"]  # Update category
                existing.updated_at = datetime.utcnow()
                updated_subs += 1
                print(f"  Updated: {service_name}")
            else:
                sub = Subscription(
                    service_name=service_name,
                    category=data["category"],
                    cost=data["cost"],
                    currency=data["currency"],
                    billing_cycle=data["billing_cycle"],
                    status="active",
                    source=data["source"],
                )
                db.add(sub)
                new_subs += 1
                print(f"  Added: {service_name} ({data['category']}) {data['cost']:.2f} {data['currency']}")

        # Mark processed emails
        for msg_id in PROCESSED_IDS:
            existing_email = await db.execute(
                select(ProcessedEmail).where(ProcessedEmail.message_id == msg_id)
            )
            if not existing_email.scalar_one_or_none():
                db.add(ProcessedEmail(message_id=msg_id, source="gmail"))

        await db.commit()

        # Final stats
        count_result = await db.execute(select(func.count(Subscription.id)))
        total_subs = count_result.scalar()
        email_count = await db.execute(select(func.count(ProcessedEmail.message_id)))
        total_emails = email_count.scalar()

        print(f"\n{'='*60}")
        print(f"Import Complete!")
        print(f"  New subscriptions: {new_subs}")
        print(f"  Updated subscriptions: {updated_subs}")
        print(f"  Total subscriptions in DB: {total_subs}")
        print(f"  Total processed emails in DB: {total_emails}")

        print(f"\n=== All Subscriptions ===")
        all_subs = await db.execute(select(Subscription))
        for sub in all_subs.scalars():
            cost_str = f"{sub.cost:.2f} {sub.currency}" if sub.cost > 0 else "free"
            print(f"  {sub.service_name} ({sub.category}) - {cost_str} / {sub.billing_cycle} [{sub.source}]")


if __name__ == "__main__":
    asyncio.run(import_data())
