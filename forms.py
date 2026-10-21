from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, DateField
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

class AddLocationForm(FlaskForm):
    name = StringField('Location Name', validators=[DataRequired(), Length(max=100)])
    parent_id = SelectField(
        'Parent Location',
        coerce=lambda value: int(value) if value else None,
        validators=[Optional()],
    )
    code = StringField('ISO 3166-2 Code', validators=[Optional(), Length(max=10)])
    level = SelectField(
        'Location Level',
        choices=[(1, 'Continent'), (2, 'Country'), (3, 'Region')],
        coerce=int,
        validators=[InputRequired()]
    );


class PlateSubmissionForm(FlaskForm):
    plate = StringField('Serial *', validators=[DataRequired(), Length(max=20)])
    date = DateField('Date *', validators=[DataRequired()], default=date.today)
    county = StringField('County', validators=[Length(max=100), Optional()])
    type = StringField('Specialty', validators=[Length(max=100), Optional()]) # specialty type
    location = StringField('Location', validators=[Length(max=100), Optional()])
    notes = StringField('Notes', validators=[Length(max=500), Optional()])
    expiration_date = DateField('Expiration Date', validators=[Optional()])