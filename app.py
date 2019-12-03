from bson.objectid import ObjectId
from datetime import datetime
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, url_for, redirect, \
    make_response, jsonify, flash, session

# get environment variables
load_dotenv()

app = Flask(__name__)
# app.config['MONGO_DBNAME'] = 'travelPal'
app.config['MONGO_URI'] = os.getenv('MONGODB_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# initialise mongoDb
mongo = PyMongo(app)

# set collections variables
users = mongo.db.users
trips = mongo.db.trips
stops = mongo.db.stops


def checkUserPermission(checkLogin=True, checkTripOwner=False,
                        checkStopOwner=False, trip_id='', stop_id=''):
    # check to see if the user is logged in
    if not session.get('USERNAME'):
        return False

    # check that the variables needed to perform the db checks have been
    # passed through
    if checkTripOwner and trip_id == '':
        print('checkUserPermission(): Trip ID is required')
        return False

    if checkStopOwner and (trip_id == '' or stop_id == ''):
        print('checkUserPermission(): Trip ID and Stop ID are both required')
        return False

    # if checkTripOwner is True, OR, checkStopOwner is True - need to check
    # that User owns the Trip
    if checkTripOwner or checkStopOwner:
        query = {'_id': ObjectId(trip_id),
                 'owner_id': ObjectId(session.get('USERNAME'))}

        # check user is the user that owns this trip
        trip = trips.find_one(query)

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

    if checkStopOwner:
        query = {'_id': ObjectId(stop_id), 'trip_id': ObjectId(trip_id)}

        # check that the Stop is part of the Trip and by association the User
        # owns this Stop
        stop = stops.find_one(query)

        # does the stop belong to the trip?
        if not stop:
            # stop is not part of trip
            print('checkUserPermission(checkStopOwner): Stop does not belong'
                  ' to Trip - permission denied.')
            flash('The page you are trying to access does not exist or you do'
                  ' not have permission.')

            return False

    # User is Logged In
    # PASSTHROUGH VARIABLE DEPENDENT
    # User owns Trip
    # Stop belongs to Trip - and User owns Trip
    return True

#
# trips functionality
#
@app.route('/')
@app.route('/trips/')
@app.route('/trips/<show>/')
def show_trips(show='all'):

    if checkUserPermission():
        user_id = ObjectId(session.get('USERNAME'))
    else:
        user_id = ''

    if show == 'user':
        #  check if user logged in, if not redirect to all trips
        if not checkUserPermission():
            return redirect(url_for('show_trips'))

        # if user is logged in, show only their trips (i.e. route is
        # /trips/user)
        queryFilter = {
            "$match": {
                "$or":
                    [{"owner_id": user_id}]
            }
        }
    else:
        queryFilter = {
            "$match": {
                "$or":
                    [{"owner_id": user_id},
                     {"public": True}]
            }
        }
    # pass through the trips collection, using .find() to return all contents
    # of collection enabling iteration
    agg = [
        queryFilter,
        {"$lookup": {"from": "stops", "localField": "_id",
                     "foreignField": "trip_id", "as": "stops"}
         },
        {"$lookup": {"from": "users", "localField": "owner_id",
                     "foreignField": "_id", "as": "users"}
         },
        {
            "$unwind": {
                "path": "$stops",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "number_of_stops": {
                    "$sum": {
                        "$cond": {

                            "if": {"$gt": ["$stops.trip_id", "null"]},
                            "then": 1, "else": 0}
                    }
                },
                "duration": {"$sum": "$stops.duration"},
                "total_accommodation": {
                    "$sum": {
                        "$multiply": ["$stops.duration",
                                      "$stops.cost_accommodation"]
                    }
                },
                "total_food": {
                    "$sum": {
                        "$multiply": ["$stops.duration", "$stops.cost_food"]
                    }
                },
                "total_other": {
                    "$sum": {
                        "$multiply": ["$stops.duration", "$stops.cost_other"]
                    }
                },
                "start_date": {
                    "$min": "$start_date"
                },
                "end_date": {
                    "$max": "$end_date"
                },
                "country": {
                    "$first": "$stops.country"
                },
                "name": {
                    "$first": "$name"
                },
                "travelers": {
                    "$max": "$travelers"
                },
                "owner_id": {
                    "$first": "$owner_id"
                },
                "public": {
                    "$min": "$public"
                },
                "display_name": {
                    "$first": "$users.display_name"
                }
            }
        },
        {
            "$project": {
                "start_date": True,
                "end_date": True,
                "display_name": True,
                "name": True,
                "travelers": True,
                "public": True,
                "owner_id": True,
                "country": True,
                "number_of_stops": True,
                "duration": True,
                "total_accommodation": True,
                "total_food": True,
                "total_other": True,
                "total_cost": {"$multiply":
                               ["$travelers",
                                {"$add": ["$total_accommodation", "$total_food",
                                          "$total_other"]}]}
            }
        },
        {
            "$sort": {
                "start_date": 1,
                "end_date": 1
            }
        }
    ]

    getTrips = trips.aggregate(agg)

    return render_template('trips_show.html', trips=getTrips,
                           user_id=user_id, trips_showing=show)


@app.route('/trip/new/', methods=['POST', 'GET'])
def trip_new():
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('show_trips'))

    if request.method == 'POST':
        # create functionality to process form
        # then add to db
        # then redirect back to all trips

        try:
            name = str(request.form.get('trip-name'))
            travelers = int(request.form.get('travelers'))
            # convert form date strings to datetime
            startdate = datetime.strptime(
                request.form.get('start-date'), '%d %b %Y')
            enddate = datetime.strptime(
                request.form.get('end-date'), '%d %b %Y')

            # convert checkbox 'on' or 'off' to boolean value for storing
            public = True if request.form.get('public') == 'on' else False

            # create new entry if validation is successful
            newTrip = {
                'name': name,
                'travelers': travelers,
                'start_date': startdate,
                'end_date': enddate,
                'owner_id': ObjectId(session.get('USERNAME')),
                'public': public
            }

            trip = trips.insert_one(newTrip)

            flash('New trip has been created - you can add stops below')

            return redirect(url_for('trip_detailed', trip_id=trip.inserted_id))
        except Exception as e:
            print(e)
            return 'Input error'
    else:
        return render_template('trip_add_edit.html', action='new')


@app.route('/trip/<trip_id>/update/', methods=['POST', 'GET'])
def trip_update(trip_id):
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('show_trips'))

    # check that the user has permission to update this trip
    trip = checkUserPermission(
        checkLogin=True, checkTripOwner=True, trip_id=trip_id)

    if trip:
        if request.method == 'POST':
            # when the form has been clicked
            # need validation (all fields proper, id exists, id is owned by user)
            # then iterate through field values and update in db
            # then redirect back to all trips
            try:
                name = str(request.form.get('trip-name'))
                travelers = int(request.form.get('travelers'))

                # convert form date strings to datetime
                startdate = datetime.strptime(
                    request.form.get('start-date'), '%d %b %Y')
                enddate = datetime.strptime(
                    request.form.get('end-date'), '%d %b %Y')
                # convert checkbox 'on' or 'off' to boolean value for storing
                public = True if request.form.get('public') == 'on' else False

                # create new entry if validation is successful
                updateCriteria = {
                    '_id': ObjectId(trip_id)
                }
                updateQuery = {
                    '$set': {
                        'name': name,
                        'travelers': travelers,
                        'start_date': startdate,
                        'end_date': enddate,
                        'public': public
                    }
                }

                trips.update_one(updateCriteria, updateQuery)

                flash('Your trip has been updated')
                return redirect(url_for('trip_detailed', trip_id=trip_id))
            except Exception as e:
                print(e)
                return 'Input error'
        else:
            # create functionality to pull trip information from db
            # then populate this data into the form
            trip_query = {'_id': ObjectId(trip_id)}

            return render_template('trip_add_edit.html', action='update',
                                   trip=trips.find_one(trip_query))

    else:
        # user does not own this trip, redirect to all trips
        return redirect(url_for('show_trips'))


@app.route('/trip/<trip_id>/delete/')
def trip_delete(trip_id):
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('show_trips'))

    # check that the user has permission to update this trip
    trip = checkUserPermission(
        checkLogin=True, checkTripOwner=True, trip_id=trip_id)

    if trip:
        # add query to delete all stops associated with this trip then delete
        # the trip

        # if user owns this entry then delete
        tripQuery = {"_id": ObjectId(trip_id)}
        stopsQuery = {"trip_id": ObjectId(trip_id)}

        flash(
            f'The trip and all associated stops have now been '
            'deleted')
        trips.delete_one(tripQuery)
        stops.delete_many(stopsQuery)

    else:
        flash(
            f'The trip you are trying to access does not exist or you do not '
            'have permission to perform this action.')

    return redirect(url_for('show_trips', show='user'))


@app.route('/trip/<trip_id>/detailed/')
def trip_detailed(trip_id):
    # check if the trip is public or private
    # if private, check that the user owns the trip - if not redirect back
    # if public, or the user owns this trip, then show the detail
    # need to query trips and stops
    # iterate through all stops
    trip_query = {'_id': ObjectId(trip_id)}
    stop_query = {'trip_id': ObjectId(trip_id)}

    return render_template('trip_detailed.html',
                           trip=trips.find_one(trip_query),
                           stops=stops.find(stop_query))

#
# stops functionality
#
@app.route('/trip/<trip_id>/stop/new/', methods=['POST', 'GET'])
def trip_stop_new(trip_id):
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('trip_detailed', trip_id=trip_id))

    # check that the user has permission to add a new stop to this trip
    trip = checkUserPermission(
        checkLogin=True, checkTripOwner=True, trip_id=trip_id)

    if trip:
        # validate that user has permission to add a new stop to this
        # (i.e. owner_id=user_id)
        # if not redirect back to trip detailed page
        if request.method == 'POST':
            try:
                # strings
                country = str(request.form.get('country'))
                city = str(request.form.get('city'))
                currency = str(request.form.get('currency'))

                # numbers
                duration = int(request.form.get('duration'))
                cost_accommodation = float(
                    request.form.get('cost-accommodation'))
                cost_food = float(request.form.get('cost-food'))
                cost_other = float(request.form.get('cost-other'))

                # create new entry if validation is successful
                newStop = {
                    'trip_id': ObjectId(trip_id),
                    'country': country,
                    'city/town': city,
                    'duration': duration,
                    'order': 1,
                    'currency': currency,
                    'cost_accommodation': cost_accommodation,
                    'cost_food': cost_food,
                    'cost_other': cost_other
                }
                stops.insert_one(newStop)

                flash('You have added a new stop to this trip')
                return redirect(url_for('trip_detailed', trip_id=trip_id))
            except Exception as e:
                print(e)
                return 'Input error'
        else:
            # need to pass through trip information from database
            tripQuery = trips.find_one({'_id': ObjectId(trip_id)})
            return render_template('stop_add_edit.html', trip=tripQuery, action='new')
    else:
        # if no trip_id or user not logged in then redirect to show all trips
        return redirect(url_for('show_trips'))


@app.route('/trip/<trip_id>/stop/<stop_id>/duplicate/',
           methods=['POST', 'GET'])
def trip_stop_duplicate(trip_id, stop_id):
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('trip_detailed', trip_id=trip_id))

    # check that the user has permission to add a new stop to this trip
    stop = checkUserPermission(checkLogin=True, checkStopOwner=True,
                               trip_id=trip_id, stop_id=stop_id)

    if stop:
        copyOfStop = stops.find_one({'_id': ObjectId(stop_id),
                                     'trip_id': ObjectId(trip_id)}, {'_id': 0})

        newStop = stops.insert_one(copyOfStop)
        flash('Stop added - you can modify the details below')
        return redirect(url_for('trip_stop_update', trip_id=trip_id, stop_id=newStop.inserted_id))
    else:
        flash(
            'The stop you are trying to access does not exist or you do '
            'not have permission to perform the action')

        return redirect(url_for('trip_detailed', trip_id=trip_id))


@app.route('/trip/<trip_id>/stop/<stop_id>/update/', methods=['POST', 'GET'])
def trip_stop_update(trip_id, stop_id):
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('trip_detailed', trip_id=trip_id))

    stop = checkUserPermission(checkLogin=True, checkStopOwner=True,
                               trip_id=trip_id, stop_id=stop_id)

    if stop:
        if request.method == 'POST':
            # when the form has been clicked
            # need validation (all fields proper, id exists, id is owned by user)
            # then iterate through field values and update in db
            # then redirect back to all trips
            try:
                # strings
                country = str(request.form.get('country'))
                city = str(request.form.get('city'))
                currency = str(request.form.get('currency'))

                # numbers
                duration = int(request.form.get('duration'))
                cost_accommodation = float(
                    request.form.get('cost-accommodation'))
                cost_food = float(request.form.get('cost-food'))
                cost_other = float(request.form.get('cost-other'))

                # create new entry if validation is successful
                updateCriteria = {
                    '_id': ObjectId(stop_id)
                }
                # build update query
                updateQuery = {
                    '$set': {
                        'trip_id': ObjectId(trip_id),
                        'country': country,
                        'city/town': city,
                        'duration': duration,
                        'order': 1,
                        'currency': currency,
                        'cost_accommodation': cost_accommodation,
                        'cost_food': cost_food,
                        'cost_other': cost_other
                    }
                }

                # process query
                stops.update_one(updateCriteria, updateQuery)

                flash('Your trip has been updated')
                return redirect(url_for('trip_detailed', trip_id=trip_id))
            except Exception as e:
                print(e)
                return 'Input error'
        else:
            # create functionality to pull trip information from db
            # then populate this data into the form
            trip = trips.find_one({'_id': ObjectId(trip_id)})
            stop = stops.find_one({'_id': ObjectId(stop_id)})

            return render_template('stop_add_edit.html', trip=trip,
                                   stop=stop, action='update')
    else:
        flash(
            'The stop you are trying to access does not exist or you do '
            'not have permission to perform the action')

        return redirect(url_for('trip_detailed', trip_id=trip_id))


@app.route('/trip/<trip_id>/stop/<stop_id>/delete/')
def trip_stop_delete(trip_id, stop_id):
    stop = checkUserPermission(checkLogin=True, checkStopOwner=True,
                               trip_id=trip_id, stop_id=stop_id)

    if stop:
        query = {"_id": ObjectId(stop_id), "trip_id": ObjectId(trip_id)}
        # check that stop exists
        if stops.find_one(query):
            # if user owns this entry then delete
            stops.delete_one(query)
            flash('The stop has been removed from this trip')
        else:
            flash('The stop you are trying to delete does not exist')
    else:
        flash(
            'The stop you are trying to access does not exist or you do '
            'not have permission to perform the action')

    return redirect(url_for('trip_detailed', trip_id=trip_id))

#
# user functionality
#

# register
@app.route('/user/register/', methods=['POST', 'GET'])
def user_new():
    if checkUserPermission(checkLogin=True):
        # if the user is already logged in then redirect them
        return redirect(url_for('show_trips'))

    if request.method == 'POST':
        # create functionality to process form
        # then add to db
        # then redirect back to all trips

        try:
            formUsername = request.form.get('username')

            user = users.find_one({"username": formUsername})

            # check to see if username already exists
            if user:
                flash(
                    'Error: this user already exists, please select a different username')
                return redirect(url_for('user_new'))
            else:

                # create new entry if validation is successful
                newUser = {
                    'username': request.form.get('username'),
                    'name': request.form.get('name'),
                    'display_name': request.form.get('display-name'),
                    'email': request.form.get('email'),
                    'password': ''
                }
                users.insert_one(newUser)

                flash('A new account has been successfully created - you can '
                      'now login')
                return redirect(url_for('show_trips'))
        except Exception as e:
            print(e)
            return 'Input error'
    else:
        return render_template('user_register.html')

# login
@app.route('/user/login/', methods=['POST', 'GET'])
def user_login():
    if checkUserPermission():
        # if user already logged in then redirect away from login page
        return redirect(url_for('show_trips'))

    if request.method == 'POST':
        # check that the username exists in the database
        user = users.find_one(
            {"username": request.form.get('username')})

        if user:
            flash('You are now logged in to your account')
            # save mongodb user _id as session to indicate logged in
            # convert ObjectId to string
            session['USERNAME'] = str(user['_id'])
            session['DISPLAY_NAME'] = str(user['display_name'])

            # return user to 'My Trips' page
            return redirect(url_for('show_trips', show='user'))
        else:
            flash('No user exists with this username - please try again')
            return redirect(url_for('user_login'))
    else:
        return render_template('user_login.html')


# logout
@app.route('/user/logout/')
def user_logout():
    if not checkUserPermission():
        # user is not logged in
        return redirect(url_for('show_trips'))

    # delete session variable
    session.pop('USERNAME', None)
    flash('You have been logged out')
    return redirect(url_for('show_trips'))


# profile
@app.route('/user/profile/')
def user_profile():
    if not checkUserPermission():
        # user is not logged in
        return redirect(url_for('show_trips'))

    return render_template('placeholder.html', run_function='Profile')


if __name__ == '__main__':
    app.run(host=os.getenv('IP'),
            port=int(os.getenv('PORT')),
            debug=os.getenv('DEBUG'))
