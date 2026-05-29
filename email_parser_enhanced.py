"""
Enhanced email parser focusing on:
1. Account creation/signup detection
2. OAuth connection confirmations  
3. First-sentence analysis (not full body)
4. Sentiment-based classification (signup vs sales)
"""

import re
from typing import Dict, Tuple

# OAuth/Identity provider connections
OAUTH_KEYWORDS = [
    "authorized", "connected your", "linked your account",
    "gmail has authorized", "github access granted",
    "facebook connected", "google account linked",
    "sign in with", "successfully connected",
]

# Account creation - first 2 sentences typically
SIGNUP_KEYWORDS = [
    "thank you for joining", "welcome to", "welcome aboard",
    "thanks for signing up", "account created", "registration complete",
    "you've successfully registered", "your account is ready",
    "get started with", "you're all set", "registration successful",
    "verify your email", "confirm your account", "activate your account",
]

# Receipt/payment - definitive subscription
PAYMENT_KEYWORDS = [
    "receipt for your payment", "payment confirmation",
    "you paid", "you sent", "transaction complete",
    "invoice", "billing statement", "payment successful",
]

# Sales spam indicators
SALES_SPAM = [
    "limited time", "% off", "discount", "sale ends",
    "buy now", "shop now", "don't miss", "last chance",
    "exclusive offer", "special promotion",
]

class EmailClassifierEnhanced:
    """Enhanced classifier with signup focus and sentiment analysis."""
    
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
    
    def extract_first_sentences(self, text: str, n: int = 2) -> str:
        """Extract first N sentences from email body."""
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        # Take first n non-empty sentences
        first_n = [s.strip() for s in sentences[:n+1] if s.strip()]
        return ' '.join(first_n[:n])
    
    def classify(
        self,
        subject: str,
        sender: str,
        body: str
    ) -> Dict:
        """
        Classify email with focus on account creation and sentiment.
        
        Returns confidence breakdown:
        - 0.70-1.0: High confidence (payment receipts, known providers + signup)
        - 0.50-0.69: Medium (signup + amount OR oauth connection)
        - 0.30-0.49: Low (just signup keywords)
        - 0.0-0.29: Not subscription (sales spam)
        """
        # Extract first 2 sentences only (where signup msgs live)
        intro = self.extract_first_sentences(body, 2)
        
        # Combine subject + intro (not full body)
        text = f"{subject} {intro}"
        text_lower = text.lower()
        
        score = 0.0
        reasons = []
        category = "other"
        service_name = None
        
        # ═══════════════════════════════════════════════════════
        # NEGATIVE FIRST: Sales spam auto-disqualifies
        # ═══════════════════════════════════════════════════════
        spam_hits = len(self.spam_pattern.findall(text))
        if spam_hits > 0:
            score -= 0.40
            reasons.append(f"sales_spam:{spam_hits}")
            return {
                "is_subscription": False,
                "confidence": max(0.0, score),
                "service_name": "Unknown",
                "category": "spam",
                "cost": 0.0,
                "currency": "USD",
                "billing_cycle": "unknown",
                "plan_name": "",
                "source_type": "spam",
                "reasons": reasons
            }
        
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
                score += 0.20  # Lower than before - provider alone not enough
                reasons.append(f"known_provider:{key}")
                break
        
        # ═══════════════════════════════════════════════════════
        # LAYER 2: Signup/Account Creation Detection
        # ═══════════════════════════════════════════════════════
        signup_hits = len(self.signup_pattern.findall(text))
        if signup_hits > 0:
            score += 0.30  # Strong signal
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
            score += 0.35  # Strongest signal
            reasons.append(f"payment_receipt:{payment_hits}")
        
        # ═══════════════════════════════════════════════════════
        # LAYER 5: Amount Detection (dynamic)
        # ═══════════════════════════════════════════════════════
        amount, currency = self._extract_amount(text)
        if amount > 0:
            score += 0.20
            reasons.append(f"amount:{amount}_{currency}")
        
        # ═══════════════════════════════════════════════════════
        # LAYER 6: Known Provider + Signup = High Confidence
        # ═══════════════════════════════════════════════════════
        if service_name and signup_hits > 0:
            score += 0.15  # Bonus for combination
            reasons.append("provider_plus_signup_bonus")
        
        # ═══════════════════════════════════════════════════════
        # BILLING CYCLE & PLAN DETECTION
        # ═══════════════════════════════════════════════════════
        billing_cycle = self._detect_billing_cycle(text)
        plan_name = self._extract_plan_name(text)
        
        # ═══════════════════════════════════════════════════════
        # SERVICE NAME EXTRACTION
        # ═══════════════════════════════════════════════════════
        if not service_name:
            # Try to extract from subject or sender
            service_name = self._extract_service_name(subject, sender)
        
        # ═══════════════════════════════════════════════════════
        # FINAL DECISION
        # ═══════════════════════════════════════════════════════
        confidence = max(0.0, min(1.0, score))
        is_subscription = confidence >= 0.30  # Lower threshold
        
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
        """Extract domain from sender email."""
        match = re.search(r'@([\w.-]+)', sender)
        return match.group(1).lower() if match else ''
    
    def _extract_service_name(self, subject: str, sender: str) -> str:
        """Extract service name from subject or sender."""
        # Try subject first
        if "welcome to" in subject.lower():
            match = re.search(r'welcome to\s+([A-Z][A-Za-z0-9\s]+)', subject, re.I)
            if match:
                return match.group(1).strip()
        
        # Fallback to domain
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
        """Extract amount and currency."""
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
        """Detect billing cycle."""
        if re.search(r'\b(monthly|month|per month|/month)\b', text, re.I):
            return 'monthly'
        elif re.search(r'\b(yearly|annual|per year|/year)\b', text, re.I):
            return 'yearly'
        return 'monthly'
    
    def _extract_plan_name(self, text: str) -> str:
        """Extract plan name."""
        plan_keywords = ['premium', 'pro', 'plus', 'family', 'enterprise', 'basic', 'standard']
        for keyword in plan_keywords:
            if keyword in text.lower():
                return keyword.title()
        return 'Standard'
