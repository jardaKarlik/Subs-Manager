"""
Intelligent Email Parser - Dual-context classification engine
with weighted keyword decision model.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter

logger = logging.getLogger("email_parser")

# ═════════════════════════════════════════════
# GROUP A — Payment / Financial Confirmation Keywords
# ═════════════════════════════════════════════

GROUP_A_KEYWORDS = {
    "receipt": 0.40, "invoice": 0.40, "payment": 0.35,
    "purchas": 0.40, "billing": 0.35, "charge": 0.30,
    "paid": 0.35, "transaction": 0.25, "debit": 0.25,
    "withdrawal": 0.25, "automatic payment": 0.40,
    "recurring": 0.35, "you paid": 0.40, "payment to": 0.40,
    "payment from": 0.30, "charged to": 0.35,
    "payment confirmation": 0.40, "payment receipt": 0.40,
    "receipt for": 0.40, "invoice from": 0.40,
    "order confirmation": 0.30, "account statement": 0.20,
    "tax invoice": 0.40, "subscription payment": 0.40,
    "payment processed": 0.35, "payment received": 0.35,
    "confirmed": 0.20,
    # Czech
    "danovy doklad": 0.40, "faktura": 0.40, "platba": 0.35,
    "uhrada": 0.35, "zuctovani": 0.30, "odchozi platba": 0.40,
    "platba kartou": 0.40, "potvrzeni platby": 0.40,
    "zauctovani": 0.30, "castka": 0.20,
}

# ═════════════════════════════════════════════
# GROUP B — Account / Subscription Creation Keywords
# ═════════════════════════════════════════════

GROUP_B_KEYWORDS = {
    "welcome": 0.35, "welcome to": 0.40, "welcome aboard": 0.40,
    "your account": 0.35, "account created": 0.40,
    "account confirmed": 0.40, "account verified": 0.35,
    "account activated": 0.40, "verification complete": 0.35,
    "verified": 0.25, "registration": 0.35, "registered": 0.35,
    "sign up": 0.35, "signup": 0.35, "subscription": 0.30,
    "subscription confirmed": 0.40, "your subscription": 0.35,
    "your plan": 0.35, "plan activated": 0.40, "activated": 0.30,
    "activation": 0.25, "confirmation": 0.25, "get started": 0.30,
    "you re in": 0.30, "you re all set": 0.35,
    "thank you for joining": 0.40, "thank you for subscribing": 0.45,
    "thank you for signing up": 0.40, "thanks for joining": 0.35,
    "thanks for subscribing": 0.40, "thanks for signing up": 0.35,
    "new account": 0.35, "your new": 0.20, "service activated": 0.35,
    "membership": 0.25, "trial started": 0.25, "trial activated": 0.25,
    "premium activated": 0.35, "pro activated": 0.35,
    "registered for": 0.30, "you joined": 0.30, "welcome back": 0.20,
    # Czech
    "vitaj": 0.35, "vitejte": 0.35, "registrace": 0.35,
    "registrovan": 0.30, "ucet": 0.30, "predplatne": 0.35,
    "aktivace": 0.25, "potvrzeni registrace": 0.35,
    "profil": 0.15, "clenstvi": 0.25,
}

# ═════════════════════════════════════════════
# NEGATIVE — Marketing/Noise Keywords (applied to BOTH groups)
# ═════════════════════════════════════════════

NEGATIVE_KEYWORDS = {
    "offer": -0.30, "discount": -0.30, "sale": -0.25,
    "promo": -0.25, "promotion": -0.25, "coupon": -0.25,
    "newsletter": -0.40, "unsubscribe": -0.30,
    "weekly digest": -0.40, "weekly update": -0.30,
    "job alert": -0.40, "marketing": -0.40,
    "advertisement": -0.40, "you might like": -0.35,
    "recommended for you": -0.35, "flash sale": -0.35,
    "limited time": -0.30, "percent off": -0.25,
    "referral": -0.30, "invite": -0.20, "gift": -0.20,
    "reward": -0.20, "check out": -0.20,
    "don t miss": -0.25, "last chance": -0.25,
    "board snapshot": -0.40, "comment on": -0.30,
    "push notification": -0.35, "mentioned you": -0.30,
    "new comment": -0.30, "new reply": -0.30, "spam": -0.50,
    "reklama": -0.40, "akce": -0.20, "sleva": -0.30, "darek": -0.20,
    # Discovery-tuned additions (from 3-month mailbox analysis)
    "ads": -0.30,                    # Meta/Facebook ads receipts (not subscriptions)
    "ad": -0.25,                     # Single "ad" in subject
    "kredit": -0.25,                 # Czech "credit" — refund notifications
    "vracena": -0.30,                # Czech "returned" — refunds
    "quota": -0.30,                  # Billing quota notifications (not charges)
    "quota increase": -0.35,
    "past due": -0.25,               # Past due notifications (not new subs)
    "overdue": -0.25,
    "refund": -0.30,                 # Refund notifications
}

BLOCKLIST_SERVICES = {
    'vase', 'vaše', 'apetitonline', 'superzoo', 'braintreegateway',
    'fastspring',
    # e-commerce / marketplaces — not subscription services
    'ebay', 'ebay s', 'amazon', 'temu', 'aliexpress', 'shein',
    'datart', 'alza', 'mall', 'czc', 'notifikace', 'novinky',
    'booking', 'airbnb', 'g2a', 'vinted', 'bazos',
    'copygeneral', 'globus', 'europosters', 'zasilkovna',
    'ticketmaster', 'asfinag',
    # clearly wrong extractions
    'view', 'shareholders', 'nl', 'mg', 'www', 'hotmail',
    'sendmail01', 'info-flyingblue', 'koninklijke luchtvaa',
    'payitgov', 'chooseatlas', 'htallc', '2fast4buds',
}

MUSIC_PURCHASE_HINTS = [
    'download', 'track', 'release', 'label', 'wav', 'mp3', 'order', 'purchase',
]

# ═════════════════════════════════════════════
# PROVIDER ALIAS MAPPINGS (sender @domain -> canonical name)
# ═════════════════════════════════════════════

PROVIDER_ALIASES = {
    # Media & Entertainment
    "sony": ("Sony", "entertainment"),
    "playstation": ("Sony", "gaming"),
    "sonyentertainment": ("Sony", "entertainment"),
    "sonyinteractive": ("Sony", "gaming"),
    # Google
    "google": ("Google", "cloud"),
    "googlemail": ("Google", "cloud"),
    "gmail": ("Google", "cloud"),
    "youtube": ("Google", "streaming"),
    "googlecloud": ("Google", "cloud"),
    "googleworkspace": ("Google", "productivity"),
    "googleone": ("Google", "cloud"),
    "googleplay": ("Google", "cloud"),
    "googlepay": ("Google", "payment_processor"),
    # Microsoft
    "microsoft": ("Microsoft", "dev_tools"),
    "office": ("Microsoft", "productivity"),
    "office365": ("Microsoft", "productivity"),
    "azure": ("Microsoft", "cloud"),
    "xbox": ("Microsoft", "gaming"),
    "live": ("Microsoft", "cloud"),
    "hotmail": ("Microsoft", "cloud"),
    "outlook": ("Microsoft", "cloud"),
    "linkedin": ("Microsoft", "productivity"),
    "skype": ("Microsoft", "productivity"),
    # Apple
    "apple": ("Apple", "cloud"),
    "icloud": ("Apple", "cloud"),
    "appleid": ("Apple", "cloud"),
    "applemusic": ("Apple", "music"),
    "appletv": ("Apple", "streaming"),
    "appstore": ("Apple", "cloud"),
    "itunes": ("Apple", "music"),
    # Amazon
    "amazon": ("Amazon", "cloud"),
    "aws": ("Amazon", "cloud"),
    "primevideo": ("Amazon", "streaming"),
    "audible": ("Amazon", "streaming"),
    "kindle": ("Amazon", "streaming"),
    "twitch": ("Amazon", "gaming"),
    "amazonpay": ("Amazon", "payment_processor"),
    "amazonmusic": ("Amazon", "music"),
    # Meta
    "meta": ("Meta", "cloud"),
    "facebook": ("Meta", "cloud"),
    "instagram": ("Meta", "cloud"),
    "whatsapp": ("Meta", "cloud"),
    "oculus": ("Meta", "gaming"),
    # Adobe
    "adobe": ("Adobe", "design"),
    "adobesign": ("Adobe", "design"),
    "adobecreativecloud": ("Adobe", "design"),
}

# Streaming, Music, AI
PROVIDER_ALIASES.update({
    "netflix": ("Netflix", "streaming"),
    "nflx": ("Netflix", "streaming"),
    "disney": ("Disney", "streaming"),
    "disneyplus": ("Disney", "streaming"),
    "marvel": ("Disney", "streaming"),
    "starwars": ("Disney", "streaming"),
    "espn": ("Disney", "streaming"),
    "hulu": ("Disney", "streaming"),
    "hbomax": ("Warner Bros.", "streaming"),
    "hbo": ("Warner Bros.", "streaming"),
    "max": ("Warner Bros.", "streaming"),
    "warnerbros": ("Warner Bros.", "streaming"),
    "discovery": ("Warner Bros.", "streaming"),
    "paramount": ("Paramount", "streaming"),
    "paramountplus": ("Paramount", "streaming"),
    "cbs": ("Paramount", "streaming"),
    "showtime": ("Paramount", "streaming"),
    "peacocktv": ("NBCUniversal", "streaming"),
    "nbcuniversal": ("NBCUniversal", "streaming"),
    "sky": ("NBCUniversal", "streaming"),
    "crunchyroll": ("Crunchyroll", "streaming"),
    "spotify": ("Spotify", "music"),
    "tidal": ("Tidal", "music"),
    "soundcloud": ("SoundCloud", "music"),
    "beatport": ("Beatport", "music"),
    "bandcamp": ("Bandcamp", "music"),
    "discogs": ("Discogs", "music"),
    "deezer": ("Deezer", "music"),
    "pandora": ("Pandora", "music"),
    # AI
    "openai": ("OpenAI", "ai"),
    "chatgpt": ("OpenAI", "ai"),
    "anthropic": ("Anthropic", "ai"),
    "claude": ("Anthropic", "ai"),
    "midjourney": ("Midjourney", "ai"),
    "elevenlabs": ("ElevenLabs", "ai"),
    "replicate": ("Replicate", "ai"),
    "perplexity": ("Perplexity", "ai"),
    "cursor": ("Cursor", "ai"),
    # Cloud & DevOps
    "digitalocean": ("DigitalOcean", "cloud"),
    "cloudflare": ("Cloudflare", "cloud"),
    "vercel": ("Vercel", "cloud"),
    "netlify": ("Netlify", "cloud"),
    "heroku": ("Heroku", "cloud"),
    "railway": ("Railway", "cloud"),
    "render": ("Render", "cloud"),
    "supabase": ("Supabase", "cloud"),
    "firebase": ("Firebase", "cloud"),
    "mongodb": ("MongoDB", "cloud"),
    "hetzner": ("Hetzner", "cloud"),
    "ovh": ("OVH", "cloud"),
    "linode": ("Linode", "cloud"),
    "vultr": ("Vultr", "cloud"),
    # Dev Tools
    "github": ("GitHub", "dev_tools"),
    "gitlab": ("GitLab", "dev_tools"),
    "figma": ("Figma", "design"),
    "notion": ("Notion", "productivity"),
    "linear": ("Linear", "dev_tools"),
    "slack": ("Slack", "productivity"),
    "discord": ("Discord", "productivity"),
    "zoom": ("Zoom", "productivity"),
    "atlassian": ("Atlassian", "dev_tools"),
    "jira": ("Atlassian", "dev_tools"),
    "trello": ("Atlassian", "dev_tools"),
    "docker": ("Docker", "dev_tools"),
    "jetbrains": ("JetBrains", "dev_tools"),
    "postman": ("Postman", "dev_tools"),
    "sentry": ("Sentry", "dev_tools"),
    "datadog": ("Datadog", "dev_tools"),
    "snyk": ("Snyk", "dev_tools"),
    "composio": ("Composio", "dev_tools"),
})

# Music Tools, Security, Productivity
PROVIDER_ALIASES.update({
    "native-instruments": ("Native Instruments", "music_tools"),
    "nativ": ("Native Instruments", "music_tools"),
    "traktor": ("Native Instruments", "music_tools"),
    "maschine": ("Native Instruments", "music_tools"),
    "komplete": ("Native Instruments", "music_tools"),
    "ni.com": ("Native Instruments", "music_tools"),
    "ableton": ("Ableton", "music_tools"),
    "pioneerdj": ("Pioneer DJ", "music_tools"),
    "rekordbox": ("Pioneer DJ", "music_tools"),
    "serato": ("Serato", "music_tools"),
    "izotope": ("iZotope", "music_tools"),
    # Productivity
    "canva": ("Canva", "design"),
    "wix": ("Wix", "productivity"),
    "squarespace": ("Squarespace", "productivity"),
    "wordpress": ("WordPress", "productivity"),
    "dropbox": ("Dropbox", "cloud"),
    "box": ("Box", "cloud"),
    # Security
    "1password": ("1Password", "security"),
    "agilebits": ("1Password", "security"),
    "bitwarden": ("Bitwarden", "security"),
    "lastpass": ("LastPass", "security"),
    "dashlane": ("Dashlane", "security"),
    "nordvpn": ("NordVPN", "security"),
    "nordaccount": ("NordVPN", "security"),
    "expressvpn": ("ExpressVPN", "security"),
    "proton": ("Proton", "security"),
    "protonmail": ("Proton", "security"),
    "protonvpn": ("Proton", "security"),
    # Payment Processors (resolve to actual payee from body)
    "paypal": (None, "payment_processor"),
    "intl.paypal": (None, "payment_processor"),
    "stripe": (None, "payment_processor"),
    "revolut": (None, "payment_processor"),
    "wise": (None, "payment_processor"),
    "transferwise": (None, "payment_processor"),
    "gocardless": (None, "payment_processor"),
    "klarna": (None, "payment_processor"),
    # Hosting
    "godaddy": ("GoDaddy", "hosting"),
    "secureserver": ("GoDaddy", "hosting"),
    "namecheap": ("Namecheap", "hosting"),
    # Fitness
    "strava": ("Strava", "fitness"),
    "onepeloton": ("Peloton", "fitness"),
    "headspace": ("Headspace", "fitness"),
    "calm": ("Calm", "fitness"),
    # Gaming
    "steam": ("Steam", "gaming"),
    "steampowered": ("Steam", "gaming"),
    "epicgames": ("Epic Games", "gaming"),
    "nintendo": ("Nintendo", "gaming"),
    "roblox": ("Roblox", "gaming"),
    # Other
    "patreon": ("Patreon", "productivity"),
    "substack": ("Substack", "productivity"),
    "medium": ("Medium", "productivity"),
})

# ═════════════════════════════════════════════
# SERVICE VARIANTS (one provider -> multiple sub-services)
# ═════════════════════════════════════════════

SERVICE_VARIANTS = {
    "Google": ["google cloud", "google one", "youtube premium",
               "youtube music", "google workspace", "google drive"],
    "Microsoft": ["microsoft 365", "office 365", "azure", "onedrive",
                  "xbox game pass", "xbox live", "linkedin premium"],
    "Apple": ["icloud", "apple music", "apple tv", "apple arcade",
              "apple one", "icloud plus"],
    "Amazon": ["aws", "prime video", "amazon music", "audible",
               "kindle unlimited"],
    "Adobe": ["creative cloud", "acrobat pro", "photoshop", "lightroom"],
    "Spotify": ["spotify premium", "spotify family", "spotify student"],
    "Netflix": ["netflix basic", "netflix standard", "netflix premium"],
}

# ═════════════════════════════════════════════
# STATUS SIGNALS
# ═════════════════════════════════════════════

STATUS_SIGNALS = {
    "active": [
        "welcome to", "thank you for subscribing", "subscription confirmed",
        "activated", "your plan is now active", "service activated",
    ],
    "cancelled": [
        "cancelled", "canceled", "cancellation confirmed",
        "subscription ended", "your subscription has been cancelled",
    ],
    "expired": [
        "expired", "your subscription has expired", "plan expired",
        "trial ended",
    ],
    "trial": [
        "trial started", "free trial", "trial period", "trial activated",
    ],
}

# ═════════════════════════════════════════════
# AMOUNT EXTRACTION
# ═════════════════════════════════════════════

AMOUNT_PATTERNS = [
    r'(?:\$|USD\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    r'(?:€|EUR\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    r'(?:£|GBP\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    r'(?:Kč\s*|CZK\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    r'(\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:\s*Kč|CZK)',
    r'(?:paid|amount|total|charged)\s*[:]?\s*(?:\$|€|£)?\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
]

CURRENCY_MAP = {
    '$': 'USD', 'usd': 'USD', 'USD': 'USD',
    '€': 'EUR', 'eur': 'EUR', 'EUR': 'EUR',
    '£': 'GBP', 'gbp': 'GBP', 'GBP': 'GBP',
    'kč': 'CZK', 'czk': 'CZK', 'CZK': 'CZK',
}

MAX_COST = {"CZK": 50000, "EUR": 2000, "USD": 2000, "GBP": 2000}

# ═════════════════════════════════════════════
# PLAN DETECTION
# ═════════════════════════════════════════════

PLAN_KEYWORDS = {
    "Premium": ["premium"],
    "Professional": ["professional", "pro"],
    "Enterprise": ["enterprise", "business", "team"],
    "Free": ["free", "starter", "basic", "community"],
    "Student": ["student", "education"],
    "Family": ["family", "duo"],
    "Ultimate": ["ultimate", "max", "unlimited"],
    "Plus": ["plus", "standard"],
}

# ═════════════════════════════════════════════
# COMPILED PATTERNS (at module load)
# ═════════════════════════════════════════════

def _build_kw_patterns(kw_dict):
    result = {}
    for kw, weight in kw_dict.items():
        pattern = re.escape(kw).replace(r"\*", ".*")
        result[kw] = {"re": re.compile(pattern, re.I), "weight": weight}
    return result

_COMPILED_A = _build_kw_patterns(GROUP_A_KEYWORDS)
_COMPILED_B = _build_kw_patterns(GROUP_B_KEYWORDS)
_COMPILED_NEG = _build_kw_patterns(NEGATIVE_KEYWORDS)

_PROVIDER_MATCHERS = {}
for alias, (name, cat) in PROVIDER_ALIASES.items():
    _PROVIDER_MATCHERS[alias] = re.compile(re.escape(alias), re.IGNORECASE)

_COMPILED_AMOUNT = [re.compile(p, re.I) for p in AMOUNT_PATTERNS]

_COMPILED_STATUS = {}
for status, signals in STATUS_SIGNALS.items():
    _COMPILED_STATUS[status] = [re.compile(re.escape(s), re.I) for s in signals]

# ═════════════════════════════════════════════
# CLASSIFIER
# ═════════════════════════════════════════════

class EmailClassifier:
    """
    Dual-context subscription email classifier.
    Group A (payments) and Group B (account creations) each have
    independent weight contexts.
    """

    def __init__(self):
        self.amount_patterns = _COMPILED_AMOUNT
        self.status_patterns = _COMPILED_STATUS

    def classify(self, subject, sender, body, search_group=None, wallet_records=None):
        """
        Classify an email and return structured result dict.

        Parameters
        ----------
        subject : str
        sender : str  (full email address)
        body : str  (plain text preferred)
        search_group : "A" | "B" | None (which search found this email)
        wallet_records : list of dict or None (for wallet cross-ref)
        """
        text = f"{subject} {body}"
        text_lower = text.lower()
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        sender_domain = self._extract_domain(sender)

        # Step 1: Provider resolution
        provider = self._resolve_provider(sender_lower, sender_domain, text_lower)

        # Step 2: Dual-context scoring
        a_score, a_hits = self._score_group(text_lower, subject_lower, _COMPILED_A)
        b_score, b_hits = self._score_group(text_lower, subject_lower, _COMPILED_B)
        neg_score, neg_hits = self._score_group(text_lower, subject_lower, _COMPILED_NEG)

        a_final = max(0.0, a_score + neg_score)
        b_final = max(0.0, b_score + neg_score)

        # Provider match boosts
        if provider and provider["category"] != "payment_processor":
            a_final += 0.15
            b_final += 0.20

        # Amount detection boosts Group A more
        amount, currency = self._extract_amount(text)
        if amount > 0:
            a_final += 0.20
            b_final += 0.10

        # Wallet cross-reference
        wallet_boost = 0.0
        if wallet_records and provider and provider["name"]:
            for wr in wallet_records:
                payee_lower = (wr.get("payee", "") or "").lower()
                if provider["name"].lower() in payee_lower:
                    wallet_boost = 0.15
                    break
        a_final += wallet_boost
        b_final += wallet_boost
        # Step 3: Decision
        threshold = 0.35
        is_group_a = a_final >= threshold
        is_group_b = b_final >= threshold

        if search_group == "A":
            is_subscription = is_group_a
        elif search_group == "B":
            is_subscription = is_group_b
        else:
            is_subscription = is_group_a or is_group_b

        # Step 4: Extract metadata
        is_free = (amount == 0 and is_group_b and b_final >= 0.30)

        service_name = provider["name"] if provider else None
        category = provider["category"] if provider else "other"

        if not service_name:
            service_name = self._service_from_domain(sender_domain)

        service_variant = self._detect_variant(service_name, text_lower)
        plan_name = self._detect_plan(text_lower)
        status = self._detect_status(text_lower)
        payment_type = self._detect_billing_cycle(text)

        source_type = "subscription_email"
        if is_free:
            source_type = "free_active"
        elif provider and provider["category"] == "payment_processor":
            source_type = "payment_notification"

        if (service_name or '').lower().strip() in BLOCKLIST_SERVICES:
            is_subscription = False
            confidence = 0.0

        # One-time purchases are not recurring subscriptions unless from a known provider
        if billing_cycle == 'one-time' and not provider_match:
            is_subscription = False
            confidence = 0.0

        return {
            "is_subscription": is_subscription,
            "confidence": round(max(a_final, b_final), 2),
            "confidence_a": round(a_final, 2),
            "confidence_b": round(b_final, 2),
            "is_free": is_free,
            "service_name": service_name or "Unknown Service",
            "service_variant": service_variant,
            "category": category,
            "cost": amount,
            "currency": currency,
            "plan_name": plan_name,
            "status": status,
            "billing_cycle": payment_type,
            "source_type": source_type,
            "provider": provider["name"] if provider else None,
            "is_group_a": is_group_a,
            "is_group_b": is_group_b,
            "a_hits": a_hits[:5],
            "b_hits": b_hits[:5],
            "neg_hits": neg_hits[:5],
            "sender_domain": sender_domain,
        }
    # ── INTERNAL METHODS ───────────────────────────────────

    def _score_group(self, text_lower, subject_lower, patterns):
        score = 0.0
        hits = []
        for kw, info in patterns.items():
            if info["re"].search(text_lower) or info["re"].search(subject_lower):
                score += info["weight"]
                hits.append(kw)
        return score, hits

    def _resolve_provider(self, sender_lower, domain, body_lower):
        """Resolve provider from sender email domain. Checks full @domain."""
        for alias, (name, cat) in PROVIDER_ALIASES.items():
            matcher = _PROVIDER_MATCHERS[alias]
            if (matcher.search(sender_lower)
                or matcher.search(domain)
                or matcher.search(domain.split(".")[0] if domain else "")):
                if name is not None:
                    return {"name": name, "category": cat, "alias": alias}
                # Payment processor — try to extract actual service from body
                extracted = self._extract_service_from_body(body_lower)
                if extracted:
                    return self._resolve_provider(extracted, extracted, body_lower)
                return None
        return None

    def _extract_service_from_body(self, body_lower):
        patterns = [
            r"to\s+([a-z0-9][a-z0-9\s.&-]{1,60}?)(?:\s*(?:view|receipt|details|transaction|$)|[.!?\n])",
            r"payment to\s+([a-z0-9][a-z0-9\s.&-]{1,60}?)(?:\s*(?:view|receipt|details|transaction|$)|[.!?\n])",
            r"receipt from\s+([a-z0-9][a-z0-9\s.&-]{1,60}?)(?:\s*#|[.!?\n]|$)",
        ]
        for pat in patterns:
            m = re.search(pat, body_lower, re.I)
            if m:
                svc = re.sub(r"\s+(llc|ltd|inc|gmbh|s\.r\.o\.|limited|pbc|payments|ireland|luxembourg)\b\.?", "", m.group(1).strip(), flags=re.I)
                svc = re.sub(r"[,;:#-]+$", "", svc).strip()
                if svc:
                    return svc
        return None

    def _extract_domain(self, sender):
        m = re.search(r"@([\w.-]+)", sender or "")
        return m.group(1).lower() if m else ""

    def _service_from_domain(self, domain):
        if not domain:
            return None
        parts = domain.split(".")
        name = parts[0]
        skip = {"mail","email","notify","noreply","no-reply","service",
                "support","updates","hello","info","contact","news",
                "newsletter","invoice","billing","intl","txn"}
        if name.lower() in skip and len(parts) > 1:
            name = parts[1]
        return name.title()

    def _detect_variant(self, service_name, text_lower):
        if not service_name:
            return None
        variants = SERVICE_VARIANTS.get(service_name, [])
        for var in variants:
            if var.lower() in text_lower:
                return var
        return None

    def _detect_plan(self, text_lower):
        for plan_name, keywords in PLAN_KEYWORDS.items():
            for kw in keywords:
                if re.search(re.escape(kw), text_lower, re.I):
                    return plan_name
        return "Standard"

    def _detect_status(self, text_lower):
        for status, patterns in _COMPILED_STATUS.items():
            for pat in patterns:
                if pat.search(text_lower):
                    return status
        return "active"

    def _refine_category(self, service_name: Optional[str], category: str, text_lower: str) -> str:
        """Refine broad categories using service and message context."""
        service_lower = (service_name or '').lower()
        combined = f"{service_lower} {text_lower}"

        if any(tool in combined for tool in ('serato', 'traktor', 'ableton', 'rekordbox', 'native instruments', 'izotope')):
            return 'music_tools'

        if any(music in combined for music in ('beatport', 'discogs', 'bandcamp')):
            return 'music'

        if category == 'music' and any(hint in combined for hint in MUSIC_PURCHASE_HINTS):
            return 'music'

        return category

    def _extract_amount(self, text):
        """Extract the most plausible monetary amount with currency context."""
        BILLING_CONTEXT = re.compile(
            r"\b(paid|amount|total|charged|billed|payment|invoice|receipt|"
            r"celkem|castka|cena|faktura|platba|uhrada)\b", re.I)
        candidates = []
        for pattern in _COMPILED_AMOUNT:
            for m in pattern.finditer(text):
                raw = m.group(1).replace(" ", "").replace(",", ".")
                try:
                    amount = float(raw)
                except ValueError:
                    continue
                if amount <= 0:
                    continue
                if len(re.sub(r'\D', '', m.group(1))) > 8:
                    continue
                ctx = text[max(0, m.start()-20):m.end()+10]
                currency = self._detect_currency(ctx)
                cap = MAX_COST.get(currency, 5000)
                if amount > cap:
                    continue
                window_start = max(0, m.start() - 150)
                window_end = min(len(text), m.end() + 150)
                window = text[window_start:window_end]
                bm = BILLING_CONTEXT.search(window)
                billing_dist = abs(m.start() - window_start - (bm.start() if bm else 9999))
                has_billing = 1 if bm else 0
                candidates.append((has_billing, billing_dist, amount, currency, m.start()))

        if not candidates:
            return 0.0, "USD"
        candidates.sort(key=lambda x: (-x[0], x[1], -x[2]))
        _, _, amount, currency, _ = candidates[0]
        return amount, currency

    def _detect_currency(self, context):
        context_lower = context.lower()
        for symbol, code in CURRENCY_MAP.items():
            if symbol in context or symbol.lower() in context_lower:
                return code
        return "USD"

    def _detect_billing_cycle(self, text):
        text_lower = text.lower()
        if re.search(r"\b(monthly|month|per month|/month|mesicni|mesicne)\b", text_lower):
            return "monthly"
        if re.search(r"\b(yearly|annual|per year|/year|rocni|rocne)\b", text_lower):
            return "yearly"
        if re.search(r"\b(weekly|per week)\b", text_lower):
            return "weekly"
        if re.search(r"\b(one.time|one time|single purchase|jednorazove)\b", text_lower):
            return "one-time"
        return "monthly"

    def build_search_queries(self, since_days=90):
        """Build Gmail-style discovery queries for both search groups."""
        after = (datetime.now() - timedelta(days=since_days)).strftime("%Y/%m/%d")
        return {
            "group_a": [
                f"subject:(receipt OR invoice OR payment OR billing OR purchas* OR charge OR transaction) after:{after}",
                f"subject:(\"you paid\" OR \"payment to\" OR \"automatic payment\" OR \"payment confirmation\" OR \"tax invoice\") after:{after}",
                f"subject:(faktura OR platba OR uhrada OR \"danovy doklad\") after:{after}",
            ],
            "group_b": [
                f"subject:(\"welcome to\" OR \"thank you for\" OR \"your subscription\" OR \"your account\") after:{after}",
                f"subject:(registration OR \"sign up\" OR subscribed OR \"your plan\" OR activated OR verified) after:{after}",
                f"subject:(registrace OR predplatne OR ucet OR aktivace) after:{after}",
            ],
        }


# ═════════════════════════════════════════════
# Quick test
# ═════════════════════════════════════════════

if __name__ == "__main__":
    c = EmailClassifier()
    tests = [
        ("Receipt for Your Payment to Last.Fm Ltd", "service@intl.paypal.com",
         "You paid 3.00 GBP to Last.Fm Ltd. Monthly recurring subscription."),
        ("Welcome to Prism Ray", "pros@notify.prismray.io",
         "Welcome to Prism Ray Online Services."),
        ("50% OFF Limited Time Sale!", "marketing@spam.com",
         "Don't miss this amazing offer!"),
        ("Your Microsoft 365 Invoice", "billing@microsoft.com",
         "Your invoice for Microsoft 365 Family. Total: 99.99 EUR yearly."),
        ("You're all set! Your Spotify Premium", "no-reply@spotify.com",
         "Get started with Spotify Premium. First month free."),
    ]
    for subj, sender, body in tests:
        r = c.classify(subj, sender, body)
        status = "SUB" if r["is_subscription"] else "SKIP"
        print(f"{status:4s} | {r['service_name']:20s} | ${r['cost']:>6.2f} {r['currency']:4s} | conf={r['confidence']:.2f} | plan={r['plan_name']:12s} | status={r['status']:10s}")

# ── Exports for backward compatibility ──────────────────────

ACCOUNT_CREATION_KEYWORDS = list(GROUP_B_KEYWORDS.keys())
