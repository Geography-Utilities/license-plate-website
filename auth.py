from flask import session

def current_user():
    return session.get('user')

def is_authenticated():
    return current_user() is not None