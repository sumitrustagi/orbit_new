"""
Cisco UC Hub — Application Factory
=====================================
10-step initialization matching Orbit's pattern:
  1. Load configuration
  2. Initialize extensions
  3. Configure Celery
  4. Register blueprints
  5. Register CLI commands
  6. Configure login manager
  7. Register template filters
  8. Register error handlers
  9. Set up request hooks
 10. Configure logging
"""
import logging
import os

from flask import Flask, redirect, url_for, render_template, request
from celery.schedules import crontab

from config import get_config


def create_app(config_class=None):
    flask_app = Flask(__name__)

    # ── Step 1: Load Configuration ────────────────────────────────────
    if config_class is None:
        config_class = get_config()
    flask_app.config.from_object(config_class)

    # ── Step 2: Initialize Extensions ─────────────────────────────────
    from app.extensions import db, migrate, login_manager, csrf, limiter, cache, mail, bcrypt
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    csrf.init_app(flask_app)
    limiter.init_app(flask_app)
    cache.init_app(flask_app)
    mail.init_app(flask_app)
    bcrypt.init_app(flask_app)

    # ── Step 3: Configure Celery ──────────────────────────────────────
    from app.extensions import celery
    celery.conf.broker_url = flask_app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery.conf.result_backend = flask_app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    celery.conf.task_serializer = "json"
    celery.conf.result_serializer = "json"
    celery.conf.accept_content = ["json"]
    celery.conf.timezone = "UTC"
    celery.conf.enable_utc = True
    celery.conf.beat_schedule = {
        "sync-cucm-hourly": {
            "task": "app.tasks.cucm_tasks.sync_all_cucm",
            "schedule": crontab(minute=0),
        },
        "sync-unity-4hourly": {
            "task": "app.tasks.unity_tasks.sync_unity_users",
            "schedule": crontab(minute=0, hour="*/4"),
        },
        "sync-unity-mailboxes-4hourly": {
            "task": "app.tasks.unity_tasks.sync_unity_mailboxes",
            "schedule": crontab(minute=10, hour="*/4"),
        },
        "sync-imp-4hourly": {
            "task": "app.tasks.imp_tasks.sync_imp_users",
            "schedule": crontab(minute=20, hour="*/4"),
        },
        "sync-expressway-4hourly": {
            "task": "app.tasks.expressway_tasks.sync_expressways",
            "schedule": crontab(minute=30, hour="*/4"),
        },
        "health-ping-5min": {
            "task": "app.tasks.system_tasks.health_ping",
            "schedule": 300.0,
        },
        "purge-audit-logs-daily": {
            "task": "app.tasks.system_tasks.purge_old_audit_logs",
            "schedule": crontab(minute=0, hour=0),
        },
    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # ── Step 4: Register Blueprints ───────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.cucm import cucm_bp
    from app.routes.unity import unity_bp
    from app.routes.imp import imp_bp
    from app.routes.expressway import expressway_bp
    from app.routes.users import users_bp
    from app.routes.settings import settings_bp
    from app.routes.audit import audit_bp
    from app.routes.tasks import tasks_bp
    from app.routes.setup import setup_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(dashboard_bp)
    flask_app.register_blueprint(cucm_bp)
    flask_app.register_blueprint(unity_bp)
    flask_app.register_blueprint(imp_bp)
    flask_app.register_blueprint(expressway_bp)
    flask_app.register_blueprint(users_bp)
    flask_app.register_blueprint(settings_bp)
    flask_app.register_blueprint(audit_bp)
    flask_app.register_blueprint(tasks_bp)
    flask_app.register_blueprint(setup_bp)

    # ── Step 5: Register CLI Commands ─────────────────────────────────
    from app.cli.admin_cli import admin_cli
    flask_app.cli.add_command(admin_cli)

    # ── Step 6: Configure Login Manager ───────────────────────────────
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # ── Step 7: Register Template Filters ─────────────────────────────
    from app.utils.template_filters import register_filters
    register_filters(flask_app)

    # ── Step 8: Register Error Handlers ───────────────────────────────
    @flask_app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @flask_app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @flask_app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(429)
    def too_many_requests(e):
        return render_template("errors/429.html"), 429

    @flask_app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    # ── Step 9: Request Hooks ─────────────────────────────────────────
    @flask_app.before_request
    def check_setup():
        from app.models.user import User
        allowed = ("setup.wizard", "static", "auth.login")
        if request.endpoint and request.endpoint not in allowed:
            try:
                if User.query.count() == 0:
                    return redirect(url_for("setup.wizard"))
            except Exception:
                pass

    @flask_app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Health endpoint
    @flask_app.route("/health")
    @csrf.exempt
    def health():
        return {"status": "ok", "app": "Cisco UC Hub"}, 200

    # ── Step 10: Configure Logging ────────────────────────────────────
    log_level = getattr(logging, flask_app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Ensure models are imported for Alembic
    with flask_app.app_context():
        import app.models  # noqa: F401

    return flask_app
