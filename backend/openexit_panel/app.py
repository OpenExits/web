"""create_app() — the panel's Flask application factory."""
from __future__ import annotations

from flask import Flask, jsonify

from .config import Config
from .db import Base, init_engine


def create_app(config_object=Config, *, create_tables: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    engine = init_engine(app.config["DB_URL"])
    if create_tables:  # tests/dev bootstrap; real schema management is Alembic
        from . import models  # noqa: F401 — register mappings
        Base.metadata.create_all(engine)

    from .api.auth_routes import bp as auth_bp
    app.register_blueprint(auth_bp)

    @app.get("/api/v1/health")
    def health():
        return jsonify({"ok": True})

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"error": "server_error"}), 500

    return app
