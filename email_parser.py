"""
Intelligent Email Parser for Subscription Manager
Multi-layer detection engine with confidence scoring.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# ─── Known Provider Mappings ─────────────────────────────────────────────────

KNOWN_PROVIDERS = {
    # Cloud & Dev
    'aws': ('Amazon Web Services', 'cloud'),
    'amazon web services': ('Amazon Web Services', 'cloud'),
    'google': ('Google', 'cloud'),
    'google cloud': ('Google Cloud', 'cloud'),
    'microsoft': ('Microsoft', 'dev_tools'),
    'github': ('GitHub', 'dev_tools'),
    'vercel': ('Vercel', 'cloud'),
    'digitalocean': ('DigitalOcean', 'cloud'),
    'cloudflare': ('Cloudflare', 'cloud'),
    'supabase': ('Supabase', 'cloud'),
    'firebase': ('Firebase', 'cloud'),
    'heroku': ('Heroku', 'cloud'),
    'netlify': ('Netlify', 'cloud'),
    'railway': ('Railway', 'cloud'),
    'linear': ('Linear', 'dev_tools'),
    'figma': ('Figma', 'dev_tools'),
    'notion': ('Notion', 'productivity'),
    'sentry': ('Sentry', 'dev_tools'),
    '1password': ('1Password', 'security'),
    'bitwarden': ('Bitwarden', 'security'),
    'docker': ('Docker', 'dev_tools'),
    'jetbrains': ('JetBrains', 'dev_tools'),
    'gitlab': ('GitLab', 'dev_tools'),
    'postman': ('Postman', 'dev_tools'),
    'composio': ('Composio', 'dev_tools'),
    # AI
    'openai': ('OpenAI', 'ai'),
    'anthropic': ('Anthropic', 'ai'),
    'claude': ('Claude', 'ai'),
    'cursor': ('Cursor', 'ai'),
    'midjourney': ('Midjourney', 'ai'),
    'elevenlabs': ('ElevenLabs', 'ai'),
    'replicate': ('Replicate', 'ai'),
    'ollama': ('Ollama', 'ai'),
    'perplexity': ('Perplexity', 'ai'),
    'poe': ('Poe', 'ai'),
    'runway': ('Runway', 'ai'),
    'leonardo': ('Leonardo.ai', 'ai'),
    'grok': ('Grok', 'ai'),
    'huggingface': ('Hugging Face', 'ai'),
    'cline': ('Cline', 'ai'),
    'openrouter': ('OpenRouter', 'ai'),
    # Streaming
    'netflix': ('Netflix', 'streaming'),
    'apple tv': ('Apple TV+', 'streaming'),
    'disney': ('Disney+', 'streaming'),
    'hbo': ('Max', 'streaming'),
    'youtube': ('YouTube', 'streaming'),
    # Music
    'spotify': ('Spotify', 'music'),
    'tidal': ('Tidal', 'music'),
    'soundcloud': ('SoundCloud', 'music'),
    'apple music': ('Apple Music', 'music'),
    'amazon music': ('Amazon Music', 'music'),
    'beatport': ('Beatport', 'music'),
    'last.fm': ('Last.fm', 'music'),
    'lastfm': ('Last.fm', 'music'),
    'discogs': ('Discogs', 'music'),
    'bandcamp': ('Bandcamp', 'music'),
    # Music tools
    'traktor': ('Native Instruments', 'music_tools'),
    'native instruments': ('Native Instruments', 'music_tools'),
    'serato': ('Serato', 'music_tools'),
    'ableton': ('Ableton', 'music_tools'),
    'rekordbox': ('Pioneer DJ', 'music_tools'),
    'mixed in key': ('Mixed In Key', 'music_tools'),
    'izotope': ('iZotope', 'music_tools'),
    # Design & Productivity
    'adobe': ('Adobe', 'design'),
    'canva': ('Canva', 'design'),
    'wix': ('Wix', 'productivity'),
    'squarespace': ('Squarespace', 'productivity'),
    'wordpress': ('WordPress', 'productivity'),
    'obsidian': ('Obsidian', 'productivity'),
    'evernote': ('Evernote', 'productivity'),
    'todoist': ('Todoist', 'productivity'),
    'dropbox': ('Dropbox', 'cloud'),
    'icloud': ('iCloud', 'cloud'),
    # Gaming
    'playstation': ('PlayStation', 'gaming'),
    'xbox': ('Xbox', 'gaming'),
    'steam': ('Steam', 'gaming'),
    'nintendo': ('Nintendo', 'gaming'),
    'epic games': ('Epic Games', 'gaming'),
    # Payment processors (no service mapping)
    'paypal': (None, 'payment_processor'),
    'google pay': (None, 'payment_processor'),
    'apple pay': (None, 'payment_processor'),
    'stripe': (None, 'payment_processor'),
}

# Domains/names that are payment gateways — NOT the actual subscription service
PAYMENT_GATEWAY_NAMES = {
    'braintree', 'braintreegateway', 'fastspring', 'paddle',
    'chargebee', 'recurly', 'chargify', '2checkout', 'adyen',
    'mollie', 'klarna', 'worldpay', 'authorize.net',
}

# Czech/Slovak words that are common false-positive subjects
FALSE_POSITIVE_SUBJECTS = {
    'vase', 'vaše', 'váše', 'váš', 'vas',   # Czech "your"
    'objednavka', 'objednávka',               # Czech "order"
    'dodani', 'dodání',                        # Czech "delivery"
    'doruceni', 'doručení',                    # Czech "delivery"
    'zasilka', 'zásilka',                      # Czech "package"
}

# Domains that are NOT subscription services (food, retail, etc.)
NON_SUBSCRIPTION_DOMAINS = {
    'apetitonline', 'apetit', 'rohlik', 'kosik', 'tesco',
    'lidl', 'kaufland', 'billa', 'albert', 'globus',
    'superzoo', 'zoohit', 'mall', 'alza', 'czc',
    'heureka', 'sleviste', 'slevomat',
    'fakturoid', 'pohoda',  # invoicing software — not subscriptions
}

PAYMENT_PROCESSORS = {
    'paypal': r'paypal',
    'google pay': r'google\s*(pay|payment)',
    'apple pay': r'apple\s*pay',
    'stripe': r'stripe',
    'bank': r'bank|card transaction|transaction notification|platba kartou|odchozí platba|zaúčtovaná platba',
}

CZECH_BANKS = {
    'airbank': r'air\s*bank',
    'raiffeisen': r'raiffeisen|rb\s*bank',
    'csob': r'čsob|csob',
    'kb': r'komerční\s*banka',
    'moneta': r'moneta',
    'fio': r'fio\s*banka',
}

# ─── Keywords ────────────────────────────────────────────────────────────────

SUBSCRIPTION_POSITIVE_KEYWORDS = [
    'invoice', 'receipt', 'subscription', 'billing', 'payment',
    'renewal', 'charge', 'monthly', 'yearly', 'annual', 'plan',
    'upgrade', 'payment confirmation', 'automatic payment',
    'welcome to', 'thank you for subscribing', 'thank you for joining',
    'thank you for your purchase', 'your plan', 'premium',
    'membership', 'activated', 'trial started', 'subscription confirmed',
    'payment received', 'payment processed', 'billed',
    'invoice ready', 'receipt for your payment', 'you sent a payment',
    'you paid', 'payment successful', 'charged to',
    'úhrada', 'daňový doklad', 'faktura', 'platba', 'předplatné',
    'měsíční', 'roční', 'částka', 'zúčtování',
]

PAYMENT_INDICATOR_KEYWORDS = [
    'receipt for your payment', 'you sent an automatic payment',
    'you successfully sent a payment', 'you paid', 'payment to',
    'automatic payment', 'receipt #', 'transaction id',
    'payment confirmation', 'payment received',
    'card transaction', 'transaction notification', 'bank transfer',
    'platba kartou', 'odchozí platba', 'zaúčtovaná platba',
]

FREE_SERVICE_KEYWORDS = [
    'welcome to', 'thank you for joining', 'thank you for registering',
    'account verified', 'verification complete', 'welcome aboard',
    'thanks for signing up', "you're all set",
    'authorization successful', 'connected your account', 'app authorized',
    'account connected', 'login successful', 'new sign-in',
]

ACCOUNT_CREATION_KEYWORDS = [
    'welcome to', 'thank you for joining', 'thank you for registering',
    'account created', 'account verified', 'verification complete',
    'welcome aboard', 'thanks for signing up', 'your account is now active',
    'get started with', 'welcome to the community', 'registration successful',
]

NEGATIVE_KEYWORDS = [
    'offer', 'discount', 'sale', 'free trial', 'limited time',
    '50% off', '% off', 'promo', 'promotion', 'coupon',
    'referral', 'invite', 'gift', 'reward',
    'unsubscribe', 'marketing', 'newsletter',
    'action required', 'verify your', 'confirm your email',
    'job alert', 'board snapshot', 'digest', 'weekly update',
]

MUSIC_PURCHASE_HINTS = [
    'download', 'track', 'release', 'label', 'wav', 'mp3', 'order', 'purchase',
]

SEARCH_QUERY_GROUPS = {
    'subscription': [
        'subject:(subscription OR invoice OR receipt OR billing OR renewal)',
        '"thank you for subscribing" OR "subscription confirmed" OR "your plan"',
        '"welcome to" OR "thank you for joining" OR "account verified"',
    ],
    'payment': [
        'from:(paypal OR stripe) OR "google pay" OR "apple pay"',
        '"receipt for your payment" OR "you paid" OR "automatic payment"',
        '"platba" OR "faktura" OR "daňový doklad" OR "zúčtování"',
    ],
    'music': [
        'beatport OR discogs OR bandcamp OR spotify OR tidal OR soundcloud',
        'serato OR traktor OR ableton OR rekordbox OR "native instruments"',
    ],
    'free_active': [
        '"welcome to" OR "account connected" OR "authorization successful"',
        '"thanks for signing up" OR "verification complete"',
    ],
}

# ─── Amount patterns ─────────────────────────────────────────────────────────
# CRITICAL: Each pattern must be preceded by a currency symbol or keyword.
# Never match bare numbers without currency context — avoids grabbing
# account numbers, reference IDs, dates etc.

AMOUNT_PATTERNS = [
    # Currency symbol BEFORE number: $15.99  €19,00  £10.99
    r'(?<!\d)(?:\$|USD\s?)(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)',
    r'(?<!\d)(?:€|EUR\s?)(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)',
    r'(?<!\d)(?:£|GBP\s?)(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)',
    # CZK: Kč 299,00  or  299,00 Kč  or  CZK 299
    r'(?:Kč\s?)(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)',
    r'(?<!\d)(\d{1,6}(?:[.,]\d{1,2})?)\s?Kč(?!\d)',
    r'(?:CZK\s?)(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)',
    # Explicit keyword context: "paid 15.99" / "total: 15.99" / "amount: 15.99"
    r'(?:paid|amount|total|charged|billed)\s*[:\s]*(?:\$|€|£|Kč)?(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)',
]

CURRENCY_MAP = {
    '$': 'USD', 'usd': 'USD',
    '€': 'EUR', 'eur': 'EUR',
    '£': 'GBP', 'gbp': 'GBP',
    'kč': 'CZK', 'czk': 'CZK',
}

# Approx FX to USD (for stats normalisation only — not stored)
FX_TO_USD = {
    'USD': 1.0,
    'EUR': 1.08,
    'GBP': 1.27,
    'CZK': 0.044,
}

BILLING_CYCLE_PATTERNS = {
    'monthly': r'\b(monthly|month|per month|/month|měsíční|měsíčně)\b',
    'yearly':  r'\b(yearly|annual|per year|/year|roční|ročně)\b',
    'weekly':  r'\b(weekly|week|per week)\b',
    'daily':   r'\b(per day|/day|daily charge)\b',
    'one-time': r'\b(one.time|one time|single purchase)\b',
}

# ─── Max reasonable cost per currency (sanity cap) ──────────────────────────
MAX_COST = {
    'USD': 5000,
    'EUR': 5000,
    'GBP': 5000,
    'CZK': 50000,   # ~2000 USD
}


class EmailClassifier:

    def __init__(self):
        self.compiled_patterns = {
            'amount': [re.compile(p, re.IGNORECASE) for p in AMOUNT_PATTERNS],
            'cycle': {k: re.compile(v, re.IGNORECASE) for k, v in BILLING_CYCLE_PATTERNS.items()},
            'positive': re.compile(r'\b(' + '|'.join(SUBSCRIPTION_POSITIVE_KEYWORDS) + r')\b', re.IGNORECASE),
            'payment_indicator': re.compile(r'\b(' + '|'.join(PAYMENT_INDICATOR_KEYWORDS) + r')\b', re.IGNORECASE),
            'free_service': re.compile(r'\b(' + '|'.join(FREE_SERVICE_KEYWORDS) + r')\b', re.IGNORECASE),
            'negative': re.compile(r'\b(' + '|'.join(NEGATIVE_KEYWORDS) + r')\b', re.IGNORECASE),
        }

    def classify(self, subject: str, sender: str, body: str) -> Dict:
        text        = f"{subject} {body}"
        text_lower  = text.lower()
        subject_lower = subject.lower()
        sender_lower  = sender.lower()

        score   = 0.0
        reasons = []

        # ── Sender / domain analysis ──────────────────────────────────
        sender_domain  = self._extract_domain(sender)
        domain_base    = sender_domain.split('.')[0] if sender_domain else ''
        provider_match = self._match_provider(sender_lower, sender_domain)

        # Hard reject: non-subscription domain
        if domain_base in NON_SUBSCRIPTION_DOMAINS:
            return self._empty_result(subject, sender_domain)

        # Hard reject: false-positive subject word
        first_word = subject_lower.split()[0] if subject_lower.split() else ''
        if first_word in FALSE_POSITIVE_SUBJECTS:
            return self._empty_result(subject, sender_domain)

        if provider_match:
            score += 0.25
            reasons.append(f"known_provider:{provider_match['key']}")

        payment_proc = self._detect_payment_processor(sender_lower, text_lower)
        if payment_proc:
            score += 0.20
            reasons.append(f"payment_processor:{payment_proc}")

        czech_bank = self._detect_czech_bank(sender_lower, text_lower)
        if czech_bank:
            score += 0.20
            reasons.append(f"czech_bank:{czech_bank}")

        # ── Keywords ──────────────────────────────────────────────────
        positive_hits = len(self.compiled_patterns['positive'].findall(text))
        if positive_hits:
            score += min(0.10 * positive_hits, 0.30)
            reasons.append(f"positive_keywords:{positive_hits}")

        payment_hits = len(self.compiled_patterns['payment_indicator'].findall(text))
        if payment_hits:
            score += min(0.15 * payment_hits, 0.25)
            reasons.append(f"payment_indicators:{payment_hits}")

        free_hits = len(self.compiled_patterns['free_service'].findall(text))
        if free_hits:
            score += 0.10
            reasons.append(f"free_service_keywords:{free_hits}")

        negative_hits = len(self.compiled_patterns['negative'].findall(text))
        if negative_hits:
            score -= min(0.15 * negative_hits, 0.35)
            reasons.append(f"negative_keywords:{negative_hits}")

        # ── Amount ────────────────────────────────────────────────────
        amount, currency = self._extract_amount(text)
        if amount > 0:
            score += 0.15
            reasons.append(f"amount_detected:{amount} {currency}")

        # ── Subject patterns ──────────────────────────────────────────
        if re.search(r'\b(receipt|invoice|payment)\b', subject_lower):
            score += 0.15
            reasons.append("subject_billing_term")
        if re.search(r'^welcome to\b', subject_lower):
            score += 0.10
            reasons.append("subject_welcome")
        if re.search(r'^thank you for (subscribing|joining|your purchase)', subject_lower):
            score += 0.15
            reasons.append("subject_thankyou")

        confidence       = max(0.0, min(1.0, score))
        is_subscription  = confidence >= 0.35
        is_free          = amount == 0 and free_hits > 0 and confidence >= 0.30

        # ── Resolve service name ──────────────────────────────────────
        service_name = None
        category     = 'other'

        if payment_proc and not provider_match:
            extracted = self._extract_service_from_payment_body(text, payment_proc)
            if extracted:
                # Reject if extracted name is a payment gateway
                if extracted.lower().replace(' ', '') in PAYMENT_GATEWAY_NAMES:
                    extracted = None
            if extracted:
                pm = self._match_provider_by_name(extracted)
                service_name = pm['name'] if pm else extracted
                category     = pm['category'] if pm else 'other'
        elif provider_match:
            service_name = provider_match['name']
            category     = provider_match['category']

        if not service_name:
            service_name = self._service_from_domain(sender_domain)

        # Reject gateway names that slipped through as service_name
        if service_name and service_name.lower().replace(' ', '') in PAYMENT_GATEWAY_NAMES:
            is_subscription = False

        billing_cycle = self._detect_billing_cycle(text)
        plan_name     = self.extract_plan_name(text, service_name or 'Unknown')
        category      = self._refine_category(service_name, category, text_lower)

        if is_free:
            source_type = 'free_active'
        elif payment_proc:
            source_type = 'payment_notification'
        else:
            source_type = 'subscription_email'

        return {
            'is_subscription': is_subscription,
            'confidence':       round(confidence, 2),
            'is_free':          is_free,
            'service_name':     service_name or 'Unknown Service',
            'category':         category,
            'cost':             amount,
            'currency':         currency,
            'plan_name':        plan_name,
            'billing_cycle':    billing_cycle,
            'source_type':      source_type,
            'payment_processor': payment_proc,
            'reasons':          reasons,
            'sender_domain':    sender_domain,
        }

    def _empty_result(self, subject: str, domain: str) -> Dict:
        return {
            'is_subscription': False, 'confidence': 0.0, 'is_free': False,
            'service_name': 'Unknown Service', 'category': 'other',
            'cost': 0.0, 'currency': 'USD', 'plan_name': 'Standard',
            'billing_cycle': 'monthly', 'source_type': 'rejected',
            'payment_processor': None, 'reasons': ['hard_reject'],
            'sender_domain': domain,
        }

    def extract_plan_name(self, text: str, service_name: str) -> str:
        text_lower = text.lower()
        plan_keywords = [
            "premium", "pro", "plus", "family", "enterprise", "standard",
            "basic", "professional", "max", "ultimate", "personal", "student",
            "business", "starter", "growth", "team", "teams", "hobby",
        ]
        for kw in plan_keywords:
            if re.search(r'\b' + kw + r'\b', text_lower):
                return kw.title()
        return 'Standard'

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_domain(self, sender: str) -> str:
        m = re.search(r'@([\w.-]+)', sender)
        return m.group(1).lower() if m else ''

    def _match_provider(self, sender_lower: str, domain: str) -> Optional[Dict]:
        domain_base = domain.split('.')[0] if domain else ''
        for key, (name, category) in KNOWN_PROVIDERS.items():
            if category == 'payment_processor':
                continue
            if key in sender_lower or key in domain or key == domain_base:
                return {'key': key, 'name': name, 'category': category}
        return None

    def _match_provider_by_name(self, name: str) -> Optional[Dict]:
        name_lower = name.lower()
        for key, (pname, category) in KNOWN_PROVIDERS.items():
            if category == 'payment_processor':
                continue
            if key in name_lower or (pname and pname.lower() in name_lower):
                return {'key': key, 'name': pname, 'category': category}
        return None

    def _detect_payment_processor(self, sender: str, text: str) -> Optional[str]:
        for name, pattern in PAYMENT_PROCESSORS.items():
            if re.search(pattern, sender, re.I) or re.search(pattern, text, re.I):
                return name
        return None

    def _detect_czech_bank(self, sender: str, text: str) -> Optional[str]:
        for name, pattern in CZECH_BANKS.items():
            if re.search(pattern, sender, re.I) or re.search(pattern, text, re.I):
                return name
        return None

    def _extract_amount(self, text: str) -> Tuple[float, str]:
        """
        Extract first reasonable monetary amount with currency context.
        Returns (amount, currency). Never grabs bare numbers without
        a currency symbol or payment keyword.
        """
        candidates = []
        for pattern in self.compiled_patterns['amount']:
            for m in pattern.finditer(text):
                raw = m.group(1).replace(' ', '').replace(',', '.')
                try:
                    amount = float(raw)
                except ValueError:
                    continue
                if amount <= 0:
                    continue
                ctx      = text[max(0, m.start()-15):m.end()+5]
                currency = self._detect_currency(ctx)
                cap      = MAX_COST.get(currency, 5000)
                if amount > cap:
                    continue  # sanity cap — rejects account numbers
                candidates.append((m.start(), amount, currency))

        # Return first (earliest in text) valid candidate
        candidates.sort(key=lambda x: x[0])
        for _, amount, currency in candidates:
            return amount, currency
        return 0.0, 'USD'

    def _detect_currency(self, context: str) -> str:
        ctx_lower = context.lower()
        for symbol, code in CURRENCY_MAP.items():
            if symbol in context or symbol in ctx_lower:
                return code
        return 'USD'

    def _detect_billing_cycle(self, text: str) -> str:
        for cycle, pattern in self.compiled_patterns['cycle'].items():
            if pattern.search(text):
                return cycle
        return 'monthly'

    def _service_from_domain(self, domain: str) -> Optional[str]:
        if not domain:
            return None
        parts = domain.split('.')
        name  = parts[0]
        skip  = {
            'mail', 'email', 'notify', 'noreply', 'no-reply', 'service',
            'support', 'updates', 'hello', 'info', 'contact', 'news',
            'newsletter', 'invoice', 'billing', 'receipts', 'accounts',
            'payments', 'transaction', 'notification', 'notifications',
        }
        if name.lower() in skip and len(parts) > 1:
            name = parts[1]
        return name.title()

    def _extract_service_from_payment_body(self, text: str, processor: str) -> Optional[str]:
        patterns = {
            'paypal': [
                r'You paid\s+(?:[^\s]+\s+){0,3}to\s+([A-Z][A-Za-z0-9][A-Za-z0-9\s.&,-]{1,50}?)(?:\s*(?:View|Receipt|Details)|[.!?\n]|$)',
                r'payment to\s+([A-Z][A-Za-z0-9][A-Za-z0-9\s.&-]{1,50}?)(?:[.!?\n]|$)',
            ],
            'stripe': [
                r'receipt from\s+([A-Z][A-Za-z0-9][A-Za-z0-9\s.&-]{1,50}?)(?:\s*#|[.!?\n]|$)',
            ],
        }
        for pattern in patterns.get(processor, []):
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                svc = m.group(1).strip()
                svc = re.sub(r'\s+(LLC|Ltd|Inc|GmbH|S\.r\.o\.|Limited|PBC|Ireland|Luxembourg|Payments)\.?$', '', svc, flags=re.I)
                svc = re.sub(r'[,;:#-]+$', '', svc).strip()
                if svc:
                    return svc
        return None

    def _refine_category(self, service_name: Optional[str], category: str, text_lower: str) -> str:
        sn = (service_name or '').lower()
        combined = f"{sn} {text_lower}"
        if any(t in combined for t in ('serato', 'traktor', 'ableton', 'rekordbox', 'native instruments', 'izotope')):
            return 'music_tools'
        if any(t in combined for t in ('beatport', 'discogs', 'bandcamp')):
            return 'music'
        return category

    def build_search_queries(self, since_days: int = 365, groups: Optional[List[str]] = None) -> List[str]:
        selected = groups or list(SEARCH_QUERY_GROUPS.keys())
        after    = (datetime.now() - timedelta(days=since_days)).strftime('%Y/%m/%d')
        queries  = []
        for group in selected:
            for query in SEARCH_QUERY_GROUPS.get(group, []):
                queries.append(f"({query}) after:{after}")
        return queries
