"""
Main Web Pages Blueprint
------------------------
Renders core UI pages: Landing/Home, Analytics Dashboard, and Project Documentation / Viva Guide.
"""

from flask import Blueprint, render_template
from app.models.transaction import Transaction
from app.models import db
from app.services.analytics_service import get_analytics_summary
from app.utils.auth import login_required, get_current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Project landing page showcasing architecture, capabilities, and quick links."""
    # Basic transaction statistics for the banner
    total_txns = Transaction.query.count()
    total_fraud = Transaction.query.filter_by(is_fraud=True).count()
    return render_template(
        "index.html",
        total_txns=total_txns,
        total_fraud=total_fraud
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Displays transactional auditing log and summary analytics."""
    current_u = get_current_user()
    role = current_u.role if current_u else "analyst"
    u_id = current_u.id if current_u else None

    analytics = get_analytics_summary(user_role=role, current_user_id=u_id)
    recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(25).all()
    total_txns = analytics["summary"]["total_predictions"]
    fraud_txns = analytics["summary"]["fraudulent_predictions"]
    legit_txns = analytics["summary"]["safe_predictions"]
    fraud_rate = analytics["summary"]["fraud_percentage"]

    return render_template(
        "dashboard.html",
        analytics=analytics,
        transactions=recent_transactions,
        total_txns=total_txns,
        fraud_txns=fraud_txns,
        legit_txns=legit_txns,
        fraud_rate=fraud_rate,
        active_tab="dashboard"
    )


@main_bp.route("/analytics")
@login_required
def analytics_page():
    """Direct route for Analytics Center view."""
    current_u = get_current_user()
    role = current_u.role if current_u else "analyst"
    u_id = current_u.id if current_u else None

    analytics = get_analytics_summary(user_role=role, current_user_id=u_id)
    recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(25).all()
    total_txns = analytics["summary"]["total_predictions"]
    fraud_txns = analytics["summary"]["fraudulent_predictions"]
    legit_txns = analytics["summary"]["safe_predictions"]
    fraud_rate = analytics["summary"]["fraud_percentage"]

    return render_template(
        "dashboard.html",
        analytics=analytics,
        transactions=recent_transactions,
        total_txns=total_txns,
        fraud_txns=fraud_txns,
        legit_txns=legit_txns,
        fraud_rate=fraud_rate,
        active_tab="analytics"
    )


@main_bp.route("/history")
@login_required
def history_page():
    """Direct route for Historical Prediction & Audit Log view."""
    analytics = get_analytics_summary()
    recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(25).all()
    total_txns = analytics["summary"]["total_predictions"]
    fraud_txns = analytics["summary"]["fraudulent_predictions"]
    legit_txns = analytics["summary"]["safe_predictions"]
    fraud_rate = analytics["summary"]["fraud_percentage"]

    return render_template(
        "dashboard.html",
        analytics=analytics,
        transactions=recent_transactions,
        total_txns=total_txns,
        fraud_txns=fraud_txns,
        legit_txns=legit_txns,
        fraud_rate=fraud_rate,
        active_tab="history"
    )


@main_bp.route("/about")
def about():
    """Diploma presentation documentation, Viva Voce prep, and ML system explanation."""
    return render_template("about.html")

