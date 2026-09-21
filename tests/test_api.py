"""
Comprehensive Automated Test Suite for Production Flask Backend API
--------------------------------------------------------------------
Validates:
1. Health endpoint (GET /api/health) diagnostics, model status, artifact availability
2. Legitimate and fraudulent prediction requests (POST /api/predict)
3. ISO 4217 multi-currency processing (INR, USD, EUR, GBP, AED, JPY, and arbitrary valid codes)
4. Validation error handling (HTTP 400) for missing fields, non-numeric amounts, negative balances
5. Unsupported transaction types and malformed currency codes
6. Model artifact failure handling (HTTP 500)
7. CORS header configuration and OPTIONS preflight requests
8. Audit database persistence and account number masking
"""

import unittest
import json
from unittest.mock import patch
from app import create_app
from app.models import db
from app.models.transaction import Transaction
from app.ml.prediction_service import get_prediction_service, ModelArtifactError


class ApiTestCase(unittest.TestCase):
    """Test suite for production REST API endpoints."""

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
        """Cleans up database and application context."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_health_endpoint_healthy(self):
        """Verifies GET /api/health reports API running, model loaded, and artifacts available."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["api_running"])
        self.assertEqual(data["database"], "connected")
        self.assertTrue(data["ml_model_loaded"])
        self.assertTrue(data["artifacts_available"])
        self.assertIn("artifacts", data)
        self.assertTrue(data["artifacts"]["model_file"]["exists"])
        self.assertIn("model_details", data)
        self.assertIn("timestamp", data)

    def test_predict_valid_legitimate_transaction(self):
        """Verifies POST /api/predict evaluates standard legitimate payment."""
        payload = {
            "amount": 75.25,
            "transaction_type": "PAYMENT",
            "old_balance_org": 2500.00,
            "new_balance_orig": 2424.75,
            "old_balance_dest": 0.00,
            "new_balance_dest": 0.00,
            "currency": "USD",
            "step": 1,
            "sender_account": "AC-1234567890",
            "receiver_account": "MC-0987654321"
        }
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["is_fraud"])
        self.assertEqual(data["predicted_class"], 0)
        self.assertEqual(data["prediction_label"], "Legitimate")
        self.assertIn(data["risk_level"], ["Low", "Moderate"])
        self.assertEqual(data["currency"], "USD")
        self.assertEqual(data["original_amount"], 75.25)
        self.assertEqual(data["normalized_amount_usd"], 75.25)
        self.assertEqual(data["validation_status"], "Passed")
        self.assertIn("transaction_ref", data)
        self.assertIn("model_info", data)
        self.assertIn("timestamp", data)

        # Verify audit persistence with account masking in SQLite
        saved = Transaction.query.filter_by(transaction_ref=data["transaction_ref"]).first()
        self.assertIsNotNone(saved)
        self.assertFalse(saved.is_fraud)
        self.assertTrue(saved.sender_account.startswith("******"))
        self.assertTrue(saved.sender_account.endswith("7890"))

    def test_predict_valid_fraudulent_transaction(self):
        """Verifies POST /api/predict flags classic account drain transfer as fraud."""
        payload = {
            "amount": 250000.00,
            "transaction_type": "TRANSFER",
            "old_balance_org": 250000.00,
            "new_balance_orig": 0.00,
            "old_balance_dest": 0.00,
            "new_balance_dest": 0.00,
            "currency": "USD",
            "step": 1,
            "sender_account": "AC-99887766",
            "receiver_account": "AC-11223344"
        }
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["is_fraud"])
        self.assertEqual(data["predicted_class"], 1)
        self.assertEqual(data["prediction_label"], "Fraudulent")
        self.assertIn(data["risk_level"], ["High", "Critical"])
        self.assertGreater(data["confidence_score"], 80.0)

    def test_predict_iso4217_currencies(self):
        """Verifies multi-currency support across various ISO 4217 currency codes."""
        test_currencies = [
            ("INR", 83500.0),   # Indian Rupee (~1000 USD)
            ("EUR", 920.0),     # Euro (~1000 USD)
            ("GBP", 790.0),     # British Pound (~1000 USD)
            ("AED", 3672.5),    # UAE Dirham (~1000 USD)
            ("JPY", 155000.0),  # Japanese Yen (~1000 USD)
            ("CAD", 1360.0),    # Canadian Dollar (~1000 USD)
            ("AUD", 1520.0),    # Australian Dollar (~1000 USD)
            ("SGD", 1350.0),    # Singapore Dollar (~1000 USD)
            ("CHF", 890.0)      # Swiss Franc (~1000 USD)
        ]

        for curr, foreign_amt in test_currencies:
            payload = {
                "amount": foreign_amt,
                "transaction_type": "PAYMENT",
                "old_balance_org": foreign_amt * 2,
                "new_balance_orig": foreign_amt,
                "currency": curr
            }
            response = self.client.post("/api/predict", json=payload)
            self.assertEqual(response.status_code, 200, f"Failed for currency {curr}")

            data = response.get_json()
            self.assertEqual(data["currency"], curr)
            self.assertEqual(data["original_amount"], foreign_amt)
            self.assertAlmostEqual(data["normalized_amount_usd"], 1000.0, delta=5.0)
            self.assertGreater(data["exchange_rate"], 0.0)

    def test_predict_arbitrary_unlisted_iso4217_code(self):
        """Verifies system accepts any valid 3-letter ISO 4217 code without hardcoded restriction."""
        payload = {
            "amount": 250.0,
            "transaction_type": "PAYMENT",
            "old_balance_org": 1000.0,
            "new_balance_orig": 750.0,
            "currency": "XYZ"  # Arbitrary standard-conforming 3-letter code
        }
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["currency"], "XYZ")
        self.assertEqual(data["original_amount"], 250.0)
        self.assertEqual(data["normalized_amount_usd"], 250.0)

    def test_predict_missing_json_body(self):
        """Verifies HTTP 400 when request body is empty or non-JSON."""
        response = self.client.post("/api/predict", data="not-json", content_type="text/plain")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error_type"], "ValidationError")

    def test_predict_malformed_json_syntax(self):
        """Verifies HTTP 400 when request sends syntactically malformed JSON."""
        response = self.client.post("/api/predict", data="{bad_json: missing_quotes,", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error_type"], "ValidationError")
        self.assertIn("Invalid request body", data["message"])

    def test_predict_missing_required_fields(self):
        """Verifies HTTP 400 when required fields (amount, transaction_type) are omitted."""
        # Missing transaction_type
        res1 = self.client.post("/api/predict", json={"amount": 100.0})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("transaction_type", str(res1.get_json()["errors"]))

        # Missing amount
        res2 = self.client.post("/api/predict", json={"transaction_type": "PAYMENT"})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("amount", str(res2.get_json()["errors"]))

    def test_predict_invalid_numeric_values(self):
        """Verifies HTTP 400 when monetary amounts or balances are invalid or negative."""
        # Negative amount
        res1 = self.client.post("/api/predict", json={"amount": -50.0, "transaction_type": "PAYMENT"})
        self.assertEqual(res1.status_code, 400)

        # Zero amount
        res2 = self.client.post("/api/predict", json={"amount": 0.0, "transaction_type": "PAYMENT"})
        self.assertEqual(res2.status_code, 400)

        # Negative origin balance
        res3 = self.client.post("/api/predict", json={
            "amount": 50.0,
            "transaction_type": "PAYMENT",
            "old_balance_org": -100.0
        })
        self.assertEqual(res3.status_code, 400)

        # Non-numeric string for amount
        res4 = self.client.post("/api/predict", json={
            "amount": "NOT_A_NUMBER",
            "transaction_type": "PAYMENT"
        })
        self.assertEqual(res4.status_code, 400)

    def test_predict_invalid_transaction_type(self):
        """Verifies HTTP 400 when transaction_type is not in the recognized categories."""
        res = self.client.post("/api/predict", json={
            "amount": 100.0,
            "transaction_type": "CRYPTO_TRADE"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error_type"], "ValidationError")
        self.assertTrue(any("Invalid transaction type" in e for e in data["errors"]))

    def test_predict_invalid_currency_code(self):
        """Verifies HTTP 400 when currency code is malformed (not 3-letter alphabetic)."""
        invalid_codes = ["US", "USDD", "123", "$$$", "U$D"]
        for code in invalid_codes:
            res = self.client.post("/api/predict", json={
                "amount": 100.0,
                "transaction_type": "PAYMENT",
                "currency": code
            })
            self.assertEqual(res.status_code, 400, f"Expected 400 for invalid currency code '{code}'")
            self.assertTrue(any("currency code" in e.lower() for e in res.get_json()["errors"]))

    def test_cors_headers_and_options_preflight(self):
        """Verifies CORS headers are attached and OPTIONS preflight succeeds with HTTP 204."""
        # Test OPTIONS preflight
        res_options = self.client.options("/api/predict")
        self.assertEqual(res_options.status_code, 204)
        self.assertEqual(res_options.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", res_options.headers.get("Access-Control-Allow-Methods", ""))

        # Test CORS headers on POST response
        res_post = self.client.post("/api/predict", json={"amount": 50.0, "transaction_type": "PAYMENT"})
        self.assertEqual(res_post.headers.get("Access-Control-Allow-Origin"), "*")

    def test_model_artifact_error_handling(self):
        """Verifies HTTP 500 error response structure when prediction service raises ModelArtifactError."""
        with patch.object(get_prediction_service(), "predict", side_effect=ModelArtifactError("Simulated missing model file")):
            response = self.client.post("/api/predict", json={"amount": 50.0, "transaction_type": "PAYMENT"})
            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "ModelArtifactError")
            self.assertIn("unavailable", data["message"].lower())


if __name__ == "__main__":
    unittest.main()
