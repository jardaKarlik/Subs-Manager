#!/usr/bin/env python3
"""
Test script for Composio email integration.
Run this to verify Gmail and Outlook email fetching works correctly.
"""

import asyncio
import os
import ssl
import urllib3
from dotenv import load_dotenv

# Disable SSL verification warnings (local testing only)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkey-patch SSL to disable certificate verification for local testing
import ssl as ssl_module
ssl_module._create_default_https_context = ssl_module._create_unverified_context

from email_fetcher import EmailFetcher

load_dotenv()

async def test_email_fetcher():
    """Test the updated email fetcher with Composio."""
    fetcher = EmailFetcher()

    print("=" * 60)
    print("Testing Composio Email Integration")
    print("=" * 60)

    # Test Gmail
    print("\n[1] Testing Gmail Fetch...")
    print("-" * 60)
    gmail_emails = await fetcher.fetch_gmail(max_results=10, since_days=365)
    print(f"✓ Gmail: Retrieved {len(gmail_emails)} emails")
    if gmail_emails:
        print(f"  First email: {gmail_emails[0].get('subject', 'N/A')}")
        print(f"  Sender: {gmail_emails[0].get('sender', 'N/A')}")

    # Test Outlook
    print("\n[2] Testing Outlook Fetch...")
    print("-" * 60)
    outlook_emails = await fetcher.fetch_outlook(max_results=10, since_days=365)
    print(f"✓ Outlook: Retrieved {len(outlook_emails)} emails")
    if outlook_emails:
        print(f"  First email: {outlook_emails[0].get('subject', 'N/A')}")
        print(f"  Sender: {outlook_emails[0].get('sender', 'N/A')}")

    # Test IMAP
    print("\n[3] Testing IMAP Fetch...")
    print("-" * 60)
    imap_emails = await fetcher.fetch_imap(max_results=10, since_days=365)
    print(f"✓ IMAP: Retrieved {len(imap_emails)} emails")
    if imap_emails:
        print(f"  First email: {imap_emails[0].get('subject', 'N/A')}")
        print(f"  Sender: {imap_emails[0].get('sender', 'N/A')}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Gmail:   {len(gmail_emails)} emails")
    print(f"  Outlook: {len(outlook_emails)} emails")
    print(f"  IMAP:    {len(imap_emails)} emails")
    print(f"  Total:   {len(gmail_emails) + len(outlook_emails) + len(imap_emails)} emails")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_email_fetcher())
