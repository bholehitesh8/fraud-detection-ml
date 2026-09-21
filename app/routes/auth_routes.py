"""
Authentication and User Access Blueprint
----------------------------------------
Handles:
- User Login & Session Initiation (/login) with lockout defense
- User Logout & Session Invalidation (/logout)
- Self-Registration (/register) with role defaulting
- Forwarding endpoints for backwards-compatible admin user management
"""

import hmac
import logging
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.models import db
from app.models.user import User
from app.utils.auth import (
    login_user,
    logout_user,
    get_current_user,
    admin_required,
    validate_registration_data
)
from app.services.audit_service import log_security_event
from app.utils.limiter import rate_limit
from app.utils.google_oauth import (
    is_google_oauth_configured,
    build_google_auth_url,
    exchange_code_for_tokens,
    get_google_user_info,
    generate_unique_username
)

logger = logging.getLogger("fraud_detection.auth_routes")

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(max_requests=25, window_seconds=60, key_prefix="auth_login")
def login():
    """
    Renders login form and authenticates user credentials.
    Enforces account lockout and records security audit trail.
    """
    current_user = get_current_user()
    if current_user:
        return redirect(url_for("main.dashboard"))

    next_page = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        identifier = (request.form.get("identifier") or request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not identifier or not password:
            flash("Please provide both username/email and password.", "danger")
            return render_template("auth/login.html", identifier=identifier, next=next_page)

        # Look up by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        # Check account lockout before password verification
        if user and user.is_locked:
            log_security_event(
                action="ACCOUNT_LOCKED_ATTEMPT",
                event_type="AUTH",
                description=f"Login attempt on locked account '{user.username}'",
                user=user,
                status="WARNING",
                metadata={"identifier": identifier}
            )
            flash("Account is temporarily locked due to excessive failed attempts. Please wait 15 minutes.", "danger")
            return render_template("auth/login.html", identifier=identifier, next=next_page)

        # Verify password
        if user is None or not user.check_password(password):
            logger.warning("Failed login attempt for identifier: %s", identifier)
            became_locked = False
            if user:
                max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
                lockout_min = current_app.config.get("LOCKOUT_DURATION_MINUTES", 15)
                became_locked = user.record_failed_login(max_attempts=max_attempts, lockout_minutes=lockout_min)
                db.session.commit()

            log_security_event(
                action="LOGIN_FAILED",
                event_type="AUTH",
                description=f"Failed login attempt for '{identifier}'",
                user=user,
                username=identifier,
                status="FAILURE",
                metadata={"identifier": identifier, "account_locked": became_locked}
            )

            if became_locked:
                flash("Too many failed attempts. Account has been temporarily locked for 15 minutes.", "danger")
            else:
                flash("Invalid username/email or password.", "danger")
            return render_template("auth/login.html", identifier=identifier, next=next_page)

        # Check deactivated status
        if not user.is_active:
            logger.warning("Deactivated user login attempted: %s", user.username)
            log_security_event(
                action="INACTIVE_ACCOUNT_ATTEMPT",
                event_type="AUTH",
                description=f"Login attempt on deactivated account '{user.username}'",
                user=user,
                status="FAILURE"
            )
            flash("This account has been deactivated. Please contact an administrator.", "danger")
            return render_template("auth/login.html", identifier=identifier, next=next_page)

        # Successful authentication
        user.reset_failed_logins()
        login_user(user)

        log_security_event(
            action="LOGIN_SUCCESS",
            event_type="AUTH",
            description=f"User '{user.username}' signed in successfully (role={user.role})",
            user=user,
            status="SUCCESS",
            metadata={"role": user.role}
        )

        flash(f"Welcome back, {user.username}! Signed in as {user.role.title()}.", "success")

        # Safe redirection
        if next_page and next_page.startswith("/") and not next_page.startswith("//"):
            return redirect(next_page)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", next=next_page)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Logs out current user, records audit event, and clears session."""
    user = get_current_user()
    if user:
        log_security_event(
            action="LOGOUT",
            event_type="AUTH",
            description=f"User '{user.username}' logged out",
            user=user,
            status="SUCCESS"
        )
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
@rate_limit(max_requests=15, window_seconds=60, key_prefix="auth_register")
def register():
    """
    Handles self-registration for new analyst accounts.
    Default role assigned is strictly 'analyst'.
    """
    current_user = get_current_user()
    if current_user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        data = {
            "username": (request.form.get("username") or "").strip(),
            "email": (request.form.get("email") or "").strip().lower(),
            "password": request.form.get("password") or "",
            "confirm_password": request.form.get("confirm_password") or ""
        }

        is_valid, errors = validate_registration_data(data)
        if not is_valid:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html", form_data=data)

        # Check for uniqueness
        if User.query.filter_by(username=data["username"]).first():
            flash("That username is already taken. Please choose another.", "danger")
            return render_template("auth/register.html", form_data=data)

        if User.query.filter_by(email=data["email"]).first():
            flash("That email address is already registered. Please sign in.", "danger")
            return render_template("auth/register.html", form_data=data)

        try:
            new_user = User(
                username=data["username"],
                email=data["email"],
                role="analyst",  # Public registration strictly creates 'analyst' accounts
                is_active=True
            )
            new_user.set_password(data["password"])
            db.session.add(new_user)
            db.session.commit()

            log_security_event(
                action="USER_REGISTERED",
                event_type="AUTH",
                description=f"New analyst user '{new_user.username}' registered",
                user=new_user,
                status="SUCCESS",
                metadata={"email": new_user.email, "role": new_user.role}
            )

            logger.info("New analyst account registered: %s (%s)", new_user.username, new_user.email)
            flash("Registration successful! You may now sign in with your credentials.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            db.session.rollback()
            logger.error("Failed to register user: %s", e)
            flash("An error occurred during account creation. Please try again.", "danger")
            return render_template("auth/register.html", form_data=data)

    return render_template("auth/register.html", form_data={})


# ============================================================================
# Google OAuth 2.0 / OpenID Connect Authentication Flow
# ============================================================================

@auth_bp.route("/auth/google/login", methods=["GET"])
@auth_bp.route("/auth/google", methods=["GET"])
def google_login():
    """
    Initiates Google OAuth 2.0 / OpenID Connect authorization flow.
    Generates cryptographically random state token stored in session for CSRF defense.
    """
    if get_current_user():
        return redirect(url_for("main.dashboard"))

    if not is_google_oauth_configured(current_app.config):
        flash(
            "Google Sign-In is not configured on this server. Please sign in using your username/email and password, or contact an administrator.",
            "warning"
        )
        return redirect(url_for("auth.login"))

    # Cryptographic state parameter to prevent CSRF attacks
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    # Store requested destination if safe relative path
    next_page = request.args.get("next")
    if next_page and next_page.startswith("/") and not next_page.startswith("//"):
        session["oauth_next"] = next_page

    redirect_uri = current_app.config.get("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        redirect_uri = url_for("auth.google_callback", _external=True)

    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    auth_url = build_google_auth_url(client_id, redirect_uri, state)
    return redirect(auth_url)


@auth_bp.route("/auth/google/callback", methods=["GET"])
@rate_limit(max_requests=30, window_seconds=60, key_prefix="auth_google_cb")
def google_callback():
    """
    Handles Google OAuth 2.0 redirect callback:
    1. Validates callback error status from Google.
    2. Validates cryptographically secure state token to prevent CSRF.
    3. Securely exchanges authorization code for tokens.
    4. Fetches and validates verified user identity from Google UserInfo.
    5. Links to existing user by email or provisions new non-admin account.
    6. Establishes application session and records immutable audit ledger event.
    """
    # 1. Handle error response from Google
    error = request.args.get("error")
    if error:
        if error == "access_denied":
            log_security_event(
                action="GOOGLE_LOGIN_CANCELLED",
                event_type="AUTH",
                description="Google OAuth authentication cancelled by user.",
                status="WARNING",
                metadata={"error": error}
            )
            flash("Google sign-in was cancelled.", "warning")
        else:
            log_security_event(
                action="GOOGLE_LOGIN_FAILURE",
                event_type="AUTH",
                description=f"Google OAuth returned error: {error}",
                status="FAILURE",
                metadata={"error": error}
            )
            flash("Google authentication failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    # 2. Validate state token (CSRF Defense)
    state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)
    if not state or not expected_state or not hmac.compare_digest(state, expected_state):
        log_security_event(
            action="GOOGLE_LOGIN_FAILURE",
            event_type="AUTH",
            description="Google OAuth state token mismatch or missing (possible CSRF attack).",
            status="FAILURE"
        )
        flash("Unable to complete Google sign-in right now.", "danger")
        return redirect(url_for("auth.login"))

    # 3. Validate authorization code
    code = request.args.get("code")
    if not code:
        log_security_event(
            action="GOOGLE_LOGIN_FAILURE",
            event_type="AUTH",
            description="Google OAuth callback missing authorization code.",
            status="FAILURE"
        )
        flash("Google authentication failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    # 4. Exchange code for tokens
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = current_app.config.get("GOOGLE_REDIRECT_URI") or url_for("auth.google_callback", _external=True)

    try:
        token_data = exchange_code_for_tokens(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
    except Exception as e:
        logger.error("Token exchange failed: %s", e)
        log_security_event(
            action="GOOGLE_LOGIN_FAILURE",
            event_type="AUTH",
            description="Failed to exchange authorization code with Google token endpoint.",
            status="FAILURE"
        )
        flash("Unable to complete Google sign-in right now.", "danger")
        return redirect(url_for("auth.login"))

    access_token = token_data.get("access_token")
    if not access_token:
        log_security_event(
            action="GOOGLE_LOGIN_FAILURE",
            event_type="AUTH",
            description="Google token response did not contain an access_token.",
            status="FAILURE"
        )
        flash("Google authentication failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    # 5. Retrieve verified user identity
    try:
        user_info = get_google_user_info(access_token)
    except Exception as e:
        logger.error("Userinfo retrieval failed: %s", e)
        log_security_event(
            action="GOOGLE_LOGIN_FAILURE",
            event_type="AUTH",
            description="Failed to retrieve profile from Google UserInfo endpoint.",
            status="FAILURE"
        )
        flash("Unable to complete Google sign-in right now.", "danger")
        return redirect(url_for("auth.login"))

    email = (user_info.get("email") or "").strip().lower()
    email_verified = user_info.get("email_verified") in (True, "true", "True", 1)

    if not email or not email_verified:
        log_security_event(
            action="GOOGLE_LOGIN_FAILURE",
            event_type="AUTH",
            description="Google account email is missing or unverified.",
            status="FAILURE",
            metadata={"email": email}
        )
        flash("Google authentication failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    # 6. Locate or Provision Local User
    user = User.query.filter_by(email=email).first()

    if user:
        # Check active status
        if not user.is_active:
            log_security_event(
                action="GOOGLE_LOGIN_FAILURE",
                event_type="AUTH",
                description=f"Deactivated user '{user.username}' attempted Google login.",
                user=user,
                status="WARNING",
                metadata={"email": email}
            )
            flash("This account is inactive.", "danger")
            return redirect(url_for("auth.login"))

        # User is active -> log them in
        user.reset_failed_logins()
        db.session.commit()

        login_user(user)
        log_security_event(
            action="GOOGLE_LOGIN_SUCCESS",
            event_type="AUTH",
            description=f"User '{user.username}' signed in successfully via Google OAuth.",
            user=user,
            status="SUCCESS",
            metadata={"email": email, "auth_provider": "google"}
        )
        flash(f"Welcome back, {user.username}! Successfully signed in with Google.", "success")
    else:
        # Provision new local account with analyst role and randomized unusable password
        try:
            candidate_username = generate_unique_username(email)
            random_pwd = secrets.token_urlsafe(32)

            new_user = User(
                username=candidate_username,
                email=email,
                role="analyst",  # Google sign-up strictly defaults to analyst
                is_active=True
            )
            new_user.set_password(random_pwd)
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            log_security_event(
                action="GOOGLE_LOGIN_SUCCESS",
                event_type="AUTH",
                description=f"New analyst user '{new_user.username}' provisioned via Google OAuth.",
                user=new_user,
                status="SUCCESS",
                metadata={"email": email, "auth_provider": "google", "is_new_user": True}
            )
            flash(f"Welcome to FraudGuard AI, {new_user.username}! Your account has been created.", "success")
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to provision user for Google OAuth email %s: %s", email, e)
            log_security_event(
                action="GOOGLE_LOGIN_FAILURE",
                event_type="AUTH",
                description="Database error provisioning new user from Google OAuth.",
                status="FAILURE",
                metadata={"email": email}
            )
            flash("Unable to complete Google sign-in right now.", "danger")
            return redirect(url_for("auth.login"))

    # 7. Redirect to requested destination or dashboard
    next_destination = session.pop("oauth_next", None)
    if next_destination and next_destination.startswith("/") and not next_destination.startswith("//"):
        return redirect(next_destination)
    return redirect(url_for("main.dashboard"))


