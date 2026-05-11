#!/usr/bin/env python3
"""
Test Composio connection and discover available integrations
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_composio_connection():
    """Test Composio API connection and list integrations"""
    api_key = os.getenv('COMPOSIO_API_KEY')
    
    if not api_key or api_key == 'your_composio_api_key_here':
        print("❌ COMPOSIO_API_KEY not set in .env file")
        return False
    
    print(f"🔑 Using API key: {api_key[:8]}...")
    
    # Test API connection
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # Get user info to test connection
        print("🔍 Testing Composio API connection...")
        response = requests.get('https://backend.composio.dev/api/v1/connectedAccounts', headers=headers)
        
        if response.status_code == 200:
            print("✅ Composio API connection successful!")
            
            # List connected accounts
            accounts = response.json()
            print(f"\n📋 Connected Accounts ({len(accounts)}):")
            
            gmail_accounts = []
            outlook_accounts = []
            
            for account in accounts:
                app_name = account.get('appName', 'Unknown')
                connection_id = account.get('id', 'N/A')
                status = account.get('status', 'Unknown')
                
                print(f"  - {app_name}: {connection_id} (Status: {status})")
                
                if app_name.lower() == 'gmail':
                    gmail_accounts.append(account)
                elif app_name.lower() in ['outlook', 'microsoft']:
                    outlook_accounts.append(account)
            
            # Summary
            print(f"\n📊 Integration Summary:")
            print(f"  - Gmail accounts: {len(gmail_accounts)}")
            print(f"  - Outlook accounts: {len(outlook_accounts)}")
            
            if gmail_accounts:
                print(f"\n✅ Gmail Integration Ready:")
                for acc in gmail_accounts:
                    print(f"  - Connection ID: {acc.get('id')}")
            
            if outlook_accounts:
                print(f"\n✅ Outlook Integration Ready:")
                for acc in outlook_accounts:
                    print(f"  - Connection ID: {acc.get('id')}")
            else:
                print(f"\n⚠️  No Outlook integration found. You may need to connect Outlook in Composio dashboard.")
            
            return True
            
        else:
            print(f"❌ API connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Composio connection: {e}")
        return False

def get_available_apps():
    """Get list of available apps in Composio"""
    api_key = os.getenv('COMPOSIO_API_KEY')
    
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        print("\n🔍 Checking available integrations...")
        response = requests.get('https://backend.composio.dev/api/v1/apps', headers=headers)
        
        if response.status_code == 200:
            apps = response.json()
            
            # Look for email-related apps
            email_apps = []
            for app in apps:
                app_name = app.get('name', '').lower()
                if any(term in app_name for term in ['gmail', 'outlook', 'mail', 'microsoft']):
                    email_apps.append(app)
            
            print(f"📧 Available Email Integrations:")
            for app in email_apps:
                print(f"  - {app.get('name')}: {app.get('description', 'No description')}")
            
            return email_apps
        else:
            print(f"❌ Failed to get available apps: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting available apps: {e}")
        return []

def main():
    """Main test function"""
    print("🚀 Testing Composio Connection and Integrations")
    print("=" * 50)
    
    # Test connection and list integrations
    if test_composio_connection():
        # Get available apps
        get_available_apps()
        
        print("\n" + "=" * 50)
        print("✅ Composio connection test completed!")
        print("\n💡 Next steps:")
        print("  1. If Gmail is connected, you can start testing email parsing")
        print("  2. If Outlook is not connected, connect it in Composio dashboard")
        print("  3. Update your .env file with the correct email addresses")
    else:
        print("\n❌ Composio connection failed. Please check your API key.")

if __name__ == "__main__":
    main()