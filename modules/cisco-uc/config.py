"""
Cisco UC Hub — Flask Configuration Classes
=============================================
Hierarchy:
  BaseConfig        — shared defaults, reads from environment variables
  DevelopmentConfig — local dev (DEBUG=True, SQLite fallback)
  TestingConfig     — pytest (in-memory SQLite, CSRF disabled)
  ProductionConfig  — production (PostgreSQL, strict security)
"""
import os
from datetime import timedelta


class BaseConfig:
    APP_NAME                       = "Cisco UC Hub"
    APP_VERSION                    = "1.0.0"
    SECRET_KEY                     = os.environ.get("SECRET_KEY", "change-me-to-a-long-random-string")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {"pool_pre_ping": True, "pool_recycle": 300, "pool_size": 10, "max_overflow": 20}

    SESSION_COOKIE_HTTPONLY         = True
    SESSION_COOKIE_SAMESITE        = "Lax"
    PERMANENT_SESSION_LIFETIME     = timedelta(minutes=30)
    SESSION_COOKIE_NAME            = "uc_hub_session"

    WTF_CSRF_ENABLED               = True
    WTF_CSRF_TIME_LIMIT            = 3600
    WTF_CSRF_SSL_STRICT            = False

    CACHE_TYPE                     = "RedisCache"
    CACHE_DEFAULT_TIMEOUT          = 300
    CACHE_REDIS_URL                = os.environ.get("REDIS_URL", "redis://localhost:6379/2")

    RATELIMIT_ENABLED              = True
    RATELIMIT_STORAGE_URI          = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    RATELIMIT_DEFAULT              = "200 per hour"
    RATELIMIT_STRATEGY             = "fixed-window"
    RATELIMIT_HEADERS_ENABLED      = True

    CELERY_BROKER_URL              = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND          = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    MAIL_SERVER                    = os.environ.get("SMTP_HOST", "")
    MAIL_PORT                      = int(os.environ.get("SMTP_PORT", "587"))
    MAIL_USE_TLS                   = os.environ.get("SMTP_USE_TLS", "true") == "true"
    MAIL_USE_SSL                   = False
    MAIL_USERNAME                  = os.environ.get("SMTP_USERNAME", "")
    MAIL_PASSWORD                  = os.environ.get("SMTP_PASSWORD", "")
    MAIL_DEFAULT_SENDER            = os.environ.get("SMTP_SENDER_EMAIL", "uc-hub@localhost")

    # -- Cisco CUCM (AXL / RIS / UDS) --
    CUCM_HOST                      = os.environ.get("CUCM_HOST", "")
    CUCM_USERNAME                  = os.environ.get("CUCM_USERNAME", "")
    CUCM_PASSWORD                  = os.environ.get("CUCM_PASSWORD", "")
    CUCM_VERSION                   = os.environ.get("CUCM_VERSION", "14.0")
    CUCM_VERIFY_SSL                = os.environ.get("CUCM_VERIFY_SSL", "false") == "true"

    # -- Cisco Unity Connection --
    UNITY_HOST                     = os.environ.get("UNITY_HOST", "")
    UNITY_USERNAME                 = os.environ.get("UNITY_USERNAME", "")
    UNITY_PASSWORD                 = os.environ.get("UNITY_PASSWORD", "")
    UNITY_VERIFY_SSL               = os.environ.get("UNITY_VERIFY_SSL", "false") == "true"

    # -- Cisco IM&P --
    IMP_HOST                       = os.environ.get("IMP_HOST", "")
    IMP_USERNAME                   = os.environ.get("IMP_USERNAME", "")
    IMP_PASSWORD                   = os.environ.get("IMP_PASSWORD", "")
    IMP_VERIFY_SSL                 = os.environ.get("IMP_VERIFY_SSL", "false") == "true"

    # -- Cisco Expressway --
    EXPRESSWAY_HOST                = os.environ.get("EXPRESSWAY_HOST", "")
    EXPRESSWAY_USERNAME            = os.environ.get("EXPRESSWAY_USERNAME", "")
    EXPRESSWAY_PASSWORD            = os.environ.get("EXPRESSWAY_PASSWORD", "")
    EXPRESSWAY_VERIFY_SSL          = os.environ.get("EXPRESSWAY_VERIFY_SSL", "false") == "true"

    LOG_LEVEL                      = os.environ.get("LOG_LEVEL", "INFO")
    LOG_TO_STDOUT                  = os.environ.get("LOG_TO_STDOUT", "true") == "true"


class DevelopmentConfig(BaseConfig):
    DEBUG                          = True
    SQLALCHEMY_DATABASE_URI        = os.environ.get("DATABASE_URL", "sqlite:///uc_hub_dev.db")
    SQLALCHEMY_ECHO                = os.environ.get("SQL_ECHO", "false") == "true"
    SESSION_COOKIE_SECURE          = False
    WTF_CSRF_SSL_STRICT            = False
    CACHE_TYPE                     = "SimpleCache"
    RATELIMIT_ENABLED              = False
    LOG_LEVEL                      = "DEBUG"


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


class ProductionConfig(BaseConfig):
    DEBUG                          = False
    TESTING                        = False
    SQLALCHEMY_DATABASE_URI        = os.environ.get("DATABASE_URL", "")
    SESSION_COOKIE_SECURE          = True
    SESSION_COOKIE_SAMESITE        = "Strict"
    WTF_CSRF_SSL_STRICT            = True
    PREFERRED_URL_SCHEME           = "https"
    SQLALCHEMY_ENGINE_OPTIONS      = {"pool_pre_ping": True, "pool_recycle": 300, "pool_size": 20, "max_overflow": 40}
    LOG_LEVEL                      = os.environ.get("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        required = {
            "SECRET_KEY":   os.environ.get("SECRET_KEY"),
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")


_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
}


def get_config():
    env = (os.environ.get("FLASK_ENV") or os.environ.get("UC_HUB_CONFIG") or "production").lower()
    return _CONFIG_MAP.get(env, ProductionConfig)
