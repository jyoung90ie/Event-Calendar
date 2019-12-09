from datetime import datetime, timedelta
from wtforms.validators import DataRequired, NumberRange, Email, Length, \
    ValidationError, InputRequired
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, \
    IntegerField, DateTimeField, DecimalField, FloatField, HiddenField

# import db connection and collection variables
from db import trips, users, stops

# Custom validation functions


def user_exists(for_login=False):
    '''
    Checks to see if a username exists in the database.

    By default the check is used for ensuring no duplicate usernames when
    registering. This is also used for checking that a username exists
    when logging in.
    '''
    def _user_exists(form, field):
        username = users.find_one({"username": field.data})

        if for_login:
            if not username:
                message = ('This user does not exist - please check your '
                           'username and try again.')
                raise ValidationError(message)
        else:
            if username:
                message = ('This username is already in use, please try '
                           'another.')
                raise ValidationError(message)

    return _user_exists


def check_dates(start_date_field):
    '''
    Checks that the field this validator is attached to is
    greater than the Start Date field supplied.
    '''
    message = 'End Date must take place after the Start Date.'

    def _check_dates(form, field):

        if field.data <= form[start_date_field].data:
            raise ValidationError(message)

    return _check_dates


def check_duration():
    '''
    Simple validation to ensure that the duration of a single stop does
    not exceed the total length of the trip (end date - start date)
    '''
    message = 'Duration cannot be longer than the time period of the trip'

    def _check_duration(form, field):
        trip_duration = (form.trip_end_date.data -
                         form.trip_start_date.data)

        if type(field.data) == int:
            if field.data > trip_duration.days:
                raise ValidationError(message)

    return _check_duration


# Form setup
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
                           DataRequired(), Length(min=3, max=32),
                           user_exists()])
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2)])
    display_name = StringField('Display Name', validators=[
                               DataRequired(), Length(min=2, max=32)])
    email = StringField('Email', validators=[DataRequired(), Email()])


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
                           DataRequired(), user_exists(for_login=True)])


class TripForm(FlaskForm):
    default_start = datetime.now()
    default_end = default_start + timedelta(days=1)

    name = StringField('Name', validators=[DataRequired()])
    travelers = IntegerField('Number of Travelers', default=1,
                             validators=[InputRequired(), NumberRange(min=1)])
    start_date = DateTimeField('Start Date', default=default_start, validators=[
        InputRequired()], format='%d %b %Y')
    public = BooleanField('Display Trip to Public?', default='checked')


class StopForm(FlaskForm):
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
