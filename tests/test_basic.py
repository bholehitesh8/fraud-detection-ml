"""
Basic Verification and Regression Tests
---------------------------------------
Validates Flask application initialization, SQLite database operations,
route HTTP status codes, and feature preprocessing integrity.
"""

import unittest
from app import create_app
from app.models import db
from app.models.transaction import Transaction
from app.ml.preprocessor import TransactionPreprocessor
from app.utils.helpers import validate_transaction_data, determine_risk_level


class BasicTestCase(unittest.TestCase):
    """Test suite for core application foundation."""

    def setUp(self):
        """Initializes isolated in-memory test application and test client."""
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        from app.utils.auth import seed_default_users
        from app.models.user import User
        seed_default_users(self.app)
        user = User.query.filter_by(role="analyst").first() or User.query.first()
        if user:
            with self.client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["username"] = user.username
                sess["role"] = user.role

    def tearDown(self):
        """Cleans up in-memory database and context."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_app_exists(self):
        """Verifies Flask instance is properly created."""
        self.assertIsNotNone(self.app)
        self.assertTrue(self.app.config["TESTING"])

    def test_database_persistence(self):
        """Verifies SQLite database can create and query Transaction records."""
        txn = Transaction(
            amount=1500.0,
            transaction_type="TRANSFER",
            old_balance_org=1500.0,
            new_balance_orig=0.0,
            sender_account="AC-TEST1",
            receiver_account="AC-TEST2",
            is_fraud=True,
            prediction_label="Fraudulent",
            confidence_score=92.5,
            risk_level="Critical"
        )
        db.session.add(txn)
        db.session.commit()

        retrieved = Transaction.query.filter_by(sender_account="AC-TEST1").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.amount, 1500.0)
        self.assertTrue(retrieved.is_fraud)
        self.assertEqual(retrieved.risk_level, "Critical")

    def test_home_route(self):
        """Verifies GET / returns HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Fraud Detection in Online Transactions", response.data)

    def test_predict_get_route(self):
        """Verifies GET /predict returns HTTP 200."""
        response = self.client.get("/predict")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Online Transaction Evaluation", response.data)

    def test_dashboard_route(self):
        """Verifies GET /dashboard returns HTTP 200."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Transaction Security Audit Log", response.data)

    def test_about_route(self):
        """Verifies GET /about returns HTTP 200."""
        response = self.client.get("/about")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Viva Voce Defense Questions", response.data)

    def test_api_health(self):
        """Verifies GET /api/health returns HTTP 200 and healthy status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")

    def test_feature_preprocessor(self):
        """Verifies feature extraction vector format and lengths."""
        raw = {
            "amount": 200.0,
            "old_balance_org": 1000.0,
            "new_balance_orig": 800.0,
            "transaction_type": "PAYMENT"
        }
        vec = TransactionPreprocessor.to_feature_vector(raw)
        self.assertEqual(len(vec), 11)
        self.assertEqual(vec[0], 200.0)  # amount

    def test_risk_level_helper(self):
        """Verifies risk level calculation logic."""
        self.assertEqual(determine_risk_level(0.95), "Critical")
        self.assertEqual(determine_risk_level(0.65), "High")
        self.assertEqual(determine_risk_level(0.35), "Moderate")
        self.assertEqual(determine_risk_level(0.10), "Low")

    def test_validation_helper(self):
        """Verifies input validation handles empty/invalid payloads."""
        valid, msg = validate_transaction_data({"amount": -50, "transaction_type": "PAYMENT"})
        self.assertFalse(valid)

        valid, msg = validate_transaction_data({"amount": 50, "transaction_type": "INVALID_TYPE"})
        self.assertFalse(valid)

        valid, msg = validate_transaction_data({"amount": 50, "transaction_type": "PAYMENT"})
        self.assertTrue(valid)

    def test_predict_form_post(self):
        """Verifies POST /predict processes transaction and logs to SQLite."""
        form_payload = {
            "amount": "45.00",
            "transaction_type": "PAYMENT",
            "old_balance_org": "1200.00",
            "new_balance_orig": "1155.00",
            "sender_account": "AC-11112222",
            "receiver_account": "MC-33334444",
            "device_type": "Mobile",
            "location": "Domestic"
        }
        response = self.client.post("/predict", data=form_payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Transaction successfully evaluated and recorded in database!", response.data)
        
        # Verify saved in SQLite
        saved = Transaction.query.filter_by(amount=45.00).first()
        self.assertIsNotNone(saved)
        self.assertIn("Legitimate", saved.prediction_label)

    def test_api_predict_json(self):
        """Verifies POST /api/predict returns structured JSON inference."""
        json_payload = {
            "amount": 45000.00,
            "transaction_type": "TRANSFER",
            "old_balance_org": 45000.00,
            "new_balance_orig": 0.00,
            "sender_account": "AC-99998888",
            "receiver_account": "AC-00001111"
        }
        response = self.client.post("/api/predict", json=json_payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("is_fraud", data)
        self.assertIn("confidence_score", data)
        self.assertIn("risk_level", data)
        self.assertIn("transaction_ref", data)


if __name__ == "__main__":
    unittest.main()
