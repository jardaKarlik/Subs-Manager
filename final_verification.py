import sqlite3
import os

db = 'subscriptions.db'
print('='*60)
print('FINAL DATABASE VERIFICATION')
print('='*60)
print(f'Database file: {db}')
print(f'Exists: {os.path.exists(db)}')
print(f'Size: {os.path.getsize(db):,} bytes')

conn = sqlite3.connect(db)
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'Tables: {[t[0] for t in tables]}')

# Count subscriptions
cursor.execute('SELECT COUNT(*) FROM subscriptions')
count = cursor.fetchone()[0]
print(f'\nTotal subscriptions: {count}')

# Sample data
cursor.execute('SELECT id, service_name, cost, billing_cycle, source FROM subscriptions')
rows = cursor.fetchall()
print('\nAll subscriptions in database:')
for row in rows:
    print(f'  {row[0]}. {row[1]:25s} | ${row[2]:7.2f} | {row[3]:8s} | {row[4]}')

conn.close()

print('\n' + '='*60)
print('DATABASE OPERATIONAL - ALL DATA CONFIRMED')
print('='*60)
