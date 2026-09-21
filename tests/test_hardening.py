"""
Comprehensive Reliability, Hardening, and Error Handling Test Suite (Prompt 10)
-------------------------------------------------------------------------------
Validates:
1. Centralized HTTP error handling (400, 401, 403, 404, 405, 409, 422, 429, 500)
2. Content negotiation: Structured JSON for API routes vs Styled HTML for browser routes
3. Defense-in-depth security response headers (CSP, Frame-Options, nosniff, Permissions-Policy)
4. Sliding window in-memory rate limiting and HTTP 429 response structure
5. Authentication via Email AND Username
6. Role-based access authorization boundaries (Admin vs Analyst vs Public)
7. Health diagnostic endpoint integrity without credential leakage
8. Database transaction rollback safety during persistence failures
"""

import unittest
import json
from unittest.mock import patch
from flask import session
from app import create_app, db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.utils.limiter import InMemoryRateLimiter


class ReliabilityAndHardeningTestCase(unittest.TestCase):
    """Test case covering production reliability, security hardening, and error handlers."""

    def setUp(self):
        """Initializes testing application context with in-memory SQLite database."""
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create standard test users
        self.admin = User(username="harden_admin", email="harden_admin@test.local", role="admin", is_active=True)
        self.admin.set_password("AdminSecurePass123!")

        self.analyst = User(username="harden_analyst", email="harden_analyst@test.local", role="analyst", is_active=True)
        self.analyst.set_password("AnalystSecurePass123!")

        self.inactive = User(username="harden_inactive", email="harden_inactive@test.local", role="analyst", is_active=False)
        self.inactive.set_password("InactivePass123!")

        db.session.add_all([self.admin, self.analyst, self.inactive])
        db.session.commit()

    def tearDown(self):
        """Cleans up database and request context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, identifier: str, password: str):
        """Helper to sign in via web session."""
        return self.client.post("/login", data={
            "identifier": identifier,
            "password": password
        }, follow_redirects=True)

    # =========================================================================
    # 1. Centralized Error Handling & Content Negotiation Tests
    # =========================================================================

    def test_404_api_returns_structured_json(self):
        """Verifies missing API routes return structured JSON with 404 status."""
        resp = self.client.get("/api/nonexistent-endpoint")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], 404)
        self.assertEqual(data["error"]["type"], "NotFound")
        self.assertIn("timestamp", data)

    def test_404_browser_renders_html_template(self):
        """Verifies missing browser routes render styled error template."""
        resp = self.client.get("/nonexistent-page-url", headers={"Accept": "text/html"})
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"404 - Resource Not Found", resp.data)
        self.assertIn(b"Reference Code:", resp.data)

    def test_405_method_not_allowed_negotiation(self):
        """Verifies 405 Method Not Allowed returns JSON for API and HTML for browser."""
        # API route
        resp_api = self.client.post("/api/health")
        self.assertEqual(resp_api.status_code, 405)
        self.assertEqual(resp_api.content_type, "application/json")
        data_api = resp_api.get_json()
        self.assertEqual(data_api["error"]["code"], 405)

        # Browser route
        resp_browser = self.client.post("/about", headers={"Accept": "text/html"})
        self.assertEqual(resp_browser.status_code, 405)
        self.assertIn(b"405", resp_browser.data)

    def test_401_unauthorized_api_returns_structured_json(self):
        """Verifies unauthenticated API access returns HTTP 401 with structured JSON."""
        resp = self.client.get("/api/predictions")
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("authenticated", True))

    def test_403_forbidden_analyst_accessing_admin_api(self):
        """Verifies analyst cannot access admin audit logs or users API."""
        self._login("harden_analyst", "AnalystSecurePass123!")
        resp = self.client.get("/api/users")
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data["error_type"], "AuthorizationError")

    def test_500_error_response_safety_no_leakage(self):
        """Verifies 500 error response hides stack traces and internal secrets."""
        self._login("harden_analyst", "AnalystSecurePass123!")
        # Force a route to raise an unexpected runtime error
        with patch("app.models.transaction.Transaction.query") as mock_query:
            mock_query.count.side_effect = RuntimeError("Simulated internal DB failure")
            resp = self.client.get("/api/stats")
            self.assertEqual(resp.status_code, 500)
            data = resp.get_json()
            self.assertEqual(data["status"], "error")
            # Must not expose raw Python traceback
            self.assertNotIn("Traceback", resp.get_data(as_text=True))

    # =========================================================================
    # 2. Dual Authentication Tests (Email vs Username)
    # =========================================================================

    def test_login_with_username(self):
        """Verifies login succeeds when providing username."""
        resp = self._login("harden_admin", "AdminSecurePass123!")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"harden_admin", resp.data)

    def test_login_with_email(self):
        """Verifies login succeeds when providing email address."""
        resp = self._login("harden_admin@test.local", "AdminSecurePass123!")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"harden_admin", resp.data)

    def test_api_login_with_email(self):
        """Verifies /api/auth/login succeeds with email identifier."""
        resp = self.client.post("/api/auth/login", json={
            "identifier": "harden_analyst@test.local",
            "password": "AnalystSecurePass123!"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], "harden_analyst")

    # =========================================================================
    # 3. Security Response Headers Tests
    # =========================================================================

    def test_security_headers_enforcement(self):
        """Verifies comprehensive defense-in-depth security headers on all responses."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertEqual(resp.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertIn("Permissions-Policy", resp.headers)
        self.assertIn("Content-Security-Policy", resp.headers)

    # =========================================================================
    # 4. Rate Limiter Unit Tests
    # =========================================================================

    def test_sliding_window_rate_limiter_logic(self):
        """Verifies sliding window rate limiter tracking and cooldown calculation."""
        test_limiter = InMemoryRateLimiter()
        key = "test_client_ip"

        # Allow first 3 requests
        for i in range(3):
            allowed, remaining, retry_after = test_limiter.is_allowed(key, max_requests=3, window_seconds=10)
            self.assertTrue(allowed)
            self.assertEqual(remaining, 2 - i)
            self.assertEqual(retry_after, 0)

        # 4th request must be denied
        allowed, remaining, retry_after = test_limiter.is_allowed(key, max_requests=3, window_seconds=10)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 10)

        # Reset limiter
        test_limiter.reset()
        allowed, remaining, _ = test_limiter.is_allowed(key, max_requests=3, window_seconds=10)
        self.assertTrue(allowed)

    # =========================================================================
    # 5. Database Rollback and Error Safety
    # =========================================================================

    def test_database_rollback_on_session_error(self):
        """Verifies database transactions roll back cleanly without leaving hanging transactions."""
        initial_count = Transaction.query.count()
        try:
            # Create a broken transaction that fails constraint
            txn = Transaction(amount=-999.0)  # Violates expected schema
            db.session.add(txn)
            db.session.flush()
        except Exception:
            db.session.rollback()

        # Database state must be clean and uncorrupted
        current_count = Transaction.query.count()
        self.assertEqual(initial_count, current_count)

    # =========================================================================
    # 6. Public Diagnostics Health Check Integrity
    # =========================================================================

    def test_health_check_public_no_secret_exposure(self):
        """Verifies /api/health exposes diagnostics without exposing secrets or connection URLs."""
        resp = self.client.get("/api/health")
        self.assertIn(resp.status_code, [200, 500])
        data = resp.get_json()

        self.assertIn("status", data)
        self.assertIn("service", data)
        self.assertIn("database", data)

        # Must not expose secret keys or raw credentials
        text = resp.get_data(as_text=True)
        self.assertNotIn("SECRET_KEY", text)
        self.assertNotIn("AdminPassword123!", text)
        self.assertNotIn("password_hash", text)


if __name__ == "__main__":
    unittest.main()
