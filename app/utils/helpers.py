"""
Helper Utilities
----------------
Functions for payload validation, risk level assignment, and account masking.
"""

import re


def mask_account(account_str: str) -> str:
    """Masks an account number leaving only the last 4 characters visible."""
    if not account_str:
        return "N/A"
    clean = str(account_str).strip()
    if len(clean) <= 4:
        return clean
    return "*" * (len(clean) - 4) + clean[-4:]


def determine_risk_level(fraud_probability: float) -> str:
    """
    Categorizes the risk level based on fraud probability score (0.0 to 1.0 or 0 to 100).
    """
    # Normalize to 0.0 - 1.0 if passed as percentage
    score = fraud_probability / 100.0 if fraud_probability > 1.0 else fraud_probability
    
    if score >= 0.80:
        return "Critical"
    elif score >= 0.50:
        return "High"
    elif score >= 0.25:
        return "Moderate"
    return "Low"


def validate_transaction_data(data: dict) -> tuple[bool, str]:
    """
    Validates user form or JSON submission for transaction evaluation.
    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Payload must be a key-value object."

    # Validate amount
    amount = data.get("amount")
    if amount is None or str(amount).strip() == "":
        return False, "Transaction amount is required."
    try:
        amt = float(amount)
        if amt <= 0:
            return False, "Transaction amount must be greater than zero."
    except ValueError:
        return False, "Transaction amount must be a valid numeric value."

    # Validate transaction type
    txn_type = data.get("transaction_type")
    valid_types = ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
    if not txn_type or txn_type.upper() not in valid_types:
        return False, f"Invalid transaction type. Supported types: {', '.join(valid_types)}"

    return True, ""
