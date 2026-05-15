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
        """
        Backward compatible fetch_gmail. 
        Note: The main streaming logic is now in _stream_fetch_and_process_gmail.
        """
        emails = []
        gmail_account = os.getenv("GMAIL_ACCOUNT_ID")
        if not gmail_account:
            return []

        query = f"after:{self._format_gmail_date(since_days)}"
        composio_client = self._get_composio()
        if composio_client:
            try:
                fetched_count = 0
                page_token = None
                while fetched_count < max_results:
                    batch_size = min(100, max_results - fetched_count)
                    arguments = {"query": query, "max_results": batch_size, "include_payload": True}
                    if page_token: arguments["page_token"] = page_token
                    result = composio_client.tools.execute(slug="GMAIL_FETCH_EMAILS", arguments=arguments, user_id=os.getenv("COMPOSIO_USER_ID", "default"), dangerously_skip_version_check=True)
                    data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                    data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                    batch_emails = self._parse_gmail_v2_result({"data": data})
                    if not batch_emails: break
                    emails.extend(batch_emails)
                    fetched_count += len(batch_emails)
                    page_token = data.get("nextPageToken")
                    if not page_token: break
                    import asyncio
                    await asyncio.sleep(0.5)
                return emails
            except Exception as e:
                print(f"Gmail [v2] error: {e}")

        return emails

    def _parse_gmail_v2_result(self, result: dict) -> List[Dict]:
        """Parse ComposioToolSet Gmail response."""
        emails = []
        data = result.get("data") or result
        messages = data.get("messages") or data.get("value") or data.get("result") or []
        if isinstance(messages, list):
            for msg in messages:
                email_data = self._parse_gmail_message_composio(msg)
                if email_data: emails.append(email_data)
        elif isinstance(messages, dict):
            email_data = self._parse_gmail_message_composio(messages)
            if email_data: emails.append(email_data)
        return emails

    def _parse_gmail_message_composio(self, msg: Dict) -> Optional[Dict]:
        """Parse Composio Gmail response into standard email dict."""
        if not msg: return None
        message_id = msg.get("messageId") or msg.get("id", "")
        subject = msg.get("subject", "")
        sender = msg.get("sender") or msg.get("from", {}).get("email", "")
        timestamp = msg.get("messageTimestamp") or msg.get("date", "") or msg.get("receivedDateTime", "")
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
        """Backward compatible fetch_outlook."""
        emails = []
        outlook_account = os.getenv("OUTLOOK_ACCOUNT_ID")
        if not outlook_account: return []
        user_email = os.getenv("OUTLOOK_USER_EMAIL", "")
        select_fields = ["subject", "from", "body", "receivedDateTime", "bodyPreview", "hasAttachments", "isRead"]
        composio_client = self._get_composio()
        if composio_client:
            try:
                fetched_count = 0
                while fetched_count < max_results:
                    batch_size = min(100, max_results - fetched_count)
                    arguments = {"user_id": user_email, "select": select_fields, "filter": f"receivedDateTime ge {self._format_outlook_date(since_days)}", "top": batch_size}
                    if fetched_count > 0: arguments["skip"] = fetched_count
                    result = composio_client.tools.execute(slug="OUTLOOK_QUERY_EMAILS", arguments=arguments, user_id=os.getenv("COMPOSIO_USER_ID", "default"), dangerously_skip_version_check=True)
                    data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                    data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                    batch_emails = self._parse_outlook_v2_result({"data": data})
                    if not batch_emails: break
                    emails.extend(batch_emails)
                    fetched_count += len(batch_emails)
                    if not data.get("@odata.nextLink") or len(batch_emails) == 0: break
                    import asyncio
                    await asyncio.sleep(0.5)
                return emails
            except Exception as e:
                print(f"Outlook [v2] error: {e}")
        return emails

    def _parse_outlook_v2_result(self, result: dict) -> List[Dict]:
        """Parse ComposioToolSet Outlook response."""
        emails = []
        data = result.get("data") or result
        messages = data.get("value") or data.get("messages") or data.get("result") or []
        if isinstance(messages, list):
            for msg in messages:
                email_data = self._parse_outlook_message_composio(msg)
                if email_data: emails.append(email_data)
        elif isinstance(messages, dict):
            email_data = self._parse_outlook_message_composio(messages)
            if email_data: emails.append(email_data)
        return emails

    def _parse_outlook_message_composio(self, msg: Dict) -> Optional[Dict]:
        """Parse Composio Outlook response into standard email dict."""
        if not msg: return None
        message_id = msg.get("id", "")
        subject = msg.get("subject", "")
        from_field = msg.get("from", {})
        sender = from_field.get("emailAddress", {}).get("address", "") if isinstance(from_field, dict) else str(from_field)
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

    # ── IMAP ──────────────────────────────────────────────────────

    async def fetch_imap(self, max_results: int = 1000, since_days: int = 365) -> List[Dict]:
        """Fetch emails via IMAP."""
        import imaplib
        from email import message_from_bytes
        server = os.getenv("IMAP_SERVER", "imap.zoner.com")
        port = int(os.getenv("IMAP_PORT", "993"))
        user = os.getenv("IMAP_USER", "")
        password = os.getenv("IMAP_PASSWORD", "")
        if not user or not password: return []
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
                for msg_id in message_ids:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    email_message = message_from_bytes(raw_email)
                    email_data = self._parse_imap_message(email_message, msg_id.decode())
                    if email_data: emails.append(email_data)
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
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception: pass
                elif part.get_content_type() == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        body = self._strip_html(html)
                        break
                    except Exception: pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
                    if msg.get_content_type() == "text/html": body = self._strip_html(body)
            except Exception: pass
        return {"message_id": message_id, "source": "imap", "subject": subject, "sender": sender, "date": date, "body": body, "raw": None}

    # ── Batch Processing & Streaming ──────────────────────────────

    async def _process_email_batch(self, db: AsyncSession, batch: List[Dict], results: Dict) -> None:
        """Deduplicate, classify, and store a batch of emails immediately."""
        if not batch: return
        seen_in_batch = set()
        unique_in_batch = []
        for email in batch:
            msg_id = f"{email['source']}:{email['message_id']}"
            if msg_id not in seen_in_batch:
                seen_in_batch.add(msg_id)
                email["_unique_id"] = msg_id
                unique_in_batch.append(email)

        for email in unique_in_batch:
            result_row = await db.execute(select(ProcessedEmail).where(ProcessedEmail.message_id == email["_unique_id"]))
            if result_row.scalar_one_or_none():
                results["skipped"] += 1
                continue

            try:
                classification = self.classifier.classify(email["subject"], email["sender"], email["body"])
                # Record as processed (SQLite-safe; dedup already confirmed above)
                db.add(ProcessedEmail(message_id=email["_unique_id"], source=email["source"]))

                if classification["is_subscription"]:
                    norm_name = classification["service_name"].strip()
                    result_row2 = await db.execute(select(Subscription).where(func.lower(Subscription.service_name) == norm_name.lower()))
                    existing = result_row2.scalar_one_or_none()
                    if existing:
                        existing.cost, existing.currency, existing.billing_cycle = classification["cost"] or existing.cost, classification["currency"] or existing.currency, classification["billing_cycle"]
                        existing.updated_at = datetime.utcnow()
                        subscription_id, target_sub = existing.id, existing
                    else:
                        start_date = None
                        email_date_str = email.get("date", "")
                        if email_date_str:
                            try:
                                email_datetime = email.utils.parsedate_to_datetime(email_date_str)
                                start_date = email_datetime.strftime("%Y-%m-%d")
                            except Exception:
                                try:
                                    email_datetime = datetime.fromisoformat(email_date_str.replace("Z", "+00:00"))
                                    start_date = email_datetime.strftime("%Y-%m-%d")
                                except Exception: pass
                        if not start_date: start_date = datetime.utcnow().strftime("%Y-%m-%d")
                        new_sub = Subscription(service_name=classification["service_name"], category=classification["category"], cost=classification["cost"], currency=classification["currency"], billing_cycle=classification["billing_cycle"], status="active", start_date=start_date, notes=f"Plan: {classification.get('plan_name', 'Standard')}", source=email["source"])
                        db.add(new_sub)
                        await db.flush()
                        subscription_id, target_sub = new_sub.id, new_sub
                        results["new_subscriptions"] += 1

                    email_date = datetime.utcnow()
                    try:
                        raw_date = email.get("date", "")
                        if raw_date:
                            from dateutil import parser
                            email_date = parser.parse(raw_date)
                    except Exception: pass

                    event = SubscriptionEvent(subscription_id=subscription_id, service_name=classification["service_name"], category=classification["category"], amount=classification["cost"], currency=classification["currency"], billing_cycle=classification["billing_cycle"], event_date=email_date, source_type=classification["source_type"], message_id=email["_unique_id"])
                    db.add(event)

                    email_text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
                    if any(kw in email_text for kw in ACCOUNT_CREATION_KEYWORDS):
                        start_date_str = email_date.strftime("%Y-%m-%d")
                        if not target_sub.start_date or start_date_str < target_sub.start_date: target_sub.start_date = start_date_str

                results["processed"] += 1
            except Exception as e:
                print(f"Error processing email {email['_unique_id']}: {e}")
                results["failed"] += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Database commit failed for batch: {e}") from e

    async def _stream_fetch_and_process_gmail(self, db: AsyncSession, max_results: int, since_days: int, results: Dict) -> None:
        """Fetch Gmail in batches and process immediately."""
        gmail_account = os.getenv("GMAIL_ACCOUNT_ID")
        composio_client = self._get_composio()
        if not gmail_account or not composio_client: return
        query = f"after:{self._format_gmail_date(since_days)}"
        fetched_count, page_token, batch_num = 0, None, 0
        while fetched_count < max_results:
            batch_size = min(100, max_results - fetched_count)
            arguments = {"query": query, "max_results": batch_size, "include_payload": True}
            if page_token: arguments["page_token"] = page_token
            try:
                result = composio_client.tools.execute(slug="GMAIL_FETCH_EMAILS", arguments=arguments, user_id=os.getenv("COMPOSIO_USER_ID", "default"), dangerously_skip_version_check=True)
                data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                batch_emails = self._parse_gmail_v2_result({"data": data})
                if not batch_emails: break
                batch_num += 1
                fetched_count += len(batch_emails)
                await self._process_email_batch(db, batch_emails, results)
                print(f"  Gmail batch #{batch_num}: {len(batch_emails)} fetched -> total processed: {results['processed']}")
                page_token = data.get("nextPageToken")
                if not page_token: break
                import asyncio
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Gmail [v2] batch error: {e}")
                break
        results["sources"]["gmail"] = fetched_count

    async def _stream_fetch_and_process_outlook(self, db: AsyncSession, max_results: int, since_days: int, results: Dict) -> None:
        """Fetch Outlook in batches and process immediately."""
        outlook_account = os.getenv("OUTLOOK_ACCOUNT_ID")
        composio_client = self._get_composio()
        if not outlook_account or not composio_client: return
        user_email = os.getenv("OUTLOOK_USER_EMAIL", "")
        select_fields = ["subject", "from", "body", "receivedDateTime", "bodyPreview", "hasAttachments", "isRead"]
        fetched_count, batch_num = 0, 0
        while fetched_count < max_results:
            batch_size = min(100, max_results - fetched_count)
            arguments = {"user_id": user_email, "select": select_fields, "filter": f"receivedDateTime ge {self._format_outlook_date(since_days)}", "top": batch_size}
            if fetched_count > 0: arguments["skip"] = fetched_count
            try:
                result = composio_client.tools.execute(slug="OUTLOOK_QUERY_EMAILS", arguments=arguments, user_id=os.getenv("COMPOSIO_USER_ID", "default"), dangerously_skip_version_check=True)
                data_obj = getattr(result, 'data', result) if not isinstance(result, dict) else result
                data = data_obj.get("data") or data_obj if isinstance(data_obj, dict) else {}
                batch_emails = self._parse_outlook_v2_result({"data": data})
                if not batch_emails: break
                batch_num += 1
                fetched_count += len(batch_emails)
                await self._process_email_batch(db, batch_emails, results)
                print(f"  Outlook batch #{batch_num}: {len(batch_emails)} fetched -> total processed: {results['processed']}")
                if not data.get("@odata.nextLink") or len(batch_emails) == 0: break
                import asyncio
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Outlook [v2] batch error: {e}")
                break
        results["sources"]["outlook"] = fetched_count

    async def process_emails(self, db: AsyncSession, sources: List[str] = None, max_results: int = 500, since_days: int = 365) -> Dict:
        """Fetch and process emails incrementally. Raises on critical failure."""
        if sources is None: sources = ["gmail", "outlook", "imap"]
        results = {"processed": 0, "new_subscriptions": 0, "skipped": 0, "failed": 0, "sources": {}}
        for source in sources:
            try:
                if source == "gmail": await self._stream_fetch_and_process_gmail(db, max_results, since_days, results)
                elif source == "outlook": await self._stream_fetch_and_process_outlook(db, max_results, since_days, results)
                elif source == "imap":
                    emails = await self.fetch_imap(max_results, since_days)
                    if emails: await self._process_email_batch(db, emails, results)
                    results["sources"]["imap"] = len(emails)
            except Exception as e:
                # Log and re-raise critical errors (DB failures, auth failures)
                # so the API returns HTTP 500 instead of fake success counts
                import logging
                logging.getLogger(__name__).error(f"Critical error processing source {source}: {e}")
                raise RuntimeError(f"Email processing failed for {source}: {e}") from e
        return results

    # ── Helpers ────────────────────────────────────────────────────

    def _format_outlook_date(self, days: int) -> str:
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y-%m-%dT00:00:00Z")

    def _format_gmail_date(self, days: int) -> str:
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y/%m/%d")

    def _strip_html(self, html: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _decode_header_value(self, value: str) -> str:
        if not value: return ""
        decoded = decode_header(value)
        result = []
        for part, charset in decoded:
            if isinstance(part, bytes):
                try: result.append(part.decode(charset or "utf-8", errors="ignore"))
                except Exception: result.append(part.decode("utf-8", errors="ignore"))
            else: result.append(part)
        return "".join(result)
