''' This creates a connection to MongoDB and creates collection variables '''
import os
from flask import Flask
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
