#!/usr/bin/env python3
"""
Initial backfill using MCP tools directly.
Run inside Cline where MCP is available.
"""
import asyncio
import json
import os
from datetime import datetime, timedelta

# Must be inside Cline for this import to work
from mcp import use_mcp_tool

from database import init_db, AsyncSessionLocal, Subscription, ProcessedEmail, SubscriptionEvent
from email_parser import EmailClassifier
from sqlalchemy import select, func


classifier = EmailClassifier()


def format_gmail_date(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")


def format_iso_date(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


async def fetch_gmail_list(max_results: int = 100, since_days: int = 365):
    """Fetch Gmail message IDs via MCP."""
    result = await use_mcp_tool(
        "COMPOSIO_MULTI_EXECUTE_TOOL",
        {
            "tools": [{
                "tool_slug": "GMAIL_FETCH_EMAILS",
                "arguments": {
                    "max_results": max_results,
                    "query": f"after:{format_gmail_date(since_days)}",
                    "include_payload": False,
                    "verbose": False,
                }
            }],
            "sync_response_to_workbench": False
        }
    )
    data = result.get("data", {}) if isinstance(result, dict) else {}
    msgs = data.get("messages", []) if isinstance(data, dict) else []
    return msgs


async def fetch_gmail_detail(message_id: str):
    """Fetch full Gmail message via MCP."""
    result = await use_mcp_tool(
        "COMPOSIO_MULTI_EXECUTE_TOOL",
        {
            "tools": [{
                "tool_slug": "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
                "arguments": {"message_id": message_id, "format": "full"}
            }],
            "sync_response_to_workbench": False
        }
    )
    data = result.get("data", {}) if isinstance(result, dict) else {}
    return data


def parse_gmail_message(data: dict, message_id: str) -> dict:
    payload = data.get("payload", {})
    headers = {h.get("name", ""): h.get("value", "") for h in payload.get("headers", [])}
    body = extract_gmail_body(payload)
    return {
        "message_id": message_id,
        "source": "gmail",
        "subject": headers.get("Subject", ""),
        "sender": headers.get("From", ""),
        "date": headers.get("Date", ""),
        "body": body,
        "raw": data,
    }


def extract_gmail_body(payload: dict) -> str:
    import base64
    mime_type = payload.get("mimeType", "")
    if mime_type in {"text/plain", "text/html"}:
        data = payload.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="ignore")
            return decoded if mime_type == "text/plain" else strip_html(decoded)
    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            result = extract_gmail_body(part)
            if result:
                return result
    return ""


def strip_html(html: str) -> str:
    import re
    text = re.sub(r'<[^>]+>', ' ', html or "")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


async def fetch_outlook_list(max_results: int = 100, since_days: int = 365):
    """Fetch Outlook messages via MCP."""
    result = await use_mcp_tool(
        "COMPOSIO_MULTI_EXECUTE_TOOL",
        {
            "tools": [{
                "tool_slug": "OUTLOOK_QUERY_EMAILS",
                "arguments": {
                    "top": max_results,
                    "folder": "inbox",
                    "filter": f"receivedDateTime ge {format_iso_date(since_days)}",
                    "select": ["id", "subject", "from", "receivedDateTime", "body"],
                }
            }],
            "sync_response_to_workbench": False
        }
    )
    data = result.get("data", {}) if isinstance(result, dict) else {}
    msgs = data.get("value", []) if isinstance(data, dict) else []
    return msgs


def parse_outlook_message(msg: dict) -> dict:
    body = msg.get("body", {}) or {}
    body_text = body.get("content", "")
    if str(body.get("contentType", "")).lower() == "html":
        body_text = strip_html(body_text)
    return {
        "message_id": msg.get("id", ""),
        "source": "outlook",
        "subject": msg.get("subject", ""),
        "sender": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
        "date": msg.get("receivedDateTime", ""),
        "body": body_text,
        "raw": msg,
    }


async def process_and_store(emails: list, db):
    """Classify and store emails in DB."""
    results = {"processed": 0, "new_subscriptions": 0, "skipped": 0, "errors": 0}
    seen_ids = set()
    for email in emails:
        uid = f"{email['source']}:{email['message_id']}"
        if uid in seen_ids:
            continue
        seen_ids.add(uid)

        existing = await db.execute(select(ProcessedEmail).where(ProcessedEmail.message_id == uid))
        if existing.scalar_one_or_none():
            results["skipped"] += 1
            continue

        classification = classifier.classify(email["subject"], email["sender"], email["body"])
        db.add(ProcessedEmail(message_id=uid, source=email["source"]))

        if classification["is_subscription"]:
            norm_name = classification["service_name"].strip()
            result = await db.execute(
                select(Subscription).where(func.lower(Subscription.service_name) == norm_name.lower())
            )
            existing_sub = result.scalar_one_or_none()
            if existing_sub:
                existing_sub.cost = classification["cost"] or existing_sub.cost
                existing_sub.currency = classification["currency"] or existing_sub.currency
                existing_sub.billing_cycle = classification["billing_cycle"]
                existing_sub.updated_at = datetime.utcnow()
                sub_id = existing_sub.id
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
                sub_id = new_sub.id
                results["new_subscriptions"] += 1

            db.add(SubscriptionEvent(
                subscription_id=sub_id,
                service_name=classification["service_name"],
                category=classification["category"],
                amount=classification["cost"],
                currency=classification["currency"],
                billing_cycle=classification["billing_cycle"],
                event_date=datetime.utcnow(),
                source_type=classification["source_type"],
                message_id=uid,
            ))

        results["processed"] += 1

    await db.commit()
    return results


async def run_backfill(gmail_limit=50, outlook_limit=50, since_days=365):
    await init_db()
    all_emails = []

    print("Fetching Gmail...")
    gmail_msgs = await fetch_gmail_list(gmail_limit, since_days)
    print(f"Gmail: {len(gmail_msgs)} message IDs")
    for msg in gmail_msgs:
        mid = msg.get("id") or msg.get("messageId")
        if not mid:
            continue
        detail = await fetch_gmail_detail(mid)
        parsed = parse_gmail_message(detail, mid)
        if parsed["body"]:
            all_emails.append(parsed)

    print("Fetching Outlook...")
    outlook_msgs = await fetch_outlook_list(outlook_limit, since_days)
    print(f"Outlook: {len(outlook_msgs)} messages")
    for msg in outlook_msgs:
        parsed = parse_outlook_message(msg)
        if parsed["body"]:
            all_emails.append(parsed)

    print(f"\nTotal emails to process: {len(all_emails)}")

    async with AsyncSessionLocal() as db:
        results = await process_and_store(all_emails, db)
        print(f"Processed: {results['processed']}")
        print(f"New subscriptions: {results['new_subscriptions']}")
        print(f"Skipped: {results['skipped']}")

        # Show current subscription count
        count_result = await db.execute(select(func.count(Subscription.id)))
        print(f"Total subscriptions in DB: {count_result.scalar()}")


if __name__ == "__main__":
    asyncio.run(run_backfill())
