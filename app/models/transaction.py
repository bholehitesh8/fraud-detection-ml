"""
Transaction and Prediction History Database Model
-------------------------------------------------
Stores transaction attributes, client details, ISO 4217 currency metadata,
and ML prediction outcomes in SQLite with indexed fields for fast querying.
"""

from datetime import datetime, timezone
import uuid
from app.models import db


class Transaction(db.Model):
    """
    Represents an individual financial transaction and its ML fraud evaluation outcome.
    Also aliased as Prediction and TransactionHistory for modularity.
    """
    __tablename__ = "transactions"

    # Primary key and external reference
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_ref = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: f"TXN-{uuid.uuid4().hex[:8].upper()}"
    )

    # Monetary and currency fields
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD", index=True)
    normalized_amount = db.Column(db.Float, nullable=True)
    exchange_rate = db.Column(db.Float, nullable=True, default=1.0)
    transaction_type = db.Column(db.String(30), nullable=False, index=True)  # PAYMENT, TRANSFER, CASH_OUT, etc.

    # Financial account balance features required by ML pipeline
    old_balance_org = db.Column(db.Float, default=0.0)
    new_balance_orig = db.Column(db.Float, default=0.0)
    old_balance_dest = db.Column(db.Float, default=0.0)
    new_balance_dest = db.Column(db.Float, default=0.0)
    step = db.Column(db.Float, default=1.0)

    # Client and channel metadata (masked accounts for privacy)
    sender_account = db.Column(db.String(64), nullable=True)
    receiver_account = db.Column(db.String(64), nullable=True)
    device_type = db.Column(db.String(30), default="Web")
    location = db.Column(db.String(64), default="Domestic")

    # ML Model Prediction Results
    is_fraud = db.Column(db.Boolean, default=False, nullable=False, index=True)
    prediction_label = db.Column(db.String(20), default="Legitimate", nullable=False)
    confidence_score = db.Column(db.Float, default=0.0)
    fraud_probability = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), default="Low")

    # Model tracking metadata
    model_name = db.Column(db.String(64), default="ExtraTrees")
    model_version = db.Column(db.String(32), default="1.0.0")
    status = db.Column(db.String(32), default="COMPLETED", nullable=False)

    # Timestamps
    prediction_timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def to_dict(self):
        """Converts transaction record into a serializable dictionary."""
        return {
            "id": self.id,
            "transaction_ref": self.transaction_ref,
            "amount": round(self.amount, 2) if self.amount is not None else 0.0,
            "currency": self.currency or "USD",
            "normalized_amount": round(self.normalized_amount, 2) if self.normalized_amount is not None else self.amount,
            "exchange_rate": self.exchange_rate if self.exchange_rate is not None else 1.0,
            "transaction_type": self.transaction_type,
            "old_balance_org": round(self.old_balance_org, 2) if self.old_balance_org is not None else 0.0,
            "new_balance_orig": round(self.new_balance_orig, 2) if self.new_balance_orig is not None else 0.0,
            "old_balance_dest": round(self.old_balance_dest, 2) if self.old_balance_dest is not None else 0.0,
            "new_balance_dest": round(self.new_balance_dest, 2) if self.new_balance_dest is not None else 0.0,
            "step": self.step if self.step is not None else 1.0,
            "sender_account": self.sender_account,
            "receiver_account": self.receiver_account,
            "device_type": self.device_type,
            "location": self.location,
            "is_fraud": self.is_fraud,
            "prediction_label": self.prediction_label,
            "fraud_probability": round(self.fraud_probability, 4) if self.fraud_probability is not None else None,
            "confidence_score": round(self.confidence_score, 2) if self.confidence_score is not None else 0.0,
            "risk_level": self.risk_level,
            "model_name": self.model_name or "ExtraTrees",
            "model_version": self.model_version or "1.0.0",
            "status": self.status or "COMPLETED",
            "prediction_timestamp": self.prediction_timestamp.isoformat() if self.prediction_timestamp else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if self.created_at else None
        }

    def __repr__(self):
        return f"<Transaction {self.transaction_ref}: {self.prediction_label} ({self.amount} {self.currency})>"


# Domain aliases for Prompt 5 architecture
Prediction = Transaction
TransactionHistory = Transaction
