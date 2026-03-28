"""
Celery worker entry point.

Usage:
    celery -A celery_worker.celery worker --loglevel=info
    celery -A celery_worker.celery beat   --loglevel=info
"""
from app import create_app
from app.extensions import celery

app = create_app()
celery.conf.update(app.config)


class ContextTask(celery.Task):
    """Ensure every Celery task runs inside a Flask app context."""

    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask
