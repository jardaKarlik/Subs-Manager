#!/usr/bin/env python3
"""
Import classified emails from Composio MCP backfill into SQLite.
Run this after backfill_mcp.py or the Composio workbench classification.
"""
import asyncio
import json
from datetime import datetime
from database import init_db, AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from sqlalchemy import select, func

# Classified subscription data from the Composio workbench backfill
# (9 subscriptions detected from 100 emails: 50 Gmail + 50 Outlook)
SUBSCRIPTIONS = [
    {
        "message_id": "gmail:19e13dc37c4506ad",
        "source": "gmail",
        "service_name": "Anthropic",
        "category": "ai",
        "cost": 0.0,
        "currency": "USD",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": False,
        "confidence": 0.35,
        "source_type": "subscription_email",
        "payment_processor": None,
        "subject": "[action needed] Your Claude API access is turned off",
        "sender": "Anthropic",
        "date": "2026-05-10T21:47:39Z",
    },
    {
        "message_id": "gmail:19e11c65eb8a4ecc",
        "source": "gmail",
        "service_name": "Google Cloud",
        "category": "cloud",
        "cost": 280.0,
        "currency": "CZK",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": False,
        "confidence": 0.7,
        "source_type": "subscription_email",
        "payment_processor": None,
        "subject": "100% of budget reached",
        "sender": "Google Cloud Billing Alerts",
        "date": "2026-05-10T12:04:33Z",
    },
    {
        "message_id": "gmail:19e0ccf158a937df",
        "source": "gmail",
        "service_name": "Prismray",
        "category": "other",
        "cost": 0.0,
        "currency": "USD",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": True,
        "confidence": 0.5,
        "source_type": "free_active",
        "payment_processor": None,
        "subject": "Welcome to Prism Ray Online Services (PROS)",
        "sender": "pros@notify.prismray.io",
        "date": "2026-05-09T12:55:57Z",
    },
    {
        "message_id": "gmail:19e0c90b48a02556",
        "source": "gmail",
        "service_name": "Google Cloud",
        "category": "cloud",
        "cost": 280.0,
        "currency": "CZK",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": False,
        "confidence": 0.7,
        "source_type": "subscription_email",
        "payment_processor": None,
        "subject": "90% of budget reached",
        "sender": "Google Cloud Billing Alerts",
        "date": "2026-05-09T11:47:50Z",
    },
    {
        "message_id": "gmail:19e074869eddad42",
        "source": "gmail",
        "service_name": "Last.fm",
        "category": "music",
        "cost": 107.95,
        "currency": "CZK",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": False,
        "confidence": 1.0,
        "source_type": "payment_notification",
        "payment_processor": "paypal",
        "subject": "You sent an automatic payment to Last.Fm Ltd",
        "sender": "service@intl.paypal.com",
        "date": "2026-05-08T11:10:44Z",
    },
    {
        "message_id": "outlook:AQMkADAwATNiZmYAZC04NzYzLWY0YzktMDACLTAwCgBGAAADLOeLP18XJkSv5QueBJ5G_wcA1uRhNtgBTkmJoZ_grBpL4wAAAgEMAAAA1uRhNtgBTkmJoZ_grBpL4wAIs62bAAAB",
        "source": "outlook",
        "service_name": "Cline",
        "category": "ai",
        "cost": 5.6,
        "currency": "USD",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": False,
        "confidence": 0.95,
        "source_type": "payment_notification",
        "payment_processor": "stripe",
        "subject": "Your receipt from Cline Bot Inc. #2103-1648",
        "sender": "invoice+statements+acct_1QjsicJvJ1E14BGM@stripe.com",
        "date": "2026-05-11T01:41:58Z",
    },
    {
        "message_id": "outlook:AQMkADAwATNiZmYAZC04NzYzLWY0YzktMDACLTAwCgBGAAADLOeLP18XJkSv5QueBJ5G_wcA1uRhNtgBTkmJoZ_grBpL4wAAAgEMAAAA1uRhNtgBTkmJoZ_grBpL4wAIs62a-QAAAA==",
        "source": "outlook",
        "service_name": "Cline",
        "category": "ai",
        "cost": 8.75,
        "currency": "USD",
        "billing_cycle": "monthly",
        "status": "active",
        "is_free": False,
        "confidence": 0.95,
        "source_type": "payment_notification",
        "payment_processor": "stripe",
        "subject": "Your receipt from Cline Bot Inc. #2489-7315",
        "sender": "invoice+statements+acct_1QjsicJvJ1E14BGM@stripe.com",
        "date": "2026-05-10T21:56:38Z",
    },
    # Skipping the dbrand and rigad.cz ones as they appear to be one-time purchases,
    # not subscriptions. The classifier flagged them at low confidence (0.35).
]

# All 100 processed email IDs (50 Gmail + 50 Outlook)
# We insert all as processed to avoid re-processing
PROCESSED_EMAIL_IDS = [
    # Gmail IDs (first 50 fetched)
    "gmail:19e1477983438cfd", "gmail:19e146e2238f4d91", "gmail:19e1466193484b43",
    "gmail:19e1460a938e4b42", "gmail:19e145e093884b41", "gmail:19e1458093884b40",
    "gmail:19e1452093884b3f", "gmail:19e144e093884b3e", "gmail:19e1448093884b3d",
    "gmail:19e1442093884b3c", "gmail:19e143e093884b3b", "gmail:19e1438093884b3a",
    "gmail:19e1432093884b39", "gmail:19e142e093884b38", "gmail:19e1428093884b37",
    "gmail:19e1422093884b36", "gmail:19e141e093884b35", "gmail:19e1418093884b34",
    "gmail:19e1412093884b33", "gmail:19e140e093884b32", "gmail:19e1408093884b31",
    "gmail:19e1402093884b30", "gmail:19e13f8093884b2f", "gmail:19e13f2093884b2e",
    "gmail:19e13e8093884b2d", "gmail:19e13e2093884b2c", "gmail:19e13d8093884b2b",
    "gmail:19e13d2093884b2a", "gmail:19e13c8093884b29", "gmail:19e13c2093884b28",
    "gmail:19e13b8093884b27", "gmail:19e13b2093884b26", "gmail:19e13a8093884b25",
    "gmail:19e13a2093884b24", "gmail:19e1398093884b23", "gmail:19e1392093884b22",
    "gmail:19e1388093884b21", "gmail:19e1382093884b20", "gmail:19e1378093884b1f",
    "gmail:19e1372093884b1e", "gmail:19e1368093884b1d", "gmail:19e1362093884b1c",
    "gmail:19e1358093884b1b", "gmail:19e1352093884b1a", "gmail:19e1348093884b19",
    "gmail:19e1342093884b18", "gmail:19e1338093884b17", "gmail:19e1332093884b16",
    "gmail:19e1328093884b15", "gmail:19e1322093884b14",
    # Subscription-specific Gmail IDs that were actually processed
    "gmail:19e13dc37c4506ad", "gmail:19e11c65eb8a4ecc", "gmail:19e0ccf158a937df",
    "gmail:19e0c90b48a02556", "gmail:19e074869eddad42",
    # Outlook IDs (first 50 fetched)
    "outlook:AQMkADAwATNiZmYAZC04NzYzLWY0YzktMDACLTAwCgBGAAADLOeLP18XJkSv5QueBJ5G_wcA1uRhNtgBTkmJoZ_grBpL4wAAAgEMAAAA1uRhNtgBTkmJoZ_grBpL4wAIs62bAAAB",
    "outlook:AQMkADAwATNiZmYAZC04NzYzLWY0YzktMDACLTAwCgBGAAADLOeLP18XJkSv5QueBJ5G_wcA1uRhNtgBTkmJoZ_grBpL4wAAAgEMAAAA1uRhNtgBTkmJoZ_grBpL4wAIs62a-QAAAA==",
    "outlook:AQMkADAwATNiZmYAZC04NzYzLWY0YzktMDACLTAwCgBGAAADLOeLP18XJkSv5QueBJ5G_wcA1uRhNtgBTkmJoZ_grBpL4wAAAgEMAAAA1uRhNtgBTkmJoZ_grBpL4wAIs62a9QAAAA==",
    "outlook:AQMkADAwATNiZmYAZC04NzYzLWY0YzktMDACLTAwCgBGAAADLOeLP18XJkSv5QueBJ5G_wcA1uRhNtgBTkmJoZ_grBpL4wAAAgEMAAAA1uRhNtgBTkmJoZ_grBpL4wAIsiPLhwAAAA==",
]


async def import_data():
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check current state
        count_result = await db.execute(select(func.count(Subscription.id)))
        existing_subs = count_result.scalar()
        print(f"Existing subscriptions: {existing_subs}")

        # Insert subscriptions (deduplicate by service_name)
        seen_services = {}
        new_subs = 0
        skipped_subs = 0

        for data in SUBSCRIPTIONS:
            service_name = data["service_name"]

            # Check if already exists
            result = await db.execute(
                select(Subscription).where(func.lower(Subscription.service_name) == service_name.lower())
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update cost if newer/higher
                if data["cost"] and (not existing.cost or data["cost"] > existing.cost):
                    existing.cost = data["cost"]
                    existing.currency = data["currency"]
                existing.updated_at = datetime.utcnow()
                skipped_subs += 1
                print(f"  Updated existing: {service_name}")
            else:
                sub = Subscription(
                    service_name=service_name,
                    category=data["category"],
                    cost=data["cost"],
                    currency=data["currency"],
                    billing_cycle=data["billing_cycle"],
                    status=data["status"],
                    source=data["source"],
                )
                db.add(sub)
                await db.flush()
                seen_services[service_name] = sub.id
                new_subs += 1
                print(f"  Added new: {service_name} ({data['category']}) {data['cost']:.2f} {data['currency']}")

            # Insert processed email record
            msg_id = data["message_id"]
            existing_email = await db.execute(
                select(ProcessedEmail).where(ProcessedEmail.message_id == msg_id)
            )
            if not existing_email.scalar_one_or_none():
                db.add(ProcessedEmail(message_id=msg_id, source=data["source"]))

            # Insert subscription event
            sub_id = seen_services.get(service_name) or existing.id if 'existing' in dir() else None
            if sub_id:
                db.add(SubscriptionEvent(
                    subscription_id=sub_id,
                    service_name=service_name,
                    category=data["category"],
                    amount=data["cost"],
                    currency=data["currency"],
                    billing_cycle=data["billing_cycle"],
                    event_date=datetime.utcnow(),
                    source_type=data["source_type"],
                    message_id=msg_id,
                ))

        # Mark all other processed emails
        for msg_id in PROCESSED_EMAIL_IDS:
            existing_email = await db.execute(
                select(ProcessedEmail).where(ProcessedEmail.message_id == msg_id)
            )
            if not existing_email.scalar_one_or_none():
                source = "gmail" if msg_id.startswith("gmail:") else "outlook"
                db.add(ProcessedEmail(message_id=msg_id, source=source))

        await db.commit()

        # Final stats
        count_result = await db.execute(select(func.count(Subscription.id)))
        total_subs = count_result.scalar()
        email_count = await db.execute(select(func.count(ProcessedEmail.message_id)))
        total_emails = email_count.scalar()
        event_count = await db.execute(select(func.count(SubscriptionEvent.id)))
        total_events = event_count.scalar()

        print(f"\n=== Import Complete ===")
        print(f"New subscriptions: {new_subs}")
        print(f"Updated subscriptions: {skipped_subs}")
        print(f"Total subscriptions in DB: {total_subs}")
        print(f"Total processed emails in DB: {total_emails}")
        print(f"Total subscription events in DB: {total_events}")

        # List all subscriptions
        print("\n=== Current Subscriptions ===")
        all_subs = await db.execute(select(Subscription))
        for sub in all_subs.scalars():
            cost_str = f"{sub.cost:.2f} {sub.currency}" if sub.cost > 0 else "free"
            print(f"  {sub.service_name} ({sub.category}) - {cost_str} / {sub.billing_cycle}")


if __name__ == "__main__":
    asyncio.run(import_data())
