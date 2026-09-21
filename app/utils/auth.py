"""
Authentication and Authorization Utility Module
------------------------------------------------
Provides session helpers, role-based access control (RBAC) decorators,
current-user context binding, and seed account initialization.
"""

from functools import wraps
import logging
import re
from typing import Optional, Tuple, List
from flask import session, g, redirect, url_for, request, flash, jsonify
from app.models import db
from app.models.user import User

logger = logging.getLogger("fraud_detection.auth")


def get_current_user() -> Optional[User]:
    """
    Retrieves the currently authenticated user from Flask session,
    caching on Flask request context 'g' to prevent redundant queries.
    Returns None if unauthenticated or if the account is deactivated.
    """
    user_id = session.get("user_id")
    if hasattr(g, "_current_user") and getattr(g, "_cached_user_id", None) == user_id:
        return g._current_user

    user = None
    if user_id:
        try:
            user = db.session.get(User, user_id)
            if user and not user.is_active:
                logger.warning("Deactivated user %s attempted session access.", user.username)
                user = None
                session.clear()
        except Exception as e:
            logger.error("Error retrieving user from session: %s", e)
            user = None

    g._current_user = user
    g._cached_user_id = user_id
    return user


def login_user(user: User) -> None:
    """
    Sets session identifiers for an authenticated user and updates last_login.
    """
    from datetime import datetime, timezone
    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    session.permanent = True

    try:
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
    except Exception as e:
        logger.error("Failed to update last_login timestamp: %s", e)
        db.session.rollback()

    g._current_user = user
    logger.info("User logged in: %s (role=%s)", user.username, user.role)


def logout_user() -> None:
    """
    Clears all authentication session data.
    """
    user_id = session.get("user_id")
    session.clear()
    g._current_user = None
    logger.info("User logged out (user_id=%s)", user_id)


def login_required(f):
    """
    Decorator requiring authentication.
    - If request is to an API endpoint (/api/*) or Accept is json: returns 401 JSON.
    - If browser request: redirects to /login with 'next' parameter.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({
                    "success": False,
                    "status": "error",
                    "error_type": "AuthenticationError",
                    "message": "Authentication required. Please log in to proceed.",
                    "authenticated": False
                }), 401

            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))

        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator requiring one of the specified roles (e.g. 'admin', 'analyst').
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if user is None:
                if request.path.startswith("/api/") or request.is_json:
                    return jsonify({
                        "success": False,
                        "status": "error",
                        "error_type": "AuthenticationError",
                        "message": "Authentication required.",
                        "authenticated": False
                    }), 401

                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.url))

            if user.role not in roles:
                try:
                    from app.services.audit_service import log_security_event
                    log_security_event(
                        action="UNAUTHORIZED_ACCESS",
                        event_type="SECURITY",
                        description=f"Unauthorized access attempt to '{request.path}' (required: {', '.join(roles)})",
                        user=user,
                        status="FAILURE",
                        metadata={"path": request.path, "required_roles": list(roles), "user_role": user.role}
                    )
                except Exception as log_err:
                    logger.error("Audit log error on unauthorized access: %s", log_err)

                logger.warning(
                    "Unauthorized role access by %s (role=%s) on %s. Required: %s",
                    user.username, user.role, request.path, roles
                )
                if request.path.startswith("/api/") or request.is_json:
                    return jsonify({
                        "success": False,
                        "status": "error",
                        "error_type": "AuthorizationError",
                        "message": f"Access denied. Required role: {', '.join(roles)}.",
                        "current_role": user.role
                    }), 403

                flash("Access denied: You do not have permission to view this resource.", "danger")
                return redirect(url_for("main.dashboard"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Convenience decorator specifically requiring admin role."""
    return role_required("admin")(f)


def is_last_active_admin(user_id: int) -> bool:
    """
    Determines if the specified user is the sole remaining active administrator.
    Guards against accidental administrator lockout.
    """
    target = db.session.get(User, user_id)
    if not target or target.role != "admin" or not target.is_active:
        return False
    active_admins = User.query.filter_by(role="admin", is_active=True).count()
    return active_admins <= 1


def validate_registration_data(data: dict) -> Tuple[bool, List[str]]:
    """
    Validates registration form inputs:
    - Username: 3-30 chars, alphanumeric + underscores
    - Email: standard email pattern
    - Password: min 8 chars, at least one letter and one digit
    - Confirm password matching
    """
    errors = []
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not username:
        errors.append("Username is required.")
    elif len(username) < 3 or len(username) > 30:
        errors.append("Username must be between 3 and 30 characters.")
    elif not re.match(r"^[a-zA-Z0-9_]+$", username):
        errors.append("Username may only contain letters, numbers, and underscores.")

    if not email:
        errors.append("Email address is required.")
    elif len(email) > 120 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("Please enter a valid email address.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    elif not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        errors.append("Password must contain both letters and numbers.")

    if password != confirm_password:
        errors.append("Password and confirmation password do not match.")

    return len(errors) == 0, errors


def seed_default_users(app=None) -> None:
    """
    Idempotently seeds initial 'admin' and 'analyst' users if the users table is empty.
    Credentials are read from application configuration (overridable by environment).
    """
    try:
        user_count = User.query.count()
        if user_count > 0:
            return  # Already seeded or has users

        from flask import current_app
        config = app.config if app else current_app.config

        # 1. Default Admin Account
        admin_username = config.get("DEFAULT_ADMIN_USERNAME", "admin")
        admin_password = config.get("DEFAULT_ADMIN_PASSWORD", "AdminPassword123!")
        admin_email = config.get("DEFAULT_ADMIN_EMAIL", "admin@fraudguard.local")

        admin_user = User(
            username=admin_username,
            email=admin_email,
            role="admin",
            is_active=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)

        # 2. Default Analyst Account
        analyst_username = config.get("DEFAULT_ANALYST_USERNAME", "analyst")
        analyst_password = config.get("DEFAULT_ANALYST_PASSWORD", "AnalystPassword123!")
        analyst_email = config.get("DEFAULT_ANALYST_EMAIL", "analyst@fraudguard.local")

        analyst_user = User(
            username=analyst_username,
            email=analyst_email,
            role="analyst",
            is_active=True
        )
        analyst_user.set_password(analyst_password)
        db.session.add(analyst_user)

        db.session.commit()
        logger.info(
            "Default accounts seeded: '%s' (admin) and '%s' (analyst).",
            admin_username, analyst_username
        )
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to seed default user accounts: %s", e)
