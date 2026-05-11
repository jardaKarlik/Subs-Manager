#!/usr/bin/env python3
"""
IMAP Connection Test Script for Subscription Manager
Tests the IMAP connection using the configuration from .env file
"""

import os
import imaplib
import ssl
from dotenv import load_dotenv
from datetime import datetime

def test_imap_connection():
    """Test IMAP connection with detailed logging"""
    
    # Load environment variables
    load_dotenv()
    
    # Get IMAP configuration
    imap_server = os.getenv('IMAP_SERVER')
    imap_port = int(os.getenv('IMAP_PORT', 993))
    imap_user = os.getenv('IMAP_USER')
    imap_password = os.getenv('IMAP_PASSWORD')
    
    print("=== IMAP Connection Test ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Server: {imap_server}")
    print(f"Port: {imap_port}")
    print(f"User: {imap_user}")
    print(f"Password: {'*' * len(imap_password) if imap_password else 'Not set'}")
    print("-" * 40)
    
    # Validate configuration
    if not all([imap_server, imap_user, imap_password]):
        print("❌ ERROR: Missing IMAP configuration!")
        print("Please check your .env file for:")
        print("- IMAP_SERVER")
        print("- IMAP_USER") 
        print("- IMAP_PASSWORD")
        return False
    
    try:
        print("🔄 Attempting to connect to IMAP server...")
        
        # Create SSL context with less strict verification
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Connect to IMAP server
        if imap_port == 993:
            # SSL connection
            mail = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
            print("✅ SSL connection established")
        else:
            # Non-SSL connection (usually port 143)
            mail = imaplib.IMAP4(imap_server, imap_port)
            print("✅ Connection established (non-SSL)")
        
        print("🔄 Attempting to login...")
        
        # Login
        mail.login(imap_user, imap_password)
        print("✅ Login successful!")
        
        # Get server capabilities
        print("\n📋 Server capabilities:")
        capabilities = mail.capabilities
        for cap in sorted(capabilities):
            print(f"  - {cap.decode() if isinstance(cap, bytes) else cap}")
        
        # List mailboxes
        print("\n📁 Available mailboxes:")
        status, mailboxes = mail.list()
        if status == 'OK':
            for mailbox in mailboxes[:10]:  # Show first 10 mailboxes
                mailbox_info = mailbox.decode() if isinstance(mailbox, bytes) else str(mailbox)
                print(f"  - {mailbox_info}")
            if len(mailboxes) > 10:
                print(f"  ... and {len(mailboxes) - 10} more mailboxes")
        
        # Select INBOX and get message count
        print("\n📧 INBOX information:")
        status, messages = mail.select('INBOX')
        if status == 'OK':
            message_count = int(messages[0])
            print(f"  - Total messages: {message_count}")
            
            # Get recent messages count
            status, recent = mail.recent()
            if status == 'OK':
                recent_count = int(recent[0]) if recent[0] else 0
                print(f"  - Recent messages: {recent_count}")
        
        # Test search functionality
        print("\n🔍 Testing search functionality...")
        status, message_ids = mail.search(None, 'ALL')
        if status == 'OK':
            ids = message_ids[0].split()
            print(f"  - Search successful: found {len(ids)} messages")
            
            # Fetch a sample message if available
            if ids:
                print("📄 Sample message header:")
                status, msg_data = mail.fetch(ids[-1], '(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])')
                if status == 'OK':
                    header = msg_data[0][1].decode('utf-8', errors='ignore')
                    print(f"  {header}")
        
        # Close connection
        mail.close()
        mail.logout()
        print("\n✅ Connection test completed successfully!")
        print("🔌 Connection closed gracefully")
        
        return True
        
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP Error: {e}")
        return False
    except ssl.SSLError as e:
        print(f"❌ SSL Error: {e}")
        print("💡 Try checking if the server supports SSL/TLS")
        return False
    except ConnectionRefusedError as e:
        print(f"❌ Connection Refused: {e}")
        print("💡 Check if the server and port are correct")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        return False

def test_imap_with_real_fetch():
    """Test IMAP connection with actual email fetching"""
    
    # Load environment variables
    load_dotenv()
    
    # Get IMAP configuration
    imap_server = os.getenv('IMAP_SERVER')
    imap_port = int(os.getenv('IMAP_PORT', 993))
    imap_user = os.getenv('IMAP_USER')
    imap_password = os.getenv('IMAP_PASSWORD')
    
    print("\n" + "=" * 50)
    print("=== REAL EMAIL FETCH TEST ===")
    print("=" * 50)
    
    try:
        # Connect and login with SSL context that ignores certificate issues
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        mail = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
        mail.login(imap_user, imap_password)
        
        # Select INBOX
        mail.select('INBOX')
        
        # Search for recent emails (last 30 days)
        print("🔍 Searching for recent emails...")
        status, message_ids = mail.search(None, 'SINCE "01-Oct-2024"')
        
        if status == 'OK':
            ids = message_ids[0].split()
            print(f"📧 Found {len(ids)} recent emails")
            
            # Fetch details of last 5 emails
            recent_ids = ids[-5:] if len(ids) >= 5 else ids
            
            print(f"\n📋 Details of last {len(recent_ids)} emails:")
            print("-" * 60)
            
            for i, msg_id in enumerate(recent_ids, 1):
                try:
                    # Fetch email headers and body
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status == 'OK':
                        import email
                        email_message = email.message_from_bytes(msg_data[0][1])
                        
                        subject = email_message.get('Subject', 'No Subject')
                        sender = email_message.get('From', 'Unknown Sender')
                        date = email_message.get('Date', 'Unknown Date')
                        
                        print(f"{i}. Email ID: {msg_id.decode()}")
                        print(f"   From: {sender}")
                        print(f"   Subject: {subject}")
                        print(f"   Date: {date}")
                        
                        # Get email body preview
                        body_preview = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    body_preview = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:100]
                                    break
                        else:
                            body_preview = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')[:100]
                        
                        if body_preview:
                            print(f"   Preview: {body_preview.replace(chr(10), ' ').replace(chr(13), ' ')}...")
                        
                        print("-" * 60)
                        
                except Exception as e:
                    print(f"   Error fetching email {msg_id}: {e}")
        
        # Close connection
        mail.close()
        mail.logout()
        print("✅ Real email fetch test completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during real email fetch: {e}")
        return False

if __name__ == "__main__":
    print("Starting IMAP connection tests...\n")
    
    # Test basic connection
    basic_success = test_imap_connection()
    
    if basic_success:
        # Test real email fetching
        fetch_success = test_imap_with_real_fetch()
        overall_success = basic_success and fetch_success
    else:
        print("\n❌ Basic connection test failed. Skipping email fetch test.")
        overall_success = False
    
    print(f"\n{'='*50}")
    if overall_success:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ TESTS FAILED!")
    print(f"{'='*50}")
