from flask import session
from models import User
from database import db

def current_user():
    return session.get('user')

def is_authenticated():
    return current_user() is not None

def discord_user_login(discord_id, discord_name):
    user = User.query.filter_by(discord_id=discord_id).first()
    if user is None:
        user = User(discord_id=discord_id, display_name=discord_name)
        db.session.add(user)
        db.session.commit()
    return user