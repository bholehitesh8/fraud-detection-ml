"""
Application Server Entry Point
------------------------------
Launches the Flask development server for the Fraud Detection system.

Usage:
    python run.py
"""

import os
from app import create_app

# Instantiate application using environment setting or default development configuration
env_name = os.getenv("FLASK_ENV", "development")
app = create_app(config_name=env_name)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f" * Starting Fraud Detection ML Application on http://127.0.0.1:{port}")
    print(f" * Active Environment: {env_name}")
    app.run(host="127.0.0.1", port=port, debug=True)
