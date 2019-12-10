''' This creates a connection to MongoDB and creates collection variables '''
import os
from bson.objectid import ObjectId
from flask import Flask, flash, session
from flask_pymongo import PyMongo
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
    '''
    This checks if a user has been logged in by default. Additional checks
    are included to determine if a user is the owner of a trip and thus
    should have permission to add, update, and/or, remove trip details/stops.
    '''
    if not session.get('USERNAME'):
        return False

    # check that the variables needed to perform the db checks have been
    # passed through
    if check_trip_owner and trip_id == '':
        print('checkUserPermission(): Trip ID is required')
        return False

    if check_stop_owner and (trip_id == '' or stop_id == ''):
        print('checkUserPermission(): Trip ID and Stop ID are both required')
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
            print(
                'checkUserPermission(checkTripOwner): User does not own this'
                ' Trip - permission denied.')
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
            print('checkUserPermission(checkStopOwner): Stop does not belong'
                  ' to Trip - permission denied.')
            flash('The page you are trying to access does not exist or you do'
                  ' not have permission.')

            return False

    # User is Logged In
    return True


def get_trip_duration(trip_id):
    '''
    Creates an aggregate MongoDB query which returns the total duration
    for all stops for a given trip_id.
    '''
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
    except Exception as ex:
        # if query throws exception set total_duration to zero
        print(ex)
        total_duration = 0

    return total_duration
