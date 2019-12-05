from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from flask import Flask

# get environment variables
load_dotenv()

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv('MONGODB_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# initialise mongoDb
mongo = PyMongo(app)

# set collections variables
users = mongo.db.users
trips = mongo.db.trips
stops = mongo.db.stops
