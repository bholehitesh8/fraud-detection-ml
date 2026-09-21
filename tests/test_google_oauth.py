"""
Automated Test Suite for Google OAuth 2.0 / OpenID Connect Authentication
-------------------------------------------------------------------------
Validates:
1. Google login route redirection to Google authorization URL with CSRF state token.
2. Graceful warning when Google OAuth credentials are not configured.
3. OAuth callback handling for user cancellation (error=access_denied).
4. OAuth callback handling for generic Google errors.
5. CSRF state parameter validation (missing, mismatched, or altered state rejected).
6. Missing authorization code rejected.
7. Token exchange failure handled gracefully.
8. Unverified email from Google rejected.
9. Existing user with verified email authenticated into existing account without duplication.
10. Inactive user account blocked from logging in via Google.
11. New user provisioned automatically with default 'analyst' role and random unusable password.
12. Session creation and integration with /api/auth/me.
13. Logout clearing Google-authenticated session.
14. Normal username/email + password login remains fully operational.
15. Login UI renders the "Continue with Google" button.
"""

import unittest
from unittest.mock import patch
from app import create_app
from app.models import db
from app.models.user import User


class GoogleOAuthTestCase(unittest.TestCase):
    """Unit and integration test cases for Google OAuth 2.0 authentication."""

    def setUp(self):
        """Initializes isolated in-memory test database and client."""
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed baseline accounts
        self.admin = User(
            username="testadmin",
            email="admin@test.com",
            role="admin",
            is_active=True
        )
        self.admin.set_password("AdminSecurePass123!")
        db.session.add(self.admin)

        self.existing_user = User(
            username="analyst_jane",
            email="jane.doe@example.com",
            role="analyst",
            is_active=True
        )
        self.existing_user.set_password("AnalystSecurePass123!")
        db.session.add(self.existing_user)

        self.inactive_user = User(
            username="inactive_john",
            email="john.inactive@example.com",
            role="analyst",
            is_active=False
        )
        self.inactive_user.set_password("InactivePass123!")
        db.session.add(self.inactive_user)

        db.session.commit()

    def tearDown(self):
        """Cleans up database and context."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_google_login_button_rendered_on_login_page(self):
        """Verifies GET /login displays the 'Continue with Google' button and divider."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Continue with Google", content)
        self.assertIn("googleLoginBtn", content)
        self.assertIn("auth-divider", content)
        # Normal login must still be present
        self.assertIn("Sign In to Dashboard", content)
        self.assertIn("Email or Username", content)

    def test_google_login_redirect_to_google_when_configured(self):
        """Verifies GET /auth/google/login sets session state and redirects to accounts.google.com."""
        response = self.client.get("/auth/google/login")
        self.assertEqual(response.status_code, 302)
        redirect_url = response.headers.get("Location")
        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth", redirect_url)
        self.assertIn("client_id=mock-google-client-id.apps.googleusercontent.com", redirect_url)
        self.assertIn("response_type=code", redirect_url)
        self.assertIn("scope=openid+email+profile", redirect_url)
        self.assertIn("state=", redirect_url)

        # Verify state is saved in session
        with self.client.session_transaction() as sess:
            self.assertIn("oauth_state", sess)
            self.assertTrue(len(sess["oauth_state"]) >= 20)

    def test_google_login_not_configured_shows_graceful_flash(self):
        """Verifies GET /auth/google/login handles unconfigured credentials gracefully."""
        # Temporarily clear credentials
        self.app.config["GOOGLE_CLIENT_ID"] = ""
        self.app.config["GOOGLE_CLIENT_SECRET"] = ""

        response = self.client.get("/auth/google/login", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Google Sign-In is not configured on this server", content)

        # Restore credentials
        self.app.config["GOOGLE_CLIENT_ID"] = "mock-google-client-id.apps.googleusercontent.com"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "mock-google-client-secret-key"

    def test_google_callback_cancelled_by_user(self):
        """Verifies callback handles access_denied error when user cancels Google login."""
        response = self.client.get("/auth/google/callback?error=access_denied", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Google sign-in was cancelled.", content)

    def test_google_callback_oauth_error(self):
        """Verifies callback handles other OAuth errors from Google."""
        response = self.client.get("/auth/google/callback?error=server_error", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Google authentication failed. Please try again.", content)

    def test_google_callback_missing_state_csrf_rejected(self):
        """Verifies callback without state or mismatched state is rejected."""
        response = self.client.get("/auth/google/callback?code=mock_code&state=fake_state", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Unable to complete Google sign-in right now.", content)

    def test_google_callback_missing_code_rejected(self):
        """Verifies callback with valid state but missing authorization code is rejected."""
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        response = self.client.get("/auth/google/callback?state=valid_test_state_123", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Google authentication failed. Please try again.", content)

    @patch("app.routes.auth_routes.exchange_code_for_tokens")
    def test_google_callback_token_exchange_failure(self, mock_exchange):
        """Verifies callback handles network/token exchange failure gracefully."""
        mock_exchange.side_effect = RuntimeError("Connection timed out")

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        response = self.client.get(
            "/auth/google/callback?code=auth_code_xyz&state=valid_test_state_123",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Unable to complete Google sign-in right now.", content)

    @patch("app.routes.auth_routes.get_google_user_info")
    @patch("app.routes.auth_routes.exchange_code_for_tokens")
    def test_google_callback_unverified_email_rejected(self, mock_exchange, mock_userinfo):
        """Verifies Google accounts with unverified emails are strictly rejected."""
        mock_exchange.return_value = {"access_token": "mock_access_token_123"}
        mock_userinfo.return_value = {
            "email": "unverified@example.com",
            "email_verified": False,
            "sub": "google-sub-12345"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        response = self.client.get(
            "/auth/google/callback?code=valid_code&state=valid_test_state_123",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Google authentication failed. Please try again.", content)

    @patch("app.routes.auth_routes.get_google_user_info")
    @patch("app.routes.auth_routes.exchange_code_for_tokens")
    def test_google_callback_existing_user_signs_in_without_duplicate(self, mock_exchange, mock_userinfo):
        """Verifies existing user with matching verified email signs in without creating duplicate account."""
        mock_exchange.return_value = {"access_token": "mock_access_token_123"}
        mock_userinfo.return_value = {
            "email": "jane.doe@example.com",
            "email_verified": True,
            "sub": "google-sub-jane-123",
            "name": "Jane Doe"
        }

        user_count_before = User.query.count()

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        response = self.client.get(
            "/auth/google/callback?code=valid_code&state=valid_test_state_123",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)

        # No duplicate user created
        user_count_after = User.query.count()
        self.assertEqual(user_count_before, user_count_after)

        # Session established
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), self.existing_user.id)
            self.assertEqual(sess.get("username"), "analyst_jane")

        # API /api/auth/me returns this authenticated user
        me_resp = self.client.get("/api/auth/me")
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.get_json()
        self.assertTrue(me_data.get("authenticated"))
        self.assertEqual(me_data["user"]["email"], "jane.doe@example.com")
        self.assertEqual(me_data["user"]["role"], "analyst")

    @patch("app.routes.auth_routes.get_google_user_info")
    @patch("app.routes.auth_routes.exchange_code_for_tokens")
    def test_google_callback_inactive_user_blocked(self, mock_exchange, mock_userinfo):
        """Verifies inactive/deactivated users cannot authenticate via Google."""
        mock_exchange.return_value = {"access_token": "mock_access_token_123"}
        mock_userinfo.return_value = {
            "email": "john.inactive@example.com",
            "email_verified": True,
            "sub": "google-sub-inactive-123"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        response = self.client.get(
            "/auth/google/callback?code=valid_code&state=valid_test_state_123",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("This account is inactive.", content)

        # Ensure no session is active
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    @patch("app.routes.auth_routes.get_google_user_info")
    @patch("app.routes.auth_routes.exchange_code_for_tokens")
    def test_google_callback_new_user_provisioned_as_analyst(self, mock_exchange, mock_userinfo):
        """Verifies new user from Google is provisioned as analyst with random unusable password."""
        mock_exchange.return_value = {"access_token": "mock_access_token_123"}
        new_email = "alex.newuser@example.com"
        mock_userinfo.return_value = {
            "email": new_email,
            "email_verified": True,
            "sub": "google-sub-alex-999",
            "name": "Alex NewUser"
        }

        user_count_before = User.query.count()

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        response = self.client.get(
            "/auth/google/callback?code=valid_code&state=valid_test_state_123",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)

        # 1 new user created
        user_count_after = User.query.count()
        self.assertEqual(user_count_after, user_count_before + 1)

        new_user = User.query.filter_by(email=new_email).first()
        self.assertIsNotNone(new_user)
        # Default role must strictly be analyst, never admin
        self.assertEqual(new_user.role, "analyst")
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.username.startswith("alex_newuser"))
        # Password hash exists and is non-empty
        self.assertTrue(len(new_user.password_hash) > 20)

        # Session established
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), new_user.id)
            self.assertEqual(sess.get("username"), new_user.username)

    @patch("app.routes.auth_routes.get_google_user_info")
    @patch("app.routes.auth_routes.exchange_code_for_tokens")
    def test_logout_after_google_login(self, mock_exchange, mock_userinfo):
        """Verifies logging out properly terminates Google-authenticated session."""
        mock_exchange.return_value = {"access_token": "mock_access_token_123"}
        mock_userinfo.return_value = {
            "email": "jane.doe@example.com",
            "email_verified": True,
            "sub": "google-sub-jane-123"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid_test_state_123"

        # Sign in via Google
        self.client.get("/auth/google/callback?code=valid_code&state=valid_test_state_123")

        # Call logout
        logout_resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

        # Verify /api/auth/me shows unauthenticated
        me_resp = self.client.get("/api/auth/me")
        self.assertFalse(me_resp.get_json().get("authenticated"))

    def test_normal_password_login_remains_functional(self):
        """Verifies standard username/password login continues to work alongside Google login."""
        # Login with testadmin
        resp = self.client.post("/login", data={
            "identifier": "testadmin",
            "password": "AdminSecurePass123!"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("username"), "testadmin")


if __name__ == "__main__":
    unittest.main()
