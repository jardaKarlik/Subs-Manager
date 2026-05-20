"""
Parse emails and export classification results to CSV for analysis.
Does NOT write to database - just classifies and logs.
"""

import asyncio
import csv
from datetime import datetime
from email_fetcher import EmailFetcher
from email_parser import EmailClassifier

async def main():
    print("📊 Export Email Classifications")
    print("=" * 60)
    
    fetcher = EmailFetcher()
    classifier = EmailClassifier()
    
    # Fetch emails (without processing to database)
    print("\n📧 Fetching emails...")
    gmail_emails = await fetcher.fetch_gmail(max_results=100, since_days=30)
    outlook_emails = await fetcher.fetch_outlook(max_results=100, since_days=30)
    
    all_emails = gmail_emails + outlook_emails
    
    print(f"✅ Fetched {len(gmail_emails)} emails from Gmail")
    print(f"✅ Fetched {len(outlook_emails)} emails from Outlook")
    print(f"✅ Total: {len(all_emails)} emails")
    
    # Classify each one
    print("\n🔍 Classifying emails...")
    classifications = []
    
    for i, email in enumerate(all_emails, 1):
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(all_emails)}")
        
        result = classifier.classify(
            email["subject"],
            email["sender"],
            email["body"]
        )
        
        classifications.append({
            "message_id": email["message_id"],
            "source": email["source"],
            "subject": email["subject"][:100],
            "sender": email["sender"],
            "is_subscription": result["is_subscription"],
            "confidence": result["confidence"],
            "service_name": result["service_name"],
            "category": result["category"],
            "cost": result["cost"],
            "currency": result["currency"],
            "billing_cycle": result["billing_cycle"],
            "plan_name": result.get("plan_name", ""),
            "reasons": ", ".join(result["reasons"][:3])
        })
    
    # Write to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"classifications_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=classifications[0].keys())
        writer.writeheader()
        writer.writerows(classifications)
    
    print(f"\n✅ Exported {len(classifications)} classifications to: {filename}")
    
    # Summary statistics
    total = len(classifications)
    subscriptions = sum(1 for c in classifications if c["is_subscription"])
    high_conf = sum(1 for c in classifications if c["confidence"] >= 0.50)
    medium_conf = sum(1 for c in classifications if 0.35 <= c["confidence"] < 0.50)
    low_conf = sum(1 for c in classifications if c["confidence"] < 0.35)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total emails: {total}")
    print(f"   Detected subscriptions: {subscriptions} ({subscriptions/total*100:.1f}%)")
    print(f"   Not subscriptions: {total - subscriptions} ({(total-subscriptions)/total*100:.1f}%)")
    print(f"\n   Confidence breakdown:")
    print(f"   - High (≥0.50): {high_conf}")
    print(f"   - Medium (0.35-0.49): {medium_conf}")
    print(f"   - Low (<0.35): {low_conf}")
    
    # Show top detected services
    if subscriptions > 0:
        print(f"\n📋 TOP DETECTED SERVICES:")
        services = {}
        for c in classifications:
            if c["is_subscription"]:
                name = c["service_name"]
                services[name] = services.get(name, 0) + 1
        
        for service, count in sorted(services.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   - {service}: {count} emails")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Open {filename} in Excel/Google Sheets")
    print(f"   2. Sort by 'confidence' descending")
    print(f"   3. Review false positives (is_subscription=TRUE but shouldn't be)")
    print(f"   4. Review false negatives (is_subscription=FALSE but should be)")
    print(f"   5. Adjust thresholds in email_parser.py if needed")

if __name__ == "__main__":
    asyncio.run(main())
