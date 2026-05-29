"""
Subscription cross-reference engine.
Includes discovery mode: scores unmatched recurring wallet payees by
subscription likelihood so genuine new subs bubble to the top.

Links financial_records to subscriptions via payee name normalization + fuzzy matching.
Updates confirmed_by_wallet, last_payment_date, actual_cost on matched subscriptions.
Also identifies unmatched recurring wallet transactions as new subscription candidates.
"""

import re
import math
from datetime import datetime
from collections import defaultdict
from typing import Optional

from sqlalchemy import select, update, func
from database import FinancialRecord, Subscription, AsyncSessionLocal

# ── Payee normalization ───────────────────────────────────────────────────────

# Strip these prefixes from payee strings before matching
_STRIP_PREFIXES = [
    r"^paypal\s*\*\s*",        # PAYPAL *NETFLIX COM
    r"^paypal[-_][a-z]+@",     # paypal-se@spotify.com  → extract domain
    r"^paypal@",               # paypal@beatport.com
    r"^paymentsadmin\+.*@",    # paymentsadmin+ppmid3@patreon.com
    r"^payment@",              # payment@native-instruments.de
    r"^[a-z0-9._+-]+@",       # any remaining email prefix  → domain part used below
]

# Known payee fragments → canonical service name
# Order matters: more specific first
_ALIASES: list[tuple[str, str]] = [
    # Microsoft family
    ("piemeur3",           "microsoft"),
    ("microsoft",          "microsoft"),
    # Google family
    ("gpil-pl",            "google"),
    ("google",             "google"),
    ("youtube",            "youtube"),
    ("stadia",             "google"),
    # Apple / iCloud
    ("apple",              "apple"),
    ("icloud",             "apple"),
    # Sony / PlayStation
    ("siee.psn",           "playstation"),
    ("playstation",        "playstation"),
    ("psn",                "playstation"),
    ("sony",               "playstation"),
    # Meta / Facebook
    ("fb.com",             "facebook"),
    ("facebook",           "facebook"),
    ("meta",               "facebook"),
    # Anthropic / Claude
    ("anthropic",          "anthropic"),
    ("claude",             "claude"),
    # Music / audio
    ("spotify",            "spotify"),
    ("beatport",           "beatport"),
    ("mixcloud",           "mixcloud"),
    ("last.fm",            "last.fm"),
    ("lastfm",             "last.fm"),
    ("last fm",            "last.fm"),
    ("native-instruments", "native instruments"),
    ("native inst",        "native instruments"),
    ("patreon",            "patreon"),
    # Gaming
    ("steamgames",         "steam"),
    ("steam",              "steam"),
    ("epicgames",          "epic games"),
    ("epic",               "epic games"),
    ("xbox",               "xbox"),
    ("nintendo",           "nintendo"),
    # Video
    ("netflix",            "netflix"),
    ("disney",             "disney+"),
    ("hulu",               "hulu"),
    ("hbo",                "hbo"),
    # Productivity / dev
    ("github",             "github"),
    ("slack",              "slack"),
    ("notion",             "notion"),
    ("figma",              "figma"),
    ("adobe",              "adobe"),
    ("canva",              "canva"),
    ("dropbox",            "dropbox"),
    ("zoom",               "zoom"),
    # Web / hosting
    ("wix",                "wix"),
    ("cloudflare",         "cloudflare"),
    ("namecheap",          "namecheap"),
    ("godaddy",            "godaddy"),
    ("vercel",             "vercel"),
    ("heroku",             "heroku"),
    # AI
    ("openai",             "openai"),
    ("midjourney",         "midjourney"),
    ("composio",           "composio"),
    # Other
    ("linkedin",           "linkedin"),
    ("twitter",            "twitter"),
    ("amazon",             "amazon"),
    ("aws",                "amazon web services"),
    ("paypal",             "paypal"),
    ("wfp",                "wfp"),           # charity — useful to keep for filtering
]


def _normalize_payee(raw: str) -> str:
    """
    Collapse a raw payee string to a lowercase service name.
    e.g. "PAYPAL *NETFLIX COM" -> "netflix"
         "paypal-se@spotify.com" -> "spotify"
         "PIEMEUR3@microsoft.com" -> "microsoft"
    """
    s = raw.lower().strip()

    # If it looks like an email, try the domain first
    if "@" in s:
        domain = s.split("@")[-1]                 # "spotify.com" / "native-instruments.de"
        domain_core = domain.split(".")[0]         # "spotify" / "native-instruments"
        # Check alias table with domain
        for fragment, canonical in _ALIASES:
            if fragment in domain or fragment in domain_core:
                return canonical
        # fall through with domain_core as the string
        s = domain_core

    # Strip PAYPAL * and similar prefixes
    for pat in _STRIP_PREFIXES:
        s = re.sub(pat, "", s)

    # Remove trailing noise: ".com", "ltd", "s.r.o.", numbers, extra spaces
    s = re.sub(r"\.(com|eu|de|cz|net|org|io)\b", "", s)
    s = re.sub(r"\b(ltd|llc|gmbh|s\.r\.o\.|a\.s\.|inc|plc)\b", "", s)
    s = re.sub(r"\s+\d+$", "", s)   # trailing numbers "STORE 4259522"
    s = s.strip()

    # Alias lookup on cleaned string
    for fragment, canonical in _ALIASES:
        if fragment in s:
            return canonical

    return s


def _normalize_service(name: str) -> str:
    """Normalize a subscription service_name for comparison."""
    s = name.lower().strip()
    s = re.sub(r"\b(plus|pro|premium|demo|test|subscription|sub)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Alias lookup
    for fragment, canonical in _ALIASES:
        if fragment in s:
            return canonical
    return s


def _names_match(payee_norm: str, service_norm: str) -> bool:
    """True if the normalized strings refer to the same service."""
    if not payee_norm or not service_norm:
        return False
    # Exact
    if payee_norm == service_norm:
        return True
    # One contains the other (min 4 chars to avoid false positives)
    if len(payee_norm) >= 4 and payee_norm in service_norm:
        return True
    if len(service_norm) >= 4 and service_norm in payee_norm:
        return True
    return False


# ── Subscription likelihood scoring ──────────────────────────────────────────

# Payee fragments that almost certainly mean NOT a subscription
_NOISE_FRAGMENTS = [
    "lidl", "kaufland", "tesco", "albert", "globus", "penny", "makro", "rohlik",
    "super zoo", "bauhaus", "dm drog", "tk maxx", "alza",
    "mcdonald", "kfc", "bageterie", "wolt", "pizza", "restaurace", "kebab",
    "burger", "siciliana", "chlebomat", "delikomat", "eldorado",
    "orlen", "petrol", "cs petrol", "fuel",
    "air bank", "airbank", "ceska spor", "csob", "splat",
    "rewe", "franken", "kammersteiner",
    "skolni jidelna", "jidelna",
    "adam karl", "tomas kold", "jaroslava",
]

# Payee fragments that strongly suggest a digital subscription
_SUB_SIGNALS = [
    "paypal *", "paypal-", "paypal@",
    "spotify", "netflix", "mixcloud", "beatport", "soundcloud", "lastfm", "last.fm",
    "steam", "roblox", "epic", "playstation", "xbox", "nintendo",
    "anthropic", "claude", "openai", "midjourney",
    "microsoft", "adobe", "google", "apple", "amazon",
    "github", "slack", "notion", "figma", "canva", "dropbox", "zoom",
    "wix", "vercel", "heroku", "cloudflare",
    "patreon", "substack", "ifttt", "zapier",
    "loopmasters", "splice", "plugin",
    "subscription", ".com", "pro ", " ltd", "limited",
]


def _score_subscription_likelihood(
    payee: str,
    occurrences: int,
    avg_amount: float,
    min_amount: float,
    max_amount: float,
) -> tuple[int, list[str]]:
    """
    Score a recurring wallet payee on a 0-100 scale for subscription likelihood.
    Returns (score, list_of_signal_strings).
    """
    score = 0
    signals = []
    p = payee.lower()

    # Hard disqualify: known non-sub noise
    for noise in _NOISE_FRAGMENTS:
        if noise in p:
            return 0, [f"noise:{noise}"]

    # Numeric-only payees (bank account numbers) → noise
    if re.match(r"^[\d\s/.-]+$", payee.strip()):
        return 0, ["noise:bank_account_number"]

    # Amount consistency — subscriptions charge the same amount each time
    if avg_amount > 0:
        variance_pct = (max_amount - min_amount) / avg_amount * 100
        if variance_pct <= 5:
            score += 35
            signals.append("amount:very_consistent")
        elif variance_pct <= 15:
            score += 20
            signals.append("amount:mostly_consistent")
        elif variance_pct <= 30:
            score += 8
            signals.append("amount:slightly_variable")
        else:
            signals.append("amount:variable")

    # Reasonable subscription price range (5–5000 CZK / 1–200 USD/EUR)
    if 5 <= avg_amount <= 5000:
        score += 10
        signals.append("price:in_range")

    # Known sub signals in payee name
    for sig in _SUB_SIGNALS:
        if sig in p:
            score += 25
            signals.append(f"keyword:{sig.strip()}")
            break  # only score once

    # Occurrence bonus (more = more confident it's recurring)
    if occurrences >= 4:
        score += 15
        signals.append(f"recurrence:{occurrences}x")
    elif occurrences >= 3:
        score += 8
        signals.append(f"recurrence:{occurrences}x")
    else:
        score += 3
        signals.append(f"recurrence:{occurrences}x")

    return min(score, 100), signals


# ── Main matcher ──────────────────────────────────────────────────────────────

class SubscriptionMatcher:

    async def match_all(self) -> dict:
        """
        For every unmatched FinancialRecord (expense, payee not empty):
          1. Normalize payee
          2. Match against all subscriptions
          3. Update matched_subscription_id on the record
          4. Update confirmed_by_wallet, last_payment_date, actual_cost on the sub

        Returns stats dict.
        """
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Load all subs once
                subs_result = await session.execute(select(Subscription))
                subs = subs_result.scalars().all()
                sub_map = {s.id: (_normalize_service(s.service_name), s) for s in subs}

                # Load unmatched expense records
                recs_result = await session.execute(
                    select(FinancialRecord).where(
                        FinancialRecord.matched_subscription_id == None,  # noqa: E711
                        FinancialRecord.record_type == "expense",
                        FinancialRecord.payee != "",
                    )
                )
                records = recs_result.scalars().all()

                matched = 0
                unmatched_payees: set[str] = set()

                for rec in records:
                    payee_norm = _normalize_payee(rec.payee)
                    best_sub = None

                    for sub_id, (service_norm, sub) in sub_map.items():
                        if _names_match(payee_norm, service_norm):
                            best_sub = sub
                            break

                    if best_sub:
                        rec.matched_subscription_id = best_sub.id
                        matched += 1

                        # Update sub's wallet confirmation fields
                        best_sub.confirmed_by_wallet = True
                        if rec.date and (
                            best_sub.last_payment_date is None
                            or rec.date > best_sub.last_payment_date
                        ):
                            best_sub.last_payment_date = rec.date
                        # actual_cost: use most recent payment amount (absolute value)
                        if rec.amount and (best_sub.actual_cost is None):
                            best_sub.actual_cost = abs(rec.amount)
                    else:
                        unmatched_payees.add(rec.payee)

        return {
            "records_processed": len(records),
            "matched": matched,
            "unmatched": len(records) - matched,
            "unmatched_payees_sample": sorted(unmatched_payees)[:20],
        }

    async def infer_billing_cycles(self) -> dict:
        """
        For each subscription with matched wallet records, infer billing cycle
        from the gaps between payment dates. Updates billing_cycle if confident.
        """
        updated = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Get subs that have matched records
                result = await session.execute(
                    select(FinancialRecord.matched_subscription_id, FinancialRecord.date)
                    .where(FinancialRecord.matched_subscription_id != None)  # noqa: E711
                    .order_by(FinancialRecord.matched_subscription_id, FinancialRecord.date)
                )
                rows = result.all()

                # Group dates by subscription
                by_sub: dict[int, list[datetime]] = defaultdict(list)
                for sub_id, dt in rows:
                    if dt:
                        by_sub[sub_id].append(dt)

                for sub_id, dates in by_sub.items():
                    if len(dates) < 2:
                        continue
                    dates.sort()
                    gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                    avg_gap = sum(gaps) / len(gaps)

                    if avg_gap <= 10:
                        cycle = "weekly"
                    elif avg_gap <= 35:
                        cycle = "monthly"
                    elif avg_gap <= 100:
                        cycle = "quarterly"
                    elif avg_gap <= 400:
                        cycle = "yearly"
                    else:
                        continue  # not confident enough

                    sub = await session.get(Subscription, sub_id)
                    if sub and sub.billing_cycle != cycle:
                        sub.billing_cycle = cycle
                        updated += 1

        return {"billing_cycles_updated": updated}

    async def find_unmatched_recurring(self, min_occurrences: int = 2) -> list[dict]:
        """
        Return wallet payees that appear multiple times as expenses
        but have no matched subscription — candidates for new sub discovery.
        Each result is scored for subscription likelihood (0-100).
        Results sorted by score descending so real subs surface first.
        """
        async with AsyncSessionLocal() as session:
            # Get aggregate stats per payee
            agg_result = await session.execute(
                select(
                    FinancialRecord.payee,
                    FinancialRecord.currency,
                    func.count(FinancialRecord.id).label("count"),
                    func.avg(FinancialRecord.amount).label("avg_amount"),
                    func.min(FinancialRecord.amount).label("min_amount"),
                    func.max(FinancialRecord.amount).label("max_amount"),
                    func.max(FinancialRecord.date).label("last_seen"),
                    func.min(FinancialRecord.date).label("first_seen"),
                )
                .where(
                    FinancialRecord.matched_subscription_id == None,  # noqa: E711
                    FinancialRecord.record_type == "expense",
                    FinancialRecord.payee != "",
                )
                .group_by(FinancialRecord.payee, FinancialRecord.currency)
                .having(func.count(FinancialRecord.id) >= min_occurrences)
            )
            rows = agg_result.all()

        candidates = []
        for r in rows:
            avg = abs(r.avg_amount or 0)
            min_a = abs(r.min_amount or 0)
            max_a = abs(r.max_amount or 0)
            score, signals = _score_subscription_likelihood(
                payee=r.payee,
                occurrences=r.count,
                avg_amount=avg,
                min_amount=min_a,
                max_amount=max_a,
            )
            candidates.append({
                "payee": r.payee,
                "normalized": _normalize_payee(r.payee),
                "occurrences": r.count,
                "avg_amount": round(avg, 2),
                "currency": r.currency,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
                "first_seen": r.first_seen.isoformat() if r.first_seen else None,
                "score": score,
                "signals": signals,
            })

        # Sort by score desc, then occurrences desc
        candidates.sort(key=lambda x: (-x["score"], -x["occurrences"]))
        return candidates

    async def promote_candidate(self, payee: str, service_name: str, category: str = "other") -> dict:
        """
        Promote a wallet payee to a subscription entry.
        Creates the sub, then re-runs match_all so its records get linked.
        """
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Find the financial records for this payee to get cost/currency
                recs_result = await session.execute(
                    select(FinancialRecord)
                    .where(
                        FinancialRecord.payee == payee,
                        FinancialRecord.record_type == "expense",
                    )
                    .order_by(FinancialRecord.date.desc())
                    .limit(5)
                )
                recs = recs_result.scalars().all()
                if not recs:
                    return {"error": "No wallet records found for this payee"}

                avg_cost = round(abs(sum(r.amount for r in recs) / len(recs)), 2)
                currency = recs[0].currency
                last_date = recs[0].date

                new_sub = Subscription(
                    service_name=service_name,
                    category=category,
                    cost=avg_cost,
                    currency=currency,
                    billing_cycle="monthly",
                    status="active",
                    start_date=recs[-1].date.strftime("%Y-%m-%d") if recs[-1].date else None,
                    source="wallet_discovery",
                    confirmed_by_wallet=True,
                    last_payment_date=last_date,
                    actual_cost=avg_cost,
                )
                session.add(new_sub)

        # Re-run matching to link the records
        match_result = await self.match_all()
        return {
            "created": service_name,
            "avg_cost": avg_cost,
            "currency": currency,
            **match_result,
        }
