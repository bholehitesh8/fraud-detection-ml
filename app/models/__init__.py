"""
Database Models Package
-----------------------
Initializes SQLAlchemy db instance and exposes models.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.transaction import Transaction, Prediction, TransactionHistory
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.migrator import upgrade_database_schema

__all__ = ["db", "Transaction", "Prediction", "TransactionHistory", "User", "AuditLog", "upgrade_database_schema"]
