"""
BudgetBakers Wallet fetcher for Subscription Manager.
Fetches financial records via the Wallet REST API and stores them in
the financial_records table for cross-referencing against subscriptions.

Rate limit: 300 req/hr — ~0.083 req/sec safe ceiling.

PayPal dedup rule:
  When a subscription is paid via PayPal, Wallet records TWO transactions:
    1. expense_paypal_mirror  — from the PayPal account (intermediary)
    2. expense                — from the bank card (the real debit)
  We tag PayPal-account records as "expense_paypal_mirror" at ingest so
  the matcher and spend calculations can safely ignore them.
"""

import os
import re
import ssl
import json
import time
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

from database import FinancialRecord, AsyncSessionLocal
from dotenv import load_dotenv

load_dotenv()

WALLET_BASE  = os.getenv("WALLET_API_BASE",  "https://rest.budgetbakers.com/wallet")
WALLET_TOKEN = os.getenv("WALLET_API_TOKEN", "")

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode    = ssl.CERT_NONE


def _get(path: str, params: dict) -> dict:
    qs  = urllib.parse.urlencode(params, doseq=True)
    url = f"{WALLET_BASE}{path}?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {WALLET_TOKEN}"})
    with urllib.request.urlopen(req, context=_ssl_ctx, timeout=30) as resp:
        return json.loads(resp.read())


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _is_paypal_account(account_name: str) -> bool:
    return bool(re.search(r'paypal', account_name or '', re.I))


def _record_to_model(rec: dict, account_map: dict) -> FinancialRecord:
    """Convert raw Wallet API record dict to FinancialRecord ORM instance.

    Tags PayPal-intermediary records with record_type='expense_paypal_mirror'
    so spend calculations can exclude the double-counted amount.
    """
    account_id   = rec.get("accountId", "")
    account_name = account_map.get(account_id, "")
    record_type  = rec.get("recordType")   # "expense" / "income"

    # Tag PayPal mirror records — same payment, PayPal side
    if record_type == "expense" and _is_paypal_account(account_name):
        record_type = "expense_paypal_mirror"

    return FinancialRecord(
        id=rec["id"],
        date=_parse_dt(rec.get("recordDate")) or datetime.utcnow(),
        amount=rec.get("amount", {}).get("value", 0.0),
        currency=rec.get("amount", {}).get("currencyCode", "CZK"),
        payee=rec.get("counterParty") or "",
        category_id=rec.get("category", {}).get("id"),
        category_name=rec.get("category", {}).get("name"),
        account_id=account_id,
        account_name=account_name,
        note=rec.get("note") or "",
        labels=json.dumps(rec.get("labels", [])),
        record_type=record_type,
        matched_subscription_id=None,
        fetched_at=datetime.utcnow().isoformat(),
    )


class WalletFetcher:

    async def sync(self, since_days: int = 120) -> dict:
        since_date  = datetime.utcnow() - timedelta(days=since_days)
        print(f"[WalletFetcher] Syncing from {since_date.date()}")

        account_map = await asyncio.to_thread(self._fetch_account_map)
        print(f"[WalletFetcher] {len(account_map)} accounts")

        records = await asyncio.to_thread(self._fetch_all_records, since_date)
        print(f"[WalletFetcher] {len(records)} records fetched")

        if not records:
            return {"fetched": 0, "upserted": 0, "paypal_mirrors": 0,
                    "since_date": since_date.isoformat()}

        models   = [_record_to_model(r, account_map) for r in records]
        mirrors  = sum(1 for m in models if m.record_type == "expense_paypal_mirror")
        upserted = await self._upsert(models)

        print(f"[WalletFetcher] {upserted} upserted, {mirrors} PayPal mirrors tagged")
        return {
            "fetched":         len(records),
            "upserted":        upserted,
            "paypal_mirrors":  mirrors,
            "since_date":      since_date.isoformat(),
            "accounts":        len(account_map),
        }

    async def fetch_accounts(self) -> list[dict]:
        return await asyncio.to_thread(self._fetch_raw_accounts)

    def _fetch_raw_accounts(self) -> list[dict]:
        data = _get("/v1/api/accounts", {"limit": 50})
        return data.get("accounts", [])

    def _fetch_account_map(self) -> dict:
        accounts = self._fetch_raw_accounts()
        return {a["id"]: a.get("name", "") for a in accounts}

    def _fetch_all_records(self, since_date: datetime) -> list[dict]:
        all_records = []
        offset      = 0
        page_size   = 200
        since_str   = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        while True:
            params = {
                "recordDate": f"gte.{since_str}",
                "limit":      page_size,
                "offset":     offset,
            }
            data  = _get("/v1/api/records", params)
            batch = data.get("records", [])
            all_records.extend(batch)

            next_offset = data.get("nextOffset")
            if not next_offset or len(batch) < page_size:
                break

            offset = next_offset
            time.sleep(0.5)

        return all_records

    async def _upsert(self, models: list[FinancialRecord]) -> int:
        if not models:
            return 0

        upserted = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for m in models:
                    existing = await session.get(FinancialRecord, m.id)
                    if existing is None:
                        session.add(m)
                        upserted += 1
                    else:
                        existing.payee        = m.payee
                        existing.category_id  = m.category_id
                        existing.category_name= m.category_name
                        existing.note         = m.note
                        existing.labels       = m.labels
                        existing.record_type  = m.record_type   # re-tag on update
                        existing.fetched_at   = m.fetched_at
        return upserted
