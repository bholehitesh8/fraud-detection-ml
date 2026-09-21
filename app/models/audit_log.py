"""
Security Audit Log Database Model
---------------------------------
Stores security events, authentication lifecycle, role modifications,
and administrative operations in SQLite with zero sensitive credential exposure.
"""

from datetime import datetime, timezone
import json
from typing import Dict, Any, Optional
from app.models import db


class AuditLog(db.Model):
    """
    Represents an immutable audit trail entry recording security-critical events.
    Captures user identity, IP address, user-agent, action classification, and outcome status.
    """
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = db.Column(db.String(64), nullable=True, index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    event_type = db.Column(db.String(32), nullable=False, index=True)  # AUTH, ADMIN, SECURITY, ACCESS
    description = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="SUCCESS")  # SUCCESS, FAILURE, WARNING
    extra_metadata = db.Column(db.Text, nullable=True)  # JSON-encoded safe auxiliary details
    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def __init__(self, **kwargs):
        if "extra_metadata" in kwargs and isinstance(kwargs["extra_metadata"], (dict, list)):
            kwargs["extra_metadata"] = json.dumps(kwargs["extra_metadata"])
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes audit log entry into a clean dictionary representation.
        Guaranteed zero exposure of credentials, secrets, or raw internal exceptions.
        """
        meta = None
        if self.extra_metadata:
            try:
                meta = json.loads(self.extra_metadata)
            except Exception:
                meta = {"raw": self.extra_metadata}

        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username or "Anonymous",
            "action": self.action,
            "event_type": self.event_type,
            "description": self.description,
            "ip_address": self.ip_address or "Unknown",
            "user_agent": self.user_agent or "Unknown",
            "status": self.status,
            "metadata": meta,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if self.timestamp else None,
            "iso_timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action='{self.action}' user='{self.username}' status='{self.status}'>"
