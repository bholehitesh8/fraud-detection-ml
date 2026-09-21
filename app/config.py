"""
Application Configuration Module
--------------------------------
Defines configuration classes for different runtime environments:
- Development
- Testing
- Production
"""

import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
SAVED_MODELS_DIR = BASE_DIR / "saved_models"
DATA_DIR = BASE_DIR / "data"

from datetime import timedelta

# Ensure instance and model directories exist
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    """Base configuration settings."""
    SECRET_KEY = os.getenv("SECRET_KEY", "diploma-fraud-detection-secret-key-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SAVED_MODELS_PATH = SAVED_MODELS_DIR
    RAW_DATA_PATH = DATA_DIR / "raw"
    PROCESSED_DATA_PATH = DATA_DIR / "processed"

    # Session and Cookie Security Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1")
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

    # Brute-force & Account Lockout Protections
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

    # Initial System Accounts (overridable via environment variables)
    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminPassword123!")
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@fraudguard.local")

    DEFAULT_ANALYST_USERNAME = os.getenv("DEFAULT_ANALYST_USERNAME", "analyst")
    DEFAULT_ANALYST_PASSWORD = os.getenv("DEFAULT_ANALYST_PASSWORD", "AnalystPassword123!")
    DEFAULT_ANALYST_EMAIL = os.getenv("DEFAULT_ANALYST_EMAIL", "analyst@fraudguard.local")

    # Abuse defense and rate limiting
    RATE_LIMITING_ENABLED = os.getenv("RATE_LIMITING_ENABLED", "True").lower() in ("true", "1")
    RATE_LIMIT_PREDICT = int(os.getenv("RATE_LIMIT_PREDICT", "120"))
    RATE_LIMIT_LOGIN = int(os.getenv("RATE_LIMIT_LOGIN", "20"))
    RATE_LIMIT_REGISTER = int(os.getenv("RATE_LIMIT_REGISTER", "10"))

    # Google OAuth 2.0 / OpenID Connect Settings
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{INSTANCE_DIR / 'fraud_detection_dev.db'}"
    )


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    # In-memory SQLite for high-speed, isolated unit testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATE_LIMITING_ENABLED = False

    # Mock Google OAuth settings for testing
    GOOGLE_CLIENT_ID = "mock-google-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "mock-google-client-secret-key"
    GOOGLE_REDIRECT_URI = "http://localhost:5000/auth/google/callback"


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{INSTANCE_DIR / 'fraud_detection.db'}"
    )


# Mapping environment name to config object
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
