#!/usr/bin/env python3
"""
Test which Outlook actions actually work with this Composio project
"""
import os
import sys
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import requests
requests.packages.urllib3.disable_warnings()
original_request = requests.Session.request
def patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, *args, **kwargs)
requests.Session.request = patched_request

from dotenv import load_dotenv
load_dotenv()

from composio import Composio, Action

api_key = os.getenv("COMPOSIO_API_KEY")
outlook_email = os.getenv("OUTLOOK_USER_EMAIL", "")

if not api_key:
    print("Missing COMPOSIO_API_KEY")
    sys.exit(1)

composio = Composio(api_key=api_key)

# Get connected accounts
try:
    connected_accounts = composio.connected_accounts.get()
    print(f"\nConnected accounts: {len(connected_accounts)}")
    for i, acc in enumerate(connected_accounts):
        print(f"  {i}: {acc.id}")
except Exception as e:
    print(f"Error getting connected accounts: {e}")
    sys.exit(1)

if len(connected_accounts) < 2:
    print("Not enough connected accounts")
    sys.exit(1)

outlook_account = connected_accounts[1]
outlook_account_id = outlook_account.id

# List of Outlook actions to try
actions_to_try = [
    (Action.OUTLOOK_GET_EMAILS, "GET_EMAILS"),
    (Action.OUTLOOK_GET_ALL_EMAILS, "GET_ALL_EMAILS"),
    (Action.OUTLOOK_LIST_MESSAGES, "LIST_MESSAGES"),
    (Action.OUTLOOK_GET_MESSAGES, "GET_MESSAGES"),
    (Action.OUTLOOK_FETCH_EMAILS, "FETCH_EMAILS"),
    (Action.OUTLOOK_SEARCH_EMAILS, "SEARCH_EMAILS"),
]

print(f"\nTesting Outlook actions with account {outlook_account_id}...")
print("=" * 70)

for action, name in actions_to_try:
    try:
        print(f"\nTesting {name}...")
        result = composio.actions.execute(
            action=action,
            params={"max_results": 5},
            connected_account=outlook_account_id
        )
        
        status = "SUCCESS" if result.get("successful") or result.get("status") == "success" else "FAILED"
        print(f"  Status: {status}")
        if result.get("error"):
            print(f"  Error: {result.get('error')}")
        elif result.get("message"):
            print(f"  Message: {result.get('message')}")
        print(f"  Full result keys: {list(result.keys())}")
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"  ERROR: {error_type}: {error_msg}")
