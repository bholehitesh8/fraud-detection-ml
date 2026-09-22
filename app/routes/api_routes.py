"""
Production-Ready REST API Blueprint
-----------------------------------
Provides machine-readable JSON endpoints for:
- GET  /api/health: System, database, model, and artifact readiness diagnostics.
- GET  /api/stats: Aggregated transaction statistics.
- POST /api/predict: Real-time fraud detection inference with schema validation,
  ISO 4217 multi-currency support, safe database persistence, and CORS handling.
- GET  /api/predictions: Paginated, filtered, and sorted prediction history query API.
- GET  /api/predictions/<identifier>: Single prediction details lookup by ID or TXN- ref.
"""

import os
from datetime import datetime, timezone
import logging
import time
from flask import Blueprint, jsonify, request, make_response
from app.models import db
from app.models.transaction import Transaction
from app.models.user import User
from app.ml.prediction_service import get_prediction_service, ModelArtifactError
from app.services.prediction_repository import (
    create_prediction_record,
    get_prediction_by_identifier,
    query_predictions,
    DatabasePersistenceError
)
from app.services.analytics_service import get_analytics_summary
from app.utils.validator import validate_prediction_payload
from app.utils.auth import (
    get_current_user,
    login_required,
    login_user,
    logout_user,
    role_required
)
from app.services.audit_service import log_security_event, query_audit_logs
from app.utils.limiter import rate_limit

logger = logging.getLogger("fraud_detection.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [API]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.after_request
def add_cors_headers(response):
    """
    Applies Cross-Origin Resource Sharing (CORS) headers to all API endpoints,
    allowing browser frontends or external consumers to interact seamlessly.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@api_bp.route("/predict", methods=["OPTIONS"])
@api_bp.route("/health", methods=["OPTIONS"])
@api_bp.route("/stats", methods=["OPTIONS"])
@api_bp.route("/analytics/summary", methods=["OPTIONS"])
@api_bp.route("/predictions", methods=["OPTIONS"])
@api_bp.route("/predictions/<identifier>", methods=["OPTIONS"])
@api_bp.route("/auth/me", methods=["OPTIONS"])
@api_bp.route("/auth/login", methods=["OPTIONS"])
@api_bp.route("/auth/logout", methods=["OPTIONS"])
@api_bp.route("/users", methods=["OPTIONS"])
@api_bp.route("/admin/audit-logs", methods=["OPTIONS"])
def handle_options(identifier=None):
    """Handles HTTP OPTIONS preflight checks for CORS compliance."""
    response = make_response("", 204)
    return response


@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    System health and readiness diagnostics endpoint.
    Reports API running state, database connectivity, ML model loading status,
    and individual artifact existence on disk.
    """
    prediction_service = get_prediction_service()
    service_health = prediction_service.get_health_status()

    # 1. Verify Database connectivity
    db_ok = False
    try:
        Transaction.query.count()
        db_ok = True
    except Exception as e:
        logger.error("Health check database probe failed: %s", e)
        db_ok = False

    is_overall_healthy = db_ok and service_health["service_ready"]
    http_status = 200 if is_overall_healthy else 500

    response_data = {
        "status": "healthy" if is_overall_healthy else "degraded",
        "service": "Fraud Detection ML API",
        "version": "1.0.1",
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "local-dev"),
        "api_running": True,
        "database": "connected" if db_ok else "error",
        "ml_model_loaded": service_health["ml_model_loaded"],
        "preprocessor_loaded": service_health["preprocessor_loaded"],
        "artifacts_available": service_health["artifacts_available"],
        "artifacts": service_health["artifacts"],
        "model_details": service_health["model_info"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if service_health.get("load_error"):
        response_data["model_error"] = service_health["load_error"]

    return jsonify(response_data), http_status


# ==============================================================================
# Authentication & User State APIs
# ==============================================================================

@api_bp.route("/auth/me", methods=["GET"])
def api_auth_me():
    """
    Returns current authenticated user status and public profile data.
    Never exposes password or password_hash.
    """
    current_user = get_current_user()
    if current_user is None:
        return jsonify({
            "authenticated": False,
            "user": None
        }), 200

    return jsonify({
        "authenticated": True,
        "user": current_user.to_dict()
    }), 200


@api_bp.route("/auth/login", methods=["POST"])
@rate_limit(max_requests=25, window_seconds=60, key_prefix="api_login")
def api_auth_login():
    """
    Authenticates user credentials and establishes a session for API clients.
    Enforces account lockout checks and records audit log telemetry.
    """
    payload = request.get_json(silent=True) or {}
    identifier = (payload.get("identifier") or payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not identifier or not password:
        return jsonify({
            "success": False,
            "error": "Missing credentials. Both username/email and password are required."
        }), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    # Check account lockout before verifying password
    if user and user.is_locked:
        log_security_event(
            action="ACCOUNT_LOCKED_ATTEMPT",
            event_type="AUTH",
            description=f"API login attempt on locked account '{user.username}'",
            user=user,
            status="WARNING"
        )
        return jsonify({
            "success": False,
            "error": "Account is temporarily locked due to excessive failed attempts. Please try again later."
        }), 403

    if user is None or not user.check_password(password):
        became_locked = False
        if user:
            from flask import current_app
            max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
            lockout_min = current_app.config.get("LOCKOUT_DURATION_MINUTES", 15)
            became_locked = user.record_failed_login(max_attempts=max_attempts, lockout_minutes=lockout_min)
            db.session.commit()

        log_security_event(
            action="API_LOGIN_FAILED",
            event_type="AUTH",
            description=f"Failed API login attempt for '{identifier}'",
            user=user,
            username=identifier,
            status="FAILURE",
            metadata={"account_locked": became_locked}
        )

        error_msg = "Too many failed attempts. Account temporarily locked." if became_locked else "Invalid username/email or password."
        return jsonify({
            "success": False,
            "error": error_msg
        }), 401

    if not user.is_active:
        log_security_event(
            action="INACTIVE_ACCOUNT_ATTEMPT",
            event_type="AUTH",
            description=f"API login attempt on deactivated account '{user.username}'",
            user=user,
            status="FAILURE"
        )
        return jsonify({
            "success": False,
            "error": "Account is deactivated. Please contact an administrator."
        }), 403

    user.reset_failed_logins()
    login_user(user)

    log_security_event(
        action="API_LOGIN_SUCCESS",
        event_type="AUTH",
        description=f"API login successful for '{user.username}' (role={user.role})",
        user=user,
        status="SUCCESS"
    )

    return jsonify({
        "success": True,
        "message": f"Successfully signed in as {user.username}.",
        "user": user.to_dict()
    }), 200


@api_bp.route("/auth/logout", methods=["POST"])
def api_auth_logout():
    """Clears API/client session and logs security event."""
    user = get_current_user()
    if user:
        log_security_event(
            action="API_LOGOUT",
            event_type="AUTH",
            description=f"API logout for '{user.username}'",
            user=user,
            status="SUCCESS"
        )
    logout_user()
    return jsonify({
        "success": True,
        "message": "Successfully logged out."
    }), 200


@api_bp.route("/admin/audit-logs", methods=["GET"])
@login_required
@role_required("admin")
def api_get_audit_logs():
    """
    Administrator-only API returning paginated security audit events.
    Supports filtering by event_type, status, search string, and date ranges.
    """
    try:
        page = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid 'page' parameter."}), 400

    try:
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid 'per_page' parameter."}), 400

    event_type = request.args.get("event_type")
    status = request.args.get("status")
    search = request.args.get("search")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    order = request.args.get("order", "desc")

    result = query_audit_logs(
        page=page,
        per_page=per_page,
        event_type=event_type,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        order=order
    )
    return jsonify(result), 200


@api_bp.route("/users", methods=["GET"])
@login_required
@role_required("admin")
def api_get_users():
    """Administrator-only API listing all registered users."""
    users = User.query.order_by(User.id.asc()).all()
    return jsonify({
        "success": True,
        "count": len(users),
        "users": [u.to_dict() for u in users]
    }), 200


@api_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    """Returns aggregated transaction metrics from SQLite audit database."""
    try:
        total = Transaction.query.count()
        fraud_count = Transaction.query.filter_by(is_fraud=True).count()
        legit_count = total - fraud_count

        return jsonify({
            "status": "success",
            "total_transactions": total,
            "fraudulent_transactions": fraud_count,
            "legitimate_transactions": legit_count,
            "fraud_percentage": round((fraud_count / total * 100), 2) if total > 0 else 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200
    except Exception as e:
        logger.error("Failed to query transaction stats: %s", e)
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve database statistics",
            "details": str(e)
        }), 500


@api_bp.route("/analytics/summary", methods=["GET"])
@login_required
def get_analytics():
    """
    Consolidated Fraud Detection Analytics Center endpoint.
    Computes real-time statistics directly from SQLite database:
    - Summary KPI counters and normalized USD volumes
    - Fraud vs Safe distributions
    - Time-series trend points (with optional ?days= filter, e.g. 1, 7, 30, all)
    - Multi-currency amount analytics (strictly avoiding cross-currency additions)
    - Currency distribution
    - Risk level distribution
    - Machine learning model metadata and training performance
    - Recent prediction activity
    - Security audit activity scoped to user permissions
    """
    try:
        days_arg = request.args.get("days")
        days = int(days_arg) if (days_arg and days_arg.isdigit()) else None
    except Exception:
        days = None

    currency = request.args.get("currency")
    status = request.args.get("status")
    risk_level = request.args.get("risk_level")

    current_u = get_current_user()
    user_role = current_u.role if current_u else "analyst"
    user_id = current_u.id if current_u else None

    try:
        summary_data = get_analytics_summary(
            days=days,
            currency=currency,
            status=status,
            risk_level=risk_level,
            user_role=user_role,
            current_user_id=user_id
        )
        return jsonify(summary_data), 200
    except Exception as e:
        logger.error("Failed to compute analytics summary: %s", e, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to generate analytics summary from database.",
            "details": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500


@api_bp.route("/predict", methods=["POST"])
@rate_limit(max_requests=120, window_seconds=60, key_prefix="api_predict")
@login_required
def api_predict():
    """
    Real-time transaction fraud evaluation endpoint.

    Expects JSON payload:
    {
        "amount": 5000.0,
        "transaction_type": "TRANSFER",
        "old_balance_org": 5000.0,
        "new_balance_orig": 0.0,
        "old_balance_dest": 0.0,
        "new_balance_dest": 5000.0,
        "currency": "INR",           # Optional, defaults to USD, supports any ISO 4217 code
        "step": 1,                   # Optional, defaults to 1.0
        "sender_account": "AC-1234", # Optional
        "receiver_account": "MC-5678"# Optional
    }
    """
    t_start = time.time()

    raw_payload = request.get_json(silent=True)
    if raw_payload is None:
        logger.warning("Rejected prediction request: Missing or invalid JSON body.")
        return jsonify({
            "status": "error",
            "error_type": "ValidationError",
            "message": "Invalid request body: Expected valid JSON payload.",
            "errors": ["Request body must be non-empty valid JSON."],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 400

    # 1. Schema and constraints validation
    is_valid, validation_errors, sanitized_data = validate_prediction_payload(raw_payload)
    if not is_valid:
        logger.warning("Rejected invalid transaction payload: %s", validation_errors)
        return jsonify({
            "status": "error",
            "error_type": "ValidationError",
            "message": "Transaction validation failed.",
            "errors": validation_errors,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 400

    # 2. Model Inference via PredictionService
    prediction_service = get_prediction_service()
    try:
        prediction_result = prediction_service.predict(sanitized_data)
    except ModelArtifactError as e:
        logger.critical("Model artifact failure during inference: %s", e)
        return jsonify({
            "status": "error",
            "error_type": "ModelArtifactError",
            "message": "Machine learning prediction service is currently unavailable.",
            "details": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500
    except Exception as e:
        logger.error("Unexpected error during transaction classification: %s", e, exc_info=True)
        return jsonify({
            "status": "error",
            "error_type": "InternalServerError",
            "message": "An unexpected error occurred while scoring the transaction.",
            "details": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

    # 3. Database Persistence using PredictionRepository
    try:
        persisted_record = create_prediction_record(sanitized_data, prediction_result)
        txn_ref = persisted_record.transaction_ref
    except DatabasePersistenceError as e:
        logger.error("Failed to safely persist prediction: %s", e)
        return jsonify({
            "success": False,
            "status": "error",
            "error_type": "DatabaseError",
            "error": "Failed to safely persist prediction record to database.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500
    except Exception as e:
        logger.error("Unexpected database error during prediction persistence: %s", e)
        return jsonify({
            "success": False,
            "status": "error",
            "error_type": "DatabaseError",
            "error": "An unexpected error occurred while storing the prediction record.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

    # 4. Sanitized Production Logging (Zero Sensitive PII exposure)
    duration_ms = round((time.time() - t_start) * 1000, 2)
    logger.info(
        "Transaction Evaluated & Saved | Ref=%s | Amount=%.2f %s (norm: $%.2f) | Type=%s | Risk=%s | Label=%s | Prob=%s | Latency=%.2fms",
        txn_ref,
        prediction_result["original_amount"],
        prediction_result["currency"],
        prediction_result["normalized_amount_usd"],
        sanitized_data["transaction_type"],
        prediction_result["risk_level"],
        prediction_result["prediction_label"],
        f"{prediction_result['fraud_probability']:.4f}" if prediction_result['fraud_probability'] is not None else "N/A",
        duration_ms
    )

    # 5. Response Construction
    response_payload = {
        "status": "success",
        "transaction_ref": txn_ref,
        "is_fraud": prediction_result["is_fraud"],
        "predicted_class": prediction_result["predicted_class"],
        "prediction_label": prediction_result["prediction_label"],
        "fraud_probability": prediction_result["fraud_probability"],
        "confidence_score": prediction_result["confidence_score"],
        "risk_level": prediction_result["risk_level"],
        "currency": prediction_result["currency"],
        "original_amount": prediction_result["original_amount"],
        "normalized_amount_usd": prediction_result["normalized_amount_usd"],
        "exchange_rate": prediction_result["exchange_rate"],
        "model_info": prediction_result["model_info"],
        "model_status": prediction_result["model_status"],
        "validation_status": "Passed",
        "timestamp": prediction_result["timestamp"],
        "latency_ms": duration_ms
    }

    return jsonify(response_payload), 200


@api_bp.route("/predictions", methods=["GET"])
@login_required
def get_predictions_history():
    """
    Retrieves stored prediction history with pagination, multi-attribute filtering,
    and safe sorting.

    Query Parameters:
    - page: int (default 1)
    - per_page: int (default 20, max 100)
    - status: 'fraud' | 'safe' | 'legitimate' | 'fraudulent'
    - currency: ISO 4217 code (e.g. 'INR', 'USD')
    - ref / transaction_ref: search string
    - sort_by: 'created_at' | 'amount' | 'confidence_score' | 'risk_level' | 'id'
    - order: 'desc' | 'asc' (default 'desc')
    - start_date: ISO 8601 string (e.g. '2026-09-01T00:00:00')
    - end_date: ISO 8601 string
    """
    # 1. Parse pagination parameters
    try:
        page_val = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid 'page' parameter. Must be an integer greater than or equal to 1."
        }), 400

    try:
        per_page_val = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid 'per_page' parameter. Must be an integer between 1 and 100."
        }), 400

    # 2. Extract query filters
    status_filter = request.args.get("status")
    currency_filter = request.args.get("currency")
    ref_filter = request.args.get("ref", request.args.get("transaction_ref"))
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    # 3. Query prediction repository
    try:
        history_result = query_predictions(
            page=page_val,
            per_page=per_page_val,
            status=status_filter,
            currency=currency_filter,
            transaction_ref=ref_filter,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            order=order
        )
        return jsonify(history_result), 200

    except ValueError as e:
        logger.warning("Invalid prediction history query parameters: %s", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        logger.error("Failed to retrieve prediction history: %s", e, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error occurred while querying prediction history."
        }), 500


@api_bp.route("/predictions/<identifier>", methods=["GET"])
@login_required
def get_single_prediction(identifier: str):
    """
    Retrieves complete details for a single prediction record by primary key ID
    or transaction reference string.
    """
    try:
        txn = get_prediction_by_identifier(identifier)
        if not txn:
            logger.info("Prediction details not found for identifier: %s", identifier)
            return jsonify({
                "success": False,
                "error": f"Prediction record not found for identifier: {identifier}"
            }), 404

        return jsonify({
            "success": True,
            "prediction": txn.to_dict()
        }), 200

    except Exception as e:
        logger.error("Error retrieving prediction record '%s': %s", identifier, e)
        return jsonify({
            "success": False,
            "error": "Internal server error occurred while retrieving prediction details."
        }), 500
