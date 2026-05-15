"""
Email Fetcher for Subscription Manager
Fetches emails from Gmail (via Composio), Outlook (via Composio), and IMAP.
Integrates with the EmailClassifier for subscription detection.
"""

import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import func

import email.utils

from email.parser import Parser
from email.header import decode_header

from email_parser import EmailClassifier, ACCOUNT_CREATION_KEYWORDS
from database import (
    Subscription, ProcessedEmail, SubscriptionEvent,
    AsyncSessionLocal, AsyncSession
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


class EmailFetcher:
    """Fetch and classify emails from multiple sources."""

    def __init__(self):
        self.classifier = EmailClassifier()

    # ── Gmail via Composio ─────────────────────────────────────────

    async def fetch_gmail(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails from Gmail using Composio SDK."""
        try:
            from composio import Composio, Action
        except ImportError:
            print("Composio SDK not available, skipping Gmail")
            return []

        emails = []
        try:
            composio_client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))

            # Fetch emails using Composio
            query = f"after:{self._format_gmail_date(since_days)}"
            result = composio_client.execute_action(
                action=Action.GMAIL_FETCH_EMAILS,
                params={
                    "max_results": max_results,
                    "query": query
                }
            )

            messages = result.get("data", {}).get("messages", [])
            print(f"Gmail: Found {len(messages)} messages")

            for msg in messages:
                message_id = msg.get("id")
                # Fetch full message
                detail = composio_client.execute_action(
                    action=Action.GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID,
                    params={"message_id": message_id}
                )

                email_data = self._parse_gmail_message(detail, message_id)
                if email_data:
                    emails.append(email_data)

        except Exception as e:
            print(f"Gmail fetch error: {e}")

        return emails

    def _parse_gmail_message(self, detail: Dict, message_id: str) -> Optional[Dict]:
        """Parse Gmail API response into standard email dict."""
        data = detail.get("data", {})
        if not data:
            return None

        payload = data.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        # Extract body
        body = self._extract_gmail_body(payload)

        return {
            "message_id": message_id,
            "source": "gmail",
            "subject": headers.get("Subject", ""),
            "sender": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "raw": data
        }

    def _extract_gmail_body(self, payload: Dict) -> str:
        """Extract text body from Gmail message payload."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            import base64
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        elif mime_type == "text/html":
            import base64
            data = payload.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                return self._strip_html(html)

        elif mime_type.startswith("multipart/"):
            parts = payload.get("parts", [])
            for part in parts:
                result = self._extract_gmail_body(part)
                if result:
                    return result

        return ""

    # ── Outlook via Composio ───────────────────────────────────────

    async def fetch_outlook(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails from Outlook using Composio SDK."""
        try:
            from composio import Composio, Action
        except ImportError:
            print("Composio SDK not available, skipping Outlook")
            return []

        emails = []
        try:
            composio_client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))

            # Format filter for Outlook
            filter_str = f"receivedDateTime ge {self._format_iso_date(since_days)}"

            # Fetch emails using Composio
            result = composio_client.execute_action(
                action=Action.OUTLOOK_QUERY_EMAILS,
                params={
                    "limit": max_results,
                    "filter": filter_str
                }
            )

            messages = result.get("data", {}).get("value", [])
            print(f"Outlook: Found {len(messages)} messages")

            for msg in messages:
                email_data = self._parse_outlook_message(msg)
                if email_data:
                    emails.append(email_data)

        except Exception as e:
            print(f"Outlook fetch error: {e}")

        return emails

    def _parse_outlook_message(self, msg: Dict) -> Optional[Dict]:
        """Parse Outlook API response into standard email dict."""
        if not msg:
            return None

        body_text = msg.get("body", {}).get("content", "")
        # If HTML, strip tags
        if msg.get("body", {}).get("contentType") == "html":
            body_text = self._strip_html(body_text)

        return {
            "message_id": msg.get("id", ""),
            "source": "outlook",
            "subject": msg.get("subject", ""),
            "sender": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            "date": msg.get("receivedDateTime", ""),
            "body": body_text,
            "raw": msg
        }

    # ── IMAP (Zoner) ───────────────────────────────────────────────

    async def fetch_imap(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails via IMAP for third mailbox."""
        import imaplib
        import ssl
        from email import message_from_bytes

        server = os.getenv("IMAP_SERVER", "imap.zoner.com")
        port = int(os.getenv("IMAP_PORT", "993"))
        user = os.getenv("IMAP_USER", "")
        password = os.getenv("IMAP_PASSWORD", "")

        if not user or not password:
            print("IMAP credentials not configured, skipping")
            return []

        verify_ssl = os.getenv("IMAP_VERIFY_SSL", "true").lower() not in ("false", "0", "no")

        emails = []
        try:
            context = ssl.create_default_context()
            if not verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            with imaplib.IMAP4_SSL(server, port, ssl_context=context) as mail:
                mail.login(user, password)
                mail.select("inbox")

                since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
                _, search_data = mail.search(None, f'(SINCE "{since_date}")')

                message_ids = search_data[0].split()
                # Limit to max_results (most recent)
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

        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except:
                        pass
                elif content_type == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        body = self._strip_html(html)
                        break
                    except:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
                    if msg.get_content_type() == "text/html":
                        body = self._strip_html(body)
            except:
                pass

        return {
            "message_id": message_id,
            "source": "imap",
            "subject": subject,
            "sender": sender,
            "date": date,
            "body": body,
            "raw": None
        }

    # ── Classification & Storage ───────────────────────────────────

    async def process_emails(
        self,
        db: AsyncSession,
        sources: List[str] = None,
        max_results: int = 500,
        since_days: int = 365
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
            "sources": {}
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
                    email["body"]
                )

                # Mark as processed regardless of classification
                processed = ProcessedEmail(
                    message_id=email["_unique_id"],
                    source=email["source"]
                )
                db.add(processed)

                if classification["is_subscription"]:
                    # Check if subscription already exists for this service (case-insensitive)
                    norm_name = classification["service_name"].strip()
                    result = await db.execute(
                        select(Subscription).where(
                            func.lower(Subscription.service_name) == norm_name.lower()
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update existing subscription with latest info
                        existing.cost = classification["cost"] or existing.cost
                        existing.currency = classification["currency"] or existing.currency
                        existing.billing_cycle = classification["billing_cycle"]
                        existing.updated_at = datetime.utcnow()
                        subscription_id = existing.id
                        target_sub = existing
                    else:
                        # Extract start date from email date
                        start_date = None
                        email_date = email.get("date", "")
                        if email_date:
                            try:
                                # Try standard email date parser
                                email_datetime = email.utils.parsedate_to_datetime(email_date)
                                start_date = email_datetime.strftime("%Y-%m-%d")
                            except Exception:
                                try:
                                    # Fallback to ISO
                                    email_datetime = datetime.fromisoformat(email_date.replace("Z", "+00:00"))
                                    start_date = email_datetime.strftime("%Y-%m-%d")
                                except Exception:
                                    pass
                        
                        if not start_date:
                            start_date = datetime.utcnow().strftime("%Y-%m-%d")

                        # Extract plan type if available
                        plan_name = classification.get("plan_name", "Standard")

                        # Create new subscription
                        new_sub = Subscription(
                            service_name=classification["service_name"],
                            category=classification["category"],
                            cost=classification["cost"],
                            currency=classification["currency"],
                            billing_cycle=classification["billing_cycle"],
                            status="active",
                            start_date=start_date,                              # ? FIX #2: From email date
                            notes=f"Plan: {plan_name}",                         # ? FIX #3: Store plan type
                            source=email["source"],
                        )
                        db.add(new_sub)
                        await db.flush()  # Get the ID
                        subscription_id = new_sub.id
                        results["new_subscriptions"] += 1
                        target_sub = new_sub

                    # Determine event date from email
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
                        message_id=email["_unique_id"]
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

        await db.commit()
        return results

    # ── Helpers ────────────────────────────────────────────────────

    def _format_gmail_date(self, days: int) -> str:
        """Format date for Gmail search query (YYYY/MM/DD)."""
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y/%m/%d")

    def _format_iso_date(self, days: int) -> str:
        """Format date for Outlook filter (ISO 8601)."""
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y-%m-%dT%H:%M:%SZ")

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
                except:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(part)
        return "".join(result)


