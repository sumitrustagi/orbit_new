"""
Teams Hub — Flask Configuration Classes
=========================================
Hierarchy:
  BaseConfig        — shared defaults, reads from environment variables
  DevelopmentConfig — local dev (DEBUG=True, SQLite fallback, no Redis required)
  TestingConfig     — pytest (in-memory SQLite, CSRF disabled, no rate limiting)
  ProductionConfig  — production (PostgreSQL, strict security, Redis required)

The active config is resolved by get_config() using FLASK_ENV or
TEAMS_HUB_CONFIG environment variables. ProductionConfig is the safe default
when neither is set.
"""
import os
from datetime import timedelta


# =============================================================================
# BASE CONFIG
# =============================================================================

class BaseConfig:

    # -- Application ---------------------------------------------------------
    APP_NAME                       = "Teams Hub"
    APP_VERSION                    = "1.0.0"
    SECRET_KEY                     = os.environ.get(
        "SECRET_KEY", "change-me-to-a-long-random-string"
    )

    # -- Database ------------------------------------------------------------
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        "pool_pre_ping":  True,
        "pool_recycle":   300,
        "pool_size":      10,
        "max_overflow":   20,
    }

    # -- Session -------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY         = True
    SESSION_COOKIE_SAMESITE        = "Lax"
    PERMANENT_SESSION_LIFETIME     = timedelta(minutes=30)
    SESSION_COOKIE_NAME            = "teams_hub_session"

    # -- CSRF ----------------------------------------------------------------
    WTF_CSRF_ENABLED               = True
    WTF_CSRF_TIME_LIMIT            = 3600
    WTF_CSRF_SSL_STRICT            = False

    # -- Cache (Redis in prod, SimpleCache in dev) ---------------------------
    CACHE_TYPE                     = "RedisCache"
    CACHE_DEFAULT_TIMEOUT          = 300
    CACHE_REDIS_URL                = os.environ.get(
        "REDIS_URL", "redis://localhost:6379/2"
    )

    # -- Rate limiting -------------------------------------------------------
    RATELIMIT_ENABLED              = True
    RATELIMIT_STORAGE_URI          = os.environ.get(
        "REDIS_URL", "redis://localhost:6379/3"
    )
    RATELIMIT_DEFAULT              = "200 per hour"
    RATELIMIT_STRATEGY             = "fixed-window"
    RATELIMIT_HEADERS_ENABLED      = True

    # -- Celery --------------------------------------------------------------
    CELERY_BROKER_URL              = os.environ.get(
        "CELERY_BROKER_URL", "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND          = os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
    )

    # -- Flask-Mail (SMTP) ---------------------------------------------------
    MAIL_SERVER                    = os.environ.get("SMTP_HOST",     "")
    MAIL_PORT                      = int(os.environ.get("SMTP_PORT", "587"))
    MAIL_USE_TLS                   = os.environ.get("SMTP_USE_TLS", "true") == "true"
    MAIL_USE_SSL                   = False
    MAIL_USERNAME                  = os.environ.get("SMTP_USERNAME", "")
    MAIL_PASSWORD                  = os.environ.get("SMTP_PASSWORD", "")
    MAIL_DEFAULT_SENDER            = os.environ.get(
        "SMTP_SENDER_EMAIL", "teams-hub@localhost"
    )

    # -- Microsoft Graph API -------------------------------------------------
    MS_TENANT_ID                   = os.environ.get("MS_TENANT_ID", "")
    MS_CLIENT_ID                   = os.environ.get("MS_CLIENT_ID", "")
    MS_CLIENT_SECRET               = os.environ.get("MS_CLIENT_SECRET", "")
    MS_GRAPH_SCOPES                = os.environ.get(
        "MS_GRAPH_SCOPES",
        "https://graph.microsoft.com/.default"
    )

    # -- Logging -------------------------------------------------------------
    LOG_LEVEL                      = os.environ.get("LOG_LEVEL",     "INFO")
    LOG_TO_STDOUT                  = os.environ.get(
        "LOG_TO_STDOUT", "true"
    ) == "true"


# =============================================================================
# DEVELOPMENT CONFIG
# =============================================================================

class DevelopmentConfig(BaseConfig):
    DEBUG                          = True
    SQLALCHEMY_DATABASE_URI        = os.environ.get(
        "DATABASE_URL", "sqlite:///teams_hub_dev.db"
    )
    SQLALCHEMY_ECHO                = os.environ.get("SQL_ECHO", "false") == "true"

    SESSION_COOKIE_SECURE          = False
    WTF_CSRF_SSL_STRICT            = False

    CACHE_TYPE                     = "SimpleCache"
    RATELIMIT_ENABLED              = False

    LOG_LEVEL                      = "DEBUG"


# =============================================================================
# TESTING CONFIG
# =============================================================================

class TestingConfig(BaseConfig):
    TESTING                        = True
    DEBUG                          = True

    SQLALCHEMY_DATABASE_URI        = "sqlite:///:memory:"
    SQLALCHEMY_ECHO                = False

    WTF_CSRF_ENABLED               = False
    SESSION_COOKIE_SECURE          = False

    CACHE_TYPE                     = "SimpleCache"
    RATELIMIT_ENABLED              = False

    SERVER_NAME                    = "localhost"

    CELERY_TASK_ALWAYS_EAGER       = True
    CELERY_TASK_EAGER_PROPAGATES   = True

    LOG_LEVEL                      = "WARNING"


# =============================================================================
# PRODUCTION CONFIG
# =============================================================================

class ProductionConfig(BaseConfig):
    DEBUG                          = False
    TESTING                        = False

    SQLALCHEMY_DATABASE_URI        = os.environ.get("DATABASE_URL", "")

    SESSION_COOKIE_SECURE          = True
    SESSION_COOKIE_SAMESITE        = "Strict"
    WTF_CSRF_SSL_STRICT            = True

    PREFERRED_URL_SCHEME           = "https"

    SQLALCHEMY_ENGINE_OPTIONS      = {
        "pool_pre_ping":  True,
        "pool_recycle":   300,
        "pool_size":      20,
        "max_overflow":   40,
    }

    LOG_LEVEL                      = os.environ.get("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """
        Called by the app factory on startup.
        Raises ValueError listing any missing critical env vars.
        """
        required = {
            "SECRET_KEY":     os.environ.get("SECRET_KEY"),
            "DATABASE_URL":   os.environ.get("DATABASE_URL"),
            "MS_TENANT_ID":   os.environ.get("MS_TENANT_ID"),
            "MS_CLIENT_ID":   os.environ.get("MS_CLIENT_ID"),
            "MS_CLIENT_SECRET": os.environ.get("MS_CLIENT_SECRET"),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )


# =============================================================================
# CONFIG SELECTOR
# =============================================================================

_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
}


def get_config():
    """
    Return the correct config class based on the environment.
    Reads FLASK_ENV first, then TEAMS_HUB_CONFIG, then defaults to Production.
    """
    env = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("TEAMS_HUB_CONFIG")
        or "production"
    ).lower()
    return _CONFIG_MAP.get(env, ProductionConfig)
