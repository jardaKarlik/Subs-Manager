#!/usr/bin/env python3
"""
List all available Outlook actions in Composio
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

from composio import Composio

api_key = os.getenv("COMPOSIO_API_KEY")
if not api_key:
    print("Missing COMPOSIO_API_KEY")
    sys.exit(1)

composio = Composio(api_key=api_key)

# Try to access actions directly
print("\nFetching Outlook actions from Composio...")
print("=" * 60)

try:
    # Try to get the raw client actions
    response = composio.client.http.get(
        url=f"{composio.client.base_url}/v1/apps/outlook/actions"
    )
    print("\nRaw response:")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying alternative approach...")
    
    # Let's try to manually check a few known Outlook action names
    test_actions = [
        "OUTLOOK_SEARCH_MESSAGES",
        "OUTLOOK_GET_MESSAGES",
        "OUTLOOK_FETCH_EMAILS",
        "OUTLOOK_LIST_MESSAGES",
        "OUTLOOK_GET_EMAILS",
        "OUTLOOK_GET_ALL_EMAILS",
        "OUTLOOK_SEARCH_EMAILS",
        "OUTLOOK_QUERY_EMAILS",
    ]
    
    from composio import Action
    print("\nTesting action names:")
    for action_name in test_actions:
        try:
            # Try to access the action
            action = getattr(Action, action_name, None)
            if action:
                print(f"  ✓ {action_name} - FOUND")
            else:
                print(f"  ✗ {action_name} - NOT FOUND")
        except Exception as e:
            print(f"  ✗ {action_name} - ERROR: {e}")
