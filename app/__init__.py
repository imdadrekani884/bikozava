"""
Bikozava — Application Factory (`app/__init__.py`)
Initializes Flask application, configures security headers, CSRF tokens,
database schema & seeding, blueprints, and production error handlers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config import load_config
from .database import close_db, init_db_schema
from .flask_compat import Flask, render_template, request
from .i18n import localize_field
from .routes.admin import admin_bp
from .routes.public import public_bp
from .security import (
    apply_security_headers,
    generate_csrf_token,
    get_current_admin,
)
from .seed import seed_database


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure an instance of the Bikozava application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    cfg = load_config(test_config)
    app.config.update(cfg)

    # Support Render / Cloudflare reverse proxy headers (X-Forwarded-For, X-Forwarded-Proto)
    if app.config.get("TRUST_PROXY_HEADERS", True) and hasattr(app, "wsgi_app"):
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix  # type: ignore
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)  # type: ignore
        except Exception:
            pass

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Attach security headers to every HTTP response
    app.after_request(apply_security_headers)

    # Inject global template helpers (CSRF token, current_admin, app_name, localize_field)
    @app.context_processor
    def inject_globals() -> Dict[str, Any]:
        return {
            "csrf_token": generate_csrf_token,
            "current_admin": get_current_admin(),
            "app_name": app.config.get("APP_NAME", "Bikozava"),
            "public_base_url": app.config.get("PUBLIC_BASE_URL", "https://bikozava.com"),
            "localize_field": localize_field,
        }

    # Register blueprints (Admin first so `/admin/...` never collides with `/<slug>`)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)

    # Production Error Handlers (never expose stack traces to visitors)
    @app.errorhandler(400)
    def handle_400(err: Any) -> Any:
        desc = getattr(err, "description", "Invalid request.")
        if request.is_json or request.path.startswith("/admin/api/"):
            return {"error": desc, "status": 400}, 400
        return render_template("errors/error.html", code=400, title="Bad Request", message=desc), 400

    @app.errorhandler(403)
    def handle_403(err: Any) -> Any:
        desc = getattr(err, "description", "Access denied.")
        if request.is_json or request.path.startswith("/admin/api/"):
            return {"error": desc, "status": 403}, 403
        return render_template("errors/error.html", code=403, title="Access Denied", message=desc), 403

    @app.errorhandler(404)
    def handle_404(err: Any) -> Any:
        desc = getattr(err, "description", "The wedding invitation or page you requested could not be found.")
        if request.is_json or request.path.startswith("/admin/api/"):
            return {"error": desc, "status": 404}, 404
        return render_template("errors/error.html", code=404, title="Page Not Found", message=desc), 404

    @app.errorhandler(413)
    def handle_413(err: Any) -> Any:
        desc = "Uploaded file exceeds the maximum allowed size."
        if request.is_json:
            return {"error": desc, "status": 413}, 413
        return render_template("errors/error.html", code=413, title="File Too Large", message=desc), 413

    @app.errorhandler(429)
    def handle_429(err: Any) -> Any:
        desc = "Too many attempts. Please wait a few minutes and try again."
        if request.is_json:
            return {"error": desc, "status": 429}, 429
        return render_template("errors/error.html", code=429, title="Too Many Requests", message=desc), 429

    @app.errorhandler(500)
    def handle_500(err: Any) -> Any:
        desc = "An unexpected server error occurred. Please try again shortly."
        if request.is_json:
            return {"error": desc, "status": 500}, 500
        return render_template("errors/error.html", code=500, title="Server Error", message=desc), 500

    # Initialize schema and seed default data inside app context
    with app.app_context():
        init_db_schema()
        seed_database()

    return app
