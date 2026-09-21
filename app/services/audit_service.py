"""
Security Audit Logging and Event Management Service
---------------------------------------------------
Provides unified methods for recording authentication milestones, administrative
actions, and security alerts into the audit_logs repository with IP/UA telemetry.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Optional, Dict, Any, List
from flask import request, has_request_context
from sqlalchemy import or_, desc, asc
from app.models import db
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger("fraud_detection.audit")


def _get_client_ip() -> str:
    """Extracts client IP address safely considering reverse proxies."""
    if not has_request_context():
        return "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def _get_user_agent() -> str:
    """Extracts and sanitizes client User-Agent string."""
    if not has_request_context():
        return "SystemInternal"
    ua = request.headers.get("User-Agent") or "Unknown"
    return ua[:250]


def log_security_event(
    action: str,
    event_type: str,
    description: str,
    user: Optional[User] = None,
    username: Optional[str] = None,
    status: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[AuditLog]:
    """
    Persists an immutable security audit event into the database.

    Args:
        action: Specific event identifier (e.g. 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'ROLE_CHANGED')
        event_type: Broad category ('AUTH', 'ADMIN', 'SECURITY', 'ACCESS')
        description: Human-readable narrative explanation
        user: Optional User model instance associated with event
        username: Optional username string (useful for failed logins or deleted users)
        status: Event outcome ('SUCCESS', 'FAILURE', 'WARNING')
        metadata: Optional dictionary of non-sensitive contextual parameters
    """
    try:
        user_id = user.id if user else None
        effective_username = username or (user.username if user else None) or "Anonymous"

        # Sanitize metadata to guarantee zero credential exposure
        clean_meta = None
        if metadata:
            sanitized = {}
            for k, v in metadata.items():
                if any(secret_term in k.lower() for secret_term in ("pass", "secret", "token", "hash", "key")):
                    continue
                sanitized[k] = str(v)
            clean_meta = json.dumps(sanitized)

        entry = AuditLog(
            user_id=user_id,
            username=effective_username,
            action=action,
            event_type=event_type,
            description=description[:250],
            ip_address=_get_client_ip(),
            user_agent=_get_user_agent(),
            status=status,
            extra_metadata=clean_meta,
            timestamp=datetime.now(timezone.utc)
        )

        db.session.add(entry)
        db.session.commit()
        logger.info(
            "Security Event Logged | [%s] [%s] %s | User=%s | IP=%s | Status=%s",
            event_type, action, description, effective_username, entry.ip_address, status
        )
        return entry

    except Exception as e:
        db.session.rollback()
        logger.error("Failed to record security audit log: %s", e, exc_info=True)
        return None


def query_audit_logs(
    page: int = 1,
    per_page: int = 20,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order: str = "desc"
) -> Dict[str, Any]:
    """
    Queries and paginates security audit log entries with multi-attribute filtering.
    """
    page = max(1, page)
    per_page = max(1, min(100, per_page))

    query = AuditLog.query

    if event_type and event_type.strip():
        query = query.filter(AuditLog.event_type == event_type.strip().upper())

    if status and status.strip():
        query = query.filter(AuditLog.status == status.strip().upper())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuditLog.username.ilike(term),
                AuditLog.action.ilike(term),
                AuditLog.description.ilike(term),
                AuditLog.ip_address.ilike(term)
            )
        )

    if start_date and start_date.strip():
        try:
            dt_start = datetime.fromisoformat(start_date.strip())
            query = query.filter(AuditLog.timestamp >= dt_start)
        except ValueError:
            pass

    if end_date and end_date.strip():
        try:
            dt_end = datetime.fromisoformat(end_date.strip())
            query = query.filter(AuditLog.timestamp <= dt_end)
        except ValueError:
            pass

    if order == "asc":
        query = query.order_by(asc(AuditLog.timestamp), asc(AuditLog.id))
    else:
        query = query.order_by(desc(AuditLog.timestamp), desc(AuditLog.id))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    serialized_logs = [log.to_dict() for log in pagination.items]

    return {
        "success": True,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages or 1,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "logs": serialized_logs,
        "audit_logs": serialized_logs
    }
