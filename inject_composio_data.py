import asyncio
import json
from datetime import datetime
from email_parser import EmailClassifier
from database import AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from sqlalchemy import select, func

async def inject_data():
    classifier = EmailClassifier()
    
    with open("composio_emails.json", "r", encoding="utf-8") as f:
        emails = json.load(f)
    
    async with AsyncSessionLocal() as db:
        processed_count = 0
        new_subs_count = 0
        
        for email in emails:
            unique_id = f"{email['source']}:{email['message_id']}"
            
            # Check if already processed
            result = await db.execute(
                select(ProcessedEmail).where(ProcessedEmail.message_id == unique_id)
            )
            if result.scalar_one_or_none():
                continue
            
            try:
                classification = classifier.classify(
                    email["subject"],
                    email["sender"],
                    email["body"]
                )
                
                # Mark as processed
                processed = ProcessedEmail(
                    message_id=unique_id,
                    source=email["source"]
                )
                db.add(processed)
                
                if classification["is_subscription"]:
                    norm_name = classification["service_name"].strip()
                    res = await db.execute(
                        select(Subscription).where(
                            func.lower(Subscription.service_name) == norm_name.lower()
                        )
                    )
                    existing = res.scalar_one_or_none()
                    
                    if existing:
                        existing.cost = classification["cost"] or existing.cost
                        existing.currency = classification["currency"] or existing.currency
                        existing.billing_cycle = classification["billing_cycle"]
                        existing.updated_at = datetime.utcnow()
                        subscription_id = existing.id
                        target_sub = existing
                    else:
                        new_sub = Subscription(
                            service_name=classification["service_name"],
                            category=classification["category"],
                            cost=classification["cost"],
                            currency=classification["currency"],
                            billing_cycle=classification["billing_cycle"],
                            status="active",
                            source=email["source"],
                        )
                        db.add(new_sub)
                        await db.flush()
                        subscription_id = new_sub.id
                        new_subs_count += 1
                        target_sub = new_sub
                    
                    # Event
                    event = SubscriptionEvent(
                        subscription_id=subscription_id,
                        service_name=classification["service_name"],
                        category=classification["category"],
                        amount=classification["cost"],
                        currency=classification["currency"],
                        billing_cycle=classification["billing_cycle"],
                        event_date=datetime.utcnow(),
                        source_type=classification["source_type"],
                        message_id=unique_id
                    )
                    db.add(event)
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing {unique_id}: {e}")
        
        await db.commit()
        print(f"Successfully processed {processed_count} emails.")
        print(f"Found {new_subs_count} new subscriptions.")

if __name__ == "__main__":
    asyncio.run(inject_data())