"""
RELAXED Email Parser - More permissive for testing
Lower threshold + full body analysis = more DB inserts for testing
"""

import re
from typing import Dict, Tuple

# Same keywords as enhanced version
OAUTH_KEYWORDS = [
    "authorized", "connected your", "linked your account",
    "gmail has authorized", "github access granted",
    "facebook connected", "google account linked",
    "sign in with", "successfully connected",
]

SIGNUP_KEYWORDS = [
    "thank you for joining", "welcome to", "welcome aboard",
    "thanks for signing up", "account created", "registration complete",
    "you've successfully registered", "your account is ready",
    "get started with", "you're all set", "registration successful",
    "verify your email", "confirm your account", "activate your account",
]

PAYMENT_KEYWORDS = [
    "receipt for your payment", "payment confirmation",
    "you paid", "you sent", "transaction complete",
    "invoice", "billing statement", "payment successful",
]

SALES_SPAM = [
    "limited time", "% off", "discount", "sale ends",
    "buy now", "shop now", "don't miss", "last chance",
    "exclusive offer", "special promotion",
]

class EmailClassifierRelaxed:
    """
    Relaxed classifier for testing - prioritizes recall over precision.
    Goal: Insert more rows to test database logic.
    """
    
    def __init__(self):
        self.signup_pattern = re.compile(
            r'\b(' + '|'.join(SIGNUP_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.oauth_pattern = re.compile(
            r'\b(' + '|'.join(OAUTH_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.payment_pattern = re.compile(
            r'\b(' + '|'.join(PAYMENT_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.spam_pattern = re.compile(
            r'\b(' + '|'.join(SALES_SPAM) + r')\b',
            re.IGNORECASE
        )
    
    def extract_first_sentences(self, text: str, n: int = 5) -> str:
        """
        Extract first N sentences - INCREASED from 2 to 5 for better context.
        """
        sentences = re.split(r'[.!?]+', text)
        first_n = [s.strip() for s in sentences[:n+1] if s.strip()]
        return ' '.join(first_n[:n])
    
    def classify(
        self,
        subject: str,
        sender: str,
        body: str
    ) -> Dict:
        """
        Relaxed classification - LOWER THRESHOLD for more matches.
        
        Changes from enhanced version:
        - Uses first 5 sentences (was 2)
        - Threshold 0.25 (was 0.30)
        - Less aggressive spam filtering
        - More bonus points for combinations
        """
        # Use first 5 sentences for better context
        intro = self.extract_first_sentences(body, 5)
        
        # Combine subject + intro
        text = f"{subject} {intro}"
        text_lower = text.lower()
        
        score = 0.0
        reasons = []
        category = "other"
        service_name = None
        
        # ═══════════════════════════════════════════════════════
        # SPAM CHECK - But less aggressive (only blocks if 2+ spam keywords)
        # ═══════════════════════════════════════════════════════
        spam_hits = len(self.spam_pattern.findall(text))
        if spam_hits >= 2:  # Changed from > 0 to >= 2
            score -= 0.30  # Reduced from -0.40
            reasons.append(f"sales_spam:{spam_hits}")
            # Don't auto-reject - let it continue scoring
        
        # ═══════════════════════════════════════════════════════
        # LAYER 1: Known Provider Detection
        # ═══════════════════════════════════════════════════════
        from email_parser import KNOWN_PROVIDERS
        
        domain = self._extract_domain(sender)
        domain_base = domain.split('.')[0] if domain else ''
        
        for key, (name, cat) in KNOWN_PROVIDERS.items():
            if cat == 'payment_processor':
                continue
            if key in sender.lower() or key in domain or key in domain_base:
                service_name = name
                category = cat
                score += 0.25  # Increased from 0.20
                reasons.append(f"known_provider:{key}")
                break
        
        # ═══════════════════════════════════════════════════════
        # LAYER 2: Signup/Account Creation Detection
        # ═══════════════════════════════════════════════════════
        signup_hits = len(self.signup_pattern.findall(text))
        if signup_hits > 0:
            score += 0.25  # Reduced from 0.30 but still strong
            reasons.append(f"signup_keywords:{signup_hits}")
        
        # ═══════════════════════════════════════════════════════
        # LAYER 3: OAuth/Identity Provider Connection
        # ═══════════════════════════════════════════════════════
        oauth_hits = len(self.oauth_pattern.findall(text))
        if oauth_hits > 0:
            score += 0.25
            reasons.append(f"oauth_connection:{oauth_hits}")
        
        # ═══════════════════════════════════════════════════════
        # LAYER 4: Payment/Receipt Confirmation
        # ═══════════════════════════════════════════════════════
        payment_hits = len(self.payment_pattern.findall(text))
        if payment_hits > 0:
            score += 0.30  # Reduced from 0.35
            reasons.append(f"payment_receipt:{payment_hits}")
        
        # ═══════════════════════════════════════════════════════
        # LAYER 5: Amount Detection
        # ═══════════════════════════════════════════════════════
        amount, currency = self._extract_amount(text)
        if amount > 0:
            score += 0.20
            reasons.append(f"amount:{amount}_{currency}")
        
        # ═══════════════════════════════════════════════════════
        # LAYER 6: Combination Bonuses (MORE GENEROUS)
        # ═══════════════════════════════════════════════════════
        if service_name and signup_hits > 0:
            score += 0.20  # Increased from 0.15
            reasons.append("provider_plus_signup_bonus")
        
        if service_name and payment_hits > 0:
            score += 0.15  # New bonus
            reasons.append("provider_plus_payment_bonus")
        
        # ═══════════════════════════════════════════════════════
        # BILLING CYCLE & PLAN DETECTION
        # ═══════════════════════════════════════════════════════
        billing_cycle = self._detect_billing_cycle(text)
        plan_name = self._extract_plan_name(text)
        
        # ═══════════════════════════════════════════════════════
        # SERVICE NAME EXTRACTION
        # ═══════════════════════════════════════════════════════
        if not service_name:
            service_name = self._extract_service_name(subject, sender)
        
        # ═══════════════════════════════════════════════════════
        # FINAL DECISION - LOWER THRESHOLD
        # ═══════════════════════════════════════════════════════
        confidence = max(0.0, min(1.0, score))
        is_subscription = confidence >= 0.25  # ⭐ LOWERED FROM 0.30
        
        # Determine source type
        if payment_hits > 0:
            source_type = "payment_receipt"
        elif oauth_hits > 0:
            source_type = "oauth_connection"
        elif signup_hits > 0:
            source_type = "account_creation"
        else:
            source_type = "unknown"
        
        return {
            "is_subscription": is_subscription,
            "confidence": round(confidence, 2),
            "service_name": service_name or "Unknown Service",
            "category": category,
            "cost": amount,
            "currency": currency,
            "billing_cycle": billing_cycle,
            "plan_name": plan_name,
            "source_type": source_type,
            "reasons": reasons
        }
    
    def _extract_domain(self, sender: str) -> str:
        match = re.search(r'@([\w.-]+)', sender)
        return match.group(1).lower() if match else ''
    
    def _extract_service_name(self, subject: str, sender: str) -> str:
        if "welcome to" in subject.lower():
            match = re.search(r'welcome to\s+([A-Z][A-Za-z0-9\s]+)', subject, re.I)
            if match:
                return match.group(1).strip()
        
        domain = self._extract_domain(sender)
        if domain:
            parts = domain.split('.')
            name = parts[0]
            if name not in ('mail', 'email', 'notify', 'noreply', 'no-reply'):
                return name.title()
            elif len(parts) > 1:
                return parts[1].title()
        
        return "Unknown"
    
    def _extract_amount(self, text: str) -> Tuple[float, str]:
        patterns = [
            (r'\$\s*([\d,]+\.?\d*)', 'USD'),
            (r'([\d,]+\.?\d*)\s*USD', 'USD'),
            (r'€\s*([\d,]+\.?\d*)', 'EUR'),
            (r'([\d,]+\.?\d*)\s*EUR', 'EUR'),
            (r'£\s*([\d,]+\.?\d*)', 'GBP'),
            (r'([\d,]+\.?\d*)\s*Kč', 'CZK'),
        ]
        
        for pattern, currency in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str), currency
                except:
                    continue
        
        return 0.0, 'USD'
    
    def _detect_billing_cycle(self, text: str) -> str:
        if re.search(r'\b(monthly|month|per month|/month)\b', text, re.I):
            return 'monthly'
        elif re.search(r'\b(yearly|annual|per year|/year)\b', text, re.I):
            return 'yearly'
        return 'monthly'
    
    def _extract_plan_name(self, text: str) -> str:
        plan_keywords = ['premium', 'pro', 'plus', 'family', 'enterprise', 'basic', 'standard']
        for keyword in plan_keywords:
            if keyword in text.lower():
                return keyword.title()
        return 'Standard'
