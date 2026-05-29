"""
Export email classifications using the enhanced parser.
Tests the new signup/OAuth detection logic.
Data saved to: classifications_enhanced_TIMESTAMP.csv
"""

import asyncio
import csv
from datetime import datetime
from pathlib import Path

from email_fetcher import EmailFetcher
from email_parser_enhanced import EmailClassifierEnhanced

async def main():
    print("📊 TESTING ENHANCED EMAIL CLASSIFIER")
    print("=" * 60)
    print("📂 Output: classifications_enhanced_TIMESTAMP.csv")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    fetcher = EmailFetcher()
    classifier = EmailClassifierEnhanced()
    
    # Fetch emails
    print("\n📧 Fetching emails...")
    gmail_emails = await fetcher.fetch_gmail(max_results=100, since_days=30)
    
    print(f"✅ Fetched {len(gmail_emails)} emails from Gmail")
    
    # Classify each one
    print("\n🔍 Classifying with enhanced parser...")
    classifications = []
    
    # Counters for statistics
    signup_count = 0
    oauth_count = 0
    payment_count = 0
    spam_count = 0
    
    for i, email in enumerate(gmail_emails, 1):
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(gmail_emails)}")
        
        result = classifier.classify(
            email["subject"],
            email["sender"],
            email["body"]
        )
        
        # Track source types
        if result["source_type"] == "account_creation":
            signup_count += 1
        elif result["source_type"] == "oauth_connection":
            oauth_count += 1
        elif result["source_type"] == "payment_receipt":
            payment_count += 1
        elif result["category"] == "spam":
            spam_count += 1
        
        classifications.append({
            "message_id": email["message_id"],
            "source": email["source"],
            "subject": email["subject"][:80],
            "sender": email["sender"][:50],
            "is_subscription": result["is_subscription"],
            "confidence": result["confidence"],
            "source_type": result["source_type"],
            "service_name": result["service_name"],
            "category": result["category"],
            "cost": result["cost"],
            "currency": result["currency"],
            "billing_cycle": result["billing_cycle"],
            "plan_name": result.get("plan_name", ""),
            "reasons": ", ".join(result["reasons"][:5])
        })
    
    # Write to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = output_dir / f"classifications_enhanced_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=classifications[0].keys())
        writer.writeheader()
        writer.writerows(classifications)
    
    print(f"\n✅ Exported {len(classifications)} classifications")
    
    # Summary statistics
    total = len(classifications)
    subscriptions = sum(1 for c in classifications if c["is_subscription"])
    high_conf = sum(1 for c in classifications if c["confidence"] >= 0.60)
    medium_conf = sum(1 for c in classifications if 0.40 <= c["confidence"] < 0.60)
    low_conf = sum(1 for c in classifications if 0.30 <= c["confidence"] < 0.40)
    rejected = total - subscriptions
    
    print("\n" + "=" * 60)
    print("📊 CLASSIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total emails: {total}")
    print(f"\n✅ Detected as subscriptions: {subscriptions} ({subscriptions/total*100:.1f}%)")
    print(f"   - Account creation: {signup_count}")
    print(f"   - OAuth connections: {oauth_count}")
    print(f"   - Payment receipts: {payment_count}")
    print(f"\n❌ Rejected: {rejected} ({rejected/total*100:.1f}%)")
    print(f"   - Sales spam: {spam_count}")
    print(f"   - Low confidence: {rejected - spam_count}")
    
    print(f"\n📈 Confidence breakdown:")
    print(f"   High (≥0.60):   {high_conf} emails")
    print(f"   Medium (0.40-0.59): {medium_conf} emails")
    print(f"   Low (0.30-0.39):    {low_conf} emails")
    print(f"   Below threshold:  {rejected} emails")
    
    # Show top detected services
    if subscriptions > 0:
        print(f"\n🏆 TOP DETECTED SERVICES:")
        services = {}
        for c in classifications:
            if c["is_subscription"]:
                name = c["service_name"]
                services[name] = services.get(name, 0) + 1
        
        for service, count in sorted(services.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {service}: {count} emails")
    
    # Show detection by source type
    print(f"\n📋 DETECTION BY TYPE:")
    print(f"   Account creation: {signup_count}/{total} ({signup_count/total*100:.1f}%)")
    print(f"   OAuth connections: {oauth_count}/{total} ({oauth_count/total*100:.1f}%)")
    print(f"   Payment receipts: {payment_count}/{total} ({payment_count/total*100:.1f}%)")
    print(f"   Spam rejected: {spam_count}/{total} ({spam_count/total*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("📂 OUTPUT FILES:")
    print("=" * 60)
    print(f"📄 CSV: {csv_file}")
    
    print("\n💡 NEXT STEPS:")
    print("   1. Open the CSV in Excel/Google Sheets")
    print("   2. Sort by 'confidence' descending")
    print("   3. Review 'source_type' column:")
    print("      - account_creation: New signups detected")
    print("      - oauth_connection: Service authorizations")
    print("      - payment_receipt: Billing confirmations")
    print("   4. Check false positives (is_subscription=TRUE but shouldn't be)")
    print("   5. Check false negatives (is_subscription=FALSE but should be)")
    
    if subscriptions < total * 0.05:
        print("\n⚠️  WARNING: Very low detection rate (<5%)")
        print("   This might indicate:")
        print("   - No subscription emails in sample")
        print("   - Threshold too high")
        print("   - Keywords need tuning")

if __name__ == "__main__":
    asyncio.run(main())
