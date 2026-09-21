"""
Administrator Management and Security Operations Blueprint
----------------------------------------------------------
Provides administrative views and controls for:
- System Telemetry & Admin Dashboard (/admin)
- User Account Provisioning & Lifecycle Management (/admin/users)
- Security Audit Log Explorer (/admin/audit-logs)
All routes strictly enforced with @admin_required decorator.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func
from app.models import db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.utils.auth import (
    admin_required,
    get_current_user,
    is_last_active_admin,
    validate_registration_data
)
from app.services.audit_service import log_security_event, query_audit_logs
from app.utils.limiter import rate_limit

logger = logging.getLogger("fraud_detection.admin")

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("", methods=["GET"])
@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    """
    Administrator Operations & Security Center Dashboard.
    Displays real database telemetry, identity metrics, model throughput, and audit feed.
    """
    # 1. Identity & Account Metrics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    inactive_users = total_users - active_users
    admin_count = User.query.filter_by(role="admin").count()
    analyst_count = User.query.filter_by(role="analyst").count()

    # 2. Financial Transaction & ML Metrics
    total_predictions = Transaction.query.count()
    fraud_predictions = Transaction.query.filter_by(is_fraud=True).count()
    safe_predictions = total_predictions - fraud_predictions
    fraud_rate = round((fraud_predictions / total_predictions * 100), 2) if total_predictions > 0 else 0.0

    # 3. Recent Security Audit Events (Latest 10)
    recent_events = AuditLog.query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        admin_count=admin_count,
        analyst_count=analyst_count,
        total_predictions=total_predictions,
        fraud_predictions=fraud_predictions,
        safe_predictions=safe_predictions,
        fraud_rate=fraud_rate,
        recent_events=recent_events
    )


@admin_bp.route("/users", methods=["GET"])
@admin_required
def users_list():
    """
    Administrator User Directory with search and filtering by role/status.
    """
    search = (request.args.get("q") or "").strip()
    role_filter = (request.args.get("role") or "").strip().lower()
    status_filter = (request.args.get("status") or "").strip().lower()

    query = User.query

    if search:
        term = f"%{search}%"
        query = query.filter((User.username.ilike(term)) | (User.email.ilike(term)))

    if role_filter in ("admin", "analyst"):
        query = query.filter(User.role == role_filter)

    if status_filter == "active":
        query = query.filter(User.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(User.is_active == False)

    users = query.order_by(User.id.asc()).all()

    # Check if there is only one active admin to flag safety in template
    single_admin_active = User.query.filter_by(role="admin", is_active=True).count() <= 1

    return render_template(
        "auth/users.html",
        users=users,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        single_admin_active=single_admin_active
    )


@admin_bp.route("/users/create", methods=["POST"])
@admin_required
@rate_limit(max_requests=30, window_seconds=60, key_prefix="admin_create_user")
def create_user():
    """
    Administrator provisions a new account with designated role.
    """
    admin_user = get_current_user()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    role = request.form.get("role", "analyst").strip().lower()

    if role not in ("admin", "analyst"):
        flash("Invalid role specified. Must be 'admin' or 'analyst'.", "danger")
        return redirect(url_for("admin.users_list"))

    data = {
        "username": username,
        "email": email,
        "password": password,
        "confirm_password": password
    }
    is_valid, errors = validate_registration_data(data)
    if not is_valid:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("admin.users_list"))

    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for("admin.users_list"))

    if User.query.filter_by(email=email).first():
        flash("Email already registered.", "danger")
        return redirect(url_for("admin.users_list"))

    try:
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        log_security_event(
            action="USER_CREATED",
            event_type="ADMIN",
            description=f"Admin '{admin_user.username}' provisioned user '{username}' with role '{role}'",
            user=admin_user,
            status="SUCCESS",
            metadata={"created_user": username, "assigned_role": role, "email": email}
        )

        flash(f"User '{username}' successfully created with role '{role}'.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to create user: %s", e)
        flash(f"Database error creating user: {str(e)}", "danger")

    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@admin_required
def toggle_user_status(user_id: int):
    """
    Toggles user active/inactive state with last-active-admin safeguard.
    """
    admin_user = get_current_user()

    # 1. Prevent deactivating the last active administrator
    if is_last_active_admin(user_id):
        flash("Operation rejected: Cannot deactivate the sole active administrator.", "danger")
        log_security_event(
            action="LAST_ADMIN_PROTECTED",
            event_type="SECURITY",
            description=f"Prevented deactivation of the last active administrator (ID={user_id})",
            user=admin_user,
            status="WARNING"
        )
        return redirect(url_for("admin.users_list"))

    # 2. Prevent deactivating self
    if admin_user and admin_user.id == user_id:
        flash("You cannot deactivate your own account while signed in.", "warning")
        return redirect(url_for("admin.users_list"))

    target_user = db.session.get(User, user_id)
    if not target_user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users_list"))

    try:
        target_user.is_active = not target_user.is_active
        db.session.commit()
        status_str = "activated" if target_user.is_active else "deactivated"

        log_security_event(
            action="USER_STATUS_TOGGLED",
            event_type="ADMIN",
            description=f"Admin '{admin_user.username}' {status_str} account '{target_user.username}'",
            user=admin_user,
            status="SUCCESS",
            metadata={"target_user": target_user.username, "new_active_state": target_user.is_active}
        )

        flash(f"User '{target_user.username}' has been {status_str}.", "info")
    except Exception as e:
        db.session.rollback()
        logger.error("Error toggling user status: %s", e)
        flash("Failed to update user status.", "danger")

    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/change-role", methods=["POST"])
@admin_required
def change_user_role(user_id: int):
    """
    Promotes or demotes user between 'analyst' and 'admin' with last-admin safeguard.
    """
    admin_user = get_current_user()

    # 1. Prevent demoting the last active administrator
    new_role = request.form.get("role", "").strip().lower()
    if new_role != "admin" and is_last_active_admin(user_id):
        flash("Operation rejected: Cannot demote the sole active administrator.", "danger")
        log_security_event(
            action="LAST_ADMIN_PROTECTED",
            event_type="SECURITY",
            description=f"Prevented demoting the last active administrator (ID={user_id})",
            user=admin_user,
            status="WARNING"
        )
        return redirect(url_for("admin.users_list"))

    # 2. Prevent demoting self
    if admin_user and admin_user.id == user_id:
        flash("You cannot change your own administrator role.", "warning")
        return redirect(url_for("admin.users_list"))

    target_user = db.session.get(User, user_id)
    if not target_user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users_list"))

    if new_role not in ("admin", "analyst"):
        flash("Invalid role specified.", "danger")
        return redirect(url_for("admin.users_list"))

    try:
        old_role = target_user.role
        target_user.role = new_role
        db.session.commit()

        log_security_event(
            action="ROLE_CHANGED",
            event_type="ADMIN",
            description=f"Admin '{admin_user.username}' changed '{target_user.username}' role from '{old_role}' to '{new_role}'",
            user=admin_user,
            status="SUCCESS",
            metadata={"target_user": target_user.username, "old_role": old_role, "new_role": new_role}
        )

        flash(f"User '{target_user.username}' role changed to '{new_role}'.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error("Error changing user role: %s", e)
        flash("Failed to update user role.", "danger")

    return redirect(url_for("admin.users_list"))


@admin_bp.route("/audit-logs", methods=["GET"])
@admin_required
def audit_logs():
    """
    Security Audit Log Explorer.
    Server-side pagination, search, and filtering by event type and outcome status.
    """
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    event_type = request.args.get("event_type")
    status = request.args.get("status")
    search = request.args.get("search")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    result = query_audit_logs(
        page=page,
        per_page=per_page,
        event_type=event_type,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        order="desc"
    )

    return render_template(
        "admin/audit_logs.html",
        logs=result["logs"],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"],
        has_next=result["has_next"],
        has_prev=result["has_prev"],
        event_type=event_type or "",
        status=status or "",
        search=search or "",
        start_date=start_date or "",
        end_date=end_date or ""
    )
