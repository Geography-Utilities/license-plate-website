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


class Continent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    countries = db.relationship("Country", back_populates="continent")


class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    continent_id = db.Column(
        db.Integer, db.ForeignKey("continent.id"), nullable=False, index=True
    )

    continent = db.relationship("Continent", back_populates="countries")
    regions = db.relationship("Region", back_populates="country")

    __table_args__ = (db.UniqueConstraint("continent_id", "name"),)


class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country_id = db.Column(
        db.Integer, db.ForeignKey("country.id"), nullable=False, index=True
    )

    country = db.relationship("Country", back_populates="regions")
    subregions = db.relationship("SubRegion", back_populates="region")

    __table_args__ = (db.UniqueConstraint("country_id", "name"),)


class SubRegion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(
        db.Integer, db.ForeignKey("region.id"), nullable=False, index=True
    )

    region = db.relationship("Region", back_populates="subregions")

    __table_args__ = (db.UniqueConstraint("region_id", "name"),)


class Plates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    region = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(500), nullable=True)


class Submissions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(20), nullable=False)
    plate_id = db.Column(db.Integer, db.ForeignKey("plates.id"), nullable=False)
    date_submitted = db.Column(db.Date, nullable=False)
    date_seen = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    subregion = db.Column(db.Integer, db.ForeignKey("sub_region.id"), nullable=True)
    notes = db.Column(db.String(500), nullable=True)