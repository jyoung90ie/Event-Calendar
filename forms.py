""" This sets out the structure and validation for each input form used """
from datetime import datetime, timedelta
from wtforms import StringField, BooleanField, \
    IntegerField, DateTimeField, DecimalField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Email, Length, \
    InputRequired
from flask_wtf import FlaskForm
# import custom validator
from util import user_exists


# Form setup
class RegistrationForm(FlaskForm):
    """ Fields and validation for User Registration """
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=3, max=32),
                                       user_exists()])
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2)])
    display_name = StringField('Display Name',
                               validators=[DataRequired(),
                                           Length(min=2, max=32)])
    email = StringField('Email', validators=[DataRequired(), Email()])


class LoginForm(FlaskForm):
    """ Fields and validation for User Login """
    username = StringField('Username',
                           validators=[DataRequired(),
                                       user_exists(for_login=True)])


class TripForm(FlaskForm):
    """ Fields and validation for Adding and Updating a Trip """
    default_start = datetime.now()
    default_end = default_start + timedelta(days=1)

    name = StringField('Name', validators=[DataRequired()])
    travelers = IntegerField('Number of Travelers', default=1,
                             validators=[InputRequired(), NumberRange(min=1)])
    start_date = DateTimeField('Start Date', default=default_start, validators=[
        InputRequired()], format='%d %b %Y')
    public = BooleanField('Display Trip to Public?', default='checked')


class StopForm(FlaskForm):
    """ Fields and validation for Adding and Updating a Stop """
    trip_name = StringField('Trip Name')
    total_trip_duration = HiddenField('Total Trip Duration')
    current_stop_duration = HiddenField('Current Stop Duration')
    trip_start_date = DateTimeField('Trip Start Date', format='%d %b %Y')
    proj_end_date = DateTimeField('Projected Trip End Date', format='%d %b %Y')
    country = StringField('Country', validators=[DataRequired()])
    city_town = StringField('City/Town', validators=[DataRequired()])
    currency = StringField('Currency',
                           validators=[DataRequired(),
                                       Length(min=3, max=3,
                                              message=('Currency must be 3 '
                                                       'characters long.'))])
    duration = IntegerField('Duration',
                            validators=[InputRequired(), NumberRange(min=1)])
    cost_accommodation = DecimalField('Accommodation (Cost)', places=2,
                                      validators=[InputRequired(),
                                                  NumberRange(min=0)])
    cost_food = DecimalField('Food (Cost)', places=2, validators=[
        InputRequired(), NumberRange(min=0)])
    cost_other = DecimalField('Other (Cost)', places=2, validators=[
        InputRequired(), NumberRange(min=0)])
