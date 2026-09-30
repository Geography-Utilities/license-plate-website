from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_type = db.Column(db.String(100), nullable=True, default='discord')
    password_hash = db.Column(db.String(255), nullable=True)
    discord_id = db.Column(db.String(50), unique=True, nullable=True)
    display_name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    alpca = db.Column(db.String(100), nullable=True)
    home_country = db.Column(db.String(100), nullable=True)
    home_state = db.Column(db.String(100), nullable=True)
    permission_level = db.Column(db.Integer, default=0)  # 0: view-only, 1: submit, 2: moderator, 3: superuser
    