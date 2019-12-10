""" Test the user login and logout functionality. """
import pytest
import tempfile
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
        # with APP.app_context():
        #     APP.init_db()
        yield test_client


def login(test_client, username):
    """ Login to user account. """
    return test_client.post("/user/login",
                            data=dict(username=username),
                            follow_redirects=True)


def logout(test_client):
    """ Log out of user account. """
    return test_client.get("/user/logout", follow_redirects=True)


def register(test_client, username, name, display_name, email):
    """ Create a new user account. """
    return test_client.post("/user/register",
                            data=dict(
                                username=username,
                                name=name,
                                display_name=display_name,
                                email=email
                            ),
                            follow_redirects=True)


def load_page(test_client, page):
    """ Submit a GET request to page. """
    return test_client.get(page, follow_redirects=True)


def test_user_login_logout(test_client, username="john"):
    """ Test what happens when a user tries to login with a valid username. """
    response = login(test_client, username)
    assert response.status_code == 200
    assert b"You are now logged in to your account" in response.data
    assert b"Welcome %s" % (username.encode("utf-8").title()) in response.data
    assert b"My Trips" in response.data

    response = logout(test_client)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data
    assert b"My Trips" not in response.data
    assert b"All Trips" in response.data


@pytest.mark.parametrize("username,display_name,valid_username",
                         [("john", "John", True), ("JOHN", "John", True),
                          ("fakeuser", "", False)])
def test_login(test_client, username, display_name, valid_username):
    response = login(test_client, username)

    assert response.status_code == 200

    if valid_username is True:
        assert b"You are now logged in to your account" in response.data
        assert b"Welcome %s" % (display_name.encode("utf-8")) in response.data
        assert b"My Trips" in response.data
    else:
        assert b"This user does not exist - please check your username and " \
               b"try again." in response.data


@pytest.mark.parametrize("page", [("/user/login"), ("/user/register")])
def test_page_when_logged_in(test_client, page, username="john"):
    """ Test what happens when a user who is logged in tries to go to
    a page that should only be accessible when not logged in. """
    # login first
    login(test_client, "john")
    # load login page after logging in
    response = load_page(test_client, page)

    # expect user to be redirected to homepage due to already being logged in
    assert response.status_code == 200
    assert b"All Trips" in response.data
    assert b"Register" not in response.data
    assert b"Login" not in response.data


@pytest.mark.parametrize("page", [("/trip/new"), ("/trips/user"),
                                  ("/trip/5dee0a382739e6804e8be42f/update"),
                                  ("/trip/5dee0a382739e6804e8be42f/delete"),
                                  ("/user/logout"),
                                  ("/trip/5dee0a382739e6804e8be42f/stop/new")])
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
    url = "/"
    response = load_page(test_client, url)
    response = login(test_client, "john")

    assert response.status_code == 200
    assert b"All Trips" in response.data
    assert b"My Trips" in response.data
    assert b"Create Trip" in response.data
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Register" not in response.data
