"""
Prediction History Repository and Data Access Layer
---------------------------------------------------
Provides safe, parameterized, and optimized database queries for:
- Persisting prediction outcomes with audit logging and rollback handling
- Single prediction record retrieval by integer ID or TXN- reference
- Paginated, filtered, and sorted prediction history querying
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional, Union, List
from app.models import db
from app.models.transaction import Transaction
from app.utils.currency import is_valid_iso4217, normalize_currency_code
from app.utils.helpers import mask_account

logger = logging.getLogger("fraud_detection.repository")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [DB]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

ALLOWED_SORT_FIELDS = {
    "created_at": Transaction.created_at,
    "prediction_timestamp": Transaction.prediction_timestamp,
    "amount": Transaction.amount,
    "confidence_score": Transaction.confidence_score,
    "risk_level": Transaction.risk_level,
    "id": Transaction.id
}


class DatabasePersistenceError(Exception):
    """Raised when committing a prediction record to the database fails."""
    pass


def create_prediction_record(
    input_data: Dict[str, Any],
    prediction_result: Dict[str, Any]
) -> Transaction:
    """
    Safely creates and commits a new transaction prediction record to SQLite.

    Args:
        input_data: Validated transaction input dictionary.
        prediction_result: Output dictionary from PredictionService.

    Returns:
        Persisted Transaction model instance.

    Raises:
        DatabasePersistenceError: If transaction commit fails.
    """
    masked_sender = mask_account(input_data.get("sender_account", ""))
    masked_receiver = mask_account(input_data.get("receiver_account", ""))

    try:
        model_info = prediction_result.get("model_info", {})
        txn = Transaction(
            amount=float(input_data.get("amount", 0.0)),
            currency=normalize_currency_code(prediction_result.get("currency", input_data.get("currency", "USD"))),
            normalized_amount=prediction_result.get("normalized_amount_usd", input_data.get("amount", 0.0)),
            exchange_rate=prediction_result.get("exchange_rate", 1.0),
            transaction_type=str(input_data.get("transaction_type", input_data.get("type", "PAYMENT"))).upper(),
            old_balance_org=float(input_data.get("old_balance_org", input_data.get("oldbalanceOrg", 0.0))),
            new_balance_orig=float(input_data.get("new_balance_orig", input_data.get("newbalanceOrig", 0.0))),
            old_balance_dest=float(input_data.get("old_balance_dest", input_data.get("oldbalanceDest", 0.0))),
            new_balance_dest=float(input_data.get("new_balance_dest", input_data.get("newbalanceDest", 0.0))),
            step=float(input_data.get("step", 1.0)),
            sender_account=masked_sender,
            receiver_account=masked_receiver,
            device_type=str(input_data.get("device_type", "API")),
            location=str(input_data.get("location", "Domestic")),
            is_fraud=bool(prediction_result.get("is_fraud", False)),
            prediction_label=str(prediction_result.get("prediction_label", "Legitimate")),
            confidence_score=float(prediction_result.get("confidence_score", 0.0)),
            fraud_probability=prediction_result.get("fraud_probability"),
            risk_level=str(prediction_result.get("risk_level", "Low")),
            model_name=str(model_info.get("name", "ExtraTrees")),
            model_version=str(model_info.get("version", "1.0.0")),
            status="COMPLETED"
        )

        db.session.add(txn)
        db.session.commit()
        logger.info(
            "Saved prediction record: Ref=%s | Amount=%.2f %s | Decision=%s",
            txn.transaction_ref, txn.amount, txn.currency, txn.prediction_label
        )
        return txn

    except Exception as e:
        db.session.rollback()
        logger.error("Failed to commit prediction to database: %s", e)
        raise DatabasePersistenceError(f"Database persistence failure: {e}") from e


def get_prediction_by_identifier(identifier: Union[int, str]) -> Optional[Transaction]:
    """
    Retrieves a single prediction record by integer primary key ID or transaction reference string.

    Args:
        identifier: Primary key integer (e.g. 1) or transaction_ref string (e.g. 'TXN-1234ABCD').

    Returns:
        Transaction instance if found, or None.
    """
    if identifier is None:
        return None

    # Check if identifier can be an integer ID
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.strip().isdigit()):
        txn = db.session.get(Transaction, int(identifier))
        if txn:
            return txn

    # Query by transaction reference string
    clean_ref = str(identifier).strip()
    return Transaction.query.filter_by(transaction_ref=clean_ref).first()


def query_predictions(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    currency: Optional[str] = None,
    transaction_ref: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc"
) -> Dict[str, Any]:
    """
    Executes a validated, safe, parameterized query for prediction history with pagination.

    Args:
        page: Positive integer page number (1-indexed).
        per_page: Number of records per page (1 to 100).
        status: Optional filter ('fraud', 'safe', 'legitimate', 'fraudulent').
        currency: Optional ISO 4217 currency filter (e.g. 'INR', 'USD').
        transaction_ref: Optional reference search string.
        start_date: Optional ISO/date string filter (created_at >= start_date).
        end_date: Optional ISO/date string filter (created_at <= end_date).
        sort_by: Database field to sort on (allow-listed).
        order: Sort direction ('asc' or 'desc').

    Returns:
        Dictionary with count, total, page, per_page, total_pages, and list of records.

    Raises:
        ValueError: If query parameters fail validation.
    """
    # 1. Validate pagination bounds
    if not isinstance(page, int) or page < 1:
        raise ValueError("Invalid page number. Page must be a positive integer greater than or equal to 1.")

    if not isinstance(per_page, int) or per_page < 1 or per_page > 100:
        raise ValueError("Invalid per_page value. per_page must be an integer between 1 and 100.")

    # 2. Validate sort field against allow-list
    sort_key = sort_by.strip().lower() if sort_by else "created_at"
    if sort_key not in ALLOWED_SORT_FIELDS:
        raise ValueError(
            f"Invalid sort_by field '{sort_by}'. Allowed fields: {', '.join(sorted(ALLOWED_SORT_FIELDS.keys()))}."
        )

    order_dir = order.strip().lower() if order else "desc"
    if order_dir not in ["asc", "desc"]:
        raise ValueError("Invalid sort order. Must be 'asc' or 'desc'.")

    # 3. Build parameterized query
    query = Transaction.query

    # Status filter
    if status is not None and str(status).strip():
        status_clean = str(status).strip().lower()
        if status_clean in ["fraud", "fraudulent", "1", "true"]:
            query = query.filter(Transaction.is_fraud.is_(True))
        elif status_clean in ["safe", "legitimate", "0", "false"]:
            query = query.filter(Transaction.is_fraud.is_(False))
        else:
            raise ValueError(
                f"Invalid status filter '{status}'. Supported values: 'fraud', 'safe', 'legitimate', 'fraudulent'."
            )

    # Currency filter
    if currency is not None and str(currency).strip():
        curr_clean = str(currency).strip().upper()
        if not is_valid_iso4217(curr_clean):
            raise ValueError(
                f"Invalid currency filter '{currency}'. Must be a valid 3-letter ISO 4217 code."
            )
        query = query.filter(Transaction.currency == curr_clean)

    # Reference filter (parameterized ilike search)
    if transaction_ref is not None and str(transaction_ref).strip():
        ref_clean = str(transaction_ref).strip()
        query = query.filter(Transaction.transaction_ref.ilike(f"%{ref_clean}%"))

    # Date filters
    if start_date is not None and str(start_date).strip():
        try:
            dt_start = datetime.fromisoformat(str(start_date).strip().replace("Z", "+00:00"))
            # Make naive or match DB timezone
            if dt_start.tzinfo is not None:
                dt_start = dt_start.astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(Transaction.created_at >= dt_start)
        except Exception as e:
            raise ValueError(f"Invalid start_date format '{start_date}'. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS).") from e

    if end_date is not None and str(end_date).strip():
        try:
            dt_end = datetime.fromisoformat(str(end_date).strip().replace("Z", "+00:00"))
            if dt_end.tzinfo is not None:
                dt_end = dt_end.astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(Transaction.created_at <= dt_end)
        except Exception as e:
            raise ValueError(f"Invalid end_date format '{end_date}'. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS).") from e

    # 4. Total record count at SQL level (fast indexed count)
    total_count = query.count()

    # 5. Apply sorting
    sort_col = ALLOWED_SORT_FIELDS[sort_key]
    query = query.order_by(sort_col.asc() if order_dir == "asc" else sort_col.desc())

    # 6. Apply pagination at SQL level
    offset_val = (page - 1) * per_page
    records = query.offset(offset_val).limit(per_page).all()

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return {
        "success": True,
        "count": len(records),
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "predictions": [record.to_dict() for record in records]
    }
