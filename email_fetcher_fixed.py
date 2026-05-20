"""
Fixed email fetcher with sequential batch processing and confirmation.
Prevents race conditions and ensures each batch is committed before fetching next.
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from email_parser import EmailClassifier
from database import Subscription, ProcessedEmail, SubscriptionEvent

class EmailFetcherFixed:
    """Email fetcher with proper batch synchronization."""
    
    def __init__(self):
        self.classifier = EmailClassifier()
        self._toolset = None
    
    async def _process_email_batch_safe(
        self, 
        db: AsyncSession, 
        batch: List[Dict], 
        results: Dict,
        batch_num: int
    ) -> bool:
        """
        Process batch with proper error handling and confirmation.
        Returns True if successful, False if failed.
        """
        if not batch:
            return True
        
        print(f"\n{'='*60}")
        print(f"📦 Batch #{batch_num}: Processing {len(batch)} emails")
        print(f"{'='*60}")
        
        # Deduplicate within batch
        seen = set()
        unique = []
        for email in batch:
            msg_id = f"{email['source']}:{email['message_id']}"
            if msg_id not in seen:
                seen.add(msg_id)
                email["_unique_id"] = msg_id
                unique.append(email)
        
        print(f"  After deduplication: {len(unique)} unique emails")
        
        classified_count = 0
        stored_count = 0
        skipped_count = 0
        
        try:
            for email in unique:
                # Check if already processed
                result_row = await db.execute(
                    select(ProcessedEmail).where(
                        ProcessedEmail.message_id == email["_unique_id"]
                    )
                )
                
                if result_row.scalar_one_or_none():
                    skipped_count += 1
                    results["skipped"] += 1
                    continue
                
                # Classify
                classification = self.classifier.classify(
                    email["subject"],
                    email["sender"],
                    email["body"]
                )
                classified_count += 1
                
                # Mark as processed FIRST (important for dedup)
                db.add(ProcessedEmail(
                    message_id=email["_unique_id"],
                    source=email["source"]
                ))
                
                # Store if subscription
                if classification["is_subscription"]:
                    # Check for existing subscription
                    norm_name = classification["service_name"].strip()
                    result_row2 = await db.execute(
                        select(Subscription).where(
                            Subscription.service_name.ilike(norm_name)
                        )
                    )
                    existing = result_row2.scalar_one_or_none()
                    
                    if existing:
                        # Update existing
                        if classification["cost"]:
                            existing.cost = classification["cost"]
                            existing.currency = classification["currency"]
                        existing.updated_at = datetime.utcnow()
                        subscription_id = existing.id
                    else:
                        # Create new subscription
                        start_date = self._extract_date_from_email(email)
                        
                        new_sub = Subscription(
                            service_name=classification["service_name"],
                            category=classification["category"],
                            cost=classification["cost"] or 0.0,
                            currency=classification["currency"],
                            billing_cycle=classification["billing_cycle"],
                            status="active",
                            start_date=start_date,
                            notes=f"Plan: {classification.get('plan_name', 'Standard')}",
                            source=email["source"]
                        )
                        db.add(new_sub)
                        await db.flush()  # Get ID
                        subscription_id = new_sub.id
                        stored_count += 1
                        results["new_subscriptions"] += 1
                    
                    # Create event
                    event_date = self._parse_email_date(email.get("date", ""))
                    event = SubscriptionEvent(
                        subscription_id=subscription_id,
                        service_name=classification["service_name"],
                        category=classification["category"],
                        amount=classification["cost"] or 0.0,
                        currency=classification["currency"],
                        billing_cycle=classification["billing_cycle"],
                        event_date=event_date,
                        source_type=classification.get("source_type", "email"),
                        message_id=email["_unique_id"]
                    )
                    db.add(event)
                    
                    print(f"  ✅ {classification['service_name']}: "
                          f"{classification['cost']} {classification['currency']} "
                          f"(conf={classification['confidence']:.2f})")
                
                results["processed"] += 1
            
            # CRITICAL: Commit and verify
            print(f"\n  📊 Batch stats:")
            print(f"     Classified: {classified_count}")
            print(f"     Stored: {stored_count}")
            print(f"     Skipped: {skipped_count}")
            print(f"  💾 Committing to database...")
            
            await db.commit()
            
            # VERIFY commit succeeded
            verify_count = await db.execute(
                select(ProcessedEmail).where(
                    ProcessedEmail.message_id.in_([e["_unique_id"] for e in unique])
                )
            )
            verified = len(verify_count.scalars().all())
            
            print(f"  ✅ Commit successful! Verified {verified}/{len(unique)} emails stored")
            
            return True
            
        except Exception as e:
            print(f"  ❌ BATCH FAILED: {e}")
            await db.rollback()
            results["failed"] += len(unique)
            return False
    
    async def process_emails_safe(
        self,
        db: AsyncSession,
        sources: List[str] = None,
        max_results: int = 500,
        since_days: int = 365
    ) -> Dict:
        """
        Process emails with proper batch synchronization.
        Each batch must complete before next one starts.
        """
        if sources is None:
            sources = ["gmail", "outlook"]
        
        results = {
            "processed": 0,
            "new_subscriptions": 0,
            "skipped": 0,
            "failed": 0,
            "sources": {}
        }
        
        for source in sources:
            print(f"\n{'='*60}")
            print(f"📧 Processing source: {source.upper()}")
            print(f"{'='*60}")
            
            if source == "gmail":
                await self._process_gmail_sequential(
                    db, max_results, since_days, results
                )
            elif source == "outlook":
                await self._process_outlook_sequential(
                    db, max_results, since_days, results
                )
        
        return results
    
    async def _process_gmail_sequential(
        self,
        db: AsyncSession,
        max_results: int,
        since_days: int,
        results: Dict
    ):
        """Process Gmail with sequential batches - wait for commit before fetching next."""
        from email_fetcher import EmailFetcher
        
        # Use existing fetcher for API calls
        fetcher = EmailFetcher()
        composio_client = fetcher._get_composio()
        
        if not composio_client:
            print("  ⚠️  Gmail: Composio not available")
            return
        
        query = fetcher._format_gmail_date(since_days)
        fetched_count = 0
        batch_num = 0
        page_token = None
        
        while fetched_count < max_results:
            batch_size = min(20, max_results - fetched_count)
            batch_num += 1
            
            # Fetch ONE batch
            arguments = {
                "query": f"after:{query}",
                "max_results": batch_size,
                "include_payload": True
            }
            if page_token:
                arguments["page_token"] = page_token
            
            try:
                result = composio_client.tools.execute(
                    slug="GMAIL_FETCH_EMAILS",
                    arguments=arguments,
                    user_id=os.getenv("COMPOSIO_USER_ID", "default"),
                    dangerously_skip_version_check=True
                )
                
                data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                
                batch_emails = fetcher._parse_gmail_v2_result({"data": data})
                
                if not batch_emails:
                    print(f"  ℹ️  No more emails available")
                    break
                
                # Process batch and WAIT for confirmation
                success = await self._process_email_batch_safe(
                    db, batch_emails, results, batch_num
                )
                
                if not success:
                    print(f"  ⚠️  Batch #{batch_num} failed, stopping Gmail processing")
                    break
                
                fetched_count += len(batch_emails)
                page_token = data.get("nextPageToken")
                
                if not page_token:
                    break
                
                # Wait before next batch
                print(f"  ⏳ Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"  ❌ Gmail fetch error: {e}")
                break
        
        results["sources"]["gmail"] = fetched_count
        print(f"\n  ✅ Gmail complete: {fetched_count} emails processed")
    
    def _extract_date_from_email(self, email: Dict) -> str:
        """Extract start date from email."""
        try:
            import email.utils
            email_datetime = email.utils.parsedate_to_datetime(email.get("date", ""))
            return email_datetime.strftime("%Y-%m-%d")
        except:
            return datetime.utcnow().strftime("%Y-%m-%d")
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date to datetime."""
        try:
            import email.utils
            return email.utils.parsedate_to_datetime(date_str)
        except:
            return datetime.utcnow()
