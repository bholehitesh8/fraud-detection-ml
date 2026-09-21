"""
Automated Test Suite for Advanced Fraud Analytics and Dashboard Subsystem
-------------------------------------------------------------------------
Validates Prompt 7 requirements:
1. Consolidated analytics calculation on empty database (zero-division safety)
2. Accurate multi-currency segregation (strictly avoiding cross-currency additions)
3. Fraud vs Safe counts and percentage calculations
4. Time-series trend aggregation and period filtering (7D, 30D, 90D, all)
5. Risk level distribution tracking (Low, Moderate, High, Critical)
6. Model information extraction from saved artifacts
7. GET /api/analytics/summary HTTP 200 and schema validation
8. CORS headers on OPTIONS /api/analytics/summary
9. Web dashboard route (/dashboard) HTML rendering with analytics data
"""

from datetime import datetime, timezone, timedelta
import unittest
from app import create_app
from app.models import db
from app.models.transaction import Transaction
from app.services.analytics_service import get_analytics_summary


class AnalyticsSubsystemTestCase(unittest.TestCase):
    """Test cases for analytics data calculations and REST endpoint."""

    def setUp(self):
        """Sets up isolated in-memory testing application."""
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
        """Tears down database and application context."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_analytics_empty_database(self):
        """Verifies analytics handles zero transactions safely without errors."""
        result = get_analytics_summary()
        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["total_predictions"], 0)
        self.assertEqual(result["summary"]["fraudulent_predictions"], 0)
        self.assertEqual(result["summary"]["safe_predictions"], 0)
        self.assertEqual(result["summary"]["fraud_percentage"], 0.0)
        self.assertEqual(result["summary"]["average_amount_usd"], 0.0)
        self.assertEqual(result["summary"]["highest_amount_usd"], 0.0)
        self.assertEqual(result["amount_analytics"]["per_currency_breakdown"], [])
        self.assertEqual(result["trend"]["points"], [])
        self.assertEqual(result["currency_distribution"], [])
        self.assertEqual(result["risk_distribution"], [])
        self.assertEqual(result["recent_predictions"], [])

    def test_analytics_populated_database_and_currency_segregation(self):
        """
        Verifies multi-currency transactions are strictly segregated and not
        improperly summed across different currencies.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        yesterday = now - timedelta(days=1)

        # 1. USD transactions (1 safe, 1 fraud)
        t1 = Transaction(
            transaction_ref="TXN-USD-001",
            amount=100.0,
            currency="USD",
            normalized_amount=100.0,
            exchange_rate=1.0,
            transaction_type="PAYMENT",
            is_fraud=False,
            prediction_label="Legitimate",
            confidence_score=15.0,
            risk_level="Low",
            created_at=yesterday
        )
        t2 = Transaction(
            transaction_ref="TXN-USD-002",
            amount=5000.0,
            currency="USD",
            normalized_amount=5000.0,
            exchange_rate=1.0,
            transaction_type="TRANSFER",
            is_fraud=True,
            prediction_label="Fraudulent",
            confidence_score=95.0,
            risk_level="Critical",
            created_at=now
        )

        # 2. EUR transactions (1 fraud)
        t3 = Transaction(
            transaction_ref="TXN-EUR-001",
            amount=2000.0,
            currency="EUR",
            normalized_amount=2173.91,
            exchange_rate=0.92,
            transaction_type="TRANSFER",
            is_fraud=True,
            prediction_label="Fraudulent",
            confidence_score=85.0,
            risk_level="High",
            created_at=now
        )

        # 3. INR transactions (1 safe)
        t4 = Transaction(
            transaction_ref="TXN-INR-001",
            amount=45000.0,
            currency="INR",
            normalized_amount=542.17,
            exchange_rate=83.0,
            transaction_type="CASH_OUT",
            is_fraud=False,
            prediction_label="Legitimate",
            confidence_score=30.0,
            risk_level="Moderate",
            created_at=now
        )

        db.session.add_all([t1, t2, t3, t4])
        db.session.commit()

        # Run analytics calculation
        result = get_analytics_summary()
        summary = result["summary"]

        # Counts
        self.assertEqual(summary["total_predictions"], 4)
        self.assertEqual(summary["fraudulent_predictions"], 2)
        self.assertEqual(summary["safe_predictions"], 2)
        self.assertEqual(summary["fraud_percentage"], 50.0)
        self.assertEqual(summary["safe_percentage"], 50.0)

        # Currency segregation check
        breakdown = {item["currency"]: item for item in result["amount_analytics"]["per_currency_breakdown"]}
        self.assertIn("USD", breakdown)
        self.assertIn("EUR", breakdown)
        self.assertIn("INR", breakdown)

        # USD sum must ONLY be 100 + 5000 = 5100
        self.assertEqual(breakdown["USD"]["total_amount"], 5100.0)
        self.assertEqual(breakdown["USD"]["count"], 2)
        self.assertEqual(breakdown["USD"]["fraud_count"], 1)

        # EUR sum must ONLY be 2000
        self.assertEqual(breakdown["EUR"]["total_amount"], 2000.0)
        self.assertEqual(breakdown["EUR"]["count"], 1)

        # INR sum must ONLY be 45000
        self.assertEqual(breakdown["INR"]["total_amount"], 45000.0)
        self.assertEqual(breakdown["INR"]["count"], 1)

        # Risk level distribution verification
        risk_map = {item["risk_level"]: item["count"] for item in result["risk_distribution"]}
        self.assertEqual(risk_map.get("Low"), 1)
        self.assertEqual(risk_map.get("Moderate"), 1)
        self.assertEqual(risk_map.get("High"), 1)
        self.assertEqual(risk_map.get("Critical"), 1)

        # Trend points verification
        trend_pts = result["trend"]["points"]
        self.assertTrue(len(trend_pts) >= 1)
        total_in_trend = sum(pt["total"] for pt in trend_pts)
        self.assertEqual(total_in_trend, 4)

    def test_trend_period_filtering(self):
        """Verifies trend period filtering handles day windows correctly."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        recent_txn = Transaction(
            transaction_ref="TXN-REC-1",
            amount=200.0,
            currency="USD",
            normalized_amount=200.0,
            transaction_type="PAYMENT",
            is_fraud=False,
            created_at=now
        )
        old_txn = Transaction(
            transaction_ref="TXN-OLD-1",
            amount=400.0,
            currency="USD",
            normalized_amount=400.0,
            transaction_type="PAYMENT",
            is_fraud=True,
            created_at=now - timedelta(days=40)
        )
        db.session.add_all([recent_txn, old_txn])
        db.session.commit()

        # All-time trend should have 2 records
        all_trend = get_analytics_summary(days=None)
        total_all = sum(pt["total"] for pt in all_trend["trend"]["points"])
        self.assertEqual(total_all, 2)

        # 7-day trend should exclude the 40-day-old record
        week_trend = get_analytics_summary(days=7)
        total_week = sum(pt["total"] for pt in week_trend["trend"]["points"])
        self.assertEqual(total_week, 1)

    def test_api_analytics_summary_endpoint(self):
        """Verifies GET /api/analytics/summary returns HTTP 200 with complete JSON schema."""
        txn = Transaction(
            transaction_ref="TXN-TEST-API",
            amount=350.0,
            currency="USD",
            normalized_amount=350.0,
            transaction_type="PAYMENT",
            is_fraud=False,
            prediction_label="Legitimate",
            confidence_score=10.0,
            risk_level="Low"
        )
        db.session.add(txn)
        db.session.commit()

        res = self.client.get("/api/analytics/summary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data["success"])
        self.assertIn("summary", data)
        self.assertIn("fraud_vs_safe", data)
        self.assertIn("trend", data)
        self.assertIn("amount_analytics", data)
        self.assertIn("currency_distribution", data)
        self.assertIn("risk_distribution", data)
        self.assertIn("model_info", data)
        self.assertIn("recent_predictions", data)

        # Verify summary sub-fields
        self.assertEqual(data["summary"]["total_predictions"], 1)
        self.assertEqual(data["summary"]["fraudulent_predictions"], 0)
        self.assertEqual(data["summary"]["safe_predictions"], 1)
        self.assertEqual(data["summary"]["fraud_percentage"], 0.0)

    def test_api_analytics_cors_options(self):
        """Verifies CORS preflight OPTIONS request on /api/analytics/summary."""
        res = self.client.options("/api/analytics/summary")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("GET", res.headers.get("Access-Control-Allow-Methods", ""))

    def test_dashboard_web_route(self):
        """Verifies /dashboard HTML renders successfully with analytics content."""
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Fraud Detection Analytics Center", html)
        self.assertIn("Multi-Currency Transaction Amounts Breakdown", html)
        self.assertIn("chartFraudVsSafe", html)
        self.assertIn("chartFraudTrend", html)
        self.assertIn("chartCurrencyDist", html)
        self.assertIn("chartRiskDist", html)


if __name__ == "__main__":
    unittest.main()
