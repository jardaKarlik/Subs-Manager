#!/usr/bin/env python3
"""
Test Outlook connection via Composio and fetch 10 messages
"""

import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

API_BASE = "https://backend.composio.dev/api/v1"

def get_headers():
    """Get API headers with key"""
    api_key = os.getenv('COMPOSIO_API_KEY')
    return {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }

def test_outlook_connection():
    """Test Outlook connection via Composio"""
    print("=== Outlook Connection Test via Composio ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    try:
        # Get connected accounts
        print("🔍 Fetching connected accounts...")
        response = requests.get(
            f"{API_BASE}/connectedAccounts",
            headers=get_headers()
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get accounts: {response.status_code}")
            print(response.text)
            return False
        
        accounts = response.json()
        outlook_account = None
        
        for account in accounts:
            app_name = account.get('appName', '').lower()
            if app_name in ['outlook', 'microsoft']:
                outlook_account = account
                break
        
        if not outlook_account:
            print("❌ No Outlook/Microsoft account found in Composio connections")
            return False
        
        print(f"✅ Outlook account found!")
        print(f"   Connection ID: {outlook_account.get('id')}")
        print(f"   Status: {outlook_account.get('status')}")
        print(f"   Created: {outlook_account.get('createdAt')}")
        
        return outlook_account
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def fetch_outlook_emails(account, max_messages=10):
    """Fetch emails from Outlook via Composio"""
    connection_id = account.get('id')
    
    print(f"\n📧 Fetching up to {max_messages} emails from Outlook...")
    print("-" * 50)
    
    try:
        # Use Composio action to list messages
        # Common action: outlook_list_messages or similar
        action_response = requests.post(
            f"{API_BASE}/actions/execute",
            headers=get_headers(),
            json={
                "connectedAccountId": connection_id,
                "actionName": "outlook_list_messages",
                "input": {
                    "maxResults": max_messages
                }
            }
        )
        
        if action_response.status_code == 200:
            result = action_response.json()
            emails = result.get('data', []) if isinstance(result, dict) else result
            
            print(f"✅ Fetched {len(emails)} emails\n")
            
            for i, email in enumerate(emails, 1):
                subject = email.get('subject', 'No Subject')
                sender = email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')
                date = email.get('receivedDateTime', 'Unknown')
                
                print(f"{i}. Subject: {subject}")
                print(f"   From: {sender}")
                print(f"   Date: {date}")
                print("-" * 50)
            
            return True
        else:
            print(f"❌ Action failed: {action_response.status_code}")
            print(action_response.text)
            
            # Try alternative: list available actions
            print("\n🔍 Checking available Outlook actions...")
            actions_resp = requests.get(
                f"{API_BASE}/apps/microsoft_outlook/actions",
                headers=get_headers()
            )
            if actions_resp.status_code == 200:
                actions = actions_resp.json()
                print("Available actions:")
                for action in actions[:10]:
                    print(f"  - {action.get('name')}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Outlook via Composio")
    print("=" * 50)
    
    # Test connection
    account = test_outlook_connection()
    
    if account:
        # Fetch 10 emails
        success = fetch_outlook_emails(account, max_messages=10)
        
        print("\n" + "=" * 50)
        if success:
            print("✅ Outlook test completed successfully!")
        else:
            print("⚠️ Connection OK but couldn't fetch emails")
    else:
        print("\n" + "=" * 50)
        print("❌ Outlook not connected via Composio")
        print("\n💡 To connect Outlook:")
        print("  1. Go to https://app.composio.dev")
        print("  2. Add Microsoft Outlook integration")
        print("  3. Authorize your account")

if __name__ == "__main__":
    main()
