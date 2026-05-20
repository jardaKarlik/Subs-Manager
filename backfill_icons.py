from email_fetcher import _get_logo_url
import sqlite3

DB = 'subscriptions.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute("SELECT id, service_name FROM subscriptions WHERE icon_url IS NULL OR icon_url=''")
rows = c.fetchall()
print(f"Found {len(rows)} subscriptions without icon_url")
updated = 0
for _id, service_name in rows:
    if not service_name:
        continue
    url = _get_logo_url(service_name)
    if url:
        c.execute("UPDATE subscriptions SET icon_url=? WHERE id=?", (url, _id))
        updated += 1

conn.commit()
conn.close()
print(f"Updated {updated} subscriptions with icon_url")
