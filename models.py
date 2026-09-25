from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50), unique=True, nullable=True)
    display_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    alpca = db.Column(db.String(100), nullable=True)
    home_country = db.Column(db.String(100), nullable=True)
    home_state = db.Column(db.String(100), nullable=True)
    permission_level = db.Column(db.Integer, default=1)  # 0: view-only, 1: submit, 2: moderator, 3: superuser
    