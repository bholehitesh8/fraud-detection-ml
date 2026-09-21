"""
Transaction Processing and Prediction Blueprint
-----------------------------------------------
Handles transaction evaluation forms, triggers the ML predictor,
and records all inference outcomes in the SQLite database.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import db
from app.models.transaction import Transaction
from app.ml.predictor import FraudPredictor
from app.utils.helpers import validate_transaction_data, mask_account
from app.utils.auth import login_required

transaction_bp = Blueprint("transactions", __name__)


@transaction_bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    """Renders transaction input form and processes ML evaluation."""
    predictor = FraudPredictor()
    prediction_result = None

    if request.method == "POST":
        data = {
            "amount": request.form.get("amount", "").strip(),
            "transaction_type": request.form.get("transaction_type", "PAYMENT").strip(),
            "old_balance_org": request.form.get("old_balance_org", "0.0").strip() or "0.0",
            "new_balance_orig": request.form.get("new_balance_orig", "0.0").strip() or "0.0",
            "sender_account": request.form.get("sender_account", "").strip(),
            "receiver_account": request.form.get("receiver_account", "").strip(),
            "device_type": request.form.get("device_type", "Web").strip(),
            "location": request.form.get("location", "Domestic").strip()
        }

        is_valid, err_msg = validate_transaction_data(data)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template("predict.html", prediction=None, form_data=data, is_model_ready=predictor.is_model_loaded)

        try:
            # 1. Run Machine Learning Inference
            eval_result = predictor.predict(data)

            currency_val = request.form.get("currency", "USD").strip().upper() or "USD"
            old_dest = float(request.form.get("old_balance_dest", "0.0") or 0.0)
            new_dest = float(request.form.get("new_balance_dest", "0.0") or 0.0)
            step_val = float(request.form.get("step", "1.0") or 1.0)

            # Currency normalization
            from app.utils.currency import convert_to_base_currency
            amount_val = float(data["amount"])
            norm_amount, rate, _ = convert_to_base_currency(amount_val, currency_val)

            # 2. Persist transaction and ML decision to SQLite with full Prompt 5/6 fields
            new_txn = Transaction(
                amount=amount_val,
                currency=currency_val,
                normalized_amount=norm_amount,
                exchange_rate=rate,
                transaction_type=data["transaction_type"],
                old_balance_org=float(data["old_balance_org"]),
                new_balance_orig=float(data["new_balance_orig"]),
                old_balance_dest=old_dest,
                new_balance_dest=new_dest,
                step=step_val,
                sender_account=mask_account(data["sender_account"]),
                receiver_account=mask_account(data["receiver_account"]),
                device_type=data["device_type"],
                location=data["location"],
                is_fraud=eval_result["is_fraud"],
                prediction_label=eval_result["prediction_label"],
                confidence_score=eval_result["confidence_score"],
                fraud_probability=round(eval_result["confidence_score"] / 100.0, 4),
                risk_level=eval_result["risk_level"],
                model_name="ExtraTrees",
                model_version="1.0.0",
                status="fraudulent" if eval_result["is_fraud"] else "legitimate"
            )
            db.session.add(new_txn)
            db.session.commit()

            prediction_result = {
                "transaction_ref": new_txn.transaction_ref,
                "amount": new_txn.amount,
                "currency": new_txn.currency,
                "normalized_amount": new_txn.normalized_amount,
                "exchange_rate": new_txn.exchange_rate,
                "type": new_txn.transaction_type,
                "is_fraud": eval_result["is_fraud"],
                "label": eval_result["prediction_label"],
                "confidence": eval_result["confidence_score"],
                "fraud_probability": round(eval_result["confidence_score"] / 100.0, 4),
                "risk_level": eval_result["risk_level"],
                "model_status": eval_result.get("model_status", "ExtraTrees ML Ensemble"),
                "features": eval_result.get("features", {})
            }

            flash("Transaction successfully evaluated and recorded in database!", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error processing transaction: {str(e)}", "danger")

    return render_template(
        "predict.html",
        prediction=prediction_result,
        form_data=request.form if request.method == "POST" else {},
        is_model_ready=predictor.is_model_loaded
    )
