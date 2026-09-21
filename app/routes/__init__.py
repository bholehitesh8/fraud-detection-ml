"""
Routes Package
--------------
Exposes Blueprints for main pages, transaction handling, and REST APIs.
"""

from app.routes.main_routes import main_bp
from app.routes.transaction_routes import transaction_bp
from app.routes.api_routes import api_bp
from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp

__all__ = ["main_bp", "transaction_bp", "api_bp", "auth_bp", "admin_bp"]
