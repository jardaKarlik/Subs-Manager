#!/usr/bin/env python3
"""
Check what's available in Composio API for this account
"""
import os
import sys
import json
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

api_key = os.getenv("COMPOSIO_API_KEY")
if not api_key:
    print("Missing COMPOSIO_API_KEY")
    sys.exit(1)

# Try to get all apps and actions from Composio API
base_url = "https://backend.composio.dev/api/v1"

print("Checking Composio API endpoint...")
print("=" * 70)

try:
    # Try to get list of all apps
    print("\n1. Getting list of all apps...")
    response = requests.get(
        f"{base_url}/apps",
        headers={"Authorization": f"Bearer {api_key}"},
        verify=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        apps = response.json()
        print(f"Found {len(apps)} apps (or response structure: {list(apps.keys()) if isinstance(apps, dict) else 'list'})")
        if isinstance(apps, dict) and 'data' in apps:
            app_list = apps['data']
            outlook_apps = [a for a in app_list if 'outlook' in str(a).lower()]
            print(f"Outlook-related apps: {outlook_apps[:3]}")
    else:
        print(f"Error: {response.text[:200]}")
        
except Exception as e:
    print(f"Error: {e}")

# Try a direct connected accounts request
print("\n2. Getting connected accounts...")
try:
    response = requests.get(
        f"{base_url}/connectedAccounts",
        headers={"Authorization": f"Bearer {api_key}"},
        verify=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
        if isinstance(data, dict) and 'accounts' in data:
            for acc in data['accounts']:
                print(f"  - {acc.get('name', 'unknown')} (ID: {acc.get('id', 'unknown')})")
except Exception as e:
    print(f"Error: {e}")

# Try to get available actions for outlook
print("\n3. Getting Outlook actions...")
try:
    response = requests.get(
        f"{base_url}/apps/outlook/actions",
        headers={"Authorization": f"Bearer {api_key}"},
        verify=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
