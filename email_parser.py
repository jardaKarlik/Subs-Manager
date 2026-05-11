"""
Intelligent Email Parser for Subscription Manager
Multi-layer detection engine with confidence scoring.
Processes real emails from Gmail, Outlook, and IMAP.
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

# ─── Layer 1: Known Provider Mappings ───────────────────────────────────────

KNOWN_PROVIDERS = {
    # Cloud & Dev
    'aws': ('Amazon Web Services', 'cloud'),
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
    # Streaming
    'netflix': ('Netflix', 'streaming'),
    'spotify': ('Spotify', 'music'),
    'apple tv': ('Apple TV+', 'streaming'),
    'disney': ('Disney+', 'streaming'),
    'hbo': ('Max', 'streaming'),
    'youtube': ('YouTube', 'streaming'),
    'tidal': ('Tidal', 'music'),
    'soundcloud': ('SoundCloud', 'music'),
    'apple music': ('Apple Music', 'music'),
    'amazon music': ('Amazon Music', 'music'),
    # Music purchases & tools
    'beatport': ('Beatport', 'music'),
    'last.fm': ('Last.fm', 'music'),
    'lastfm': ('Last.fm', 'music'),
    'discogs': ('Discogs', 'music'),
    'bandcamp': ('Bandcamp', 'music'),
    'traktor': ('Native Instruments', 'music_tools'),
    'serato': ('Serato', 'music_tools'),
    'ableton': ('Ableton', 'music_tools'),
    'rekordbox': ('Pioneer DJ', 'music_tools'),
    'mixed in key': ('Mixed In Key', 'music_tools'),
    'izotope': ('iZotope', 'music_tools'),
    # Productivity & Misc
    'adobe': ('Adobe', 'design'),
    'canva': ('Canva', 'design'),
    'wix': ('Wix', 'productivity'),
    'squarespace': ('Squarespace', 'productivity'),
    'wordpress': ('WordPress', 'productivity'),
    'notion': ('Notion', 'productivity'),
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
    # Payments (map to actual service)
    'paypal': (None, 'payment_processor'),
    'google pay': (None, 'payment_processor'),
    'apple pay': (None, 'payment_processor'),
    'stripe': (None, 'payment_processor'),
}

# Payment processor keywords that indicate a payment notification
PAYMENT_PROCESSORS = {
    'paypal': r'paypal',
    'google pay': r'google\s*(pay|payment)',
    'apple pay': r'apple\s*pay',
    'stripe': r'stripe',
}

# Czech bank patterns
CZECH_BANKS = {
    'airbank': r'air\s*bank',
    'raiffeisen': r'raiffeisen|rb\s*bank',
    'čsob': r'čsob|csob',
    'kb': r'komerční\s*banka|komerckni banka',
    'moneta': r'moneta',
    'fio': r'fio\s*banka',
}

# ─── Layer 2: Detection Keywords ────────────────────────────────────────────

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
    # Czech
    'úhrada', 'daňový doklad', 'faktura', 'platba', 'předplatné',
    'měsíční', 'roční', 'částka', 'zúčtování',
]

PAYMENT_INDICATOR_KEYWORDS = [
    'receipt for your payment', 'you sent an automatic payment',
    'you successfully sent a payment', 'you paid', 'payment to',
    'automatic payment', 'receipt #', 'transaction id',
    'payment confirmation', 'payment received',
]

FREE_SERVICE_KEYWORDS = [
    'welcome to', 'thank you for joining', 'thank you for registering',
    'account verified', 'verification complete', 'welcome aboard',
    'thanks for signing up', 'you\'re all set',
]

NEGATIVE_KEYWORDS = [
    'offer', 'discount', 'sale', 'free trial', 'limited time',
    '50% off', '% off', 'promo', 'promotion', 'coupon',
    'referral', 'invite', 'gift', 'reward',
    'unsubscribe', 'marketing', 'newsletter',
    'action required', 'verify your', 'confirm your email',
]

# ─── Layer 3: Amount Extraction ─────────────────────────────────────────────

AMOUNT_PATTERNS = [
    # $15.99, $ 15.99, USD 15.99
    r'(?:\$|USD\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    # €19,00, € 19.00, EUR 19.00
    r'(?:€|EUR\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    # £10.99, GBP 10.99
    r'(?:£|GBP\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    # Kč 209,00, 209,00 Kč, CZK 209.00
    r'(?:Kč\s*|CZK\s*)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
    r'(\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:\s*Kč|CZK)',
    # Generic fallback - amount followed by currency word
    r'(?:paid|amount|total|charged)\s*[:\s]*(?:\$|€|£)?\s*(\d[\d\s]*(?:[.,]\d{1,2})?)',
]

CURRENCY_MAP = {
    '$': 'USD', 'usd': 'USD', 'USD': 'USD',
    '€': 'EUR', 'eur': 'EUR', 'EUR': 'EUR',
    '£': 'GBP', 'gbp': 'GBP', 'GBP': 'GBP',
    'kč': 'CZK', 'czk': 'CZK', 'CZK': 'CZK',
}

# ─── Layer 4: Billing Cycle Detection ───────────────────────────────────────

BILLING_CYCLE_PATTERNS = {
    'monthly': r'\b(monthly|month|per month|/month|měsíční|měsíčně)\b',
    'yearly': r'\b(yearly|yearly|annual|per year|/year|roční|ročně)\b',
    'weekly': r'\b(weekly|week|per week)\b',
    'daily': r'\b(daily|day|per day)\b',
    'one-time': r'\b(one.time|one time|single purchase|purchase)\b',
}


class EmailClassifier:
    """Multi-layer subscription email classifier with confidence scoring."""

    def __init__(self):
        self.compiled_patterns = {
            'amount': [re.compile(p, re.IGNORECASE) for p in AMOUNT_PATTERNS],
            'cycle': {k: re.compile(v, re.IGNORECASE) for k, v in BILLING_CYCLE_PATTERNS.items()},
            'positive': re.compile(r'\b(' + '|'.join(SUBSCRIPTION_POSITIVE_KEYWORDS) + r')\b', re.IGNORECASE),
            'payment_indicator': re.compile(r'\b(' + '|'.join(PAYMENT_INDICATOR_KEYWORDS) + r')\b', re.IGNORECASE),
            'free_service': re.compile(r'\b(' + '|'.join(FREE_SERVICE_KEYWORDS) + r')\b', re.IGNORECASE),
            'negative': re.compile(r'\b(' + '|'.join(NEGATIVE_KEYWORDS) + r')\b', re.IGNORECASE),
        }

    def extract_plan_name(self, text: str, service_name: str) -> str:
        """
        Extract plan name from email body.
        Examples: "Spotify Premium", "GitHub Pro", "Adobe Creative Cloud"
        """
        text_lower = text.lower()

        # Common plan keywords to look for
        plan_patterns = [
            r'plan:\s*([a-z\s]+?)(?:\.|,|\s|$)',
            r'subscription:\s*([a-z\s]+?)(?:\.|,|\s|$)',
            r'\b(premium|pro|plus|family|enterprise|standard|basic|professional|max|ultimate)\b',
            r'version\s*[:=]?\s*([a-z\s]+?)(?:\.|,|\s|$)',
        ]

        for pattern in plan_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                plan = match.strip().title() if isinstance(match, str) else match[0].strip().title()
                # Filter out common false positives
                if plan and plan not in ['The', 'Your', 'A', 'An', 'And', 'Or', 'Is']:
                    return plan

        return 'Standard'

    def classify(self, subject: str, sender: str, body: str) -> Dict:
        """
        Classify an email and return structured result with confidence.
        Returns dict with: is_subscription, confidence, service_name, category,
                          cost, currency, billing_cycle, is_free, source_type, plan_name
        """
        text = f"{subject} {body}"
        text_lower = text.lower()
        subject_lower = subject.lower()
        sender_lower = sender.lower()

        score = 0.0
        reasons = []

        # ── Layer 1: Sender Analysis ──
        sender_domain = self._extract_domain(sender)
        provider_match = self._match_provider(sender_lower, sender_domain)

        if provider_match:
            score += 0.25
            reasons.append(f"known_provider:{provider_match['key']}")

        # Check payment processor
        payment_proc = self._detect_payment_processor(sender_lower, text_lower)
        if payment_proc:
            score += 0.20
            reasons.append(f"payment_processor:{payment_proc}")

        # Check Czech banks
        czech_bank = self._detect_czech_bank(sender_lower, text_lower)
        if czech_bank:
            score += 0.20
            reasons.append(f"czech_bank:{czech_bank}")

        # ── Layer 2: Keyword Scoring ──
        positive_hits = len(self.compiled_patterns['positive'].findall(text))
        if positive_hits > 0:
            score += min(0.10 * positive_hits, 0.30)
            reasons.append(f"positive_keywords:{positive_hits}")

        payment_hits = len(self.compiled_patterns['payment_indicator'].findall(text))
        if payment_hits > 0:
            score += min(0.15 * payment_hits, 0.25)
            reasons.append(f"payment_indicators:{payment_hits}")

        free_hits = len(self.compiled_patterns['free_service'].findall(text))
        if free_hits > 0:
            score += 0.10
            reasons.append(f"free_service_keywords:{free_hits}")

        negative_hits = len(self.compiled_patterns['negative'].findall(text))
        if negative_hits > 0:
            score -= min(0.15 * negative_hits, 0.35)
            reasons.append(f"negative_keywords:{negative_hits}")

        # ── Layer 3: Amount Detection ──
        amount, currency = self._extract_amount(text)
        if amount > 0:
            score += 0.15
            reasons.append(f"amount_detected:{amount} {currency}")

        # ── Layer 4: Subject-specific patterns ──
        if re.search(r'\b(receipt|invoice|payment)\b', subject_lower, re.I):
            score += 0.15
            reasons.append("subject_billing_term")

        if re.search(r'^welcome to\b', subject_lower, re.I):
            score += 0.10
            reasons.append("subject_welcome")

        if re.search(r'^thank you for (subscribing|joining|your purchase)', subject_lower, re.I):
            score += 0.15
            reasons.append("subject_thankyou")

        # ── Determine Classification ──
        confidence = max(0.0, min(1.0, score))
        is_subscription = confidence >= 0.35
        is_free = amount == 0 and free_hits > 0 and confidence >= 0.30

        # If it's a payment processor email, extract the actual service from body
        service_name = None
        category = 'other'

        if payment_proc and not provider_match:
            # Extract service from PayPal/Google Pay body
            extracted_name = self._extract_service_from_payment_body(text, payment_proc)
            if extracted_name:
                provider_match = self._match_provider_by_name(extracted_name)
                if provider_match:
                    service_name = provider_match['name']
                    category = provider_match['category']
                else:
                    service_name = extracted_name
        elif provider_match:
            service_name = provider_match['name']
            category = provider_match['category']
        else:
            # Try to extract from domain
            service_name = self._service_from_domain(sender_domain)

        # Detect billing cycle
        billing_cycle = self._detect_billing_cycle(text)

        # Extract plan name from email body ✅ FIX #3
        plan_name = self.extract_plan_name(text, service_name or 'Unknown')

        # Determine source type
        if is_free:
            source_type = 'free_active'
        elif payment_proc:
            source_type = 'payment_notification'
        else:
            source_type = 'subscription_email'

        return {
            'is_subscription': is_subscription,
            'confidence': round(confidence, 2),
            'is_free': is_free,
            'service_name': service_name or 'Unknown Service',
            'category': category,
            'cost': amount,
            'currency': currency,
            'plan_name': plan_name,
            'billing_cycle': billing_cycle,
            'source_type': source_type,
            'payment_processor': payment_proc,
            'reasons': reasons,
            'sender_domain': sender_domain,
        }

    def _extract_domain(self, sender: str) -> str:
        """Extract domain from sender email."""
        match = re.search(r'@([\w.-]+)', sender)
        if match:
            return match.group(1).lower()
        return ''

    def _match_provider(self, sender_lower: str, domain: str) -> Optional[Dict]:
        """Match sender against known providers."""
        domain_base = domain.split('.')[0] if domain else ''

        for key, (name, category) in KNOWN_PROVIDERS.items():
            if category == 'payment_processor':
                continue
            if key in sender_lower or key in domain or key in domain_base:
                return {'key': key, 'name': name, 'category': category}
        return None

    def _match_provider_by_name(self, name: str) -> Optional[Dict]:
        """Match a service name against known providers."""
        name_lower = name.lower()
        for key, (prov_name, category) in KNOWN_PROVIDERS.items():
            if category == 'payment_processor':
                continue
            if key in name_lower or (prov_name and prov_name.lower() in name_lower):
                return {'key': key, 'name': prov_name, 'category': category}
        return None

    def _detect_payment_processor(self, sender: str, text: str) -> Optional[str]:
        """Detect if email is from a payment processor."""
        for name, pattern in PAYMENT_PROCESSORS.items():
            if re.search(pattern, sender, re.I) or re.search(pattern, text, re.I):
                return name
        return None

    def _detect_czech_bank(self, sender: str, text: str) -> Optional[str]:
        """Detect Czech bank payment notifications."""
        for name, pattern in CZECH_BANKS.items():
            if re.search(pattern, sender, re.I) or re.search(pattern, text, re.I):
                return name
        return None

    def _extract_service_from_payment_body(self, text: str, processor: str) -> Optional[str]:
        """Extract the actual service name from payment processor email body."""
        patterns = {
            'paypal': [
                # "payment to X" - stop at sentence end, currency, or known delimiters
                r'payment to\s+([A-Z][A-Za-z0-9\s.&-]{1,40}?)(?:\s*[.!?]|\s*\n|\s+View|\s+Receipt|\s+\$|€|£|Kč|\d)',
                # "You paid $X to Y" - capture service after amount
                r'You paid\s+(?:\$|€|£|Kč)?[\d\s,.]+\s+(?:USD|EUR|CZK)?\s+to\s+([A-Z][A-Za-z0-9\s.&-]{1,40}?)(?:\s*[.!?]|\s*$|\s+\$|€|£|Kč)',
            ],
            'google pay': [
                r'payment to\s+([A-Z][A-Za-z0-9\s.&-]{1,40})(?:\s*[.!?]|\s*$)',
            ],
        }

        for pattern in patterns.get(processor, []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                service = match.group(1).strip()
                # Clean up common suffixes and trailing punctuation
                service = re.sub(r'\s+(LLC|Ltd|Inc|GmbH|S\.r\.o\.|a\.s\.|s\.r\.o|Limited)\.?$', '', service, flags=re.I)
                service = re.sub(r'[,;]$', '', service)
                return service
        return None

    def _extract_amount(self, text: str) -> Tuple[float, str]:
        """Extract monetary amount and currency from text."""
        best_amount = 0.0
        best_currency = 'USD'

        # Find currency symbol/context first
        for pattern in self.compiled_patterns['amount']:
            for match in pattern.finditer(text):
                amount_str = match.group(1)
                # Clean and parse
                amount_str = amount_str.replace(' ', '').replace(',', '.')
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue

                # Determine currency from context
                start = max(0, match.start() - 10)
                context = text[start:match.end()]
                currency = self._detect_currency(context)

                if amount > best_amount:
                    best_amount = amount
                    best_currency = currency

        return best_amount, best_currency

    def _detect_currency(self, context: str) -> str:
        """Detect currency from text context."""
        context_lower = context.lower()
        for symbol, code in CURRENCY_MAP.items():
            if symbol in context or symbol.lower() in context_lower:
                return code
        return 'USD'

    def _detect_billing_cycle(self, text: str) -> str:
        """Detect billing cycle from text."""
        for cycle, pattern in self.compiled_patterns['cycle'].items():
            if pattern.search(text):
                return cycle
        return 'monthly'  # Default

    def _service_from_domain(self, domain: str) -> str:
        """Extract service name from domain."""
        if not domain:
            return None
        parts = domain.split('.')
        name = parts[0]
        # Common cleanups
        if name in ('mail', 'email', 'notify', 'noreply', 'no-reply', 'service', 'support'):
            if len(parts) > 1:
                name = parts[1]
        return name.title()


# ─── Test against real emails ───────────────────────────────────────────────

def test_classifier():
    """Test the classifier against the 15 real emails fetched from Gmail."""
    classifier = EmailClassifier()

    test_cases = [
        ("Welcome to Prism Ray Online Services (PROS)", "pros@notify.prismray.io",
         "Welcome to Prism Ray Online Services. Thank you for registering your account and verifying your email."),
        ("You sent an automatic payment to Last.Fm Ltd", "service@intl.paypal.com",
         "Jaroslav Karlik, here's your receipt. Thank you for your payment to Last.Fm Ltd. Monthly recurring Last.fm subscription."),
        ("Your receipt from Anthropic, PBC #2599-4121-6975", "invoice+statements@mail.anthropic.com",
         "Your receipt from Anthropic, PBC"),
        ("Welcome to MuAPI – Unlock 20% OFF Your First Subscription!", "support@muapi.ai",
         "Welcome to MuAPI. To help you get started, we have a special offer."),
        ("Thank you for joining Ollama", "hello@ollama.com",
         "Thanks for joining Ollama. Download Ollama."),
        ("Receipt for Your Payment to Wix.com Luxembourg S...", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid €19,00 EUR to Wix.com"),
        ("Receipt for Your Payment to Beatport LLC", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid $15,99 USD to Beatport LLC"),
        ("Receipt for Your Payment to Microsoft Payments", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid Kč30,00 CZK to Microsoft Payments"),
        ("Thank You For Your Purchase", "sony@txn-email03.playstation.com",
         "Your PlayStation Store transaction was successful."),
        ("Receipt for Your Payment to Google", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid Kč209,00 CZK to Google"),
        ("Welcome to Claude Skills Hub!", "updates@mail.claudeskills.info",
         "Thanks for subscribing to All Updates!"),
        ("Receipt for Your Payment to Microsoft Payments", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid Kč39,00 CZK to Microsoft Payments"),
        ("Receipt for Your Payment to Microsoft Payments", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid Kč150,00 CZK to Microsoft Payments"),
        ("Action required: your billing account 01918D-8EF7BF-E946C6", "Cloud-noreply@google.com",
         "Action required. You are receiving this email because you are a Google Cloud customer."),
        ("Receipt for Your Payment to Google Payment Irela...", "service@intl.paypal.com",
         "Jaroslav Karlik, you successfully sent a payment. You paid Kč59,99 CZK to Google Payment Ireland"),
    ]

    print("=" * 100)
    print("EMAIL CLASSIFICATION RESULTS")
    print("=" * 100)

    detected = 0
    for i, (subject, sender, body) in enumerate(test_cases, 1):
        result = classifier.classify(subject, sender, body)
        status = "✅ SUB" if result['is_subscription'] else "❌ SKIP"
        free_tag = " [FREE]" if result['is_free'] else ""
        cost = f" {result['cost']:.2f} {result['currency']}" if result['cost'] > 0 else ""

        print(f"\n{i:2d}. {status}{free_tag} | conf={result['confidence']:.2f} | {result['service_name']} ({result['category']}){cost}")
        print(f"    Subject: {subject[:65]}")
        print(f"    Sender:  {sender[:50]}")
        print(f"    Type:    {result['source_type']} | cycle={result['billing_cycle']}")
        print(f"    Reasons: {', '.join(result['reasons'][:4])}")

        if result['is_subscription']:
            detected += 1

    print(f"\n{'=' * 100}")
    print(f"DETECTED: {detected}/{len(test_cases)} emails as subscriptions")
    print(f"{'=' * 100}")

    return detected


if __name__ == "__main__":
    test_classifier()
