"""
Cisco UC Hub — Flask Extension Instances
==========================================
All extension objects are created here without an app instance.
They are bound to the app inside create_app() via their init_app() methods.
"""
from flask_sqlalchemy   import SQLAlchemy
from flask_migrate      import Migrate
from flask_login        import LoginManager
from flask_wtf.csrf     import CSRFProtect
from flask_limiter      import Limiter
from flask_limiter.util import get_remote_address
from flask_caching      import Cache
from flask_mail         import Mail
from flask_bcrypt       import Bcrypt
from celery             import Celery

db            = SQLAlchemy()
migrate       = Migrate()
login_manager = LoginManager()
csrf          = CSRFProtect()
limiter       = Limiter(key_func=get_remote_address)
cache         = Cache()
mail          = Mail()
bcrypt        = Bcrypt()
celery        = Celery("cisco_uc_hub")
