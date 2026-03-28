"""
Celery worker entry-point.

Usage:
    celery -A celery_worker.celery worker --loglevel=info
    celery -A celery_worker.celery beat   --loglevel=info
"""
from app import create_app

flask_app = create_app()
flask_app.app_context().push()

from app.extensions import celery  # noqa: E402
