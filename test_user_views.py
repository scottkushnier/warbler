
from app import app, CURR_USER_KEY
import os
from unittest import TestCase
from sqlalchemy import exc
from flask import session

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserViewsTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.app_context = app.app_context()

        self.client = app.test_client()
        # self.app_context.push()

    def test_user_view(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        self.testuser_g = User.signup(username="george",
                                      email="george@foo.com",
                                      password="abc123",
                                      image_url=None)
        db.session.add(self.testuser_g)
        db.session.commit()

        self.testuser_h = User.signup(username="hector",
                                      email="hector@foo.com",
                                      password="abc124",
                                      image_url=None)
        db.session.add(self.testuser_h)
        db.session.commit()

        self.testuser_i = User.signup(username="irene",
                                      email="irene@fooforgirls.com",
                                      password="abc125",
                                      image_url=None)
        db.session.add(self.testuser_i)
        db.session.commit()

        with app.test_client() as client:
            resp = client.get("/")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn("Sign up", html)
            self.assertIn("Log in", html)
            self.assertIn("Warbler", html)
            self.assertIn("warbler-logo.png", html)

        with app.test_client() as client:
            resp = client.get("/signup")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn(
                '<button class="btn btn-primary btn-lg btn-block">Sign me up!</button>', html)
            self.assertIn(
                '<input class="form-control" id="password" minlength="6" name="password" placeholder="Password" type="password" value="">', html)

        with app.test_client() as client:
            resp = client.get("/login")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn(
                ' <button class="btn btn-primary btn-block btn-lg">Log in</button>', html)
            self.assertIn('<form method="POST" id="user_form">', html)

        # print(self.testuser)

        with self.client as client:
            with client.session_transaction() as s:
                s[CURR_USER_KEY] = self.testuser_g.id

# Test User lists w/wo search params

            resp = client.get("/users?q=")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@george</p>', html)
            self.assertIn('<p>@hector</p>', html)
            self.assertIn('<p>@irene</p>', html)

            resp = client.get("/users?q=geo")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@george</p>', html)
            self.assertNotIn('<p>@hector</p>', html)
            self.assertNotIn('<p>@irene</p>', html)

            resp = client.get("/users?q=ene")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<p>@george</p>', html)
            self.assertNotIn('<p>@hector</p>', html)
            self.assertIn('<p>@irene</p>', html)

# Test follows:
#        George follow Irene & Hector.
#        Irene follows Hector.

            follow = Follows(
                user_being_followed_id=self.testuser_i.id, user_following_id=self.testuser_g.id)
            db.session.add(follow)
            db.session.commit()

            follow = Follows(
                user_being_followed_id=self.testuser_h.id, user_following_id=self.testuser_g.id)
            db.session.add(follow)
            db.session.commit()

            follow = Follows(
                user_being_followed_id=self.testuser_h.id, user_following_id=self.testuser_i.id)
            db.session.add(follow)
            db.session.commit()

# Check that George follows 2

            # route = f"/users/{self.testuser_g.id}/following"
            # print('route: ', route)
            resp = client.get(f"/users/{self.testuser_g.id}/following")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn('Image for hector', html)
            self.assertIn(
                f'<a href="/users/{self.testuser_g.id}/following"\n                >2', html)

# Check that Irene follows 1

            with client.session_transaction() as s:
                s[CURR_USER_KEY] = self.testuser_i.id

            # route = f"/users/{self.testuser_i.id}/following"
            # print('route: ', route)
            resp = client.get(f"/users/{self.testuser_i.id}/following")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn('Image for irene', html)
            self.assertIn('Image for hector', html)
            self.assertIn(
                f'<a href="/users/{self.testuser_i.id}/following"\n                >1', html)

# Check that Irene can't see who Hector follows

            resp = client.get(
                f"/users/{self.testuser_h.id}/following", follow_redirects=False)
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 302)

# Check that Irene is followed by 1

            resp = client.get(f"/users/{self.testuser_i.id}/followers")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn('Image for george', html)
            self.assertIn(
                f'<a href="/users/{self.testuser_i.id}/followers"\n                >1', html)

# Check that Hector is followed by 2

            with client.session_transaction() as s:
                s[CURR_USER_KEY] = self.testuser_h.id

            resp = client.get(f"/users/{self.testuser_h.id}/followers")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            self.assertIn('Image for george', html)
            self.assertIn('Image for irene', html)
            self.assertIn(
                f'<a href="/users/{self.testuser_h.id}/followers"\n                >2', html)

# Check that Hector can't see who follows George

            resp = client.get(
                f"/users/{self.testuser_g.id}/followers", follow_redirects=False)
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 302)

            resp = client.get(
                f"/users/{self.testuser_g.id}/followers", follow_redirects=True)
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized', html)
            # print(html)
