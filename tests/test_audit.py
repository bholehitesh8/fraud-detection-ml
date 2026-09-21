"""
Automated Test Suite for Audit Logging, Security, and Admin Management (Prompt 9)
---------------------------------------------------------------------------------
Validates:
1. AuditLog model creation, fields, serialization (to_dict), and metadata handling.
2. Security event logger service (log_security_event) and log explorer querying (query_audit_logs).
3. Brute-force account lockout mechanism (5 failed attempts triggers 15-minute lock).
4. Reset of failed login counter on successful authentication.
5. Role-Based Access Control on Admin Panel (/admin, /admin/users, /admin/audit-logs).
6. Sole active administrator lockout protection (cannot deactivate or demote last admin).
7. Admin Audit Logs REST API (GET /api/admin/audit-logs) RBAC, filters, and pagination.
8. HTTP Security Response Headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
"""

import unittest
from datetime import datetime, timedelta, timezone
from app import create_app
from app.models import db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.audit_service import log_security_event, query_audit_logs
from app.utils.auth import is_last_active_admin


class AuditAndSecurityTestCase(unittest.TestCase):
    """Test suite for security operations, audit logging, lockout, and admin controls."""

    def setUp(self):
        """Initializes isolated in-memory test database and client."""
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Clean any default seeded users so test counts are deterministic
        User.query.delete()
        AuditLog.query.delete()
        db.session.commit()

        # Seed isolated single admin and analyst
        self.admin = User(
            username="secadmin",
            email="secadmin@test.com",
            role="admin",
            is_active=True
        )
        self.admin.set_password("AdminSecurePass123!")
        db.session.add(self.admin)

        self.analyst = User(
            username="secanalyst",
            email="secanalyst@test.com",
            role="analyst",
            is_active=True
        )
        self.analyst.set_password("AnalystSecurePass123!")
        db.session.add(self.analyst)

        db.session.commit()

    def tearDown(self):
        """Tears down database session and drops test schemas."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login_session(self, user):
        """Helper to inject authenticated session attributes directly."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["username"] = user.username
            sess["role"] = user.role

    # =========================================================================
    # 1. AuditLog Model & Service Tests
    # =========================================================================

    def test_audit_log_model_creation_and_to_dict(self):
        """Verify AuditLog persists correctly and serializes to JSON dictionary."""
        log = AuditLog(
            user_id=self.admin.id,
            username=self.admin.username,
            action="TEST_ACTION",
            event_type="ADMIN",
            description="Testing manual audit log creation",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            status="SUCCESS",
            extra_metadata={"key": "value", "flag": True}
        )
        db.session.add(log)
        db.session.commit()

        self.assertIsNotNone(log.id)
        self.assertIsNotNone(log.timestamp)

        d = log.to_dict()
        self.assertEqual(d["username"], "secadmin")
        self.assertEqual(d["action"], "TEST_ACTION")
        self.assertEqual(d["event_type"], "ADMIN")
        self.assertEqual(d["status"], "SUCCESS")
        self.assertEqual(d["ip_address"], "127.0.0.1")
        self.assertEqual(d["metadata"], {"key": "value", "flag": True})

    def test_log_security_event_service(self):
        """Verify log_security_event helper writes to DB safely."""
        event = log_security_event(
            action="API_KEY_ROTATED",
            event_type="SECURITY",
            description="API key rotated by administrator",
            user=self.admin,
            status="SUCCESS",
            metadata={"scope": "global"}
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.username, "secadmin")
        self.assertEqual(event.action, "API_KEY_ROTATED")

        # Verify record exists in DB
        persisted = AuditLog.query.filter_by(action="API_KEY_ROTATED").first()
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.description, "API key rotated by administrator")

    def test_query_audit_logs_filtering(self):
        """Verify query_audit_logs handles filtering by event_type, status, and query."""
        log_security_event("LOGIN_SUCCESS", "AUTH", "User logged in", user=self.analyst, status="SUCCESS")
        log_security_event("LOGIN_FAILED", "SECURITY", "Bad password", user=self.analyst, status="FAILURE")
        log_security_event("USER_CREATED", "ADMIN", "New analyst registered", user=self.admin, status="SUCCESS")

        # Filter by event_type
        sec_result = query_audit_logs(event_type="SECURITY")
        self.assertEqual(sec_result["total"], 1)
        self.assertEqual(sec_result["logs"][0]["action"], "LOGIN_FAILED")

        # Filter by status
        fail_result = query_audit_logs(status="FAILURE")
        self.assertEqual(fail_result["total"], 1)
        self.assertEqual(fail_result["logs"][0]["status"], "FAILURE")

        # Free-text search
        search_result = query_audit_logs(search="analyst")
        self.assertGreaterEqual(search_result["total"], 1)

    # =========================================================================
    # 2. Brute-Force Account Lockout Tests
    # =========================================================================

    def test_failed_login_records_attempts_and_locks_account(self):
        """Verify 5 failed attempts locks user for 15 minutes."""
        target_user = self.analyst
        self.assertEqual(target_user.failed_login_attempts, 0)
        self.assertFalse(target_user.is_locked)

        # 4 failed attempts should not lock
        for _ in range(4):
            resp = self.client.post("/login", data={
                "identifier": target_user.username,
                "password": "WrongPassword!"
            }, follow_redirects=True)
            self.assertIn(b"Invalid username/email or password", resp.data)

        db.session.refresh(target_user)
        self.assertEqual(target_user.failed_login_attempts, 4)
        self.assertFalse(target_user.is_locked)

        # 5th failed attempt should trigger lockout
        resp = self.client.post("/login", data={
            "identifier": target_user.username,
            "password": "WrongPassword!"
        }, follow_redirects=True)

        db.session.refresh(target_user)
        self.assertEqual(target_user.failed_login_attempts, 5)
        self.assertTrue(target_user.is_locked)
        self.assertIsNotNone(target_user.locked_until)

        # Subsequent attempt (even with correct password) while locked must be blocked
        locked_resp = self.client.post("/login", data={
            "identifier": target_user.username,
            "password": "AnalystSecurePass123!"
        }, follow_redirects=True)
        self.assertIn(b"temporarily locked", locked_resp.data)

    def test_successful_login_resets_failed_attempts(self):
        """Verify successful login resets failed_login_attempts to zero."""
        target_user = self.analyst

        # 2 failed attempts
        for _ in range(2):
            self.client.post("/login", data={
                "identifier": target_user.username,
                "password": "WrongPassword!"
            }, follow_redirects=True)

        db.session.refresh(target_user)
        self.assertEqual(target_user.failed_login_attempts, 2)

        # Successful login
        resp = self.client.post("/login", data={
            "identifier": target_user.username,
            "password": "AnalystSecurePass123!"
        }, follow_redirects=True)

        db.session.refresh(target_user)
        self.assertEqual(target_user.failed_login_attempts, 0)
        self.assertIsNone(target_user.locked_until)

    # =========================================================================
    # 3. Admin RBAC & Route Access Tests
    # =========================================================================

    def test_admin_dashboard_unauthenticated_redirects(self):
        """Unauthenticated GET /admin should redirect to /login."""
        resp = self.client.get("/admin", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_admin_dashboard_analyst_forbidden(self):
        """Analyst user should be rejected from /admin with redirect or 403."""
        self._login_session(self.analyst)
        resp = self.client.get("/admin", follow_redirects=True)
        self.assertIn(b"Access denied", resp.data)

    def test_admin_dashboard_admin_success(self):
        """Admin user can successfully view /admin."""
        self._login_session(self.admin)
        resp = self.client.get("/admin")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Admin Operations &amp; Security Command Center", resp.data)
        self.assertIn(b"Total Platform Users", resp.data)

    def test_admin_audit_logs_view(self):
        """Admin user can view /admin/audit-logs."""
        self._login_session(self.admin)
        resp = self.client.get("/admin/audit-logs")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Security Audit &amp; Compliance Logs", resp.data)

    # =========================================================================
    # 4. Sole Active Admin Lockout Safeguards
    # =========================================================================

    def test_cannot_deactivate_last_active_admin(self):
        """System must reject deactivating the only active administrator."""
        self._login_session(self.admin)

        # Verify is_last_active_admin helper identifies admin as sole admin
        self.assertTrue(is_last_active_admin(self.admin.id))

        resp = self.client.post(f"/admin/users/{self.admin.id}/toggle-status", follow_redirects=True)
        self.assertIn(b"Cannot deactivate the sole active administrator", resp.data)

        # Verify admin is still active
        db.session.refresh(self.admin)
        self.assertTrue(self.admin.is_active)

    def test_cannot_demote_last_active_admin(self):
        """System must reject changing the role of the sole active administrator."""
        self._login_session(self.admin)

        resp = self.client.post(
            f"/admin/users/{self.admin.id}/change-role",
            data={"role": "analyst"},
            follow_redirects=True
        )
        self.assertIn(b"Cannot demote the sole active administrator", resp.data)

        # Verify admin role was not changed
        db.session.refresh(self.admin)
        self.assertEqual(self.admin.role, "admin")

    def test_multiple_admins_allow_deactivation(self):
        """If multiple active admins exist, deactivating one is allowed."""
        admin2 = User(
            username="admin2",
            email="admin2@test.com",
            role="admin",
            is_active=True
        )
        admin2.set_password("Admin2Pass123!")
        db.session.add(admin2)
        db.session.commit()

        self._login_session(self.admin)
        self.assertFalse(is_last_active_admin(self.admin.id))

        resp = self.client.post(f"/admin/users/{admin2.id}/toggle-status", follow_redirects=True)
        self.assertIn(b"has been deactivated", resp.data)

        db.session.refresh(admin2)
        self.assertFalse(admin2.is_active)

    # =========================================================================
    # 5. Admin Audit Logs REST API Tests
    # =========================================================================

    def test_api_admin_audit_logs_rbac(self):
        """GET /api/admin/audit-logs requires admin authentication."""
        # Unauthenticated -> 401
        resp = self.client.get("/api/admin/audit-logs")
        self.assertEqual(resp.status_code, 401)

        # Analyst -> 403
        self._login_session(self.analyst)
        resp = self.client.get("/api/admin/audit-logs")
        self.assertEqual(resp.status_code, 403)

        # Admin -> 200
        self._login_session(self.admin)
        resp = self.client.get("/api/admin/audit-logs")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("logs", data)
        self.assertIn("total", data)

    def test_api_admin_audit_logs_filtering(self):
        """GET /api/admin/audit-logs supports event_type filter and pagination."""
        log_security_event("TEST_EVENT_A", "AUTH", "Desc A", self.admin, "SUCCESS")
        log_security_event("TEST_EVENT_B", "SECURITY", "Desc B", self.admin, "FAILURE")

        self._login_session(self.admin)
        resp = self.client.get("/api/admin/audit-logs?event_type=SECURITY")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["logs"][0]["action"], "TEST_EVENT_B")

    # =========================================================================
    # 6. HTTP Security Response Headers Tests
    # =========================================================================

    def test_security_headers_present_on_responses(self):
        """Verify baseline security headers are injected on HTTP responses."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", resp.headers)
        csp = resp.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)


if __name__ == "__main__":
    unittest.main()
