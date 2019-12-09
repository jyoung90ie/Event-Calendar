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


def getTripDuration(trip_id):
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
        get_total_duration = stops.aggregate(pipeline)

        total_duration = get_total_duration.next()['total_duration']
    except:
        # otherwise set to zero
        total_duration = 0

    return total_duration

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
        pipeline_filter = {
            "$match": {
                "$or":
                    [{"owner_id": user_id}]
            }
        }
    else:
        pipeline_filter = {
            "$match": {
                "$or":
                    [{"owner_id": user_id},
                     {"public": True}]
            }
        }
    # pass through the trips collection, using .find() to return all contents
    # of collection enabling iteration
    pipeline = [
        pipeline_filter,
        {
            u"$lookup": {
                u"from": u"stops",
                u"localField": u"_id",
                u"foreignField": u"trip_id",
                u"as": u"stops"
            }
        },
        {
            u"$lookup": {
                u"from": u"users",
                u"localField": u"owner_id",
                u"foreignField": u"_id",
                u"as": u"users"
            }
        },
        {
            u"$unwind": {
                u"path": u"$stops",
                u"includeArrayIndex": u"arrayIndex",
                u"preserveNullAndEmptyArrays": True
            }
        },
        {
            u"$group": {
                u"_id": u"$_id",
                u"number_of_stops": {
                    u"$sum": {
                        u"$cond": {
                            u"if": {
                                u"$gt": [
                                    u"$stops.trip_id",
                                    u"null"
                                ]
                            },
                            u"then": 1.0,
                            u"else": 0.0
                        }
                    }
                },
                u"duration": {
                    u"$sum": u"$stops.duration"
                },
                u"total_accommodation": {
                    u"$sum": {
                        u"$multiply": [
                            u"$stops.duration",
                            u"$stops.cost_accommodation"
                        ]
                    }
                },
                u"total_food": {
                    u"$sum": {
                        u"$multiply": [
                            u"$stops.duration",
                            u"$stops.cost_food"
                        ]
                    }
                },
                u"total_other": {
                    u"$sum": {
                        u"$multiply": [
                            u"$stops.duration",
                            u"$stops.cost_other"
                        ]
                    }
                },
                u"start_date": {
                    u"$min": u"$start_date"
                },
                u"country": {
                    u"$push": u"$stops.country"
                },
                u"name": {
                    u"$first": u"$name"
                },
                u"travelers": {
                    u"$max": u"$travelers"
                },
                u"owner_id": {
                    u"$first": u"$owner_id"
                },
                u"public": {
                    u"$min": u"$public"
                },
                u"display_name": {
                    u"$first": u"$users.display_name"
                }
            }
        },
        {
            u"$project": {
                u"number_of_stops": 1,
                u"duration": 1,
                u"total_cost": {
                    u"$multiply": [
                        u"$travelers",
                        {
                            u"$add": [
                                u"$total_accommodation",
                                u"$total_food",
                                u"$total_other"
                            ]
                        }
                    ]
                },
                u"start_date": 1,
                u"end_date": {
                    u"$add": [
                        u"$start_date",
                        {
                            u"$multiply": [
                                u"$duration",
                                24,
                                3600,
                                1000
                            ]
                        }
                    ]
                },
                u"countries": {
                    u"$reduce": {
                        u"input": u"$country",
                        u"initialValue": u"",
                        u"in": {
                            u"$cond": {
                                u"if": {
                                    u"$eq": [
                                        {
                                            u"$indexOfArray": [
                                                u"$country",
                                                u"$$this"
                                            ]
                                        },
                                        0
                                    ]
                                },
                                u"then": {
                                    u"$concat": [
                                        u"$$this"
                                    ]
                                },
                                u"else": {
                                    u"$concat": [
                                        u"$$value",
                                        u", ",
                                        u"$$this"
                                    ]
                                }
                            }
                        }
                    }
                },
                u"name": 1,
                u"travelers": 1,
                u"username": u"$display_name",
                u"public": 1,
                u"owner_id": 1
            }
        },
        {
            u"$unwind": {
                u"path": u"$username"
            }
        },
        {
            u"$sort": {
                "start_date": 1,
                "end_date": 1
            }
        }
    ]

    getTrips = trips.aggregate(pipeline)

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
                'name': form.name.data.strip().title(),
                'travelers': form.travelers.data,
                'start_date': form.start_date.data,
                'end_date': '',
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
                        'name': form.name.data.strip().title(),
                        'travelers': form.travelers.data,
                        'start_date': form.start_date.data,
                        'end_date': '',
                        'public': form.public.data
                    }
                }

                trips.update_one(updateCriteria, updateQuery)

                flash('Your trip has been updated')
                return redirect(url_for('trip_detailed', trip_id=trip_id))
            except Exception as e:
                print(e)
                flash('Database update error - please try again')

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

    # set variables needed
    last_trip_id = ''
    last_stop_end_date = ''
    trip_total_cost = 0
    trip_total_accom = 0
    trip_total_food = 0
    trip_total_other = 0
    trip_total_cost_pp = 0
    trip_total_accom_pp = 0
    trip_total_food_pp = 0
    trip_total_other_pp = 0
    trip_avg_cost_pn = 0
    trip_stops = 0
    trip_duration = 0
    trip_countries = 0

    trip_owner = ''
    trip_name = ''
    country_list = ''
    last_country = ''

    stops_detail = []

    # results counter
    results = 0

    for doc in cursor:
        # there is a result, increment countere
        results += 1

        # variables used early in the process
        stop_duration = doc['stops']['duration']
        stop_country = doc['stops']['country']

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

            # end date is max of current end date value and current stop end date
            trip_end_date = max(trip_end_date, last_stop_end_date)

            # cumulative totals
            trip_total_accom += stop_total_accom
            trip_total_food += stop_total_food
            trip_total_other += stop_total_other

            trip_total_accom_pp += stop_total_accom_pp
            trip_total_food_pp += stop_total_food_pp
            trip_total_other_pp += stop_total_other_pp

            if not last_country == stop_country:
                # increase counter if country has changed
                trip_countries += 1

                country_list = country_list + ' - ' + stop_country

            # counters
            trip_stops += 1
            trip_duration += stop_duration

        else:
            # new trip, new stop - reset
            last_trip_start_date = doc['start_date']
            last_stop_start_date = last_trip_start_date
            last_stop_end_date = last_trip_start_date + \
                timedelta(days=stop_duration)

            # reset trip totals
            trip_total_accom = stop_total_accom
            trip_total_food = stop_total_food
            trip_total_other = stop_total_other

            trip_total_accom_pp = stop_total_accom_pp
            trip_total_food_pp = stop_total_food_pp
            trip_total_other_pp = stop_total_other_pp

            # for trip overview
            trip_owner = doc['owner_id']
            trip_name = doc['name']
            trip_start_date = doc['start_date']
            trip_end_date = last_stop_end_date

            # counters
            trip_stops = 1
            trip_countries = 1
            trip_duration = stop_duration

        # outside loop
        last_trip_id = doc['_id']
        last_country = stop_country

        trip_total_cost = trip_total_accom + trip_total_food + trip_total_other
        trip_total_cost_pp = trip_total_accom_pp + \
            trip_total_food_pp + trip_total_other_pp

        stop_total_cost = stop_total_accom + stop_total_food + stop_total_other
        stop_total_cost_pp = stop_total_accom_pp + \
            stop_total_food_pp + stop_total_other_pp

        arr = {
            'trip_id': last_trip_id,
            'stop_id': doc['stops']['_id'],
            'duration': stop_duration,
            'travelers': trip_travelers,
            'country': stop_country,
            'city_town': doc['stops']['city_town'],
            'currency': doc['stops']['currency'],

            'stop_start_date': last_stop_start_date,
            'stop_end_date': last_stop_end_date,

            'stop_total_cost_pp': stop_total_cost_pp,
            'stop_total_accom_pp': stop_total_accom_pp,
            'stop_total_food_pp': stop_total_food_pp,
            'stop_total_other_pp': stop_total_other_pp,

            'stop_total_cost': stop_total_cost,
            'stop_total_accom': stop_total_accom,
            'stop_total_food': stop_total_food,
            'stop_total_other': stop_total_other
        }

        stops_detail.append(arr)

    if results > 0:
        # if the query return results continue (i.e. there were stops)

        trip_avg_cost_pn = trip_total_cost / trip_duration

        # create trip information dict
        trip_detail = {
            '_id': last_trip_id,
            'owner_id': trip_owner,
            'name': trip_name,
            'start_date': trip_start_date,
            'end_date': trip_end_date,
            'travelers': trip_travelers,
            'total_duration': trip_duration,
            'avg_cost_pn': trip_avg_cost_pn,
            'total_stops': trip_stops,
            'total_countries': trip_countries,
            'trip_total_cost': trip_total_cost,
            'trip_total_cost_pp': trip_total_cost_pp,
            'total_accom_pp': trip_total_accom_pp,
            'total_food_pp': trip_total_food_pp,
            'total_other_pp': trip_total_other_pp,
            'total_accom': trip_total_accom,
            'total_food': trip_total_food,
            'total_other': trip_total_other,
        }
    else:
        # if there were no results, need to run query
        trip_detail = trips.find_one({"_id": ObjectId(trip_id)})

    return render_template('trip_detailed.html', trip=trip_detail,
                           stops=stops_detail)

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
                    'country': form.country.data.strip().title(),
                    'city_town': form.city_town.data.strip().title(),
                    'duration': form.duration.data,
                    'order': 1,
                    'currency': form.currency.data.strip().upper(),
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

            form.current_stop_duration.data = 0
            form.total_trip_duration.data = getTripDuration(trip_id)

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
                        'country': form.country.data.strip().title(),
                        'city_town': form.city_town.data.strip().title(),
                        'duration': form.duration.data,
                        'order': 1,
                        'currency': form.currency.data.strip().upper(),
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

                # set hidden varialbes
                form.total_trip_duration.data = getTripDuration(trip_id)
                form.current_stop_duration.data = stop_query['duration']

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
                'username': form.username.data.strip().lower(),
                'name': form.name.data.strip().title(),
                'display_name': form.display_name.data.strip(),
                'email': form.email.data.strip().lower(),
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
