"""
ISO 4217 Currency Utilities and Multi-Currency Conversion Subsystem
-------------------------------------------------------------------
Provides standards-compliant validation and conversion for ISO 4217 currency codes.
Accepts any valid 3-letter currency code (e.g., INR, USD, EUR, GBP, AED, JPY, CAD, AUD)
without restrictive hard-coding, while applying realistic reference exchange rates
to normalize transaction values into the model's baseline training currency (USD).
"""

import re
from typing import Tuple, Dict, Optional

# ISO 4217 3-letter alphabetic regex pattern
ISO_4217_REGEX = re.compile(r"^[A-Z]{3}$")

# Baseline reference exchange rates relative to USD (1 USD = X Currency Units)
# Allows realistic normalization of global payment flows into the model's baseline scale
REFERENCE_EXCHANGE_RATES: Dict[str, float] = {
    "USD": 1.0000,
    "EUR": 0.9200,
    "GBP": 0.7900,
    "INR": 83.5000,
    "AED": 3.6725,
    "JPY": 155.0000,
    "CAD": 1.3600,
    "AUD": 1.5200,
    "CHF": 0.8900,
    "SGD": 1.3500,
    "CNY": 7.2300,
    "BRL": 5.4500,
    "ZAR": 18.2000,
    "SEK": 10.4000,
    "NOK": 10.6000,
    "MXN": 18.1000,
    "NZD": 1.6400,
    "HKD": 7.8100,
    "KRW": 1380.0000,
    "SAR": 3.7500
}


def is_valid_iso4217(code: str) -> bool:
    """
    Validates whether a given string is a valid ISO 4217 currency code.
    Any 3-letter alphabetic code satisfies the international standard format.

    Args:
        code: Currency code string (e.g., "USD", "inr", "EUR").

    Returns:
        bool: True if code conforms to ISO 4217 format, False otherwise.
    """
    if not isinstance(code, str):
        return False
    clean = code.strip().upper()
    return bool(ISO_4217_REGEX.match(clean))


def normalize_currency_code(code: Optional[str]) -> str:
    """
    Sanitizes and standardizes a currency code to uppercase.
    Defaults to 'USD' if omitted or empty.

    Args:
        code: Optional currency code string.

    Returns:
        str: Normalized uppercase 3-letter code.
    """
    if not code or not str(code).strip():
        return "USD"
    return str(code).strip().upper()


def convert_to_base_currency(
    amount: float,
    currency_code: str,
    base_currency: str = "USD"
) -> Tuple[float, float, bool]:
    """
    Converts a transaction amount from a specified ISO 4217 currency into base currency (USD).
    
    Supports all ISO 4217 codes:
    - Known reference currencies: Converts using realistic exchange rates.
    - Other valid ISO 4217 codes: Converts at 1:1 parity baseline with fallback note.

    Args:
        amount: Monetary transaction value.
        currency_code: Source ISO 4217 currency code.
        base_currency: Target model base currency (default: USD).

    Returns:
        Tuple of:
        - normalized_amount: Converted amount in base currency.
        - exchange_rate: Applied rate (units of foreign currency per 1 USD).
        - is_reference_rate: True if found in reference table, False if fallback parity was used.
    """
    norm_curr = normalize_currency_code(currency_code)
    
    if norm_curr == base_currency:
        return float(amount), 1.0, True

    if norm_curr in REFERENCE_EXCHANGE_RATES:
        rate = REFERENCE_EXCHANGE_RATES[norm_curr]
        # Converted Amount (in USD) = Foreign Amount / Rate
        converted = float(amount) / rate
        return round(converted, 2), rate, True

    # Open-ended ISO 4217 fallback for unlisted standard codes
    return float(amount), 1.0, False
