"""
Teams Hub — Application Factory
=================================
Follows the same 10-step initialisation pattern as Orbit:

  1. _init_logging()          – structured logging (stdout + optional file)
  2. _init_extensions()       – bind all Flask extensions to the app
  3. _register_blueprints()   – register route blueprints
  4. _register_cli()          – register admin CLI commands
  5. _register_template_utils() – Jinja2 filters & context processors
  6. _register_hooks()        – before/after request hooks
  7. _register_error_handlers() – 400/401/403/404/429/500 handlers
  8. _init_celery()           – bind Celery to the Flask app context
  9. _register_health_route() – unauthenticated /health endpoint
 10. _setup_first_run_redirect() – redirect to /setup if no users exist
"""
import logging
import sys
from datetime import datetime, timezone

from flask import (
    Flask, render_template, redirect, url_for,
    request, g, jsonify,
)
from flask_login import current_user

from config import get_config


def create_app(config_override=None):
    """
    Application factory.

    Parameters
    ----------
    config_override : class | dict | None
        Pass a config class (or dict) to override the environment-based
        configuration, e.g. TestingConfig during pytest.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Load configuration
    if config_override:
        if isinstance(config_override, dict):
            app.config.from_mapping(config_override)
        else:
            app.config.from_object(config_override)
    else:
        cfg = get_config()
        app.config.from_object(cfg)
        if hasattr(cfg, "validate") and not app.config.get("TESTING"):
            try:
                cfg.validate()
            except ValueError as exc:
                app.logger.warning(f"Config validation: {exc}")

    # 10-step init
    _init_logging(app)                    # 1
    _init_extensions(app)                 # 2
    _register_blueprints(app)            # 3
    _register_cli(app)                   # 4
    _register_template_utils(app)        # 5
    _register_hooks(app)                 # 6
    _register_error_handlers(app)        # 7
    _init_celery(app)                    # 8
    _register_health_route(app)          # 9
    _register_root_redirect(app)         # 9b
    _setup_first_run_redirect(app)       # 10

    app.logger.info(
        f"Teams Hub v{app.config.get('APP_VERSION', '1.0.0')} "
        f"started ({app.config.get('ENV', 'production')})"
    )
    return app


# ============================================================================
# 1. Logging
# ============================================================================

def _init_logging(app: Flask) -> None:
    """Configure structured logging to stdout and optional file."""
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout handler
    if app.config.get("LOG_TO_STDOUT", True):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(fmt)
        stdout_handler.setLevel(level)
        app.logger.addHandler(stdout_handler)

    app.logger.setLevel(level)

    # Silence noisy libraries
    for lib in ("urllib3", "msal", "requests", "werkzeug"):
        logging.getLogger(lib).setLevel(logging.WARNING)


# ============================================================================
# 2. Extensions
# ============================================================================

def _init_extensions(app: Flask) -> None:
    """Initialise all Flask extensions."""
    from app.extensions import (
        db, migrate, login_manager, csrf,
        limiter, cache, mail, bcrypt,
    )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)

    # Flask-Login config
    login_manager.login_view        = "auth.login"
    login_manager.login_message     = "Please log in to continue."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models.user import User
        return User.query.get(int(user_id))


# ============================================================================
# 3. Blueprints
# ============================================================================

def _register_blueprints(app: Flask) -> None:
    """Register all route blueprints."""
    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.teams     import teams_bp
    from app.routes.users     import users_bp
    from app.routes.calls     import calls_bp
    from app.routes.meetings  import meetings_bp
    from app.routes.settings  import settings_bp
    from app.routes.audit     import audit_bp
    from app.routes.tasks     import tasks_bp
    from app.routes.setup     import setup_bp

    for bp in (
        auth_bp, dashboard_bp, teams_bp, users_bp,
        calls_bp, meetings_bp, settings_bp, audit_bp,
        tasks_bp, setup_bp,
    ):
        app.register_blueprint(bp)


# ============================================================================
# 4. CLI Commands
# ============================================================================

def _register_cli(app: Flask) -> None:
    """Register admin CLI commands."""
    from app.cli.commands import admin_cli
    app.cli.add_command(admin_cli)


# ============================================================================
# 5. Template Utilities
# ============================================================================

def _register_template_utils(app: Flask) -> None:
    """Register Jinja2 filters and context processors."""
    from app.utils.template_filters import register_filters
    register_filters(app)

    @app.context_processor
    def inject_globals():
        from app.models.app_config import AppConfig
        try:
            app_name      = AppConfig.get("APP_NAME", "Teams Hub")
            primary_color = AppConfig.get("PRIMARY_COLOR", "#1E40AF")
            accent_color  = AppConfig.get("ACCENT_COLOR", "#3B82F6")
        except Exception:
            app_name      = "Teams Hub"
            primary_color = "#1E40AF"
            accent_color  = "#3B82F6"

        return {
            "app_name":      app_name,
            "primary_color": primary_color,
            "accent_color":  accent_color,
            "app_version":   app.config.get("APP_VERSION", "1.0.0"),
            "now":           datetime.now(timezone.utc),
        }


# ============================================================================
# 6. Request Hooks
# ============================================================================

def _register_hooks(app: Flask) -> None:
    """Register before/after request hooks."""

    @app.before_request
    def set_request_start_time():
        g.request_start = datetime.now(timezone.utc)

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"]        = "SAMEORIGIN"
        response.headers["X-XSS-Protection"]       = "1; mode=block"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        return response


# ============================================================================
# 7. Error Handlers
# ============================================================================

def _register_error_handlers(app: Flask) -> None:
    """Register error handlers for common HTTP errors."""

    def _wants_json() -> bool:
        return (
            request.accept_mimetypes.best == "application/json"
            or request.is_json
        )

    @app.errorhandler(400)
    def bad_request(e):
        if _wants_json():
            return jsonify({"error": "Bad request"}), 400
        return render_template("errors/400.html"), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if _wants_json():
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(e):
        if _wants_json():
            return jsonify({"error": "Forbidden"}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        if _wants_json():
            return jsonify({"error": "Not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        if _wants_json():
            return jsonify({"error": "Too many requests"}), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def internal_error(e):
        if _wants_json():
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500


# ============================================================================
# 8. Celery
# ============================================================================

def _init_celery(app: Flask) -> None:
    """Bind the Celery instance to the Flask app context."""
    from app.extensions import celery

    celery.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            "sync-teams-every-hour": {
                "task":     "app.tasks.teams_sync.sync_all_teams",
                "schedule": 3600.0,
            },
            "sync-users-every-4-hours": {
                "task":     "app.tasks.teams_sync.sync_graph_users",
                "schedule": 14400.0,
            },
            "health-ping-every-5-minutes": {
                "task":     "app.tasks.maintenance.health_ping",
                "schedule": 300.0,
            },
            "purge-audit-logs-daily": {
                "task":     "app.tasks.maintenance.purge_old_audit_logs",
                "schedule": 86400.0,
            },
        },
    )


# ============================================================================
# 9. Health Check
# ============================================================================

def _register_health_route(app: Flask) -> None:
    """Register an unauthenticated /health endpoint."""

    @app.route("/health")
    def health_check():
        from app.extensions import db
        try:
            db.session.execute(db.text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False

        return jsonify({
            "status":   "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "unavailable",
            "version":  app.config.get("APP_VERSION", "1.0.0"),
            "ts":       datetime.now(timezone.utc).isoformat(),
        }), 200 if db_ok else 503


# ============================================================================
# 10. First-Run Redirect
# ============================================================================

def _register_root_redirect(app: Flask) -> None:
    """Redirect / to the admin dashboard."""

    @app.route("/")
    def root_redirect():
        return redirect(url_for("dashboard.index"))


# ============================================================================
# 10. First-Run Redirect
# ============================================================================

def _setup_first_run_redirect(app: Flask) -> None:
    """If no users exist, redirect every request to /setup."""

    @app.before_request
    def check_first_run():
        if request.endpoint and request.endpoint.startswith("setup"):
            return
        if request.endpoint == "health_check":
            return
        if request.endpoint == "static":
            return

        try:
            from app.models.user import User
            if User.query.first() is None:
                return redirect(url_for("setup.initial_setup"))
        except Exception:
            pass
