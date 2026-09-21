"""
API Request Payload Validation Subsystem
----------------------------------------
Implements schema, numeric, categorical, and currency constraints validation
for incoming financial transaction prediction requests.
"""

from typing import Dict, Any, Tuple, List, Optional
from app.utils.currency import is_valid_iso4217, normalize_currency_code

VALID_TRANSACTION_TYPES = {"PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"}

# Recognized schema keys for financial transaction evaluation
ALLOWED_FIELDS = {
    "amount",
    "transaction_type",
    "type",
    "old_balance_org",
    "oldbalanceOrg",
    "new_balance_orig",
    "newbalanceOrig",
    "old_balance_dest",
    "oldbalanceDest",
    "new_balance_dest",
    "newbalanceDest",
    "step",
    "currency",
    "sender_account",
    "nameOrig",
    "receiver_account",
    "nameDest",
    "device_type",
    "location"
}


def validate_prediction_payload(
    payload: Any,
    reject_unexpected: bool = False
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validates a prediction request payload according to strict business constraints.

    Args:
        payload: Input dictionary received from API request.
        reject_unexpected: Whether to reject payloads containing unknown fields.

    Returns:
        Tuple of:
        - is_valid (bool): True if payload passes all checks.
        - errors (List[str]): List of validation error descriptions.
        - sanitized (Dict[str, Any]): Cleaned, standardized transaction data.
    """
    errors: List[str] = []
    sanitized: Dict[str, Any] = {}

    # 1. Type validation
    if not isinstance(payload, dict):
        return False, ["Request body must be a valid JSON object."], {}

    if not payload:
        return False, ["Request JSON payload cannot be empty."], {}

    # 2. Unexpected fields check (if enabled)
    if reject_unexpected:
        unexpected = set(payload.keys()) - ALLOWED_FIELDS
        if unexpected:
            errors.append(f"Unexpected fields detected: {sorted(list(unexpected))}")

    # 3. Required: amount
    amount_raw = payload.get("amount")
    if amount_raw is None or str(amount_raw).strip() == "":
        errors.append("Field 'amount' is required.")
    else:
        try:
            amt = float(amount_raw)
            if amt <= 0:
                errors.append("Field 'amount' must be a positive number greater than 0.")
            elif not (-1e15 < amt < 1e15):
                errors.append("Field 'amount' exceeds allowable monetary range.")
            else:
                sanitized["amount"] = amt
        except (ValueError, TypeError):
            errors.append("Field 'amount' must be a valid numeric value.")

    # 4. Required: transaction_type (or type)
    txn_type_raw = payload.get("transaction_type", payload.get("type"))
    if not txn_type_raw or str(txn_type_raw).strip() == "":
        errors.append(f"Field 'transaction_type' is required (supported: {', '.join(sorted(VALID_TRANSACTION_TYPES))}).")
    else:
        txn_type = str(txn_type_raw).strip().upper()
        if txn_type not in VALID_TRANSACTION_TYPES:
            errors.append(
                f"Invalid transaction type '{txn_type}'. Supported categories: {', '.join(sorted(VALID_TRANSACTION_TYPES))}."
            )
        else:
            sanitized["transaction_type"] = txn_type
            sanitized["type"] = txn_type

    # 5. Numeric balance fields
    balance_fields = [
        ("old_balance_org", "oldbalanceOrg", 0.0),
        ("new_balance_orig", "newbalanceOrig", 0.0),
        ("old_balance_dest", "oldbalanceDest", 0.0),
        ("new_balance_dest", "newbalanceDest", 0.0)
    ]

    for std_name, alt_name, default_val in balance_fields:
        val_raw = payload.get(std_name, payload.get(alt_name, default_val))
        try:
            val = float(val_raw)
            if val < 0:
                errors.append(f"Field '{std_name}' cannot be negative (got {val}).")
            else:
                sanitized[std_name] = val
                sanitized[alt_name] = val
        except (ValueError, TypeError):
            errors.append(f"Field '{std_name}' must be a valid numeric value.")

    # 6. Step field
    step_raw = payload.get("step", 1.0)
    try:
        step_val = float(step_raw)
        if step_val < 1:
            errors.append("Field 'step' must be greater than or equal to 1.")
        else:
            sanitized["step"] = step_val
    except (ValueError, TypeError):
        errors.append("Field 'step' must be a valid numeric value.")

    # 7. ISO 4217 Currency validation
    curr_raw = payload.get("currency")
    if curr_raw is not None and str(curr_raw).strip():
        curr_str = str(curr_raw).strip()
        if not is_valid_iso4217(curr_str):
            errors.append(
                f"Invalid currency code '{curr_str}'. Must be a valid 3-letter ISO 4217 code (e.g., INR, USD, EUR, GBP, AED, JPY, CAD, AUD)."
            )
        else:
            sanitized["currency"] = normalize_currency_code(curr_str)
    else:
        sanitized["currency"] = "USD"

    # 8. Metadata string fields
    sanitized["sender_account"] = str(payload.get("sender_account", payload.get("nameOrig", "N/A"))).strip()
    sanitized["receiver_account"] = str(payload.get("receiver_account", payload.get("nameDest", "N/A"))).strip()
    sanitized["device_type"] = str(payload.get("device_type", "API")).strip()
    sanitized["location"] = str(payload.get("location", "API")).strip()

    is_valid = len(errors) == 0
    return is_valid, errors, sanitized
