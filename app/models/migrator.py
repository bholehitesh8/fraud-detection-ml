"""
Database Schema Migration Module
--------------------------------
Provides idempotent, cross-platform schema migration for SQLite / SQLAlchemy.
Safely detects and adds missing columns, creates indexes, and backfills legacy
data without dropping tables or losing existing records.
"""

import logging
from typing import Dict, Any, List, Optional
import sqlalchemy as sa
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

# Column definitions to add if missing from the transactions table
MIGRATION_COLUMNS: List[tuple] = [
    ("currency", "VARCHAR(3) DEFAULT 'USD'"),
    ("normalized_amount", "FLOAT"),
    ("exchange_rate", "FLOAT DEFAULT 1.0"),
    ("old_balance_dest", "FLOAT DEFAULT 0.0"),
    ("new_balance_dest", "FLOAT DEFAULT 0.0"),
    ("step", "FLOAT DEFAULT 1.0"),
    ("fraud_probability", "FLOAT"),
    ("model_name", "VARCHAR(64) DEFAULT 'ExtraTrees'"),
    ("model_version", "VARCHAR(32) DEFAULT '1.0.0'"),
    ("status", "VARCHAR(32) DEFAULT 'COMPLETED'"),
    ("prediction_timestamp", "DATETIME"),
]

INDEXES_TO_ENSURE: List[str] = [
    "CREATE INDEX IF NOT EXISTS ix_transactions_currency ON transactions (currency);",
    "CREATE INDEX IF NOT EXISTS ix_transactions_is_fraud ON transactions (is_fraud);",
    "CREATE INDEX IF NOT EXISTS ix_transactions_created_at ON transactions (created_at);",
    "CREATE INDEX IF NOT EXISTS ix_transactions_prediction_timestamp ON transactions (prediction_timestamp);",
    "CREATE INDEX IF NOT EXISTS ix_transactions_transaction_type ON transactions (transaction_type);",
]

USER_INDEXES_TO_ENSURE: List[str] = [
    "CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);",
    "CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);",
]

AUDIT_INDEXES_TO_ENSURE: List[str] = [
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp);",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_event_type ON audit_logs (event_type);",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id);",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);",
]

USER_MIGRATION_COLUMNS: List[tuple] = [
    ("failed_login_attempts", "INTEGER DEFAULT 0"),
    ("locked_until", "DATETIME"),
]


def upgrade_database_schema(engine=None) -> Dict[str, Any]:
    """
    Idempotent schema upgrade for the 'transactions' table.
    
    Checks current SQLite table schema via SQLAlchemy Inspector,
    adds any missing columns with proper types and defaults,
    backfills legacy rows, and ensures performance indexes exist.

    Args:
        engine: SQLAlchemy Engine instance. If None, imported from app.models.db.

    Returns:
        Dict with migration summary: {'columns_added': [...], 'success': bool}
    """
    if engine is None:
        from app.models import db
        engine = db.engine

    result: Dict[str, Any] = {
        "columns_added": [],
        "indexes_ensured": len(INDEXES_TO_ENSURE),
        "success": True,
        "message": "Schema up to date."
    }

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "transactions" not in tables:
            # Table does not exist yet; db.create_all() will create it with full schema.
            logger.info("Table 'transactions' does not exist yet. Skipping migration.")
            result["message"] = "Table does not exist yet."
            return result

        existing_columns = {col["name"].lower() for col in inspector.get_columns("transactions")}
        columns_to_add = [
            (col_name, col_def)
            for col_name, col_def in MIGRATION_COLUMNS
            if col_name.lower() not in existing_columns
        ]

        with engine.begin() as connection:
            # 1. Add any missing columns
            for col_name, col_def in columns_to_add:
                sql = f"ALTER TABLE transactions ADD COLUMN {col_name} {col_def}"
                logger.info("Applying schema migration: %s", sql)
                connection.execute(text(sql))
                result["columns_added"].append(col_name)

            # 2. Backfill legacy records if new columns were added or have nulls
            backfill_sql = """
                UPDATE transactions
                SET 
                    currency = COALESCE(currency, 'USD'),
                    normalized_amount = COALESCE(normalized_amount, amount),
                    exchange_rate = COALESCE(exchange_rate, 1.0),
                    old_balance_dest = COALESCE(old_balance_dest, 0.0),
                    new_balance_dest = COALESCE(new_balance_dest, 0.0),
                    step = COALESCE(step, 1.0),
                    fraud_probability = COALESCE(
                        fraud_probability,
                        CASE WHEN is_fraud = 1 THEN ROUND(confidence_score / 100.0, 4) ELSE 0.0 END
                    ),
                    model_name = COALESCE(model_name, 'ExtraTrees'),
                    model_version = COALESCE(model_version, '1.0.0'),
                    status = COALESCE(
                        status,
                        CASE WHEN is_fraud = 1 THEN 'fraudulent' ELSE 'legitimate' END
                    ),
                    prediction_timestamp = COALESCE(prediction_timestamp, created_at)
                WHERE 
                    currency IS NULL 
                    OR normalized_amount IS NULL 
                    OR exchange_rate IS NULL
                    OR old_balance_dest IS NULL
                    OR new_balance_dest IS NULL
                    OR step IS NULL
                    OR fraud_probability IS NULL
                    OR model_name IS NULL
                    OR model_version IS NULL
                    OR status IS NULL
                    OR prediction_timestamp IS NULL
            """
            bf_res = connection.execute(text(backfill_sql))
            logger.info("Backfill executed: %s rows affected", bf_res.rowcount)

            # 3. Ensure B-Tree indexes exist
            for index_sql in INDEXES_TO_ENSURE:
                connection.execute(text(index_sql))

        if result["columns_added"]:
            result["message"] = f"Added {len(result['columns_added'])} missing columns: {', '.join(result['columns_added'])}"
            logger.info("Database schema upgrade successful: %s", result["message"])
        else:
            result["message"] = "All schema columns and indexes already present."

        return result

    except Exception as e:
        logger.error("Database schema upgrade failed: %s", e)
        result["success"] = False
        result["error"] = str(e)
        raise


def upgrade_user_schema(engine=None) -> Dict[str, Any]:
    """
    Idempotently upgrades users and audit_logs table schemas for Prompt 9.
    Adds failed_login_attempts and locked_until columns to users table if missing.
    Ensures indexes exist on users and audit_logs tables.
    """
    if engine is None:
        from app.models import db
        engine = db.engine

    result = {
        "columns_added": [],
        "success": True,
        "message": "User and audit schema up to date."
    }

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        with engine.begin() as connection:
            if "users" in tables:
                existing_user_cols = {col["name"].lower() for col in inspector.get_columns("users")}
                for col_name, col_def in USER_MIGRATION_COLUMNS:
                    if col_name.lower() not in existing_user_cols:
                        user_sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                        logger.info("Applying users schema migration: %s", user_sql)
                        connection.execute(text(user_sql))
                        result["columns_added"].append(f"users.{col_name}")

                for index_sql in USER_INDEXES_TO_ENSURE:
                    connection.execute(text(index_sql))

            if "audit_logs" in tables:
                for index_sql in AUDIT_INDEXES_TO_ENSURE:
                    connection.execute(text(index_sql))

        return result
    except Exception as e:
        logger.error("User schema upgrade failed: %s", e)
        result["success"] = False
        result["error"] = str(e)
        return result


def run_migrations(app=None) -> None:
    """
    Convenience wrapper called during application initialization.
    Runs schema migrations and ensures indexes across all tables.
    """
    try:
        from app.models import db
        engine = db.engine
        upgrade_database_schema(engine)
        upgrade_user_schema(engine)
    except Exception as e:
        logger.error("Failed to run migrations: %s", e)


