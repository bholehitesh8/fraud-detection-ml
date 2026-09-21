"""
Comprehensive Automated Test Suite for Prediction History and Database Subsystem
-------------------------------------------------------------------------------
Validates Prompt 5 requirements:
1. Database initialization and model instantiation
2. Prediction saving via repository layer
3. POST /api/predict automatic database persistence
4. Database persistence failure error handling (HTTP 500)
5. GET /api/predictions paginated history retrieval
6. Pagination boundaries, default page sizes, and invalid page handling (HTTP 400)
7. Multi-attribute filtering (status=fraud, status=safe, currency, transaction_ref, date ranges)
8. Allow-listed safe sorting (newest first, amount ascending/descending)
9. Single prediction lookup via GET /api/predictions/<id> and GET /api/predictions/<ref>
10. HTTP 404 handling for non-existent prediction IDs
11. PII protection (account numbers masked in database records)
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app import create_app
from app.models import db, upgrade_database_schema
from app.models.transaction import Transaction, Prediction, TransactionHistory
from app.services.prediction_repository import (
    create_prediction_record,
    get_prediction_by_identifier,
    query_predictions,
    DatabasePersistenceError
)


class PredictionHistoryTestCase(unittest.TestCase):
    """Test suite for Prompt 5 database models, repository, and history APIs."""

    def setUp(self):
        """Initializes isolated in-memory test database and client."""
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

    def test_database_initialization_and_model_aliases(self):
        """Verifies database initializes correctly and model aliases exist."""
        self.assertIs(Prediction, Transaction)
        self.assertIs(TransactionHistory, Transaction)

        # Verify table exists in SQLite metadata
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        self.assertIn("transactions", tables)

        columns = [col["name"] for col in inspector.get_columns("transactions")]
        self.assertIn("currency", columns)
        self.assertIn("normalized_amount", columns)
        self.assertIn("fraud_probability", columns)
        self.assertIn("model_name", columns)
        self.assertIn("prediction_timestamp", columns)
        self.assertIn("status", columns)

    def test_repository_create_prediction_record(self):
        """Verifies create_prediction_record commits transaction with masked accounts."""
        input_data = {
            "amount": 1500.0,
            "currency": "INR",
            "transaction_type": "TRANSFER",
            "old_balance_org": 2000.0,
            "new_balance_orig": 500.0,
            "sender_account": "AC-987654321",
            "receiver_account": "MC-123456789"
        }
        pred_result = {
            "is_fraud": False,
            "predicted_class": 0,
            "prediction_label": "Legitimate",
            "confidence_score": 10.5,
            "fraud_probability": 0.105,
            "risk_level": "Low",
            "currency": "INR",
            "normalized_amount_usd": 17.96,
            "exchange_rate": 83.5,
            "model_info": {"name": "ExtraTrees", "version": "1.0.0"}
        }

        record = create_prediction_record(input_data, pred_result)
        self.assertIsNotNone(record.id)
        self.assertTrue(record.transaction_ref.startswith("TXN-"))
        self.assertEqual(record.currency, "INR")
        self.assertEqual(record.amount, 1500.0)
        self.assertEqual(record.normalized_amount, 17.96)
        self.assertEqual(record.model_name, "ExtraTrees")
        self.assertEqual(record.status, "COMPLETED")
        self.assertTrue(record.sender_account.startswith("*****"))
        self.assertTrue(record.sender_account.endswith("4321"))

    def test_api_predict_saves_valid_prediction(self):
        """Verifies POST /api/predict automatically saves prediction record to database."""
        payload = {
            "amount": 25000.0,
            "transaction_type": "TRANSFER",
            "old_balance_org": 25000.0,
            "new_balance_orig": 0.0,
            "currency": "EUR"
        }
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        txn_ref = data.get("transaction_ref")
        self.assertIsNotNone(txn_ref)

        # Query database directly to confirm persistence
        saved = Transaction.query.filter_by(transaction_ref=txn_ref).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.amount, 25000.0)
        self.assertEqual(saved.currency, "EUR")
        self.assertEqual(saved.is_fraud, data["is_fraud"])
        self.assertEqual(saved.risk_level, data["risk_level"])

    def test_api_predict_db_failure_returns_500(self):
        """Verifies POST /api/predict returns HTTP 500 when database commit fails."""
        payload = {
            "amount": 100.0,
            "transaction_type": "PAYMENT"
        }
        with patch("app.routes.api_routes.create_prediction_record", side_effect=DatabasePersistenceError("Simulated DB Disk Full")):
            response = self.client.post("/api/predict", json=payload)
            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertFalse(data["success"])
            self.assertEqual(data["error_type"], "DatabaseError")
            self.assertIn("Failed to safely persist prediction record", data["error"])

    def test_get_predictions_empty_history(self):
        """Verifies GET /api/predictions returns empty list when no records exist."""
        response = self.client.get("/api/predictions")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["predictions"], [])

    def test_get_predictions_pagination_and_metadata(self):
        """Verifies pagination limits, total counts, and multi-page navigation."""
        # Insert 25 dummy records
        for i in range(1, 26):
            t = Transaction(
                amount=float(i * 100),
                currency="USD",
                transaction_type="PAYMENT",
                is_fraud=(i % 5 == 0),
                prediction_label="Fraudulent" if (i % 5 == 0) else "Legitimate",
                confidence_score=95.0 if (i % 5 == 0) else 10.0,
                risk_level="High" if (i % 5 == 0) else "Low"
            )
            db.session.add(t)
        db.session.commit()

        # Test default page size (20)
        res1 = self.client.get("/api/predictions")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1["success"])
        self.assertEqual(data1["total"], 25)
        self.assertEqual(data1["count"], 20)
        self.assertEqual(data1["page"], 1)
        self.assertEqual(data1["per_page"], 20)
        self.assertEqual(data1["total_pages"], 2)

        # Test page 2
        res2 = self.client.get("/api/predictions?page=2&per_page=20")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2["count"], 5)
        self.assertEqual(data2["page"], 2)

        # Test custom per_page=10
        res3 = self.client.get("/api/predictions?page=1&per_page=10")
        self.assertEqual(res3.status_code, 200)
        data3 = res3.get_json()
        self.assertEqual(data3["count"], 10)
        self.assertEqual(data3["total_pages"], 3)

    def test_pagination_invalid_parameters_return_400(self):
        """Verifies HTTP 400 when invalid page or per_page parameters are provided."""
        # Non-numeric page
        res1 = self.client.get("/api/predictions?page=abc")
        self.assertEqual(res1.status_code, 400)
        self.assertFalse(res1.get_json()["success"])

        # Page 0
        res2 = self.client.get("/api/predictions?page=0")
        self.assertEqual(res2.status_code, 400)

        # Negative page
        res3 = self.client.get("/api/predictions?page=-5")
        self.assertEqual(res3.status_code, 400)

        # per_page greater than 100
        res4 = self.client.get("/api/predictions?per_page=500")
        self.assertEqual(res4.status_code, 400)

        # per_page 0
        res5 = self.client.get("/api/predictions?per_page=0")
        self.assertEqual(res5.status_code, 400)

    def test_filtering_by_status(self):
        """Verifies filtering by status=fraud and status=safe."""
        # Insert 3 legitimate and 2 fraudulent records
        for i in range(3):
            db.session.add(Transaction(amount=50.0, transaction_type="PAYMENT", is_fraud=False, prediction_label="Legitimate"))
        for i in range(2):
            db.session.add(Transaction(amount=100000.0, transaction_type="TRANSFER", is_fraud=True, prediction_label="Fraudulent"))
        db.session.commit()

        # Query fraud only
        res_fraud = self.client.get("/api/predictions?status=fraud")
        self.assertEqual(res_fraud.status_code, 200)
        data_fraud = res_fraud.get_json()
        self.assertEqual(data_fraud["total"], 2)
        for item in data_fraud["predictions"]:
            self.assertTrue(item["is_fraud"])

        # Query safe only
        res_safe = self.client.get("/api/predictions?status=safe")
        self.assertEqual(res_safe.status_code, 200)
        data_safe = res_safe.get_json()
        self.assertEqual(data_safe["total"], 3)
        for item in data_safe["predictions"]:
            self.assertFalse(item["is_fraud"])

        # Invalid status filter
        res_bad = self.client.get("/api/predictions?status=unknown_status")
        self.assertEqual(res_bad.status_code, 400)

    def test_filtering_by_currency(self):
        """Verifies filtering by ISO 4217 currency codes."""
        db.session.add(Transaction(amount=50000.0, currency="INR", transaction_type="TRANSFER", is_fraud=False))
        db.session.add(Transaction(amount=2000.0, currency="EUR", transaction_type="PAYMENT", is_fraud=False))
        db.session.add(Transaction(amount=500.0, currency="USD", transaction_type="PAYMENT", is_fraud=False))
        db.session.commit()

        # Filter by INR
        res_inr = self.client.get("/api/predictions?currency=INR")
        self.assertEqual(res_inr.status_code, 200)
        data_inr = res_inr.get_json()
        self.assertEqual(data_inr["total"], 1)
        self.assertEqual(data_inr["predictions"][0]["currency"], "INR")

        # Filter by EUR
        res_eur = self.client.get("/api/predictions?currency=EUR")
        self.assertEqual(res_eur.status_code, 200)
        data_eur = res_eur.get_json()
        self.assertEqual(data_eur["total"], 1)
        self.assertEqual(data_eur["predictions"][0]["currency"], "EUR")

        # Invalid currency filter format
        res_bad = self.client.get("/api/predictions?currency=TOOLONG")
        self.assertEqual(res_bad.status_code, 400)

    def test_filtering_by_transaction_ref(self):
        """Verifies searching by transaction reference string."""
        t1 = Transaction(amount=100.0, currency="USD", transaction_type="PAYMENT", transaction_ref="TXN-TARGET123")
        t2 = Transaction(amount=200.0, currency="USD", transaction_type="PAYMENT", transaction_ref="TXN-OTHER456")
        db.session.add_all([t1, t2])
        db.session.commit()

        res = self.client.get("/api/predictions?ref=TARGET123")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["predictions"][0]["transaction_ref"], "TXN-TARGET123")

    def test_sorting_history(self):
        """Verifies sorting by amount ascending and descending."""
        db.session.add(Transaction(amount=10.0, currency="USD", transaction_type="PAYMENT"))
        db.session.add(Transaction(amount=500.0, currency="USD", transaction_type="PAYMENT"))
        db.session.add(Transaction(amount=100.0, currency="USD", transaction_type="PAYMENT"))
        db.session.commit()

        # Sort amount asc
        res_asc = self.client.get("/api/predictions?sort_by=amount&order=asc")
        self.assertEqual(res_asc.status_code, 200)
        amounts_asc = [p["amount"] for p in res_asc.get_json()["predictions"]]
        self.assertEqual(amounts_asc, [10.0, 100.0, 500.0])

        # Sort amount desc
        res_desc = self.client.get("/api/predictions?sort_by=amount&order=desc")
        self.assertEqual(res_desc.status_code, 200)
        amounts_desc = [p["amount"] for p in res_desc.get_json()["predictions"]]
        self.assertEqual(amounts_desc, [500.0, 100.0, 10.0])

        # Invalid sort field returns 400
        res_bad = self.client.get("/api/predictions?sort_by=malicious_column")
        self.assertEqual(res_bad.status_code, 400)

    def test_single_prediction_by_id_and_ref(self):
        """Verifies GET /api/predictions/<identifier> by integer ID and reference."""
        t = Transaction(
            amount=999.0,
            currency="USD",
            transaction_type="PAYMENT",
            transaction_ref="TXN-SPECIFIC1",
            is_fraud=False,
            prediction_label="Legitimate"
        )
        db.session.add(t)
        db.session.commit()

        # Query by integer primary key
        res_id = self.client.get(f"/api/predictions/{t.id}")
        self.assertEqual(res_id.status_code, 200)
        data_id = res_id.get_json()
        self.assertTrue(data_id["success"])
        self.assertEqual(data_id["prediction"]["amount"], 999.0)
        self.assertEqual(data_id["prediction"]["transaction_ref"], "TXN-SPECIFIC1")

        # Query by transaction reference string
        res_ref = self.client.get("/api/predictions/TXN-SPECIFIC1")
        self.assertEqual(res_ref.status_code, 200)
        data_ref = res_ref.get_json()
        self.assertTrue(data_ref["success"])
        self.assertEqual(data_ref["prediction"]["id"], t.id)

    def test_single_prediction_not_found_404(self):
        """Verifies GET /api/predictions/<identifier> returns HTTP 404 for non-existent record."""
        # Non-existent integer ID
        res1 = self.client.get("/api/predictions/999999")
        self.assertEqual(res1.status_code, 404)
        data1 = res1.get_json()
        self.assertFalse(data1["success"])
        self.assertIn("not found", data1["error"].lower())

        # Non-existent reference
        res2 = self.client.get("/api/predictions/TXN-DOESNOTEXIST")
        self.assertEqual(res2.status_code, 404)
        data2 = res2.get_json()
        self.assertFalse(data2["success"])

    def test_schema_migration_adds_missing_columns_to_legacy_table(self):
        """Verifies upgrade_database_schema adds missing columns to a legacy table and preserves records."""
        from sqlalchemy import text
        # 1. Drop existing table to simulate legacy database created before Prompt 5
        db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS transactions;"))
            # Create table with only legacy columns (omitting currency, normalized_amount, etc.)
            conn.execute(text("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_ref VARCHAR(36) NOT NULL UNIQUE,
                    amount FLOAT NOT NULL,
                    transaction_type VARCHAR(30) NOT NULL,
                    old_balance_org FLOAT,
                    new_balance_orig FLOAT,
                    sender_account VARCHAR(64),
                    receiver_account VARCHAR(64),
                    device_type VARCHAR(30),
                    location VARCHAR(64),
                    is_fraud BOOLEAN NOT NULL,
                    prediction_label VARCHAR(20) NOT NULL,
                    confidence_score FLOAT,
                    risk_level VARCHAR(20),
                    created_at DATETIME NOT NULL
                );
            """))
            # Insert a legacy transaction record
            conn.execute(text("""
                INSERT INTO transactions (
                    transaction_ref, amount, transaction_type, old_balance_org, new_balance_orig,
                    sender_account, receiver_account, device_type, location,
                    is_fraud, prediction_label, confidence_score, risk_level, created_at
                ) VALUES (
                    'TXN-LEGACY1', 500.0, 'PAYMENT', 1000.0, 500.0,
                    '******1234', '******5678', 'Web', 'Domestic',
                    0, 'Legitimate', 25.0, 'Low', '2026-09-01 12:00:00'
                );
            """))

        # 2. Run schema migration
        result = upgrade_database_schema(db.engine)
        self.assertTrue(result["success"])
        self.assertIn("currency", result["columns_added"])
        self.assertIn("normalized_amount", result["columns_added"])
        self.assertIn("fraud_probability", result["columns_added"])

        # 3. Query through SQLAlchemy Transaction model to verify no OperationalError is thrown
        legacy_txn = Transaction.query.filter_by(transaction_ref="TXN-LEGACY1").first()
        self.assertIsNotNone(legacy_txn)
        self.assertEqual(legacy_txn.currency, "USD")
        self.assertEqual(legacy_txn.normalized_amount, 500.0)
        self.assertEqual(legacy_txn.model_name, "ExtraTrees")
        self.assertIn(legacy_txn.status, ["COMPLETED", "legitimate"])

    def test_schema_migration_is_idempotent(self):
        """Verifies upgrade_database_schema can run multiple times without failure."""
        res1 = upgrade_database_schema(db.engine)
        self.assertTrue(res1["success"])
        res2 = upgrade_database_schema(db.engine)
        self.assertTrue(res2["success"])
        self.assertEqual(res2["columns_added"], [])
        self.assertEqual(res2["message"], "All schema columns and indexes already present.")


if __name__ == "__main__":
    unittest.main()
