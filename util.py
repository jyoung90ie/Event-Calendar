""" This creates a connection to MongoDB and creates collection variables """
import os
from bson.objectid import ObjectId
from flask import Flask, flash, session
from flask_pymongo import PyMongo
from wtforms.validators import ValidationError
from dotenv import load_dotenv


# get environment variables
load_dotenv()

APP = Flask(__name__)
APP.config['MONGO_URI'] = os.getenv('MONGODB_URI')
APP.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# initialise mongoDb
MONGO = PyMongo(APP)

# set collections variables
USERS = MONGO.db.users
TRIPS = MONGO.db.trips
STOPS = MONGO.db.stops


def check_user_permission(check_trip_owner=False,
                          check_stop_owner=False, trip_id='', stop_id=''):
    """
    This checks if a user has been logged in by default. Additional checks
    are included to determine if a user is the owner of a trip and thus
    should have permission to add, update, and/or, remove trip details/stops.
    """
    if not session.get('USERNAME'):
        return False

    # check that the variables needed to perform the db checks have been
    # passed through
    if check_trip_owner and trip_id == '':
        return False

    if check_stop_owner and (trip_id == '' or stop_id == ''):
        return False

    # if checkTripOwner is True, OR, checkStopOwner is True - need to check
    # that User owns the Trip
    if check_trip_owner or check_stop_owner:
        query = {'_id': ObjectId(trip_id),
                 'owner_id': ObjectId(session.get('USERNAME'))}

        # check user is the user that owns this trip
        trip = TRIPS.find_one(query)

        # check if any results were returned by the query - i.e. does this user
        # own this trip?
        if not trip:
            # user does not own the trip
            flash(
                'The page you are trying to access does not exist or you do'
                ' not have permission.')
            return False

    if check_stop_owner:
        query = {'_id': ObjectId(stop_id), 'trip_id': ObjectId(trip_id)}

        # check that the Stop is part of the Trip and by association the User
        # owns this Stop
        stop = STOPS.find_one(query)

        # does the stop belong to the trip?
        if not stop:
            # stop is not part of trip
            flash('The page you are trying to access does not exist or you do'
                  ' not have permission.')

            return False

    # User is Logged In
    return True


def get_trip_duration(trip_id):
    """
    Creates an aggregate MongoDB query which returns the total duration
    for all stops for a given trip_id.
    """
    pipeline = [
        {
            u"$match": {
                u"trip_id": ObjectId(trip_id)
            }
        },
        {
            u"$group": {
                u"_id": u"$trip_id",
                u"total_duration": {
                    u"$sum": u"$duration"
                }
            }
        },
        {
            u"$project": {
                u"total_duration": 1
            }
        }
    ]

    try:
        # set total trip duration if query is successful
        get_total_duration = STOPS.aggregate(pipeline)
        total_duration = get_total_duration.next()['total_duration']
    except:
        # if query throws exception set total_duration to zero
        total_duration = 0

    return total_duration

# Custom validation for use in forms
def user_exists(for_login=False):
    """
    Checks to see if a username exists in the database.

    By default the check is used for ensuring no duplicate usernames when
    registering. This is also used for checking that a username exists
    when logging in.
    """
    def _user_exists(form, field):
        username = USERS.find_one({"username": field.data.strip().lower()})

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
    """
    Checks that the field this validator is attached to is
    greater than the Start Date field supplied.
    """
    message = 'End Date must take place after the Start Date.'

    def _check_dates(form, field):

        if field.data <= form[start_date_field].data:
            raise ValidationError(message)

    return _check_dates


def check_duration():
    """
    Simple validation to ensure that the duration of a single stop does
    not exceed the total length of the trip (end date - start date)
    """
    message = 'Duration cannot be longer than the time period of the trip'

    def _check_duration(form, field):
        trip_duration = (form.trip_end_date.data -
                         form.trip_start_date.data)

        if isinstance(field.data, int):
            if field.data > trip_duration.days:
                raise ValidationError(message)

    return _check_duration
