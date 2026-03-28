"""WSGI entry-point for Gunicorn / Flask CLI."""
from app import create_app  # noqa: F811

# Flask CLI auto-discovers create_app; Gunicorn uses 'application'
application = create_app()
