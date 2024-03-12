"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows

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

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        # Create George, Hector, & Irene

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

        # Set up follows:
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

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_h.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "I am Hector"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "I am Hector")

# See if Hector can see his own message

            resp = c.get("/")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            # check that we're on Hector's home page
            self.assertIn('<p>@hector</p>', html)
            self.assertIn('<p>I am Hector</p>', html)

# See if George can see Hector's message

            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_g.id
            resp = c.get("/")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            # print(html)
            # check that we're on George's home page
            self.assertIn('<p>@george</p>', html)
            self.assertIn('<p>I am Hector</p>', html)

# post message as Irene
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_i.id
            resp = c.post("/messages/new", data={"text": "I am Irene"})

# Hector shouldn't see Irene's message
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_h.id
            resp = c.get("/")
            html = resp.data.decode()
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<p>I am Irene</p>', html)
            # but should see his own
            self.assertIn('<p>I am Hector</p>', html)

# Hector try to delete his own message
            msg_id = self.testuser_h.messages[0].id
            resp = c.post(f"/messages/{msg_id}/delete")
            html = resp.data.decode()
            self.assertEqual(len(self.testuser_h.messages), 0)

# Hector try to delete Irene's
            msg_id = self.testuser_i.messages[0].id
            resp = c.post(f"/messages/{msg_id}/delete", follow_redirects=True)
            html = resp.data.decode()
            self.assertIn('Access unauthorized', html)
            self.assertEqual(len(self.testuser_i.messages), 1)

# Logout & see what works
            with c.session_transaction() as sess:
                del sess[CURR_USER_KEY]

            # try: following
            resp = c.get(
                f"/users/{self.testuser_i.id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode()
            self.assertIn('Access unauthorized', html)

            # try: followers
            resp = c.get(
                f"/users/{self.testuser_i.id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode()
            self.assertIn('Access unauthorized', html)

            # try: add a message
            resp = c.post("/messages/new",
                          data={"text": "I am Hector"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode()
            self.assertIn('Access unauthorized', html)

            # try: delete a message
            msg_id = self.testuser_i.messages[0].id
            resp = c.post(f"/messages/{msg_id}/delete", follow_redirects=True)
            html = resp.data.decode()
            self.assertIn('Access unauthorized', html)
