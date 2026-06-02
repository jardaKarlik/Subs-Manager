"""
Currency conversion for subscription costs.

Static FX rates (approximate, refreshed periodically). Used to normalize
mixed-currency totals to a base currency (USD by default).

Why static? Sub costs don't need real-time precision — a 1% drift is fine
for an "estimated monthly burn" display. For accuracy-critical finance,
use a live FX feed.
"""

# Base currency for the normalized total
BASE = "USD"

# Rates: 1 unit of <key> = <value> USD
# Updated 2026-06. Approximate, for display only.
RATES_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "CZK": 0.043,   # 1 CZK ≈ $0.043 (23.3 CZK per USD)
    "GBP": 1.27,
    "PLN": 0.25,
    "CHF": 1.12,
    "CAD": 0.73,
    "AUD": 0.66,
    "JPY": 0.0064,
    "SEK": 0.094,
    "NOK": 0.092,
    "DKK": 0.145,
    "HUF": 0.0028,
    "RON": 0.22,
    "BGN": 0.55,
    "HRK": 0.14,
    "TRY": 0.031,
    "INR": 0.012,
    "BRL": 0.18,
    "MXN": 0.050,
}


def to_usd(amount: float, currency: str) -> float:
    """Convert an amount in any supported currency to USD."""
    if amount is None:
        return 0.0
    rate = RATES_TO_USD.get((currency or "USD").upper(), 0.0)
    return float(amount) * rate


def format_money(amount: float, currency: str = "USD") -> str:
    """Format money with currency symbol, comma separators, and reasonable precision."""
    cur = (currency or "USD").upper()
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "CZK": "Kč", "JPY": "¥",
               "PLN": "zł", "CHF": "CHF", "CAD": "C$", "AUD": "A$"}
    sym = symbols.get(cur, cur + " ")
    if cur == "CZK":
        # Czech uses space as thousands separator and comma as decimal
        return f"{sym} {amount:,.0f}".replace(",", " ")
    return f"{sym}{amount:,.2f}"


def format_compact(amount: float) -> str:
    """Format large USD amounts compactly: 12,000 → 12K, 1,200,000 → 1.2M."""
    if amount is None:
        return "—"
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= 1_000_000:
        return f"{sign}${a/1_000_000:.1f}M"
    if a >= 1_000:
        return f"{sign}${a/1_000:.1f}K"
    return f"{sign}${a:.2f}"
