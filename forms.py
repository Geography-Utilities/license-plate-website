from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, InputRequired, Length, Optional
from datetime import date


class AdminEditUser(FlaskForm):
    display_name = StringField('Display Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    alpca = StringField('ALPCA #', validators=[Length(max=100)])
    home_state = StringField('Home State', validators=[Length(max=100)])
    home_country = StringField('Home Country', validators=[Length(max=100)])
    permission_level = SelectField(
        'Permission Level',
        choices=[(0, 'Read-only'), (1, 'Submit'), (2, 'Moderator'), (3, 'Site Admin')],
        coerce=int,
        validators=[InputRequired()]
    )

class SubmitPermanent(FlaskForm):
    plate = StringField('License Plate', validators=[DataRequired(), Length(max=20)])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    type = StringField('Specialty', validators=[DataRequired(), Length(max=100)])
    # picture field
    location = StringField('Location', validators=[DataRequired(), Length(max=100)])
    notes = StringField('Notes', validators=[Length(max=500)])


class SubmitTemporary(FlaskForm):
    plate = StringField('License Plate', validators=[DataRequired(), Length(max=20)])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    expiration_date = DateField('Expiration Date')
    location = StringField('Location', validators=[Length(max=100)])
    notes = StringField('Notes', validators=[Length(max=500)])


class SubmitPermanentCounty(FlaskForm):
    plate = StringField('License Plate', validators=[DataRequired(), Length(max=20)])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    county = StringField('County', validators=[Length(max=100)])
    type = StringField('Specialty', validators=[Length(max=100)])
    location = StringField('Location', validators=[Length(max=100)])
    notes = StringField('Notes', validators=[Length(max=500)])


class PlateForm(FlaskForm):
    name = StringField("Plate name", validators=[DataRequired(), Length(max=80)])
    region = SelectField("Region", coerce=int, validators=[DataRequired()])
    category = StringField("Category", validators=[DataRequired(), Length(max=100)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])


class ContinentForm(FlaskForm):
    name = StringField("Continent name", validators=[DataRequired(), Length(max=100)])


class CountryForm(FlaskForm):
    name = StringField("Country name", validators=[DataRequired(), Length(max=100)])
    continent = SelectField("Continent", coerce=int, validators=[DataRequired()])


class RegionForm(FlaskForm):
    name = StringField("Region name", validators=[DataRequired(), Length(max=100)])
    country = SelectField("Country", coerce=int, validators=[DataRequired()])


class SubRegionForm(FlaskForm):
    name = StringField("Subregion name", validators=[DataRequired(), Length(max=100)])
    region = SelectField("Region", coerce=int, validators=[DataRequired()])