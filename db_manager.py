import sqlite3
import json

class DBManager:
    def __init__(self, db_name="subscriptions.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            cost REAL,
            currency TEXT,
            billing_cycle TEXT,
            start_date TEXT,
            next_billing_date TEXT,
            notes TEXT,
            source TEXT
        )
        """
        self.conn.execute(query)
        
        # Raw emails table for tracking processed items to avoid duplicates
        query_emails = """
        CREATE TABLE IF NOT EXISTS processed_emails (
            message_id TEXT PRIMARY KEY,
            source TEXT,
            processed_date TEXT
        )
        """
        self.conn.execute(query_emails)
        self.conn.commit()

    def add_subscription(self, service_name, cost, currency, billing_cycle, start_date=None, next_billing_date=None, notes=None, source=None):
        query = """
        INSERT INTO subscriptions (service_name, cost, currency, billing_cycle, start_date, next_billing_date, notes, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.conn.execute(query, (service_name, cost, currency, billing_cycle, start_date, next_billing_date, notes, source))
        self.conn.commit()
        return cursor.lastrowid

    def is_email_processed(self, message_id):
        cursor = self.conn.execute("SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id,))
        return cursor.fetchone() is not None

    def mark_email_processed(self, message_id, source):
        import datetime
        date_str = datetime.datetime.now().isoformat()
        self.conn.execute("INSERT OR IGNORE INTO processed_emails (message_id, source, processed_date) VALUES (?, ?, ?)", (message_id, source, date_str))
        self.conn.commit()

    def get_all_subscriptions(self):
        cursor = self.conn.execute("SELECT * FROM subscriptions")
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
