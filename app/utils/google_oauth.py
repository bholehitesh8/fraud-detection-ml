"""
Google OAuth 2.0 / OpenID Connect Client Utility
------------------------------------------------
Provides secure, standards-compliant OpenID Connect operations for Google authentication:
1. Authorization URL generation with state/CSRF token.
2. Code exchange for access tokens via Google Token Endpoint.
3. UserInfo identity retrieval and verification.
4. Unique username generation for newly provisioned Google users.

Zero external dependencies: utilizes Python standard library (urllib, json, secrets, hmac).
"""

import json
import logging
import re
import secrets
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any
from app.models.user import User

logger = logging.getLogger("fraud_detection.google_oauth")

# Standard Google OAuth 2.0 / OpenID Connect Endpoints
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def is_google_oauth_configured(config: Any) -> bool:
    """
    Validates whether both Google Client ID and Client Secret are configured.
    """
    client_id = (config.get("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (config.get("GOOGLE_CLIENT_SECRET") or "").strip()
    return bool(client_id and client_secret)


def build_google_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """
    Builds the Google OAuth 2.0 authorization URL requesting openid, email, and profile scopes.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "access_type": "online"
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    timeout: int = 10
) -> Dict[str, Any]:
    """
    Exchanges authorization code for tokens via Google OAuth token endpoint.
    Returns token dictionary on success, or raises RuntimeError on failure.
    """
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_TOKEN_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "FraudGuard-AI-Auth/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8")
            if status != 200:
                logger.error("Google token exchange returned status %s: %s", status, body)
                raise RuntimeError(f"Token exchange failed with status {status}")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
        logger.error("Google token HTTPError %s: %s", e.code, error_body)
        raise RuntimeError(f"Google token request failed with HTTP {e.code}") from e
    except Exception as e:
        logger.error("Unexpected error during Google token exchange: %s", e)
        raise RuntimeError("Token exchange network connection error") from e


def get_google_user_info(access_token: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetches verified user profile information from Google's OpenID Connect UserInfo endpoint.
    Returns parsed dictionary containing at least 'email', 'email_verified', 'sub', and 'name'.
    """
    req = urllib.request.Request(
        GOOGLE_USERINFO_ENDPOINT,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "FraudGuard-AI-Auth/1.0"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8")
            if status != 200:
                logger.error("Google userinfo returned status %s: %s", status, body)
                raise RuntimeError(f"Userinfo request failed with status {status}")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
        logger.error("Google userinfo HTTPError %s: %s", e.code, error_body)
        raise RuntimeError(f"Google userinfo failed with HTTP {e.code}") from e
    except Exception as e:
        logger.error("Unexpected error fetching Google userinfo: %s", e)
        raise RuntimeError("Google userinfo network connection error") from e


def generate_unique_username(email: str, max_length: int = 50) -> str:
    """
    Derives a clean, collision-free username from a user's verified Google email.
    Sanitizes to alphanumeric characters and underscores, ensuring uniqueness in DB.
    """
    base = email.split("@")[0].strip().lower()
    cleaned = re.sub(r"[^a-z0-9_]", "_", base)
    if not cleaned or len(cleaned) < 3:
        cleaned = "google_user"

    candidate = cleaned[:max_length]
    # Check if exists
    existing = User.query.filter_by(username=candidate).first()
    if not existing:
        return candidate

    # Append random suffix if taken
    for _ in range(10):
        suffix = f"_{secrets.token_hex(2)}"
        candidate = f"{cleaned[:max_length - len(suffix)]}{suffix}"
        if not User.query.filter_by(username=candidate).first():
            return candidate

    # Fallback to longer random suffix
    return f"user_{secrets.token_hex(4)}"
