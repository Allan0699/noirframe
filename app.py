"""
NOIRFRAME -- Animation & Video Editing Agency Platform
Entry point. Run with:  python app.py
"""

import os

from flask import Flask, render_template, g

from config import Config
from db import register_db, init_db
from decorators import get_current_user


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    register_db(app)
    init_db(app)

    from seed_data import seed_if_empty
    seed_if_empty(app)

    # ---- blueprints -----------------------------------------------------
    from blueprints.main import bp as main_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.team_lead import bp as team_lead_bp
    from blueprints.employee import bp as employee_bp
    from blueprints.client import bp as client_bp
    from blueprints.ai import bp as ai_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(team_lead_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(ai_bp)

    # ---- template globals -------------------------------------------------
    @app.context_processor
    def inject_globals():
        return {
            "current_user": get_current_user(),
            "company_name": app.config["COMPANY_NAME"],
            "company_tagline": app.config["COMPANY_TAGLINE"],
        }

    # ---- error pages -------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
