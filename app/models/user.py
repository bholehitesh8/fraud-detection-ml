"""
User Database Model
-------------------
Stores user credentials, roles, and status for authentication and authorization.
Passes passwords through secure one-way hashing with zero plaintext storage.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db


class User(db.Model):
    """
    Represents an authenticated user within the Fraud Detection platform.
    Supports Role-Based Access Control (RBAC) with 'admin' and 'analyst' roles.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="analyst")  # 'admin' or 'analyst'
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_login = db.Column(db.DateTime, nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    @property
    def is_locked(self) -> bool:
        """Tests whether the account is currently locked due to excessive failed attempts."""
        if self.locked_until is None:
            return False
        now_utc = datetime.now(timezone.utc)
        lock_time = self.locked_until
        if lock_time.tzinfo is None:
            lock_time = lock_time.replace(tzinfo=timezone.utc)
        return lock_time > now_utc

    def record_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
        """
        Increments failed attempt counter and locks account if threshold exceeded.
        Returns True if account is now locked.
        """
        from datetime import timedelta
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
            return True
        return False

    def reset_failed_logins(self) -> None:
        """Resets failed login counter and clears lockout timestamp."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def set_password(self, password: str) -> None:
        """
        Hashes password using Werkzeug's secure hashing algorithm (scrypt/pbkdf2).
        Never stores plaintext passwords.
        """
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Secure constant-time password hash verification.
        """
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Convenience property to test if user possesses administrator privileges."""
        return self.role == "admin"

    @property
    def is_analyst(self) -> bool:
        """Convenience property to test if user possesses analyst privileges."""
        return self.role in ("analyst", "admin")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes user object to a safe dictionary.
        NEVER exposes password or password_hash.
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "failed_login_attempts": self.failed_login_attempts or 0,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC") if self.updated_at else None,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S UTC") if self.last_login else None
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role='{self.role}' active={self.is_active}>"
