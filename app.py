import os
from flask import Flask, render_template, request
from dotenv import load_dotenv
import pymongo

# get environment variables
load_dotenv()

app = Flask(__name__)

# connect to mongodb
MONGODB_URI = os.getenv("MONGO_URI")
DB_NAME = "travelPal"
# COLLECTION_NAME = "myFirstMDB"


def mongo_connect(url):
    try:
        conn = pymongo.MongoClient(url)
        print("Mongo is connected!")
        return conn
    except pymongo.errors.ConnectionFailure as e:
        print("Could not connect to MongoDB: %s") % e


conn = mongo_connect(MONGODB_URI)

# setup path routing


@app.route('/')
@app.route('/trips/')
@app.route('/trips/all/')
def show_trips():
    return render_template('show_trips.html', trips=conn[DB_NAME]['trips'])

# trips functionality


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
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=os.environ.get('DEBUG'))


# users = conn[DBS_NAME]['trips']
# stops = conn[DBS_NAME]['trips']
