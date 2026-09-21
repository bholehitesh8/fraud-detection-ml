"""
Fraud Detection in Online Transactions Application Factory
-----------------------------------------------------------
Instantiates and configures the Flask application, database bindings,
and routes according to design best practices.
"""

from flask import Flask, render_template
from app.config import config_by_name
from app.models import db


def create_app(config_name: str = "default") -> Flask:
    """
    Application Factory pattern to initialize and configure the Flask app.

    Args:
        config_name: String key matching configuration environment.
    """
    app = Flask(__name__)

    # 1. Load configuration
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # 2. Bind SQLAlchemy database
    db.init_app(app)

    # 3. Register Application Blueprints
    from app.routes import main_bp, transaction_bp, api_bp, auth_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # 4. Global Context Processors for Templates
    from app.utils.auth import get_current_user, seed_default_users

    @app.context_processor
    def inject_current_user():
        """Exposes current authenticated user object to all Jinja2 templates."""
        return {"current_user": get_current_user()}

    # 5. Security Response Headers Middleware
    @app.after_request
    def apply_security_headers(response):
        """Enforces robust HTTP security headers across all responses."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        return response

    # 6. Centralized Error Handlers (400, 401, 403, 404, 405, 409, 422, 429, 500)
    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # 7. Initialize database tables, run schema migrations, and seed default accounts
    with app.app_context():
        db.create_all()
        from app.models.migrator import upgrade_database_schema
        upgrade_database_schema(db.engine)
        seed_default_users(app)

    return app
