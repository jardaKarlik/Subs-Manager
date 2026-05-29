"""
Query the experimental database to see results
"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "experimental_subscriptions.db"

if not db_path.exists():
    print("❌ Database not found!")
    exit(1)

print("=" * 60)
print("EXPERIMENTAL DATABASE RESULTS")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count rows
print("\n📊 TABLE COUNTS:")
print("-" * 60)

tables = ["subscriptions", "processed_emails", "subscription_events"]
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} rows")

# Show subscriptions
print("\n📋 DETECTED SUBSCRIPTIONS:")
print("-" * 60)

cursor.execute("""
    SELECT 
        id,
        service_name,
        cost,
        currency,
        billing_cycle,
        category,
        source,
        notes
    FROM subscriptions
    ORDER BY created_at DESC
""")

subscriptions = cursor.fetchall()
print(f"\nTotal: {len(subscriptions)} subscriptions detected\n")

for sub_id, service, cost, currency, cycle, category, source, notes in subscriptions:
    print(f"  {service}")
    print(f"    Cost: {cost} {currency} / {cycle}")
    print(f"    Category: {category}")
    print(f"    Source: {source}")
    print(f"    Notes: {notes}")
    print()

# Show processed emails sample
print("\n📧 PROCESSED EMAILS SAMPLE:")
print("-" * 60)

cursor.execute("""
    SELECT message_id, source, processed_date
    FROM processed_emails
    LIMIT 5
""")

emails = cursor.fetchall()
for msg_id, source, date in emails:
    print(f"  {source}: {msg_id}")
    print(f"    Date: {date}")

# Detection rate
cursor.execute("SELECT COUNT(*) FROM processed_emails")
total_emails = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM subscriptions")
total_subs = cursor.fetchone()[0]

detection_rate = (total_subs / total_emails * 100) if total_emails > 0 else 0

print("\n" + "=" * 60)
print("📈 DETECTION ANALYSIS")
print("=" * 60)
print(f"  Total emails processed: {total_emails}")
print(f"  Total subscriptions found: {total_subs}")
print(f"  Detection rate: {detection_rate:.1f}%")

if detection_rate >= 10:
    print(f"  ✅ EXCELLENT: >10% detection")
elif detection_rate >= 5:
    print(f"  ✅ GOOD: 5-10% detection")
elif detection_rate >= 2:
    print(f"  ⚠️  LOW: 2-5% detection")
else:
    print(f"  ❌ VERY LOW: <2% detection")

print("\n" + "=" * 60)

conn.close()
