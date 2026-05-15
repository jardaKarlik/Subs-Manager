#!/usr/bin/env python3
"""Quick test of Composio v2 SDK tools.execute() with real credentials."""

import composio
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("COMPOSIO_API_KEY")
entity_id = os.getenv("COMPOSIO_USER_ID", "default")
gmail_acct = os.getenv("GMAIL_ACCOUNT_ID")
outlook_acct = os.getenv("OUTLOOK_ACCOUNT_ID")

print(f"Sdk version: {composio.__version__}")
print(f"Entity: {entity_id}")
print(f"Gmail account: {gmail_acct}")
print(f"Outlook account: {outlook_acct}")

c = composio.Composio(api_key=api_key)

# Test Gmail
print("\n--- Testing GMAIL_FETCH_EMAILS ---")
try:
    result = c.tools.execute(
        slug="GMAIL_FETCH_EMAILS",
        arguments={
            "query": "after:2026/05/01",
            "max_results": 2,
            "include_payload": False,
        },
        connected_account_id=gmail_acct,
        user_id=entity_id,
        dangerously_skip_version_check=True,
    )
    print(f"Type: {type(result).__name__}")
    if hasattr(result, 'data'):
        data = result.data
        print(f"data type: {type(data).__name__}")
        if isinstance(data, dict):
            print(f"data keys: {list(data.keys())}")
            msgs = data.get("messages") or data.get("value") or []
            print(f"Messages found: {len(msgs)}")
            if msgs:
                print(f"First msg keys: {list(msgs[0].keys())}")
                print(f"Subject: {msgs[0].get('subject', 'N/A')}")
    elif isinstance(result, dict):
        print(f"Keys: {list(result.keys())}")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()

# Test Outlook
print("\n--- Testing OUTLOOK_LIST_MESSAGES ---")
if outlook_acct:
    try:
        result = c.tools.execute(
            slug="OUTLOOK_LIST_MESSAGES",
            arguments={
                "user_id": os.getenv("OUTLOOK_USER_EMAIL", ""),
                "select": ["subject", "from", "body", "receivedDateTime"],
                "filter": "receivedDateTime -30d",
                "limit": 2,
            },
            connected_account_id=outlook_acct,
            user_id=entity_id,
            dangerously_skip_version_check=True,
        )
        print(f"Type: {type(result).__name__}")
        if hasattr(result, 'data'):
            data = result.data
            print(f"data type: {type(data).__name__}")
            if isinstance(data, dict):
                print(f"data keys: {list(data.keys())}")
                msgs = data.get("value") or data.get("messages") or []
                print(f"Messages found: {len(msgs)}")
                if msgs:
                    print(f"First msg keys: {list(msgs[0].keys())}")
        elif isinstance(result, dict):
            print(f"Keys: {list(result.keys())}")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()