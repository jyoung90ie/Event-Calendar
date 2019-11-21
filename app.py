import os
from flask import Flask, render_template, request
from dotenv import load_dotenv
import pymongo

# get environment variables
load_dotenv()

app = Flask(__name__)

# connect to mongoDB
# when using Gitpod/Heroku environ variables
MONGODB_URI = os.getenv("MONGO_URI")
# MONGODB_URI = os.environ.get("MONGO_URI") # when using dotenv
DB_NAME = "travelPal"

# connection function from code institute


def mongo_connect(url):
    try:
        conn = pymongo.MongoClient(url)
        print("Mongo is connected!")
        return conn
    except pymongo.errors.ConnectionFailure as e:
        print("Could not connect to MongoDB: %s") % e


# connect to MongoDB
client = mongo_connect(MONGODB_URI)
# select relevant db
db = client[DB_NAME]

# store collections
colTrips = db.trips
colStops = db.trips
colUsers = db.trips


# setup path routing
@app.route('/')
@app.route('/trips/')
@app.route('/trips/all/')
def show_trips():
    # pass through the trips collection, using .find() to return all contents of collection enabling iteration
    return render_template('show_trips.html', trips=colTrips.find())


#
# trips functionality
#

@app.route('/trip/new/')
def trip_new():
    return render_template('new_trip.html')


@app.route('/trip/detailed/')
# @app.route('/trip/<trip_id>/detailed/')
def trip_detailed():
    return render_template('trip_detailed.html')


@app.route('/stop/new/')
# @app.route('/trip/<trip_id>/stop/new/')
def trip_new_stop():
    return render_template('new_stop.html')


if __name__ == '__main__':
    app.run(host=os.getenv('IP'),
            port=int(os.getenv('PORT')),
            debug=os.getenv('DEBUG'))
