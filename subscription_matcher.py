"""
subscription_matcher.py
Cross-reference BudgetBakers Wallet financial_records against subscriptions.

Key rules:
  1. PayPal dedup: PayPal payments always generate two records (PayPal + bank card).
     We keep only the bank card record. PayPal-sourced records are skipped in all
     spend calculations.
  2. Category filter: only records in subscription-relevant wallet categories
     (Software/apps, TV/streaming, Books/subscriptions, Internet, Music, Hobbies)
     are considered for matching and spend calculations.
  3. Payee blocklist: empty payees and numeric-only / bank-account-number payees
     are never matched to a subscription.
  4. Flat fee identification: for each matched service, the flat fee is the MOST
     FREQUENT amount across all non-PayPal wallet records for that service.
     Everything else is variable/usage spend.
  5. Matching: fuzzy name match between subscription.service_name and
     financial_record.payee (case-insensitive, common word stripping).
"""

import re
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, Subscription, FinancialRecord

logger = logging.getLogger("matcher")

# BudgetBakers category names that contain subscription spend.
# Everything else (Rent, Groceries, Leasing, etc.) is excluded from all
# matching and spend calculations.
SUBSCRIPTION_CATEGORIES = {
    'software, apps, games',
    'tv, streaming',
    'books, audio, subscription',
    'internet',
    'music',
    'hobbies',
}

# Payee fragments that indicate a PayPal intermediary record — skip these
PAYPAL_PAYEE_PATTERNS = [
    r'\bpaypal\b',
    r'\bpp\b',
    r'paypal\s*czk',
    r'paypal\s*(se|inc|ltd)',
]
PAYPAL_ACCOUNT_PATTERNS = [
    r'paypal',
]

# Words to strip from payee names before fuzzy matching
STRIP_WORDS = {
    'ab', 'ag', 'as', 'bv', 'co', 'corp', 'gmbh', 'inc', 'llc', 'ltd',
    'limited', 'pbc', 'sa', 'sro', 'technologies', 'technology', 'services',
    'software', 'solutions', 'ireland', 'luxembourg', 'payments', 'international',
    'online', 'digital', 'media', 'group', 'europe', 'global',
}

# Extra aliases: if payee contains key → match to subscription service name
PAYEE_ALIASES = {
    'spotify':              'Spotify',
    'netflix':              'Netflix',
    # Both payees from Anthropic billing merge into one subscription row
    'anthropic':            'Anthropic',
    'claude.ai':            'Anthropic',
    'claude ai':            'Anthropic',
    'openai':               'OpenAI',
    'github':               'GitHub',
    'microsoft':            'Microsoft',
    'google':               'Google',
    'apple':                'Apple',
    'adobe':                'Adobe',
    'figma':                'Figma',
    'notion':               'Notion',
    'vercel':               'Vercel',
    'digitalocean':         'DigitalOcean',
    'cloudflare':           'Cloudflare',
    'railway':              'Railway',
    'beatport':             'Beatport',
    'bandcamp':             'Bandcamp',
    'native instruments':   'Native Instruments',
    'patreon':              'Patreon',
    'cline':                'Cline',
    'openrouter':           'OpenRouter',
}

# Payee strings that must NEVER be matched to a subscription.
# Numeric-only = bank account / reference number.
# Empty = bank did not export a payee name.
_UNMATCHABLE_RE = re.compile(
    r'^$'
    r'|^[\d\s/\-\.]+$'
    r'|^\d{6,}/\d{4}$'
    r'|^\d{6,}$',
    re.IGNORECASE,
)


def _is_subscription_record(record: FinancialRecord) -> bool:
    """Return True only for records in subscription-relevant wallet categories."""
    cat = (record.category_name or '').strip().lower()
    if not cat:
        return False
    return cat in SUBSCRIPTION_CATEGORIES


def _is_paypal_record(record: FinancialRecord) -> bool:
    """Return True if this record is a PayPal intermediary (should be deduplicated)."""
    payee = (record.payee or '').lower()
    account = (record.account_name or '').lower()
    for pat in PAYPAL_PAYEE_PATTERNS:
        if re.search(pat, payee, re.I):
            return True
    for pat in PAYPAL_ACCOUNT_PATTERNS:
        if re.search(pat, account, re.I):
            return True
    return False


def _is_unmatchable_payee(payee: str) -> bool:
    """Return True if the payee string should never be matched to a subscription."""
    return bool(_UNMATCHABLE_RE.match((payee or '').strip()))


def _normalize_payee(payee: str) -> str:
    """Strip legal suffixes and punctuation for fuzzy matching."""
    s = payee.lower()
    s = re.sub(r'\b[A-Z0-9]{6,}\b', '', s)
    words = [w for w in re.split(r'[\s,;|]+', s) if w and w not in STRIP_WORDS]
    return ' '.join(words).strip()


def _match_payee_to_subscription(payee: str, subs: list) -> Optional[Subscription]:
    """
    Fuzzy match a payee string to a subscription.
    Priority: alias dict → substring match on normalized name.
    Rejects blank / numeric-only / bank-account-number payees immediately.
    """
    if _is_unmatchable_payee(payee):
        return None

    payee_lower = payee.lower()
    payee_norm  = _normalize_payee(payee)

    if not re.search(r'[a-z]', payee_norm):
        return None

    # 1. Alias table
    for alias, svc_name in PAYEE_ALIASES.items():
        if alias in payee_lower:
            for sub in subs:
                if sub.service_name.lower() == svc_name.lower():
                    return sub
            for sub in subs:
                if svc_name.lower() in sub.service_name.lower():
                    return sub

    # 2. Substring match — both sides must be at least 3 chars after normalization
    for sub in subs:
        sub_norm = _normalize_payee(sub.service_name)
        if sub_norm and len(sub_norm) >= 3 and len(payee_norm) >= 3:
            if sub_norm in payee_norm or payee_norm in sub_norm:
                return sub

    return None


class SubscriptionMatcher:
    """
    Match wallet financial records to subscriptions and compute spend analytics.
    Only records in subscription-relevant wallet categories are considered.
    """

    async def match_all(self) -> dict:
        """
        For every subscription-category, non-PayPal financial record,
        try to match it to a subscription.
        Updates financial_records.matched_subscription_id.
        Also updates subscription.confirmed_by_wallet, last_payment_date, actual_cost.
        """
        matched      = 0
        skipped      = 0
        paypal_skip  = 0
        filtered     = 0

        async with AsyncSessionLocal() as db:
            sub_result = await db.execute(select(Subscription))
            subs = sub_result.scalars().all()

            rec_result = await db.execute(
                select(FinancialRecord).where(
                    FinancialRecord.record_type == 'expense',
                    FinancialRecord.matched_subscription_id == None,  # noqa
                )
            )
            records = rec_result.scalars().all()

            for rec in records:
                if _is_paypal_record(rec):
                    paypal_skip += 1
                    continue

                if not _is_subscription_record(rec):
                    filtered += 1
                    continue

                sub = _match_payee_to_subscription(rec.payee or '', subs)
                if sub:
                    rec.matched_subscription_id = sub.id
                    matched += 1
                else:
                    skipped += 1

            # Update subscription wallet fields for all matched subs
            matched_sub_ids = set()
            all_rec_result = await db.execute(
                select(FinancialRecord).where(
                    FinancialRecord.record_type == 'expense',
                    FinancialRecord.matched_subscription_id != None,  # noqa
                )
            )
            all_matched = all_rec_result.scalars().all()

            by_sub: dict = {}
            for rec in all_matched:
                if _is_paypal_record(rec):
                    continue
                sid = rec.matched_subscription_id
                by_sub.setdefault(sid, []).append(rec)

            for sub in subs:
                recs = by_sub.get(sub.id, [])
                if not recs:
                    continue
                matched_sub_ids.add(sub.id)
                last_date = max(r.date for r in recs if r.date)
                amounts   = [round(abs(r.amount), 2) for r in recs]
                flat_fee  = Counter(amounts).most_common(1)[0][0]
                lp_str    = (last_date.strftime('%Y-%m-%d')
                             if hasattr(last_date, 'strftime')
                             else str(last_date)[:10])
                # Use raw SQL UPDATE: the SQLAlchemy model declares
                # last_payment_date as TIMESTAMP WITHOUT TIME ZONE, but the
                # DB column is character varying and asyncpg will not auto-
                # coerce a 'YYYY-MM-DD' string into a TIMESTAMP param. Bypass
                # the ORM and pass the date as a string literal (same approach
                # as commit 41e9570).
                await db.execute(
                    text(
                        f"UPDATE subscriptions SET "
                        f"confirmed_by_wallet = 1, "
                        f"last_payment_date = '{lp_str}', "
                        f"actual_cost = {float(flat_fee)} "
                        f"WHERE id = {int(sub.id)}"
                    )
                )

            await db.commit()

        return {
            'matched':           matched,
            'skipped':           skipped,
            'paypal_skipped':    paypal_skip,
            'category_filtered': filtered,
            'confirmed_subs':    len(matched_sub_ids),
        }

    async def infer_billing_cycles(self) -> dict:
        """
        For matched subscriptions, infer billing cycle from payment frequency.
        """
        updated = 0

        async with AsyncSessionLocal() as db:
            sub_result = await db.execute(
                select(Subscription).where(Subscription.confirmed_by_wallet == 1)
            )
            subs = sub_result.scalars().all()

            for sub in subs:
                rec_result = await db.execute(
                    select(FinancialRecord.date)
                    .where(
                        FinancialRecord.matched_subscription_id == sub.id,
                        FinancialRecord.record_type == 'expense',
                    )
                    .order_by(FinancialRecord.date)
                )
                raw_dates = [r[0] for r in rec_result.all() if r[0]]
                dates = []
                for d in raw_dates:
                    if isinstance(d, str):
                        try:
                            dates.append(datetime.fromisoformat(d[:10]))
                        except ValueError:
                            pass
                    else:
                        dates.append(d)
                if len(dates) < 2:
                    continue

                gaps    = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                avg_gap = sum(gaps) / len(gaps)

                if avg_gap <= 10:
                    inferred = 'weekly'
                elif avg_gap <= 100:
                    inferred = 'monthly'
                elif avg_gap <= 200:
                    inferred = 'yearly'
                else:
                    inferred = 'yearly'

                if inferred != sub.billing_cycle:
                    sub.billing_cycle = inferred
                    updated += 1

            await db.commit()

        return {'billing_cycles_updated': updated}

    async def get_spend_breakdown(self, subscription_id: int) -> dict:
        """Return flat fee vs variable spend breakdown for a subscription."""
        async with AsyncSessionLocal() as db:
            rec_result = await db.execute(
                select(FinancialRecord).where(
                    FinancialRecord.matched_subscription_id == subscription_id,
                    FinancialRecord.record_type == 'expense',
                )
            )
            records = [r for r in rec_result.scalars().all() if not _is_paypal_record(r)]

        if not records:
            return {'flat_fee': 0, 'variable_total': 0, 'payments': []}

        amounts      = [round(abs(r.amount), 2) for r in records]
        freq         = Counter(amounts)
        flat_fee     = freq.most_common(1)[0][0]
        flat_count   = freq[flat_fee]
        variable_sum = sum(abs(r.amount) for r in records if round(abs(r.amount), 2) != flat_fee)
        total        = sum(abs(r.amount) for r in records)

        payments = sorted([
            {
                'date':     r.date.isoformat() if r.date else None,
                'amount':   round(abs(r.amount), 2),
                'currency': r.currency,
                'payee':    r.payee,
                'type':     'flat' if round(abs(r.amount), 2) == flat_fee else 'variable',
                'account':  r.account_name,
            }
            for r in records
        ], key=lambda x: x['date'] or '', reverse=True)

        return {
            'subscription_id': subscription_id,
            'flat_fee':        flat_fee,
            'flat_fee_count':  flat_count,
            'variable_total':  round(variable_sum, 2),
            'total_spend':     round(total, 2),
            'currency':        records[0].currency if records else 'CZK',
            'record_count':    len(records),
            'payments':        payments,
        }

    async def find_unmatched_recurring(self, min_occurrences: int = 2) -> list:
        """
        Find subscription-category wallet payees appearing >= min_occurrences
        times with no matched subscription.
        """
        async with AsyncSessionLocal() as db:
            rec_result = await db.execute(
                select(FinancialRecord).where(
                    FinancialRecord.record_type == 'expense',
                    FinancialRecord.matched_subscription_id == None,  # noqa
                )
            )
            records = [
                r for r in rec_result.scalars().all()
                if not _is_paypal_record(r) and _is_subscription_record(r)
            ]

        by_payee: dict = {}
        for rec in records:
            key = _normalize_payee(rec.payee or 'unknown')
            by_payee.setdefault(key, []).append(rec)

        candidates = []
        for payee_norm, recs in by_payee.items():
            if len(recs) < min_occurrences:
                continue
            amounts    = [round(abs(r.amount), 2) for r in recs]
            avg_amount = round(sum(amounts) / len(amounts), 2)
            score      = min(100, len(recs) * 20 + (50 if avg_amount > 0 else 0))
            candidates.append({
                'payee':       recs[0].payee,
                'payee_norm':  payee_norm,
                'occurrences': len(recs),
                'avg_amount':  avg_amount,
                'currency':    recs[0].currency,
                'score':       score,
                'last_seen':   max(r.date for r in recs if r.date).isoformat()
                               if any(r.date for r in recs) else None,
            })

        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates

    async def promote_candidate(self, payee: str, service_name: str, category: str = 'other') -> dict:
        """Promote an unmatched recurring payee to a confirmed subscription."""
        async with AsyncSessionLocal() as db:
            rec_result = await db.execute(
                select(FinancialRecord).where(
                    FinancialRecord.record_type == 'expense',
                    FinancialRecord.matched_subscription_id == None,  # noqa
                )
            )
            records = [
                r for r in rec_result.scalars().all()
                if not _is_paypal_record(r)
                and _normalize_payee(r.payee or '') == _normalize_payee(payee)
            ]

            if not records:
                return {'error': f'No unmatched records found for payee: {payee}'}

            amounts  = [round(abs(r.amount), 2) for r in records]
            flat_fee = Counter(amounts).most_common(1)[0][0]
            last_pay = max(r.date for r in records if r.date)
            lp_str   = (last_pay.strftime('%Y-%m-%d')
                        if hasattr(last_pay, 'strftime') else str(last_pay)[:10])

            new_sub = Subscription(
                service_name=service_name,
                category=category,
                cost=flat_fee,
                currency=records[0].currency,
                billing_cycle='monthly',
                status='active',
                source='wallet_discovery',
                confirmed_by_wallet=1,
                last_payment_date=lp_str,
                actual_cost=flat_fee,
                approval_status='approved',
                start_date=min(r.date for r in records if r.date).strftime('%Y-%m-%d'),
            )
            db.add(new_sub)
            await db.flush()

            for rec in records:
                rec.matched_subscription_id = new_sub.id

            await db.commit()

        return {
            'created_subscription_id': new_sub.id,
            'service_name':            service_name,
            'records_matched':         len(records),
            'flat_fee':                flat_fee,
        }
