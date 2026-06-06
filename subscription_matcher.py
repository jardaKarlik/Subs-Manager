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

from database import AsyncSessionLocal, Subscription, FinancialRecord, ServiceCost, SubscriptionEvent, ProviderAlias

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

# Payee/account fragments that indicate a payment processor intermediary.
# These records represent the payment method, not the merchant — skip them
# to avoid attributing a Google Pay purchase to the "Google" subscription.
PAYMENT_PROCESSOR_PAYEE_PATTERNS = [
    # PayPal
    r'\bpaypal\b',
    r'\bpp\b',
    r'paypal\s*czk',
    r'paypal\s*(se|inc|ltd)',
    # Google Pay / Google as payment processor
    r'\bgoogle\s*pay\b',
    r'\bgpay\b',
    r'\bgoogle\s*payment',
]
PAYMENT_PROCESSOR_ACCOUNT_PATTERNS = [
    r'paypal',
    r'google\s*pay',
    r'gpay',
]

# Keep old names as aliases so existing call sites still work
PAYPAL_PAYEE_PATTERNS    = PAYMENT_PROCESSOR_PAYEE_PATTERNS
PAYPAL_ACCOUNT_PATTERNS  = PAYMENT_PROCESSOR_ACCOUNT_PATTERNS

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
    # Wallet-discovered subscriptions (promoted from wallet candidates)
    'disney plus':          'Disney Plus',
    'disneyplus':           'Disney Plus',
    'disney+':              'Disney Plus',
    'tv nova':              'TV Nova',
    'skyshowtime':          'SkyShowtime',
    'sky showtime':         'SkyShowtime',
    'ifttt':                'IFTTT',
    'roblox':               'Roblox',
    'loopmasters':          'Loopmasters',
    'steamgames':           'Steam',
    'steam purchase':       'Steam',
    'steam games':          'Steam',
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


def _is_payment_processor_record(record: FinancialRecord) -> bool:
    """Return True if this record is a payment processor intermediary (PayPal, Google Pay, etc.)."""
    payee = (record.payee or '').lower()
    account = (record.account_name or '').lower()
    for pat in PAYMENT_PROCESSOR_PAYEE_PATTERNS:
        if re.search(pat, payee, re.I):
            return True
    for pat in PAYMENT_PROCESSOR_ACCOUNT_PATTERNS:
        if re.search(pat, account, re.I):
            return True
    return False

# Backwards-compatible alias
_is_paypal_record = _is_payment_processor_record


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
                # NOTE: subscriptions iterated here were pre-filtered to
                # SUBSCRIPTION_CATEGORIES via the _is_subscription_record()
                # check on each FinancialRecord above.
                recon_flag = (
                    sub.cost and sub.cost > 0
                    and abs(sub.cost - float(flat_fee)) / sub.cost > 0.20
                )
                await db.execute(
                    text(
                        f"UPDATE subscriptions SET "
                        f"confirmed_by_wallet = 1, "
                        f"last_payment_date = '{lp_str}', "
                        f"actual_cost = {float(flat_fee)}, "
                        f"reconciliation_flag = {'TRUE' if recon_flag else 'FALSE'} "
                        f"WHERE id = {int(sub.id)}"
                    )
                )

            await db.commit()

        # Update rolling 3-month cost sums for all confirmed subs
        if matched_sub_ids:
            await self.update_service_costs(list(matched_sub_ids))

        return {
            'matched':           matched,
            'skipped':           skipped,
            'processor_skipped': paypal_skip,
            'category_filtered': filtered,
            'confirmed_subs':    len(matched_sub_ids),
        }

    async def detect_payment_type(self, subscription_id: int) -> dict:
        """
        Determine if a subscription is monthly or ad-hoc based on wallet payment frequency.
        
        Primary signal: recurrence of the same payment value in wallet records.
        If the same amount appears in >=50% of payments AND average gap is 25-35 days → monthly.
        Otherwise → adhoc. At this filtering level, there are no other variants.
        """
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, func
            rec_result = await db.execute(
                select(FinancialRecord).where(
                    FinancialRecord.matched_subscription_id == subscription_id,
                    FinancialRecord.record_type == 'expense',
                ).order_by(FinancialRecord.date)
            )
            records = [r for r in rec_result.scalars().all() if not _is_paypal_record(r)]

        if len(records) < 2:
            return {"payment_type": "unknown", "reason": "insufficient_data", "records": len(records)}

        from collections import Counter
        amounts = [round(abs(r.amount), 2) for r in records]
        most_common_amount, frequency = Counter(amounts).most_common(1)[0]
        recurrence_ratio = frequency / len(amounts)

        dates = sorted([r.date for r in records if r.date])
        if len(dates) >= 2:
            gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_gap = sum(gaps) / len(gaps)

            if recurrence_ratio >= 0.5 and 25 <= avg_gap <= 35:
                payment_type = "monthly"
                reason = f"same_amount_ratio={recurrence_ratio:.2f}, avg_gap={avg_gap:.0f}d"
            elif recurrence_ratio >= 0.5 and 350 <= avg_gap <= 380:
                payment_type = "yearly"
                reason = f"same_amount_ratio={recurrence_ratio:.2f}, avg_gap={avg_gap:.0f}d"
            else:
                payment_type = "adhoc"
                reason = f"recurrence_ratio={recurrence_ratio:.2f}, avg_gap={avg_gap:.0f}d"
        else:
            payment_type = "unknown"
            reason = "single_date_only"

        # Update the subscription's billing_cycle if different
        async with AsyncSessionLocal() as db:
            sub = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
            sub = sub.scalar_one_or_none()
            if sub and payment_type != "unknown" and payment_type != sub.billing_cycle:
                sub.billing_cycle = payment_type
                sub.updated_at = datetime.utcnow()
                await db.commit()

        return {
            "subscription_id": subscription_id,
            "payment_type": payment_type,
            "reason": reason,
            "flat_fee": most_common_amount,
            "frequency": frequency,
            "total_payments": len(records),
            "avg_gap_days": round(avg_gap, 1) if len(dates) >= 2 else None,
        }

    async def detect_all_payment_types(self) -> dict:
        """Run payment type detection for all wallet-confirmed subscriptions."""
        updated = 0
        async with AsyncSessionLocal() as db:
            subs = await db.execute(
                select(Subscription).where(Subscription.confirmed_by_wallet == 1)
            )
            for sub in subs.scalars().all():
                result = await self.detect_payment_type(sub.id)
                if result["payment_type"] != "unknown":
                    updated += 1
        return {"updated": updated}
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

            amounts   = [round(abs(r.amount), 2) for r in records]
            flat_fee  = Counter(amounts).most_common(1)[0][0]
            last_pay  = max(r.date for r in records if r.date)
            first_pay = min(r.date for r in records if r.date)
            # last_payment_date is TIMESTAMP — pass a datetime, not a string
            from datetime import datetime as _dt, date as _date
            def _to_datetime(d):
                if isinstance(d, _dt):
                    return d
                if isinstance(d, _date):
                    return _dt(d.year, d.month, d.day)
                return _dt.fromisoformat(str(d)[:10])

            new_sub = Subscription(
                service_name=service_name,
                category=category,
                cost=flat_fee,
                currency=records[0].currency,
                billing_cycle='monthly',
                status='active',
                source='wallet_discovery',
                confirmed_by_wallet=1,
                last_payment_date=_to_datetime(last_pay),
                actual_cost=flat_fee,
                approval_status='approved',
                start_date=_to_datetime(first_pay).strftime('%Y-%m-%d'),
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

    async def update_service_costs(self, subscription_ids: list = None) -> int:
        """
        Aggregate subscription_events by calendar month and upsert into service_costs.
        Covers the 3 most recent calendar months. Runs for all subs if subscription_ids is None.
        Returns the number of rows upserted.
        """
        from datetime import date, timedelta
        from calendar import monthrange

        today = date.today()
        # Build month boundaries for current month and 2 prior months
        months = []
        for offset in range(2, -1, -1):  # [2 months ago, 1 month ago, current]
            year = today.year
            month = today.month - offset
            while month <= 0:
                month += 12
                year -= 1
            first = date(year, month, 1)
            last_day = monthrange(year, month)[1]
            last = date(year, month, last_day)
            months.append((first, last))

        upserted = 0
        async with AsyncSessionLocal() as db:
            id_filter = (
                select(SubscriptionEvent)
                .where(SubscriptionEvent.subscription_id.in_(subscription_ids))
                if subscription_ids else select(SubscriptionEvent)
            )
            all_events_result = await db.execute(id_filter)
            all_events = all_events_result.scalars().all()

            # Group events by subscription_id
            by_sub: dict = {}
            for ev in all_events:
                by_sub.setdefault(ev.subscription_id, []).append(ev)

            for sub_id, events in by_sub.items():
                total_spent = round(sum(abs(ev.amount) for ev in events), 2)
                month_amounts = []
                for (first, last) in months:
                    month_sum = sum(
                        abs(ev.amount) for ev in events
                        if ev.event_date and first <= ev.event_date.date() <= last
                    )
                    month_amounts.append(round(month_sum, 2))

                currency = events[0].currency if events else "CZK"
                last_3_total = round(sum(month_amounts), 2)

                existing = await db.execute(
                    select(ServiceCost).where(ServiceCost.subscription_id == sub_id)
                )
                row = existing.scalar_one_or_none()
                if row:
                    row.total_spent = total_spent
                    row.month_1_amount = month_amounts[0]
                    row.month_2_amount = month_amounts[1]
                    row.month_3_amount = month_amounts[2]
                    row.last_3_months_total = last_3_total
                    row.currency = currency
                    row.last_updated = datetime.utcnow()
                else:
                    db.add(ServiceCost(
                        subscription_id=sub_id,
                        total_spent=total_spent,
                        month_1_amount=month_amounts[0],
                        month_2_amount=month_amounts[1],
                        month_3_amount=month_amounts[2],
                        last_3_months_total=last_3_total,
                        currency=currency,
                    ))
                upserted += 1

            await db.commit()
        return upserted

    async def seed_provider_aliases(self) -> int:
        """
        Seed the provider_aliases table from the hardcoded PROVIDER_ALIASES dict
        in email_parser.py. Skips entries that already exist. Returns count inserted.
        """
        from email_parser import PROVIDER_ALIASES
        inserted = 0
        async with AsyncSessionLocal() as db:
            for alias_key, (canonical, category) in PROVIDER_ALIASES.items():
                if canonical is None:
                    continue  # payment processors have no canonical name
                existing = await db.execute(
                    select(ProviderAlias).where(ProviderAlias.alias == alias_key)
                )
                if existing.scalar_one_or_none() is None:
                    db.add(ProviderAlias(
                        alias=alias_key,
                        canonical_name=canonical,
                        category=category,
                    ))
                    inserted += 1
            await db.commit()
        return inserted
