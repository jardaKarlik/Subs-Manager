import asyncio
import os
import json
from pprint import pprint

from dotenv import load_dotenv

# Load local .env file
load_dotenv()

from email_fetcher import EmailFetcher
from database import AsyncSessionLocal, ProcessedEmail, Subscription, SubscriptionEvent
from sqlalchemy import select

async def main():
    print("=" * 60)
    print("TEST: Fetching 10 recent emails from Gmail & Classifying")
    print("=" * 60)

    fetcher = EmailFetcher()

    print("\n1. Injecting dummy subscription emails...")
    emails = [
        {
            "message_id": "dummy-1",
            "source": "gmail",
            "subject": "Your Netflix Premium Subscription Receipt",
            "sender": "receipts@netflix.com",
            "date": "2026-05-15T10:00:00Z",
            "body": "Thank you for subscribing. You paid $22.99 USD for your monthly Netflix Premium plan.",
            "raw": {}
        },
        {
            "message_id": "dummy-2",
            "source": "gmail",
            "subject": "Spotify Family Plan - Payment Confirmation",
            "sender": "no-reply@spotify.com",
            "date": "2026-05-14T08:30:00Z",
            "body": "Your payment was successful. We charged 16.99 EUR to your card for your Spotify Premium Family subscription.",
            "raw": {}
        },
        {
            "message_id": "dummy-3",
            "source": "gmail",
            "subject": "Welcome to ChatGPT Plus",
            "sender": "billing@openai.com",
            "date": "2026-05-10T14:15:00Z",
            "body": "Welcome to ChatGPT Plus! Your subscription is confirmed. Amount paid: $20.00. Billed monthly.",
            "raw": {}
        }
    ]
    print(f"✅ Injected {len(emails)} dummy emails.")

    print("\n2. Connecting to DB and deduplicating...")
    async with AsyncSessionLocal() as db:
        unique_emails = []
        for em in emails:
            msg_id = f"gmail:{em['message_id']}"
            em['_unique_id'] = msg_id
            
            # Check if processed
            result = await db.execute(
                select(ProcessedEmail).where(ProcessedEmail.message_id == msg_id)
            )
            if result.scalar_one_or_none():
                print(f"   [SKIP] Already processed: {em['subject'][:30]}...")
            else:
                unique_emails.append(em)

        print(f"✅ Found {len(unique_emails)} new emails to process.")

        if not unique_emails:
            print("All fetched emails are already processed. Exiting.")
            return

        print("\n3. Classifying and creating DB records...")
        for em in unique_emails:
            print(f"\n--- Email: {em['subject'][:50]}... ---")
            
            # 1. Classify
            classification = fetcher.classifier.classify(
                em['subject'], em['sender'], em['body']
            )
            
            print(f"   Classification: {'✅ SUBSCRIPTION' if classification['is_subscription'] else '❌ IGNORE'} (Score: {classification['confidence']})")
            
            if classification['is_subscription']:
                print(f"   Detected Service: {classification['service_name']}")
                print(f"   Category: {classification['category']}")
                print(f"   Cost: {classification['cost']} {classification['currency']} ({classification['billing_cycle']})")
                print(f"   Plan: {classification['plan_name']}")
                
                # 2. Check for existing subscription
                norm_name = classification["service_name"].strip()
                result = await db.execute(
                    select(Subscription).where(func.lower(Subscription.service_name) == norm_name.lower())
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"   DB Action: UPDATE existing Subscription (ID: {existing.id})")
                else:
                    print("   DB Action: INSERT new Subscription")

                print("   DB Action: INSERT into SubscriptionEvent")
            
            print("   DB Action: INSERT into ProcessedEmail (to prevent future processing)")

        print("\n" + "=" * 60)
        print("Test complete. No data was actually committed to the DB in this run.")

if __name__ == "__main__":
    from sqlalchemy import func
    asyncio.run(main())