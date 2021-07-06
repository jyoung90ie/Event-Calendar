# pylint: disable=redefined-outer-name
""" Test travelPal functionality. """
import tempfile
import pytest
from app import APP


@pytest.fixture
def test_client():
    """ APP is initialised in db.py.
    Set additional config variables for testing environment. """
    # set flask config vars for testing
    APP.config["TESTING"] = True
    APP.config["WTF_CSRF_ENABLED"] = False
    APP.config["DATABASE"] = tempfile.mkstemp()

    with APP.test_client() as test_client:
        yield test_client

# helper functions used in the test functions


def login(test_client, username):
    """ Helper function used to perform a user login. """
    return test_client.post("/user/login",
                            data=dict(username=username),
                            follow_redirects=True)


def logout(test_client):
    """ Helper function used to perform a user logout. """
    return test_client.get("/user/logout", follow_redirects=True)


def submit_form(test_client, url, form_data):
    """ Helper function used submit form data return the response.
    'form_data' is a dict constructed to match the form input requirements. """
    return test_client.post(url, data=form_data, follow_redirects=True)


def load_page(test_client, page):
    """ Helper function used to submit a GET request to a page. """
    return test_client.get(page, follow_redirects=True)

# tests below this line


def test_user_login_logout(test_client, username="john"):
    """ Test what happens when a user tries to login with a valid username. """
    # perform user login
    response = login(test_client, username)
    # check login was successful
    assert response.status_code == 200
    assert b"You are now logged in to your account" in response.data
    assert b"Welcome %s" % (username.encode("utf-8").title()) in response.data
    assert b"My Trips" in response.data

    # perform user logout
    response = logout(test_client)
    # check logout was successful
    assert response.status_code == 200
    assert b"You have been logged out" in response.data
    assert b"All Trips" in response.data
    assert b"My Trips" not in response.data


@pytest.mark.parametrize("username,display_name,valid_username",
                         [("john", "John", True), ("JOHN", "John", True),
                          ("fakeuser", "", False)])
def test_login(test_client, username, display_name, valid_username):
    """ Test login form, passing through valid and invalid
    usernames, to ensure the response data is as expected. """
    response = login(test_client, username)

    # check the page loaded
    assert response.status_code == 200

    if valid_username is True:
        # if the username passed is an actual user then expect to see
        assert b"You are now logged in to your account" in response.data
        assert b"Welcome %s" % (display_name.encode("utf-8")) in response.data
        assert b"My Trips" in response.data
    else:
        # if username does not exist
        assert b"This user does not exist - please check your username and " \
               b"try again." in response.data


@pytest.mark.parametrize("page", [("/user/login"), ("/user/register")])
def test_page_when_logged_in(test_client, page, username="john"):
    """ Test what happens when a user who is logged in tries to go to
    a page that should only be accessible when not logged in. """
    # login first
    login(test_client, username)
    # load pages now user is logged in
    response = load_page(test_client, page)

    # expect user to be redirected to homepage due to already being logged in
    # homepage will show 'all trips'
    assert response.status_code == 200
    assert b"All Trips" in response.data
    # given user is logged in the below links should not be visible
    assert b"Register" not in response.data
    assert b"Login" not in response.data


# setup paths that the user should not be able to access unless they are
# logged in
@pytest.mark.parametrize("page", [("/trip/new"), ("/trips/user"),
                                  ("/user/logout"),
                                  ("/trip/5dee0a382739e6804e8be42f/update"),
                                  ("/trip/5dee0a382739e6804e8be42f/delete"),
                                  ("/trip/5dee0a382739e6804e8be42f/stop/new"),
                                  ("/trip/5dee0a382739e6804e8be42f/stop/5dee0bc50e46bd85b55457d9"
                                   "/duplicate")])
def test_page_when_not_logged_in(test_client, page):
    """ Test what happens when a user is not logged in but attempts
    to access a page that requires them to be logged in. """
    # run logout to make sure no session data remains
    logout(test_client)
    # load login page after logging in
    response = load_page(test_client, page)

    # do not expect to see any of the following as the user should be
    # redirected
    assert response.status_code == 200
    assert b"update your trip" not in response.data
    assert b"Add a Stop to your Trip!" not in response.data
    assert b"create a new trip" not in response.data
    assert b"The trip and all associated stops have now been deleted" not in response.data
    assert b"You have been logged out" not in response.data


def test_home_page_logged_in(test_client):
    """ Login to a user account and ensure that the navigation menu
    displays only the links that are usable while logged in. """
    url = "/"
    load_page(test_client, url)
    response = login(test_client, "john")

    assert response.status_code == 200
    # nav bar contains links to the below when logged in
    assert b"All Trips" in response.data
    assert b"My Trips" in response.data
    assert b"Create Trip" in response.data
    assert b"Logout" in response.data
    # nav bar should not contain links to the below when logged in
    assert b"Login" not in response.data
    assert b"Register" not in response.data


@pytest.mark.parametrize("page", [("/trip/fakeID/update"),
                                  ("/trip/5de7ce632e815a6653273d22/detailed"),
                                  ("/trip/5de7ce632e815a6653273d22/stop/new"),
                                  ("/trip/5de7ce632e815a6653273d20/stop/"
                                   "5de7ce632e815a6653273d20/update"),
                                  ("/trip/5de7ce632e815a6653273d20/stop/fakeID/duplicate")])
def test_invalid_page(test_client, page):
    """ Attempt to access non-existant trips and stops, and ensure that
    the outcome is a message stating the trip and/or stop does not exist. """
    response = load_page(test_client, page)

    # check that page load was successful
    assert response.status_code == 200
    # expect the user to be redirected with a flash message that contains one the below
    assert b"does not exist" or b"do not exist" in response.data


@pytest.mark.parametrize("url,valid_entry,form_data",
                         [   # blank entries
                             ("/user/register", False, {'username': '', 'name': '',
                                                        'display_name': '',
                                                        'email': ''}),
                             # user already exists
                             ("/user/register", False, {'username': 'john', 'name': 'john',
                                                        'display_name': 'john',
                                                        'email': 'john@john.com'}),
                             # valid entry - should be successful the first time
                             ("/user/register", True, {'username': 'a_new_user', 'name': 'New',
                                                       'display_name': 'New User',
                                                       'email': 'new@new.com'})
                         ])
def test_register(test_client, url, valid_entry, form_data):
    """ Attempt to register a new user and test whether the data is handled correctly,
    dependent on whether it is valid or not. """
    # clear session variables
    logout(test_client)

    response = submit_form(test_client, url, form_data)

    # check that page load was successful
    assert response.status_code == 200
    # check if the entry is valid or not and test accordingly
    if not valid_entry:
        # the below only shows if there has been a form input error
        assert b'<span class="error">' in response.data
        # the below message appears when an account has been created
        assert b'A new account has been successfully created' not in response.data
    else:
        # if this is a valid entry, expect to see inverse of above
        assert b'<span class="error">' not in response.data
        assert b'A new account has been successfully created' in response.data


@pytest.mark.parametrize("url,valid_entry,form_data",
                         [
                             # blank entries
                             ("/trip/new", False,
                              {'name': '', 'travelers': '',
                               'start_date': '', 'public': ''}),
                             # invalid start_date entry
                             ("/trip/new", False,
                              {'name': 'New Trip', 'travelers': '2',
                               'start_date': '12 Decembers 2020', 'public': 'True'}),
                             # invalid name entry (empty)
                             ("/trip/new", False,
                              {'name': '', 'travelers': '2',
                               'start_date': '12 Dec 2020', 'public': 'asdasd'}),
                             # invalid travelers entry (should be number)
                             ("/trip/new", False,
                              {'name': 'ASDASD', 'travelers': 'asdasd',
                               'start_date': '12 Dec 2020', 'public': 'asdasd'}),
                             # valid entry
                             ("/trip/new", True,
                              {'name': 'ASDASD', 'travelers': '3',
                               'start_date': '12 Dec 2020', 'public': 'True'})
                         ])
def test_add_update_trip_invalid_entry(test_client, url, valid_entry, form_data):
    """ Test that data entry in the new/update trips is correctly processed, dependent
    on whether the data entry is valid or not. """
    # login
    login(test_client, "john")

    # setup test
    response = submit_form(test_client, url, form_data)

    # check that page load was successful
    assert response.status_code == 200

    # check if the entry is valid or not and test accordingly
    if not valid_entry:
        # data entry is invalid, expect error and no added message
        assert b'<span class="error">' in response.data
        assert b'New trip has been created' not in response.data
    else:
        # if this is a valid entry, expect to see inverse of above
        assert b'<span class="error">' not in response.data
        assert b'New trip has been created' in response.data


@pytest.mark.parametrize("username,url,valid_entry,form_data",
                         [  # blank entry
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': '', 'city_town': '', 'currency': '', 'duration': '',
                                 'cost_accommodation': '', 'cost_food': '',
                                 'cost_other': ''}),
                             # invalid entry for duration (should be a number)
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'currency': 'EUR', 'duration': 'NOTANUMBER',
                                 'cost_accommodation': '50', 'cost_food': '20',
                                 'cost_other': '15'}),
                             # invalid entry for currency (should 3 characters long)
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'currency': 'EUROS', 'duration': '2',
                                 'cost_accommodation': '50', 'cost_food': '20',
                                 'cost_other': '15'}),
                             # invalid entry for accom (should be a number)
                             ('john', "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'currency': 'EUR', 'duration': '2',
                                 'cost_accommodation': 'FIFTY', 'cost_food': '20',
                                 'cost_other': '15'}),
                             # invalid entry for food (should be a number)
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'currency': 'EUR', 'duration': '2',
                                 'cost_accommodation': '50', 'cost_food': '20T',
                                 'cost_other': '15'}),
                             # invalid entry for other (should be a number)
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'currency': 'EUR', 'duration': '2',
                                 'cost_accommodation': '50', 'cost_food': '20',
                                 'cost_other': ''}),
                             # missing form data for currency & duration
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", False, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'cost_accommodation': '50', 'cost_food': '20',
                                 'cost_other': '22'}),
                             # valid entry
                             ("john", "/trip/5dee3e228f1db52b29cfce59/stop/new", True, {
                                 'country': 'Ireland', 'city_town': 'Dublin',
                                 'currency': 'EUR', 'duration': '2',
                                 'cost_accommodation': '50', 'cost_food': '20',
                                 'cost_other': '22'})
                         ])
def test_add_update_stop_invalid_entry(test_client, username, url, valid_entry, form_data):
    """ Using a valid username and a valid trip_id, attempt to add a new stop
    using invalid data entries. This should not be permitted. """
    # clear any previous session data
    logout(test_client)
    # login
    login(test_client, username)

    # setup test
    response = submit_form(test_client, url, form_data)

    # check that page load was successful
    assert response.status_code == 200

    # check if the entry is valid or not and test accordingly
    if not valid_entry:
        # data entry is invalid, expect error and no added message
        assert b'<span class="error">' in response.data
        assert b'added a new stop' not in response.data
    else:
        # if this is a valid entry, expect to see inverse of above
        assert b'<span class="error">' not in response.data
        assert b'added a new stop' in response.data
