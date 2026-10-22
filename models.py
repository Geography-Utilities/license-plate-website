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

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("location.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code = db.Column(db.String(10), nullable=True) # ISO 3166-2 code for the location, if applicable
    level = db.Column(db.Integer, nullable=True) # 1: Continent, 2: Country, 3: Region

class Plates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    region = db.Column(
        db.Integer,
        db.ForeignKey("location.id", name="fk_plates_region_location"),
        nullable=False,
    )
    category = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(500), nullable=True)

class CurrentHighs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_id = db.Column(
        db.Integer,
        db.ForeignKey("plates.id", name="fk_currenthighs_plate_plates"),
        nullable=False,
    )
    location = db.Column(
        db.Integer,
        db.ForeignKey("location.id", name="fk_currenthighs_location_location"),
        nullable=False,
    )

class Submissions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitter_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", name="fk_submissions_submitter_user"),
        nullable=False,
    )
    serial = db.Column(db.String(20), nullable=False)
    plate_id = db.Column(db.Integer, db.ForeignKey("plates.id"), nullable=False)
    date_submitted = db.Column(db.Date, nullable=False)
    date_seen = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    subregion = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, approved, rejected