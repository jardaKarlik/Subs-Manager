"""
BudgetBakers Wallet fetcher for Subscription Manager.
Fetches financial records via the Wallet REST API and stores them in
the financial_records table for cross-referencing against subscriptions.

Rate limit: 300 req/hr — ~0.083 req/sec safe ceiling.
"""

import os
import ssl
import json
import time
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database import FinancialRecord, AsyncSessionLocal
from dotenv import load_dotenv

load_dotenv()

WALLET_BASE = os.getenv("WALLET_API_BASE", "https://rest.budgetbakers.com/wallet")
WALLET_TOKEN = os.getenv("WALLET_API_TOKEN", "")

# Build a reusable SSL context that skips revocation (same pattern as IMAP)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _get(path: str, params: dict) -> dict:
    """Synchronous GET to Wallet REST API with rate-limit awareness."""
    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{WALLET_BASE}{path}?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {WALLET_TOKEN}"})
    with urllib.request.urlopen(req, context=_ssl_ctx, timeout=30) as resp:
        return json.loads(resp.read())


def _parse_dt(s: str) -> Optional[datetime]:
    """Parse ISO-8601 datetime string to naive UTC datetime."""
    if not s:
        return None
    try:
        # Remove trailing Z, parse as UTC
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _record_to_model(rec: dict, account_map: dict) -> FinancialRecord:
    """Convert raw Wallet API record dict to FinancialRecord ORM instance."""
    account_id = rec.get("accountId", "")
    return FinancialRecord(
        id=rec["id"],
        date=_parse_dt(rec.get("recordDate")),
        amount=rec.get("amount", {}).get("value", 0.0),
        currency=rec.get("amount", {}).get("currencyCode", "CZK"),
        payee=rec.get("counterParty") or "",
        category_id=rec.get("category", {}).get("id"),
        category_name=rec.get("category", {}).get("name"),
        account_id=account_id,
        account_name=account_map.get(account_id, ""),
        note=rec.get("note") or "",
        labels=rec.get("labels", []),
        record_type=rec.get("recordType"),       # "expense" / "income"
        matched_subscription_id=None,
        fetched_at=datetime.utcnow(),
    )


class WalletFetcher:
    """Fetch financial records from BudgetBakers Wallet REST API."""

    # ── Public API ────────────────────────────────────────────────────────────

    async def sync(self, since_days: int = 120) -> dict:
        """
        Main entry point. Fetches all records since `since_days` ago,
        upserts into financial_records (dedup by id), returns stats.
        """
        since_date = datetime.utcnow() - timedelta(days=since_days)
        print(f"[WalletFetcher] Syncing records from {since_date.date()} to today")

        account_map = await asyncio.to_thread(self._fetch_account_map)
        print(f"[WalletFetcher] {len(account_map)} accounts loaded")

        records = await asyncio.to_thread(self._fetch_all_records, since_date)
        print(f"[WalletFetcher] {len(records)} records fetched from API")

        if not records:
            return {"fetched": 0, "upserted": 0, "since_date": since_date.isoformat()}

        models = [_record_to_model(r, account_map) for r in records]
        upserted = await self._upsert(models)

        print(f"[WalletFetcher] {upserted} records upserted into DB")
        return {
            "fetched": len(records),
            "upserted": upserted,
            "since_date": since_date.isoformat(),
            "accounts": len(account_map),
        }

    async def fetch_accounts(self) -> list[dict]:
        """Return raw account list from the API."""
        return await asyncio.to_thread(self._fetch_raw_accounts)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_raw_accounts(self) -> list[dict]:
        data = _get("/v1/api/accounts", {"limit": 50})
        return data.get("accounts", [])

    def _fetch_account_map(self) -> dict:
        """Return {account_id: account_name} for all accounts."""
        accounts = self._fetch_raw_accounts()
        return {a["id"]: a.get("name", "") for a in accounts}

    def _fetch_all_records(self, since_date: datetime) -> list[dict]:
        """
        Paginate through all records from since_date to now.
        Respects 300 req/hr rate limit (~0.08 req/sec → 0.5s sleep between pages).
        """
        all_records = []
        offset = 0
        page_size = 200
        since_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        while True:
            params = {
                "recordDate": f"gte.{since_str}",
                "limit": page_size,
                "offset": offset,
            }
            data = _get("/v1/api/records", params)
            batch = data.get("records", [])
            all_records.extend(batch)

            next_offset = data.get("nextOffset")
            if not next_offset or len(batch) < page_size:
                break

            offset = next_offset
            time.sleep(0.5)  # stay well within 300 req/hr

        return all_records

    async def _upsert(self, models: list[FinancialRecord]) -> int:
        """Upsert FinancialRecord rows — insert or ignore on duplicate id."""
        if not models:
            return 0

        upserted = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for m in models:
                    # Check if exists
                    existing = await session.get(FinancialRecord, m.id)
                    if existing is None:
                        session.add(m)
                        upserted += 1
                    else:
                        # Update mutable fields (payee may be categorized later)
                        existing.payee = m.payee
                        existing.category_id = m.category_id
                        existing.category_name = m.category_name
                        existing.note = m.note
                        existing.labels = m.labels
                        existing.fetched_at = m.fetched_at
        return upserted
