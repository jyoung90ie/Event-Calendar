import os
from flask import Flask, render_template
from dotenv import load_dotenv
import pymongo

# get environment variables
load_dotenv()

app = Flask(__name__)


@app.route('/')
@app.route('/trips/')
@app.route('/trips/all/')
def index():
    return render_template('index.html')

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
    return render_template('trip_detailed.html')


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=os.environ.get('DEBUG'))
