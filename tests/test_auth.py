"""
Comprehensive Automated Test Suite for Authentication & User Management (Prompt 8)
----------------------------------------------------------------------------------
Validates:
1. User model instantiation, password hashing, constant-time verification, and PII protection.
2. Unique username and email constraints.
3. User login flow, invalid credentials, deactivated account rejection.
4. User logout flow and session clearing.
5. Self-registration with validation (length, regex, mismatch, analyst role default).
6. Role-Based Access Control (RBAC) on protected pages and admin portal.
7. Current user API (GET /api/auth/me) for authenticated and unauthenticated states.
8. API authentication (POST /api/auth/login, POST /api/auth/logout).
9. Protected API endpoints return 401 when unauthenticated.
10. System health API (GET /api/health) remains public without requiring authentication.
"""

import unittest
from app import create_app
from app.models import db
from app.models.user import User


class AuthenticationTestCase(unittest.TestCase):
    """Test suite for authentication models, sessions, and authorization."""

    def setUp(self):
        """Initializes isolated in-memory test application and test client."""
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Create baseline test accounts
        self.admin = User(
            username="testadmin",
            email="admin@test.com",
            role="admin",
            is_active=True
        )
        self.admin.set_password("AdminSecurePass123!")
        db.session.add(self.admin)

        self.analyst = User(
            username="testanalyst",
            email="analyst@test.com",
            role="analyst",
            is_active=True
        )
        self.analyst.set_password("AnalystSecurePass123!")
        db.session.add(self.analyst)

        self.inactive_user = User(
            username="inactiveuser",
            email="inactive@test.com",
            role="analyst",
            is_active=False
        )
        self.inactive_user.set_password("InactivePass123!")
        db.session.add(self.inactive_user)

        db.session.commit()

    def tearDown(self):
        """Cleans up database and application context."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self, username, password):
        """Helper to log in via POST /login form."""
        return self.client.post("/login", data={
            "identifier": username,
            "password": password
        }, follow_redirects=True)

    def _login_session(self, user):
        """Helper to establish an authenticated session directly in test client."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["username"] = user.username
            sess["role"] = user.role

    # ==========================================================================
    # 1. User Model & Password Security Tests
    # ==========================================================================

    def test_user_password_hashing(self):
        """Verifies passwords are never stored in plaintext and verify correctly."""
        user = User(username="newuser", email="new@test.com", role="analyst")
        user.set_password("Secret123Pass!")
        db.session.add(user)
        db.session.commit()

        # Hash must not contain plaintext password
        self.assertNotIn("Secret123Pass!", user.password_hash)
        self.assertTrue(user.password_hash.startswith(("scrypt:", "pbkdf2:")))
        self.assertTrue(user.check_password("Secret123Pass!"))
        self.assertFalse(user.check_password("WrongPassword123!"))
        self.assertFalse(user.check_password(""))

    def test_user_to_dict_never_exposes_password_hash(self):
        """Verifies serialized user dictionary omits sensitive authentication data."""
        user_dict = self.admin.to_dict()
        self.assertEqual(user_dict["username"], "testadmin")
        self.assertEqual(user_dict["role"], "admin")
        self.assertNotIn("password", user_dict)
        self.assertNotIn("password_hash", user_dict)

    def test_unique_username_and_email_constraints(self):
        """Verifies database uniqueness constraints on username and email."""
        dup_username = User(username="testadmin", email="different@test.com")
        dup_username.set_password("SomePass123!")
        db.session.add(dup_username)
        with self.assertRaises(Exception):
            db.session.commit()
        db.session.rollback()

        dup_email = User(username="differentuser", email="admin@test.com")
        dup_email.set_password("SomePass123!")
        db.session.add(dup_email)
        with self.assertRaises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_user_role_properties(self):
        """Verifies is_admin and is_analyst helper properties."""
        self.assertTrue(self.admin.is_admin)
        self.assertTrue(self.admin.is_analyst)
        self.assertFalse(self.analyst.is_admin)
        self.assertTrue(self.analyst.is_analyst)

    # ==========================================================================
    # 2. Web Authentication Flow Tests (Login, Logout, Register)
    # ==========================================================================

    def test_login_page_renders_cleanly(self):
        """Verifies GET /login displays login form and branding."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"FraudGuard ML Access Control", response.data)
        self.assertIn(b"Sign In to Dashboard", response.data)

    def test_login_success(self):
        """Verifies successful login redirects to dashboard and sets session."""
        response = self._login("testadmin", "AdminSecurePass123!")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back, testadmin!", response.data)

        # Check session
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), self.admin.id)
            self.assertEqual(sess.get("username"), "testadmin")

    def test_login_with_email(self):
        """Verifies user can log in using email address as identifier."""
        response = self._login("analyst@test.com", "AnalystSecurePass123!")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back, testanalyst!", response.data)

    def test_login_invalid_password(self):
        """Verifies failed login on incorrect password."""
        response = self._login("testadmin", "IncorrectPassword999!")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid username/email or password", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_login_nonexistent_user(self):
        """Verifies failed login on non-existent account."""
        response = self._login("nonexistent", "SomePassword123!")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid username/email or password", response.data)

    def test_login_deactivated_account_rejected(self):
        """Verifies deactivated accounts cannot sign in."""
        response = self._login("inactiveuser", "InactivePass123!")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This account has been deactivated", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_logout_clears_session(self):
        """Verifies logging out clears user session and redirects to login."""
        self._login_session(self.admin)
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"logged out successfully", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_registration_success_creates_analyst_role(self):
        """Verifies self-registration successfully creates analyst user."""
        payload = {
            "username": "newanalyst",
            "email": "newanalyst@institution.edu",
            "password": "StrongPassword2026!",
            "confirm_password": "StrongPassword2026!"
        }
        response = self.client.post("/register", data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registration successful", response.data)

        created = User.query.filter_by(username="newanalyst").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.role, "analyst")
        self.assertTrue(created.check_password("StrongPassword2026!"))

    def test_registration_validation_errors(self):
        """Verifies registration rejects weak passwords and mismatched inputs."""
        # Short password
        res = self.client.post("/register", data={
            "username": "baduser",
            "email": "bad@test.com",
            "password": "short",
            "confirm_password": "short"
        }, follow_redirects=True)
        self.assertIn(b"at least 8 characters", res.data)

        # Mismatched confirmation
        res = self.client.post("/register", data={
            "username": "mismatchuser",
            "email": "mismatch@test.com",
            "password": "ValidPassword123!",
            "confirm_password": "DifferentPassword123!"
        }, follow_redirects=True)
        self.assertIn(b"do not match", res.data)

        # Duplicate username
        res = self.client.post("/register", data={
            "username": "testadmin",
            "email": "unique@test.com",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!"
        }, follow_redirects=True)
        self.assertIn(b"already taken", res.data)

    # ==========================================================================
    # 3. Role-Based Access Control (RBAC) & Protected Pages
    # ==========================================================================

    def test_unauthenticated_page_access_redirects_to_login(self):
        """Verifies accessing /dashboard or /predict unauthenticated redirects to /login."""
        for path in ["/dashboard", "/predict"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/login", res.headers["Location"])

    def test_authenticated_analyst_can_access_dashboard_and_predict(self):
        """Verifies analyst can access /dashboard and /predict."""
        self._login_session(self.analyst)
        res1 = self.client.get("/dashboard")
        self.assertEqual(res1.status_code, 200)
        res2 = self.client.get("/predict")
        self.assertEqual(res2.status_code, 200)

    def test_analyst_cannot_access_admin_portal(self):
        """Verifies analyst is denied access to /admin/users (HTTP 302 redirect with flash)."""
        self._login_session(self.analyst)
        res = self.client.get("/admin/users", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Access denied", res.data)

    def test_admin_can_access_admin_portal(self):
        """Verifies admin can access /admin/users."""
        self._login_session(self.admin)
        res = self.client.get("/admin/users")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"User Identity &amp; Access Administration", response_data := res.data)
        self.assertIn(b"testadmin", response_data)

    def test_admin_create_user_with_role(self):
        """Verifies admin can provision new accounts with designated roles."""
        self._login_session(self.admin)
        payload = {
            "username": "secondadmin",
            "email": "second@test.com",
            "role": "admin",
            "password": "SecondAdminPass123!"
        }
        res = self.client.post("/admin/users/create", data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"successfully created", res.data)

        u = User.query.filter_by(username="secondadmin").first()
        self.assertIsNotNone(u)
        self.assertEqual(u.role, "admin")

    def test_admin_toggle_user_status(self):
        """Verifies admin can toggle another user's active status."""
        self._login_session(self.admin)
        res = self.client.post(f"/admin/users/{self.analyst.id}/toggle-status", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.analyst.is_active)

    # ==========================================================================
    # 4. API Authentication & Current User Endpoint Tests
    # ==========================================================================

    def test_api_auth_me_unauthenticated(self):
        """Verifies GET /api/auth/me reports unauthenticated status when not signed in."""
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["authenticated"])
        self.assertIsNone(data["user"])

    def test_api_auth_me_authenticated(self):
        """Verifies GET /api/auth/me returns safe profile when signed in."""
        self._login_session(self.analyst)
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["authenticated"])
        self.assertIsNotNone(data["user"])
        self.assertEqual(data["user"]["username"], "testanalyst")
        self.assertEqual(data["user"]["role"], "analyst")
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

    def test_api_login_and_logout_endpoints(self):
        """Verifies POST /api/auth/login and POST /api/auth/logout JSON API."""
        # 1. Login
        res = self.client.post("/api/auth/login", json={
            "identifier": "testanalyst",
            "password": "AnalystSecurePass123!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], "testanalyst")

        # 2. Check /api/auth/me
        res_me = self.client.get("/api/auth/me")
        self.assertTrue(res_me.get_json()["authenticated"])

        # 3. Logout
        res_out = self.client.post("/api/auth/logout")
        self.assertEqual(res_out.status_code, 200)
        self.assertTrue(res_out.get_json()["success"])

        # 4. Check /api/auth/me is now unauthenticated
        res_me2 = self.client.get("/api/auth/me")
        self.assertFalse(res_me2.get_json()["authenticated"])

    def test_protected_apis_return_401_unauthenticated(self):
        """Verifies sensitive API endpoints require authentication (return HTTP 401)."""
        endpoints = [
            ("POST", "/api/predict", {"amount": 100.0, "transaction_type": "PAYMENT"}),
            ("GET", "/api/predictions", None),
            ("GET", "/api/analytics/summary", None),
            ("GET", "/api/stats", None)
        ]

        for method, url, payload in endpoints:
            if method == "POST":
                res = self.client.post(url, json=payload)
            else:
                res = self.client.get(url)
            self.assertEqual(res.status_code, 401, f"Expected 401 for {method} {url}")
            data = res.get_json()
            self.assertFalse(data.get("authenticated", True))

    def test_health_check_remains_public(self):
        """Verifies GET /api/health is publicly accessible without login."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["api_running"])
