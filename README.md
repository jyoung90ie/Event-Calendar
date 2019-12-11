# travelPal

## Purpose

travelPal has been developed for individuals (and groups) who are planning to travel and would like to be able to plot 
out their itinerary and project basic budget requirements for their trip. It is also for those who are thinking about 
travelling and would like some inspiration, which can be found by other users public trips. 

I envisage this project as an all encompassing tool for travelers which enables to maintain a travel itinerary on-the-go
without being burdensome.

## UX Design

The initial wireframes can be found [here](travelpal.pdf)

### Users (User Stories)

When conceptualising this project, the below user stories were what I used to understand what I would need to implement:

#### Individual(s) planning a trip

- User wants to plan a trip around the world for 2 people, which will involve a number of stops in various countries and
cities. 
- User needs to be able to project start and end dates for each location, based on the number of nights they are
staying at each stop. 
- User needs to be able to add, update, and, remove trips and stops as they refine their travel itinerary.
- User should be able to duplicate previous stops to streamline the process of adding additional destinations 
in the same country.
- User also needs to be able to forecast essential costs so that they can plan to save enough for the trip.
- User wants to see costs for the trip (i.e. including all stops) and by stop, at a useful level, e.g. total cost 
and per person cost.
- User would like the ability to make their trips public or private as necessary.

#### Individual(s) researching potential trips

- User wants the ability to view other users public trips.
- User would like the ability to view the granular detail of each trip, e.g. locations stopped and estimated costs.
- User wants to be able to create their own account, in order to create their own trip if the current public trips do 
not cater to their needs.

## Features

### Implemented

1) User registration and login
2) Create, Read, Update, and Remove (CRUD) functionality for Trips and Stops 
3) Ability for users to make trips public or private
4) User permissions so that only the owner of a trip can update it and associated stops
5) Ability to duplicate stops to make the process for adding stops easier
6) When registering an account, usernames should be unique, therefore a check is in place to ensure only unique 
usernames are registered

### To be Implemented

1) Currency conversion, i.e. users are visiting countries with different currencies but would like to input costs in 
local currency, but have this converted to their home currency
2) Draggable re-ordering for 'stops' list which will update projected start and end dates for each stop
3) Search capability, to enable travelers to search by country, city, or region
4) Password login
5) Ability to add notes for each stop to capture useful information, e.g. areas of interest
6) Users can update their personal details via a user profile page
7) Ability to duplicate a trip, with its stops, as a skeleton for a new trip

## Technologies

- HTML: used to provide the front-end structure
- CSS: used to style my application
- JavaScript: used to provide a more interative user interface
- [JQuery](https://jquery.com/): used to provide easy access to DOM elements for manipulation
- [Materialize](https://materializecss.com/): used to provide a positive user experience, such as a side navigation for 
mobile devices, and a form datepicker field
- [Flask](https://palletsprojects.com/p/flask/): used to write the application back-end 
- [MongoDB](https://www.mongodb.com/): used to store and retrieve data inputs
- [Heroku](https://www.heroku.com/): used for deployment
- [PyTest](https://docs.pytest.org/en/latest/): used to perform thorough automated unit testing

## Database Schema

### Users collection

| Field name    | Type  
|---------------|-------------
| _id           | ObjectId 
| username      | String 
|name           | String 
|display_name   | String 
|email          | String 
|password       | String (placeholder for future implementation)

### Trips collection

| Field name    | Type 
|------------   |-------------
|_id           |      ObjectId
|name          |      String
|start_date    |     Date
|end_date      |     Date
|owner_id      |      ObjectId (foreign key to '_id' in the 'Users' collection)
|public        |      Boolean
|travelers     |      Int32

### Stops collection

| Field name    | Type 
|------------   |-------------
|_id              |  ObjectId
|trip_id          |  ObjectId (foreign key to '_id' in the 'Trips' collection)
|country          |  String
|city_town        |  String
|duration         |  Int32
|order            |  Int32
|currency         |  String
|cost_accommodation| Double
|cost_food        |  Double
|cost_other       |  Double

## Testing

### Planning

- Only trip owners should be able to modify a trip or associated stop
- Private trips should only be displayed and accessible to the trip owner
- A user should only be able to register an account if the username they have chosen does not already exist
- Users should not be able to 'hack' the URL path to access/modify trips they do not own
- Inputting form data in the wrong format (e.g. strings in numeric fields) should prompt the user to correct this prior 
to invoke database functions
- When deleting a trip, the trip record and all associated stop records should be deleted from the database

### Manual Testing

| # | Test | Test Criteria | Result |
|---|------|--------|------|
| 1 | Website is displayed correctly on multiple browsers | Tested on Chrome, Safari, and Edge | Passed |
| 2 | Website is responsive and displayed correctly on multiple devices | Tested on Macbook Pro, Windows Laptop, Samsung S9+, and iPhone | Passed |
| 3 | Forms do not permit entry of invalid data; invalid entries receive an error message | Input strings in numeric fields, Input invalid email address format in the email entry field, Submitting the form without populating any fields | Passed |
| 4 | All links work | Check that all links are work, including the breadcrumb navigation links | Passed |
| 5 | Manually changing the URL to access pages that the user does not have permission to is not permitted | Copying the link for deleting a trip but changing the trip_id to another trip_id that is not the user's, Trying to add a stop to a trip that is not the users by changing the trip_id | Passed |
| 6 | Images, icons, and buttons render correctly | Visual inspection of every page | Passed |
| 7 | Flash messages are displayed upon successful execution of a user action (e.g. add new trip, delete stop, etc.) | Perform each action and check MongoDB to see if the action was executed, if so, check that flash message was displayed | Passed |
| 8 | Check that the trip detail aggregate costs match stop costs | Perform manual calculation of all figures, change figures and check that changes are reflected | Passed |

### Automated Testing

I used PyTest to perform a number of automated tests, I have outlined at a high level the extent of these tests below:

- Ensure that a user who is not logged in does not have access to routes they should not
- Ensure that a user who is logged in is not able to change any trips/stops that they do not own
- Ensure that a user is not permitted to enter invalid data, and if they do, this is not entered into the database
- Ensure a user cannot manually manipulate route paths to view content they should not be able to access

The application implementation successfully passed the automated tests.


## Deployment

### Heroku
This application was deployed to Heroku using a git remote branch, to create your own deployment you will need to follow 
the steps below:

1) Create a MongoDB database with the collections noted in the *Database schema* section above
2) You will then need to [Create an app in Heroku](https://devcenter.heroku.com/articles/creating-apps)
3) Once you have created your Heroku app, you will need to create environment variables (see Environment Variables sub-section) - see [Setup environment variables in Heroku](https://devcenter.heroku.com/articles/config-vars)
4) You will then need to use Git to push the code to Heroku - you can find out more at [Deploying with Git](https://devcenter.heroku.com/articles/git)

**Please note:** To deploy a Heroku python web application you will need to ensure the following files exist in the root directory - both files exist within this repository.

1) **Procfile**: this tells Heroku what type of application you are trying to deploy, and which file should be run when it is deployed
2) **requirements.txt**: this tells Heroku what Python add-ons to download so that the deployment file can run correctly

### Local

If you wish to deploy this application to your local system, you can do so by following the steps below:

1) Download and install Git to your computer - see [here](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).
2) Once you have installed Git, you will need to create a folder on your computer and then run the _git clone_ command. A demonstration of this code can be seen below:

```terminal
mkdir travelPal
cd travelPal
git clone https://github.com/jyoung90ie/travelPal.git
```

**_The following steps should all be performed while in the root folder of your travelPal git clone from step 2_**

3) Download and install [Python](https://www.python.org/downloads/)
4) Download the necessary python requirements. Open up a terminal or cmd prompt, and run the following code, 

```
pip install -r requirements.txt
```

5) Create a .env file and input the variables outlined in the Environment Variables sub-section
6) Create a MongoDB database with the collections noted in the *Database schema* section above
7) Run the file _app.py_ by executing the following command in terminal or cmd:
```
python app.py
```
8) Open up your preferred web browser and navigate to 'localhost:5000' to use the application


### Environment Variables

| Variable | Value 
|----------|-------
| IP        | 0.0.0.0
| PORT      | 5000 
| SECRET_KEY| your-value-here
| DEBUG | False
| MONGODB_URI | [Obtaining your MongoDB URI](https://docs.atlas.mongodb.com/driver-connection/#connect-your-application) 


## Credits

### Media

- The images used for the Trips listing page are sourced from [PlaceIMG](https://placeimg.com/)