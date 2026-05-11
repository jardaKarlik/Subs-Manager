import os
import re
import asyncio
from composio import Composio
from db_manager import DBManager

# Assuming Composio is authenticated
composio = Composio()

# Simple regex heuristics for subscriptions
SUBSCRIPTION_KEYWORDS = ["subscription", "invoice", "receipt", "renewal", "payment", "your plan", "premium"]
SERVICE_REGEX = re.compile(r"(Netflix|Spotify|AWS|Google Cloud|Azure|Adobe|Apple|Microsoft|Github|OpenAI|Claude|DigitalOcean|Vercel)", re.IGNORECASE)
COST_REGEX = re.compile(r"(\$|€|£|USD|EUR|GBP)\s*(\d+[.,]\d+)")
CYCLE_REGEX = re.compile(r"(month|year|annual|monthly)", re.IGNORECASE)

class EmailParser:
    def __init__(self, db: DBManager):
        self.db = db

    def parse_and_store(self, message_id, subject, body, source_mailbox):
        if self.db.is_email_processed(message_id):
            return

        subject_lower = subject.lower() if subject else ""
        body_lower = body.lower() if body else ""

        is_sub = any(kw in subject_lower or kw in body_lower for kw in SUBSCRIPTION_KEYWORDS)
        if not is_sub:
            self.db.mark_email_processed(message_id, source_mailbox)
            return

        service_match = SERVICE_REGEX.search(subject_lower) or SERVICE_REGEX.search(body_lower)
        cost_match = COST_REGEX.search(subject_lower) or COST_REGEX.search(body_lower)
        cycle_match = CYCLE_REGEX.search(subject_lower) or CYCLE_REGEX.search(body_lower)

        service_name = service_match.group(1) if service_match else "Unknown Service"
        
        if cost_match:
            currency = cost_match.group(1)
            cost = float(cost_match.group(2).replace(',', '.'))
        else:
            currency = "USD"
            cost = 0.0

        billing_cycle = cycle_match.group(1).lower() if cycle_match else "unknown"
        if billing_cycle in ['month', 'monthly']:
            billing_cycle = 'monthly'
        elif billing_cycle in ['year', 'annual']:
            billing_cycle = 'yearly'

        if service_name != "Unknown Service" or cost > 0:
            print(f"Found subscription: {service_name} - {cost} {currency} ({billing_cycle})")
            self.db.add_subscription(
                service_name=service_name,
                cost=cost,
                currency=currency,
                billing_cycle=billing_cycle,
                notes=f"Found via {source_mailbox} email: {subject}",
                source=source_mailbox
            )

        self.db.mark_email_processed(message_id, source_mailbox)

def fetch_gmail(parser: EmailParser, session):
    try:
        # Assuming we can execute GMAIL_FETCH_EMAILS tool using Composio SDK
        # This is a mock API call structure based on Composio's execute tool
        response = composio.tools.execute(
            "GMAIL_FETCH_EMAILS",
            {"query": "subject:invoice OR subject:receipt OR subject:subscription"}
        )
        if response and "data" in response and "messages" in response["data"]:
            for msg in response["data"]["messages"]:
                msg_id = msg.get("id")
                subject = msg.get("subject", "")
                snippet = msg.get("snippet", "")
                parser.parse_and_store(msg_id, subject, snippet, "Gmail")
    except Exception as e:
        print(f"Error fetching Gmail: {e}")

def fetch_outlook(parser: EmailParser, session):
    try:
        response = composio.tools.execute(
            "OUTLOOK_SEARCH_MESSAGES",
            {"searchQuery": "invoice OR receipt OR subscription"}
        )
        if response and "data" in response and "value" in response["data"]:
            for msg in response["data"]["value"]:
                msg_id = msg.get("id")
                subject = msg.get("subject", "")
                snippet = msg.get("bodyPreview", "")
                parser.parse_and_store(msg_id, subject, snippet, "Outlook")
    except Exception as e:
        print(f"Error fetching Outlook: {e}")

import imaplib
import email
from email.header import decode_header

def fetch_generic_imap(parser: EmailParser):
    imap_host = os.getenv("IMAP_HOST")
    imap_user = os.getenv("IMAP_USER")
    imap_pass = os.getenv("IMAP_PASS")

    if not all([imap_host, imap_user, imap_pass]):
        print("Skipping IMAP fetch: IMAP credentials not set in environment.")
        return

    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_user, imap_pass)
        mail.select("inbox")

        # Search for subscription-related keywords
        # IMAP search strings format: (OR SUBJECT "invoice" SUBJECT "subscription")
        status, messages = mail.search(None, '(OR (OR SUBJECT "invoice" SUBJECT "receipt") SUBJECT "subscription")')
        
        if status == "OK" and messages[0]:
            msg_nums = messages[0].split()
            # To avoid parsing thousands of emails, limit to latest 50
            for num in msg_nums[-50:]:
                res, msg_data = mail.fetch(num, "(RFC822)")
                if res == "OK":
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Decode subject
                            subject = ""
                            if msg["Subject"]:
                                decoded_list = decode_header(msg["Subject"])
                                for text, charset in decoded_list:
                                    if isinstance(text, bytes):
                                        subject += text.decode(charset or 'utf-8', errors='ignore')
                                    else:
                                        subject += text
                                        
                            msg_id = msg.get("Message-ID", f"imap-{num.decode()}")
                            
                            # Get body
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    if content_type == "text/plain":
                                        try:
                                            body = part.get_payload(decode=True).decode(errors='ignore')
                                            break
                                        except:
                                            pass
                            else:
                                try:
                                    body = msg.get_payload(decode=True).decode(errors='ignore')
                                except:
                                    pass
                                    
                            parser.parse_and_store(msg_id, subject, body[:500], "Generic IMAP")
                            
        mail.logout()
    except Exception as e:
        print(f"Error fetching Generic IMAP: {e}")

def main():
    db = DBManager()
    parser = EmailParser(db)
    
    # Ideally, we get sessions or just execute tools if authenticated globally
    # If the user has multiple accounts, they might need multiple sessions.
    
    print("Fetching from Gmail...")
    fetch_gmail(parser, None)
    
    print("Fetching from Outlook...")
    fetch_outlook(parser, None)
    
    print("Fetching from Generic IMAP...")
    fetch_generic_imap(parser)
    
    subs = db.get_all_subscriptions()
    print(f"Total subscriptions found: {len(subs)}")
    for s in subs:
        print(f"- {s['service_name']}: {s['cost']} {s['currency']} ({s['billing_cycle']})")

if __name__ == "__main__":
    main()
