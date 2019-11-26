from bson.objectid import ObjectId
from datetime import datetime
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, url_for, redirect, \
    make_response, jsonify

# get environment variables
load_dotenv()

app = Flask(__name__)
app.config['MONGO_DBNAME'] = 'travelPal'
app.config['MONGO_URI'] = os.getenv('MONGODB_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# initialise mongoDb
mongo = PyMongo(app)

# set user id
# user_id = '5dd6ad9e1c9d4400006e56e1'  # real user_id
# user_id = '5dd6ad9e1c9d4400006e56e9'  # fake test user_id
user_id = ''

##
# setup path routing
##
#
# trips functionality
#
@app.route('/')
@app.route('/trips/')
@app.route('/trips/all/')
def show_trips():
    print('show_trips(): user_id = ' + str(user_id))
    # pass through the trips collection, using .find() to return all contents
    # of collection enabling iteration
    agg = [
        {
            "$match": {
                "$or":
                    [{"owner_id": user_id},
                     {"public": True}]
            }
        },
        {"$lookup": {"from": "stops", "localField": "_id",
                     "foreignField": "trip_id", "as": "stops"}
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
                "owner_id": {
                    "$first": "$owner_id"
                },
                "public": {
                    "$min": "$public"
                }
            }
        },
        {
            "$project": {
                "start_date": True,
                "end_date": True,
                "name": True,
                "public": True,
                "owner_id": True,
                "country": True,
                "number_of_stops": True,
                "duration": True,
                "total_accommodation": True,
                "total_food": True,
                "total_other": True,
                "total_cost": {"$add": ["$total_accommodation", "$total_food",
                                        "$total_other"]}
            }
        },
        {
            "$sort": {
                "start_date": 1,
                "end_date": 1
            }
        }
    ]
    # for row in mongo.db.trips.aggregate(agg):
    #     print(row)

    # return 'Test'

    return render_template('trips_show.html',
                           trips=mongo.db.trips.aggregate(agg),
                           user_id=user_id)


@app.route('/trip/new/', methods=['POST', 'GET'])
def trip_new():
    if request.method == 'POST':
        # create functionality to process form
        # then add to db
        # then redirect back to all trips

        try:
            # convert form date strings to datetime
            startdate = datetime.strptime(
                request.form.get('start-date'), '%d %b %Y')
            enddate = datetime.strptime(
                request.form.get('end-date'), '%d %b %Y')
            name = str(request.form.get('trip-name'))
            # convert checkbox 'on' or 'off' to boolean value for storing
            public = True if request.form.get('public') == 'on' else False

            # create new entry if validation is successful
            newTrip = {
                'name': name,
                'start_date': startdate,
                'end_date': enddate,
                'owner_id': user_id,
                'public': public
            }
            mongo.db.trips.insert_one(newTrip)

            return redirect(url_for('show_trips'))
        except Exception as e:
            print(e)
            return 'Input error'
    else:
        return render_template('trip_new.html')

# Set Username
@app.route('/set/username/', methods=['POST'])
def set_username():
    data = request.get_json()

    global user_id

    if data['username']:
        user_id = ObjectId(data['username'])

    print(data)

    # send back data to test if it worked with success code (200)
    return make_response(jsonify(data), 200)


@app.route('/trip/<trip_id>/update/', methods=['POST', 'GET'])
def trip_update(trip_id):
    if request.method == 'POST':
        # when the form has been clicked
        # need validation (all fields proper, id exists, id is owned by user)
        # then iterate through field values and update in db
        # then redirect back to all trips
        try:
            # convert form date strings to datetime
            startdate = datetime.strptime(
                request.form.get('start-date'), '%d %b %Y')
            enddate = datetime.strptime(
                request.form.get('end-date'), '%d %b %Y')
            name = str(request.form.get('trip-name'))
            # convert checkbox 'on' or 'off' to boolean value for storing
            public = True if request.form.get('public') == 'on' else False

            # create new entry if validation is successful
            updateCriteria = {
                '_id': ObjectId(trip_id)
            }
            updateQuery = {
                '$set': {
                    'name': name,
                    'start_date': startdate,
                    'end_date': enddate,
                    'public': public
                }
            }

            mongo.db.trips.update_one(updateCriteria, updateQuery)

            return redirect(url_for('show_trips'))
        except Exception as e:
            print(e)
            return 'Input error'
    else:
        # create functionality to pull trip information from db
        # then populate this data into the form
        trip_query = {'_id': ObjectId(trip_id)}

        return render_template('trip_update.html',
                               trip=mongo.db.trips.find_one(trip_query),)


@app.route('/trip/<trip_id>/delete/')
def trip_delete(trip_id):
    # need to validate that the trip_id belongs to this user
    # if not, redirect to show all trips
    # if it does, process the delete
    query = {'_id': ObjectId(trip_id), 'owner_id': ObjectId(user_id)}

    # check user is the user that owns this trip
    trip = mongo.db.trips.find_one(query)

    # check if any results were returned by the query - i.e. does this user
    # own this trip?
    if trip:
        # add query to delete all stops associated with this trip then delete
        # the trip

        # if user owns this entry then delete
        mongo.db.trips.delete_one(query)

        return redirect(url_for('show_trips'))
    else:
        return 'Trip does not exist or you do not have permission to do this'


# @app.route('/trip/detailed/')
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
                           trip=mongo.db.trips.find_one(trip_query),
                           stops=mongo.db.stops.find(stop_query),
                           user_id=user_id)

#
# stops functionality
#
@app.route('/stop/new/')
# @app.route('/trip/<trip_id>/stop/new/')
def trip_new_stop():
    return render_template('stop_new.html')


#
# user functionality
#

# register
@app.route('/user/register/')
def user_new():
    return render_template('placeholder.html', run_function='Register')

# login
@app.route('/user/login/')
def user_login():
    return render_template('placeholder.html', run_function='Login')


# logout
@app.route('/user/logout/')
def user_logout():
    return render_template('placeholder.html', run_function='Logout')


# logout
@app.route('/user/profile/')
def user_profile():
    return render_template('placeholder.html', run_function='Profile')


if __name__ == '__main__':
    app.run(host=os.getenv('IP'),
            port=int(os.getenv('PORT')),
            debug=os.getenv('DEBUG'))
