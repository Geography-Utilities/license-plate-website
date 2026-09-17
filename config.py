import os

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://plates_dev:devpassword@localhost:5432/plates_dev",
    )
    DEBUG = True

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    DEBUG = False

def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return DevelopmentConfig if env == "development" else ProductionConfig