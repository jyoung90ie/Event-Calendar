from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
from flask import Flask, render_template, request, url_for, redirect, \
    make_response, jsonify, flash, session
# user created files
from db import app, trips, users, stops
from forms import RegistrationForm, TripForm, StopForm, LoginForm


def checkUserPermission(checkLogin=True, checkTripOwner=False,
                        checkStopOwner=False, trip_id='', stop_id=''):
    '''
    This checks if a user has been logged in by default. Additional checks
    are included to determine if a user is the owner of a trip and thus
    should have permission to add, update, and/or, remove trip details/stops.
    '''
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
    '''
    Shows a filtered list of trips from the DB - those marked as public and
    those the user owners (if logged in, otherwise just public trips displayed)
    '''

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
    ''' This creates a new user in the database. '''
    # if the user is already logged in then redirect them
    if not checkUserPermission(checkLogin=True):
        flash('Please login if you wish to perform this action')
        return redirect(url_for('show_trips'))

    form = TripForm()
    # check input validation
    if form.validate_on_submit():
        # create new entry if validation is successful
        try:
            newTrip = {
                'name': form.name.data,
                'travelers': form.travelers.data,
                'start_date': form.start_date.data,
                'end_date': form.end_date.data,
                'public': form.public.data,
                'owner_id': ObjectId(session.get('USERNAME'))
            }
            trip = trips.insert_one(newTrip)
            flash('New trip has been created - you can add stops below')

            return redirect(url_for('trip_detailed',
                                    trip_id=trip.inserted_id))
        except Exception as e:
            print(e)
            flash('Database insertion error - please try again')

        # if form did not successful validate or there was an exception
        # error then redirect back to front page
        return redirect(url_for('trip_new'))
    else:
        return render_template('trip_add_edit.html', form=form, action='new')


@app.route('/trip/<trip_id>/update/', methods=['POST', 'GET'])
def trip_update(trip_id):
    '''
    Subject to user permissions, this will display an input form with
    values retrieved from the database to facilitate update.
    '''
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('show_trips'))

    # check that the user has permission to update this trip
    trip = checkUserPermission(
        checkLogin=True, checkTripOwner=True, trip_id=trip_id)

    if trip:
        form = TripForm()
        # check input validation
        if form.validate_on_submit():
            # create new entry if validation is successful
            try:
                updateCriteria = {
                    '_id': ObjectId(trip_id)
                }
                updateQuery = {
                    '$set': {
                        'name': form.name.data,
                        'travelers': form.travelers.data,
                        'start_date': form.start_date.data,
                        'end_date': form.end_date.data,
                        'public': form.public.data
                    }
                }

                trips.update_one(updateCriteria, updateQuery)

                flash('Your trip has been updated')
                return redirect(url_for('trip_detailed', trip_id=trip_id))
            except Exception as e:
                print(e)
                flash('Database insertion error - please try again')

            # if form did not successful validate or there was an exception
            # error then redirect back to front page
            return redirect(url_for('trip_new'))
        else:
            trip_query = trips.find_one({'_id': ObjectId(trip_id)})

            if trip_query:
                for field in trip_query:
                    # populate the form with values from trip_query
                    if field in form:
                        # limit to only those fields which are in the form and
                        # in the database
                        form[field].data = trip_query[field]

                return render_template('trip_add_edit.html', form=form,
                                       action='update', trip=trip_query)
            else:
                flash('The trip you tried to access does not exist')
                return redirect(url_for('show_trips'))
    else:
        # user does not own this trip, redirect to all trips
        return redirect(url_for('show_trips'))


@app.route('/trip/<trip_id>/delete/')
def trip_delete(trip_id):
    '''
    Subject to user permissions, this will delete a trip and all
    linked (via trip_id) stops.
    '''
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
    '''
    This will display all trip information, including stops. If the user
    owns this trip they will also be prompted with buttons to add, update,
    and delete various attributes.
    '''
    # check if the trip is public or private
    # if private, check that the user owns the trip - if not redirect back
    # if public, or the user owns this trip, then show the detail
    # need to query trips and stops
    # iterate through all stops
    # trip_query = {'_id': ObjectId(trip_id)}
    # stop_query = {'trip_id': ObjectId(trip_id)}

    trip_pipeline = [
        {
            '$match': {
                'trip_id': ObjectId(trip_id)
            }
        },
        {
            '$group': {
                '_id': {
                    'trip_id': '$trip_id',
                    'country': '$country'
                },
                'stats': {
                    '$push': {
                        'total_cost_pp': {
                            '$multiply':
                                ['$duration',
                                 {'$add':
                                  ['$cost_accommodation',
                                      '$cost_food', '$cost_other']
                                  }]
                        },
                        # cost per night per person
                        'total_cost_pp_pn': {
                                '$add': ['$cost_accommodation', '$cost_food', '$cost_other']
                        },
                        'total_accom_pp': {
                            '$multiply': ['$duration', '$cost_accommodation']
                        },
                        'total_food_pp': {
                            '$multiply': ['$duration', '$cost_food']
                        },
                        'total_other_pp': {
                            '$multiply': ['$duration', '$cost_other']
                        },
                    }
                },
                'total_stops': {'$sum': 1},
                'total_duration': {'$sum': '$duration'}
            }
        },
        {
            '$group': {
                '_id': '$_id.trip_id',
                'total_countries': {'$sum': 1},
                'total_stops': {'$sum': '$total_stops'},
                'total_duration': {'$sum': '$total_duration'},
                'stats': {'$push': '$stats'}
            }
        },
        {
            '$unwind': {
                'path': '$stats'
            }
        },
        {
            '$unwind': {
                'path': '$stats'
            }
        },
        {
            '$group': {
                '_id': '$_id',
                'total_countries': {'$max': '$total_countries'},
                'total_stops': {'$max': '$total_stops'},
                'total_duration': {'$max': '$total_duration'},
                'total_cost_pp': {'$sum': '$stats.total_cost_pp'},
                'total_cost_pp_pn': {'$sum': '$stats.total_cost_pp_pn'},
                'total_accom_pp': {'$sum': '$stats.total_accom_pp'},
                'total_food_pp': {'$sum': '$stats.total_food_pp'},
                'total_other_pp': {'$sum': '$stats.total_other_pp'}
            }
        },
        {
            '$lookup':
            {
                'from': 'trips',
                'let': {'trip_id': '$_id'},  # this becomes $$trip_id
                'pipeline': [{
                    '$match': {
                        '$expr': {
                            '$eq': ['$$trip_id', '$_id']
                        }
                    }
                }],
                'as': 'trips'
            }
        },
        {
            '$unwind': {
                'path': '$trips'
            }
        },
        {
            '$project': {
                '_id': 1,
                'name': '$trips.name',
                'start_date': '$trips.start_date',
                'end_date': '$trips.end_date',
                'owner_id': '$trips.owner_id',
                'public': '$trips.public',
                'travelers': '$trips.travelers',
                'owner_id': '$trips.owner_id',
                'total_duration': '$total_duration',
                'total_stops': '$total_stops',
                'total_countries': '$total_countries',
                'total_cost': {
                    '$multiply': ['$trips.travelers', '$total_cost_pp']
                },
                'total_cost_pp': '$total_cost_pp',
                'total_accom_pp': '$total_accom_pp',
                'total_food_pp': '$total_food_pp',
                'total_other_pp': '$total_other_pp',
                'avg_cost_pn': {
                    '$divide': [{'$multiply': ['$trips.travelers', '$total_cost_pp']}, '$total_duration']
                },
                'total_accom': {
                    '$multiply': ['$trips.travelers', '$total_accom_pp']
                },
                'total_food': {
                    '$multiply': ['$trips.travelers', '$total_food_pp']
                },
                'total_other': {
                    '$multiply': ['$trips.travelers', '$total_other_pp']
                },
            }
        }
    ]

    # aggregrate returns a cursor - need to convert to list to access
    # query will only return 1 result, which is stored at index 0 hence [0]
    trip_detail = list(stops.aggregate(trip_pipeline))[0]

    # create array to contain all stops detail - produced via aggregate
    # then loop through cursor, creating new array which is passed to the
    # template

    stop_pipeline = [
        {
            u"$match": {
                u"_id": ObjectId(trip_id)
            }
        },
        {
            u"$lookup": {
                u"from": u"stops",
                u"localField": u"_id",
                u"foreignField": u"trip_id",
                u"as": u"stops"
            }
        },
        {
            u"$unwind": {
                u"path": u"$stops",
                u"includeArrayIndex": u"arrayIndex",
                u"preserveNullAndEmptyArrays": False
            }
        },
        {
            u"$addFields": {
                u"stops.start_date": {
                    u"$ifNull": [
                        u"${stops.end_date}",
                        u"$start_date"
                    ]
                },
                u"stops.end_date": {
                    u"$add": [
                        u"$start_date",
                        {
                            u"$multiply": [
                                u"$stops.duration",
                                24.0,
                                3600.0,
                                1000.0
                            ]
                        }
                    ]
                }
            }
        }
    ]

    cursor = trips.aggregate(stop_pipeline)

    last_trip_id = ''
    # last_trip_start_date = ''
    # last_stop_start_date = ''
    # last_stop_end_date = ''
    # stop_total_accom = 0
    # stop_total_food = 0
    # stop_total_other = 0
    # stop_total_accom_pp = 0
    # stop_total_food_pp = 0
    # stop_total_other_pp = 0

    stops_arr = []

    for doc in cursor:
        stop_duration = doc['stops']['duration']
        trip_travelers = doc['travelers']

        # costs per person for the stop
        stop_total_accom_pp = stop_duration * \
            doc['stops']['cost_accommodation']
        stop_total_food_pp = stop_duration * doc['stops']['cost_food']
        stop_total_other_pp = stop_duration * doc['stops']['cost_other']

        # total cost for stop
        stop_total_accom = trip_travelers * stop_total_accom_pp
        stop_total_food = trip_travelers * stop_total_food_pp
        stop_total_other = trip_travelers * stop_total_other_pp

        if last_trip_id == doc['_id']:
            # same trip, different stop - continue
            last_stop_start_date = last_stop_end_date
            last_stop_end_date = last_stop_start_date + \
                timedelta(days=stop_duration)

        else:
            # new trip, new stop - reset
            last_trip_start_date = doc['start_date']
            last_stop_start_date = last_trip_start_date
            last_stop_end_date = last_trip_start_date + \
                timedelta(days=stop_duration)

        last_trip_id = doc['_id']

        data = {
            'trip_id': last_trip_id,
            'stop_id': doc['stops']['_id'],
            'duration': stop_duration,
            'travelers': trip_travelers,
            'country': doc['stops']['country'],
            'city_town': doc['stops']['city_town'],
            'currency': doc['stops']['currency'],

            'stop_start_date': last_stop_start_date,
            'stop_end_date': last_stop_end_date,

            'stop_total_accom_pp': stop_total_accom_pp,
            'stop_total_food_pp': stop_total_food_pp,
            'stop_total_other_pp': stop_total_other_pp,

            'stop_total_accom': stop_total_accom,
            'stop_total_food': stop_total_food,
            'stop_total_other': stop_total_other
        }

        stops_arr.append(data)

    # stop_detail = stops.find({'trip_id': ObjectId(trip_id)})

    return render_template('trip_detailed.html', trip=trip_detail,
                           stops=stops_arr)
    # return render_template('trip_detailed.html',
    #                        trip=trips.find_one(trip_query),
    #                        stops=stops.find(stop_query))

#
# stops functionality
#
@app.route('/trip/<trip_id>/stop/new/', methods=['POST', 'GET'])
def trip_stop_new(trip_id):
    '''
    Subject to user permissions, this enables a user to add new stops
    to their trip.
    '''
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('trip_detailed', trip_id=trip_id))

    # check that the user has permission to add a new stop to this trip
    trip = checkUserPermission(
        checkLogin=True, checkTripOwner=True, trip_id=trip_id)

    if trip:

        form = StopForm()

        if form.validate_on_submit():
            # create new entry if validation is successful
            try:
                newStop = {
                    'trip_id': ObjectId(trip_id),
                    'country': form.country.data,
                    'city_town': form.city_town.data,
                    'duration': form.duration.data,
                    'order': 1,
                    'currency': form.currency.data,
                    'cost_accommodation': float(form.cost_accommodation.data),
                    'cost_food': float(form.cost_food.data),
                    'cost_other': float(form.cost_other.data)
                }
                stops.insert_one(newStop)
                flash('You have added a new stop to this trip')

            except Exception as e:
                print(e)
                flash('Database insertion error - please try again')

            # if form did not successful validate or there was an exception
            # error then redirect back to front page
            return redirect(url_for('trip_detailed', trip_id=trip_id))
        else:
            trip_query = trips.find_one({'_id': ObjectId(trip_id)})
            prefix = 'trip_'  # used to identify trip form fields
            if trip_query:
                for field in trip_query:
                    # populate the form with values from trip_query
                    if (prefix + field) in form:
                        # limit to only those fields which are in the form and
                        # in the database
                        form[(prefix + field)].data = trip_query[field]

            return render_template('stop_add_edit.html', form=form,
                                   action='new', trip=trip_query)
    else:
        # if no trip_id or user not logged in then redirect to show all trips
        return redirect(url_for('show_trips'))


@app.route('/trip/<trip_id>/stop/<stop_id>/duplicate/',
           methods=['POST', 'GET'])
def trip_stop_duplicate(trip_id, stop_id):
    '''
    Duplicates a trip 'stop' for the user, to save time from filling in repeat
    fields, such as country, city, etc.
    '''
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
        return redirect(url_for('trip_stop_update', trip_id=trip_id,
                                stop_id=newStop.inserted_id))
    else:
        flash(
            'The stop you are trying to access does not exist or you do '
            'not have permission to perform the action')

        return redirect(url_for('trip_detailed', trip_id=trip_id))


@app.route('/trip/<trip_id>/stop/<stop_id>/update/', methods=['POST', 'GET'])
def trip_stop_update(trip_id, stop_id):
    '''
    Subject to user permissions, this will enable a permitted user to update a
    stop within a trip they own.
    '''
    if not checkUserPermission():
        flash('Please login if you wish to perform this action')
        return redirect(url_for('trip_detailed', trip_id=trip_id))

    stop = checkUserPermission(checkLogin=True, checkStopOwner=True,
                               trip_id=trip_id, stop_id=stop_id)

    if stop:
        form = StopForm()
        # check input validation
        if form.validate_on_submit():
            # create new entry if validation is successful
            try:
                updateCriteria = {
                    '_id': ObjectId(stop_id)
                }
                # build update query
                updateQuery = {
                    '$set': {
                        'trip_id': ObjectId(trip_id),
                        'country': form.country.data,
                        'city_town': form.city_town.data,
                        'duration': form.duration.data,
                        'order': 1,
                        'currency': form.currency.data,
                        'cost_accommodation':
                            float(form.cost_accommodation.data),
                        'cost_food': float(form.cost_food.data),
                        'cost_other': float(form.cost_other.data)
                    }
                }

                stops.update_one(updateCriteria, updateQuery)

                flash('The stop has been updated')
            except Exception as e:
                print(e)
                flash('Database insertion error - please try again')

            # if form did not successful validate or there was an exception
            # error then redirect back to front page
            return redirect(url_for('trip_detailed', trip_id=trip_id))
        else:
            trip_query = trips.find_one({'_id': ObjectId(trip_id)})
            stop_query = stops.find_one({'_id': ObjectId(stop_id)})

            if trip_query and stop_query:
                prefix = 'trip_'  # used to identify trip form fields

                # update the form fields with trip data
                for field in trip_query:
                    # populate the form with values from query
                    if (prefix + field) in form:
                        # limit to only those fields which are in the form and
                        # in the database
                        form[(prefix + field)].data = trip_query[field]

                # update the form fields with stop data
                for field in stop_query:
                    # populate the form with values from query
                    if field in form:
                        form[field].data = stop_query[field]

                return render_template('stop_add_edit.html', form=form,
                                       action='update', trip=trip_query,
                                       stop=stop_query)
            else:
                flash('The trip or stop you tried to access does not exist')
                return redirect(url_for('show_trips'))
    else:
        # user does not own this trip
        flash(
            'The stop you are trying to access does not exist or you do '
            'not have permission to perform the action')

        return redirect(url_for('trip_detailed', trip_id=trip_id))


@app.route('/trip/<trip_id>/stop/<stop_id>/delete/')
def trip_stop_delete(trip_id, stop_id):
    '''
    Subject to user permissions, this will enable a user to delete a
    stop from a trip they own.
    '''
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
@app.route('/user/register/', methods=['POST', 'GET'])
def user_new():
    ''' This creates a new user in the database. '''
    # if the user is already logged in then redirect them
    if checkUserPermission(checkLogin=True):
        return redirect(url_for('show_trips'))

    form = RegistrationForm()
    # check input validation
    if form.validate_on_submit():
        try:
            # create new entry if validation is successful
            newUser = {
                'username': form.username.data,
                'name': form.name.data,
                'display_name': form.display_name.data,
                'email': form.email.data,
                'password': ''
            }
            users.insert_one(newUser)

            flash('A new account has been successfully created - you '
                  'can now login')
            return redirect(url_for('show_trips'))

        except Exception as e:
            print(e)
            flash(
                'There was a problem creating this user account - please '
                'try again later')
    else:
        return render_template('user_register.html', form=form)


# login
@app.route('/user/login/', methods=['POST', 'GET'])
def user_login():
    '''
    This enables a user to login, allowing them to perform CRUD
    operations on their own trips and/or stops.
    '''
    if checkUserPermission():
        # if user already logged in then redirect away from login page
        return redirect(url_for('show_trips'))

    form = LoginForm()
    # check input validation
    if form.validate_on_submit():
        # check that the username exists in the database
        user = users.find_one({"username": form.username.data})

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
        return render_template('user_login.html', form=form)


# logout
@app.route('/user/logout/')
def user_logout():
    ''' This logs a user out and removes and session variables. '''
    if not checkUserPermission():
        # user is not logged in
        return redirect(url_for('show_trips'))

    # delete session variable
    session.pop('USERNAME', None)
    session.pop('DISPLAY_NAME', None)

    flash('You have been logged out')
    return redirect(url_for('show_trips'))


if __name__ == '__main__':
    app.run(host=os.getenv('IP'),
            port=int(os.getenv('PORT')),
            debug=os.getenv('DEBUG'))
