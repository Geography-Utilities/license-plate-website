import os

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    RATELIMIT_STORAGE_URI = "memory://"

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://plates_dev:devpassword@localhost:5432/plates_dev",
    )
    DEBUG = True

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    DEBUG = False
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI")
    SESSION_COOKIE_NAME = "__Host-session"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    if env == "development":
        print("Development Config Enabled")
    return DevelopmentConfig if env == "development" else ProductionConfig