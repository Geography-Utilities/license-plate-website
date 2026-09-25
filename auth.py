from flask import session, render_template, current_app
from models import User
from database import db
from functools import wraps
from sqlalchemy.exc import IntegrityError

def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)

def is_authenticated():
    return current_user() is not None

def discord_user_login(discord_id, display_name):
    user = User.query.filter_by(discord_id=discord_id).first()
    if user is None:
        user = User(discord_id=discord_id, display_name=display_name)
        db.session.add(user)
        db.session.commit()
    return user

def get_permission_level():
    override = current_app.config.get("DEV_AUTH_LEVEL")
    if override is not None:
        return override

    uid = session.get("user_id")
    if uid is None:
        return 0
    db_user = db.session.get(User, uid)
    if db_user is None:
        return 0
    return db_user.permission_level or 0

def require_level(minimum):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if get_permission_level() < minimum:
                return render_template("unauthorized.html"), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator