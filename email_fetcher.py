"""
Email Fetcher for Subscription Manager
Fetches emails from Gmail (via Composio), Outlook (via Composio), and IMAP.
Integrates with the EmailClassifier for subscription detection.

Uses Composio SDK v2 (ComposioToolSet) for OAuth email fetching.
"""

import os
import re
import ssl
import email.utils
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy import select, func, insert
from sqlalchemy.ext.asyncio import AsyncSession

from email.parser import Parser
from email.header import decode_header

from email_parser import EmailClassifier, ACCOUNT_CREATION_KEYWORDS
from database import (
    Subscription, ProcessedEmail, SubscriptionEvent,
    AsyncSessionLocal
)


# ── Optional SSL hardening ────────────────────────────────────────────────
# Set IMAP_VERIFY_SSL=false in .env to disable cert verification for IMAP.
# Composio SDK calls respect standard SSL context and do NOT need monkey-patching.

IMAP_VERIFY_SSL = os.getenv("IMAP_VERIFY_SSL", "true").lower() not in ("false", "0", "no")


class EmailFetcher:
    """Fetch and classify emails from multiple sources."""

    def __init__(self):
        self.classifier = EmailClassifier()
        self._toolset = None  # lazy-init ComposioToolSet

    # ── Composio SDK setup (v2 session-based API) ─────────────────

    def _get_composio(self):
        """
        Lazy-initialise and return a Composio v2 instance.

        Uses composio.Composio (v2 SDK, >= 0.13.0 / >= 1.0.0).
        Falls back to the old v1 SDK if v2 is not available.
        """
        if self._toolset is not None:
            return self._toolset

        api_key = os.getenv("COMPOSIO_API_KEY")
        if not api_key:
            print("Composio: Missing COMPOSIO_API_KEY")
            return None

        try:
            import composio
            self._toolset = composio.Composio(api_key=api_key)
            print(f"Composio v2 client initialised (SDK {getattr(composio, '__version__', '?')})")
            return self._toolset
        except ImportError:
            print("Composio v2 SDK not available, trying v1 fallback")
            return None
        except Exception as e:
            print(f"Composio v2 init failed: {e}")
            return None

    # ── V1 fallback (compat with old SDK 0.7.x) ───────────────────

    def _get_v1_client(self):
        """Fallback: initialise old Composio client (v0.7.x / v1 API)."""
        api_key = os.getenv("COMPOSIO_API_KEY")
        if not api_key:
            return None
        try:
            from composio.client import Composio as ClientComposio
            return ClientComposio(api_key=api_key)
        except ImportError:
            pass
        try:
            from composio import Composio
            return Composio(api_key=api_key)
        except Exception:
            return None

    # ── Gmail via Composio OAuth ──────────────────────────────────

    async def fetch_gmail(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails from Gmail using Composio with OAuth account."""
        emails = []
        gmail_account = os.getenv("GMAIL_ACCOUNT_ID")
        if not gmail_account:
            print("Gmail: Missing GMAIL_ACCOUNT_ID in .env")
            return []

        query = f"after:{self._format_gmail_date(since_days)}"

        # ── Try v2 SDK (composio.Composio.tools.execute) ────────────
        composio_client = self._get_composio()
        if composio_client:
            try:
                print(f"Gmail [v2]: query='{query}', requested_total={max_results}")
                fetched_count = 0
                page_token = None
                
                while fetched_count < max_results:
                    batch_size = min(50, max_results - fetched_count)
                    arguments = {
                        "query": query,
                        "max_results": batch_size,
                        "include_payload": True,
                    }
                    if page_token:
                        arguments["page_token"] = page_token

                    result = composio_client.tools.execute(
                        slug="GMAIL_FETCH_EMAILS",
                        arguments=arguments,
                        user_id=os.getenv("COMPOSIO_USER_ID", "default"),
                        dangerously_skip_version_check=True,
                    )
                    
                    data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                    data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                    
                    batch_emails = self._parse_gmail_v2_result({"data": data})
                    if not batch_emails:
                        break
                        
                    emails.extend(batch_emails)
                    fetched_count += len(batch_emails)
                    
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break

                if emails:
                    print(f"Gmail [v2]: total emails extracted: {len(emails)}")
                    return emails
                print("Gmail [v2]: no emails extracted, trying v1 fallback")
            except Exception as e:
                import traceback
                print(f"Gmail [v2] error: {e}")
                print(traceback.format_exc())

        # ── V1 fallback ────────────────────────────────────────────
        try:
            from composio import Action
        except ImportError:
            return []

        client = self._get_v1_client()
        if not client:
            print("Gmail: no v1 client available")
            return []

        try:
            print(f"Gmail [v1]: account={gmail_account}, query='{query}', max_results={max_results}")
            result = client.actions.execute(
                action=Action.GMAIL_FETCH_EMAILS,
                params={"query": query, "max_results": max_results, "include_payload": True},
                connected_account=gmail_account,
            )
            if result.get("successful") or result.get("status") == "success":
                messages = result.get("data", {}).get("messages", [])
                print(f"Gmail [v1]: found {len(messages)} messages")
                for msg in messages:
                    email_data = self._parse_gmail_message_composio(msg)
                    if email_data:
                        emails.append(email_data)
            else:
                print(f"Gmail [v1]: failed - {result.get('error', 'unknown')}")
        except Exception as e:
            import traceback
            print(f"Gmail [v1] error: {type(e).__name__}: {e}")
            print(traceback.format_exc())

        return emails

    def _parse_gmail_v2_result(self, result: dict) -> List[Dict]:
        """Parse ComposioToolSet Gmail response."""
        emails = []
        # v2 SDK returns data in various shapes; try common patterns
        data = result.get("data") or result
        messages = data.get("messages") or data.get("value") or data.get("result") or []

        if isinstance(messages, list):
            for msg in messages:
                email_data = self._parse_gmail_message_composio(msg)
                if email_data:
                    emails.append(email_data)
        elif isinstance(messages, dict):
            # Single message result
            email_data = self._parse_gmail_message_composio(messages)
            if email_data:
                emails.append(email_data)

        print(f"Gmail [v2]: parsed {len(emails)} emails")
        return emails

    def _parse_gmail_message_composio(self, msg: Dict) -> Optional[Dict]:
        """Parse Composio Gmail response into standard email dict."""
        if not msg:
            return None

        message_id = msg.get("messageId") or msg.get("id", "")
        subject = msg.get("subject", "")
        sender = msg.get("sender") or msg.get("from", {}).get("email", "")
        timestamp = msg.get("messageTimestamp") or msg.get("date", "") or msg.get("receivedDateTime", "")

        # Body can be in preview.body or body.content
        preview = msg.get("preview", {})
        body = ""
        if isinstance(preview, dict):
            body = preview.get("body") or preview.get("content", "")
        if not body:
            body = msg.get("body", {}).get("content", "")

        return {
            "message_id": message_id,
            "source": "gmail",
            "subject": subject,
            "sender": sender,
            "date": timestamp,
            "body": body,
            "raw": msg,
        }

    # ── Outlook via Composio OAuth ────────────────────────────────

    async def fetch_outlook(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails from Outlook using Composio with OAuth account."""
        emails = []
        outlook_account = os.getenv("OUTLOOK_ACCOUNT_ID")
        if not outlook_account:
            print("Outlook: Missing OUTLOOK_ACCOUNT_ID in .env")
            return []

        user_email = os.getenv("OUTLOOK_USER_EMAIL", "")
        filter_str = f"receivedDateTime -{since_days}d"
        select_fields = ["subject", "from", "body", "receivedDateTime",
                         "bodyPreview", "hasAttachments", "isRead"]

        # ── Try v2 SDK (composio.Composio.tools.execute) ────────────
        composio_client = self._get_composio()
        if composio_client:
            try:
                print(f"Outlook [v2]: filter='{filter_str}', requested_total={max_results}")
                fetched_count = 0
                
                while fetched_count < max_results:
                    batch_size = min(50, max_results - fetched_count)
                    arguments = {
                        "user_id": user_email,
                        "select": select_fields,
                        "filter": f"receivedDateTime ge {self._format_outlook_date(since_days)}",
                        "top": batch_size,
                    }
                    if fetched_count > 0:
                        arguments["skip"] = fetched_count

                    result = composio_client.tools.execute(
                        slug="OUTLOOK_QUERY_EMAILS",
                        arguments=arguments,
                        user_id=os.getenv("COMPOSIO_USER_ID", "default"),
                        dangerously_skip_version_check=True,
                    )
                    
                    data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                    data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                    
                    batch_emails = self._parse_outlook_v2_result({"data": data})
                    if not batch_emails:
                        break
                        
                    emails.extend(batch_emails)
                    fetched_count += len(batch_emails)
                    
                    if not data.get("@odata.nextLink") or len(batch_emails) == 0:
                        break

                if emails:
                    print(f"Outlook [v2]: total emails extracted: {len(emails)}")
                    return emails
                print("Outlook [v2]: no emails extracted, trying v1 fallback")
            except Exception as e:
                import traceback
                print(f"Outlook [v2] error: {e}")
                print(traceback.format_exc())

        # ── V1 fallback ────────────────────────────────────────────
        try:
            from composio import Action
        except ImportError:
            return []

        client = self._get_v1_client()
        if not client:
            print("Outlook: no v1 client available")
            return []

        try:
            print(f"Outlook [v1]: account={outlook_account}, filter='{filter_str}', max_results={max_results}")
            result = client.actions.execute(
                action=Action.OUTLOOK_LIST_MESSAGES,
                params={"user_id": user_email, "select": select_fields, "filter": filter_str, "limit": max_results},
                connected_account=outlook_account,
            )
            if result.get("successful") or result.get("status") == "success":
                messages = result.get("data", {}).get("value", [])
                print(f"Outlook [v1]: found {len(messages)} messages")
                for msg in messages:
                    email_data = self._parse_outlook_message_composio(msg)
                    if email_data:
                        emails.append(email_data)
            else:
                print(f"Outlook [v1]: failed - {result.get('error', 'unknown')}")
        except Exception as e:
            import traceback
            print(f"Outlook [v1] error: {type(e).__name__}: {e}")
            print(traceback.format_exc())

        return emails

    def _parse_outlook_v2_result(self, result: dict) -> List[Dict]:
        """Parse ComposioToolSet Outlook response."""
        emails = []
        data = result.get("data") or result
        messages = data.get("value") or data.get("messages") or data.get("result") or []

        if isinstance(messages, list):
            for msg in messages:
                email_data = self._parse_outlook_message_composio(msg)
                if email_data:
                    emails.append(email_data)
        elif isinstance(messages, dict):
            email_data = self._parse_outlook_message_composio(messages)
            if email_data:
                emails.append(email_data)

        print(f"Outlook [v2]: parsed {len(emails)} emails")
        return emails

    def _parse_outlook_message_composio(self, msg: Dict) -> Optional[Dict]:
        """Parse Composio Outlook response into standard email dict."""
        if not msg:
            return None

        message_id = msg.get("id", "")
        subject = msg.get("subject", "")

        from_field = msg.get("from", {})
        if isinstance(from_field, dict):
            sender = from_field.get("emailAddress", {}).get("address", "")
        else:
            sender = str(from_field)

        body_text = msg.get("body", {}).get("content", "")
        if msg.get("body", {}).get("contentType") == "html":
            body_text = self._strip_html(body_text)

        timestamp = msg.get("receivedDateTime", "")

        return {
            "message_id": message_id,
            "source": "outlook",
            "subject": subject,
            "sender": sender,
            "date": timestamp,
            "body": body_text,
            "raw": msg,
        }

    # ── IMAP (Zoner / third mailbox) ──────────────────────────────

    async def fetch_imap(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails via IMAP for third mailbox."""
        import imaplib
        from email import message_from_bytes

        server = os.getenv("IMAP_SERVER", "imap.zoner.com")
        port = int(os.getenv("IMAP_PORT", "993"))
        user = os.getenv("IMAP_USER", "")
        password = os.getenv("IMAP_PASSWORD", "")

        if not user or not password:
            print("IMAP credentials not configured, skipping")
            return []

        emails = []
        try:
            context = ssl.create_default_context()
            if not IMAP_VERIFY_SSL:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            with imaplib.IMAP4_SSL(server, port, ssl_context=context) as mail:
                mail.login(user, password)
                mail.select("inbox")

                since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
                _, search_data = mail.search(None, f'(SINCE "{since_date}")')

                message_ids = search_data[0].split()
                message_ids = message_ids[-max_results:]

                print(f"IMAP: Found {len(message_ids)} messages")

                for msg_id in message_ids:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    email_message = message_from_bytes(raw_email)
                    email_data = self._parse_imap_message(email_message, msg_id.decode())
                    if email_data:
                        emails.append(email_data)

        except Exception as e:
            print(f"IMAP fetch error: {e}")

        return emails

    def _parse_imap_message(self, msg, message_id: str) -> Optional[Dict]:
        """Parse IMAP email into standard dict."""
        subject = self._decode_header_value(msg.get("Subject", ""))
        sender = self._decode_header_value(msg.get("From", ""))
        date = msg.get("Date", "")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception:
                        pass
                elif content_type == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        body = self._strip_html(html)
                        break
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
                    if msg.get_content_type() == "text/html":
                        body = self._strip_html(body)
            except Exception:
                pass

        return {
            "message_id": message_id,
            "source": "imap",
            "subject": subject,
            "sender": sender,
            "date": date,
            "body": body,
            "raw": None,
        }

    # ── Classification & Storage ───────────────────────────────────

    async def process_emails(
        self,
        db: AsyncSession,
        sources: List[str] = None,
        max_results: int = 500,
        since_days: int = 365,
    ) -> Dict:
        """
        Fetch emails from all sources, classify them, and store subscriptions.
        Returns summary of processing results.
        """
        if sources is None:
            sources = ["gmail", "outlook", "imap"]

        results = {
            "processed": 0,
            "new_subscriptions": 0,
            "skipped": 0,
            "errors": 0,
            "sources": {},
        }

        all_emails = []

        for source in sources:
            try:
                if source == "gmail":
                    emails = await self.fetch_gmail(max_results, since_days)
                elif source == "outlook":
                    emails = await self.fetch_outlook(max_results, since_days)
                elif source == "imap":
                    emails = await self.fetch_imap(max_results, since_days)
                else:
                    continue

                results["sources"][source] = len(emails)
                all_emails.extend(emails)

            except Exception as e:
                print(f"Error fetching from {source}: {e}")
                results["sources"][source] = f"error: {str(e)}"
                results["errors"] += 1

        # Deduplicate by message_id
        seen_ids = set()
        unique_emails = []
        for email in all_emails:
            msg_id = f"{email['source']}:{email['message_id']}"
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                email["_unique_id"] = msg_id
                unique_emails.append(email)

        # Check which emails have already been processed
        processed_ids = set()
        for email in unique_emails:
            result = await db.execute(
                select(ProcessedEmail).where(
                    ProcessedEmail.message_id == email["_unique_id"]
                )
            )
            if result.scalar_one_or_none():
                processed_ids.add(email["_unique_id"])

        # Process unprocessed emails
        for email in unique_emails:
            if email["_unique_id"] in processed_ids:
                results["skipped"] += 1
                continue

            try:
                classification = self.classifier.classify(
                    email["subject"],
                    email["sender"],
                    email["body"],
                )

                # Mark as processed (ON CONFLICT IGNORE for SQLite)
                try:
                    stmt = insert(ProcessedEmail).values(
                        message_id=email["_unique_id"],
                        source=email["source"],
                    )
                    stmt = stmt.on_conflict_do_nothing()
                    await db.execute(stmt)
                except Exception:
                    pass

                if classification["is_subscription"]:
                    norm_name = classification["service_name"].strip()
                    result = await db.execute(
                        select(Subscription).where(
                            func.lower(Subscription.service_name) == norm_name.lower()
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        existing.cost = classification["cost"] or existing.cost
                        existing.currency = classification["currency"] or existing.currency
                        existing.billing_cycle = classification["billing_cycle"]
                        existing.updated_at = datetime.utcnow()
                        subscription_id = existing.id
                        target_sub = existing
                    else:
                        # Extract start date from email date
                        start_date = None
                        email_date_str = email.get("date", "")
                        if email_date_str:
                            try:
                                email_datetime = email.utils.parsedate_to_datetime(email_date_str)
                                start_date = email_datetime.strftime("%Y-%m-%d")
                            except Exception:
                                try:
                                    email_datetime = datetime.fromisoformat(
                                        email_date_str.replace("Z", "+00:00")
                                    )
                                    start_date = email_datetime.strftime("%Y-%m-%d")
                                except Exception:
                                    pass

                        if not start_date:
                            start_date = datetime.utcnow().strftime("%Y-%m-%d")

                        plan_name = classification.get("plan_name", "Standard")

                        new_sub = Subscription(
                            service_name=classification["service_name"],
                            category=classification["category"],
                            cost=classification["cost"],
                            currency=classification["currency"],
                            billing_cycle=classification["billing_cycle"],
                            status="active",
                            start_date=start_date,
                            notes=f"Plan: {plan_name}",
                            source=email["source"],
                        )
                        db.add(new_sub)
                        await db.flush()
                        subscription_id = new_sub.id
                        results["new_subscriptions"] += 1
                        target_sub = new_sub

                    # Determine event date
                    email_date = datetime.utcnow()
                    try:
                        raw_date = email.get("date", "")
                        if raw_date:
                            from dateutil import parser
                            email_date = parser.parse(raw_date)
                    except Exception:
                        pass

                    event = SubscriptionEvent(
                        subscription_id=subscription_id,
                        service_name=classification["service_name"],
                        category=classification["category"],
                        amount=classification["cost"],
                        currency=classification["currency"],
                        billing_cycle=classification["billing_cycle"],
                        event_date=email_date,
                        source_type=classification["source_type"],
                        message_id=email["_unique_id"],
                    )
                    db.add(event)

                    # Update start_date if this is an account creation email
                    email_text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
                    if any(kw in email_text for kw in ACCOUNT_CREATION_KEYWORDS):
                        start_date_str = email_date.strftime("%Y-%m-%d")
                        if not target_sub.start_date or start_date_str < target_sub.start_date:
                            target_sub.start_date = start_date_str

                results["processed"] += 1

            except Exception as e:
                print(f"Error processing email {email['_unique_id']}: {e}")
                results["errors"] += 1

        try:
            await db.commit()
        except Exception as e:
            print(f"Database commit error: {e}")
            await db.rollback()

        return results

    # ── Helpers ────────────────────────────────────────────────────

    def _format_outlook_date(self, days: int) -> str:
        """Format date for Outlook OData filter (ISO 8601)."""
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y-%m-%dT00:00:00Z")

    def _format_gmail_date(self, days: int) -> str:
        """Format date for Gmail search query (YYYY/MM/DD)."""
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y/%m/%d")

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from text."""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _decode_header_value(self, value: str) -> str:
        """Decode email header value."""
        if not value:
            return ""
        decoded = decode_header(value)
        result = []
        for part, charset in decoded:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(charset or "utf-8", errors="ignore"))
                except Exception:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(part)
        return "".join(result)