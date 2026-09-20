from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField
from wtforms.validators import DataRequired, Email, InputRequired, Length

class AdminEditUser(FlaskForm):
    display_name = StringField('Display Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[Email(), Length(max=120)])
    alpca = StringField('ALPCA #', validators=[Length(max=100)])
    home_state = StringField('Home State', validators=[Length(max=100)])
    home_country = StringField('Home Country', validators=[Length(max=100)])
    permission_level = SelectField(
        'Permission Level',
        choices=[(0, 'Read-only'), (1, 'Submit'), (2, 'Moderator'), (3, 'Site Admin')],
        coerce=int,
        validators=[InputRequired()]
    )