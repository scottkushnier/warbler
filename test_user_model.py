"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


from app import app
import os
from unittest import TestCase
from sqlalchemy import exc

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


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

        # test repr, id # will be unknown, but repr will start with '<User' & end with 'testuser, test@test.com>'
        repr = u.__repr__()
        self.assertEqual(repr[0:6], '<User ')
        self.assertEqual(repr[-24:], 'testuser, test@test.com>')

        # test following
        u2 = User(
            email="test2@test.com",
            username="testuser2",
            password="HASHED_PASSWORD"
        )
        u3 = User(
            email="test3@test.com",
            username="testuser3",
            password="HASHED_PASSWORD"
        )
        db.session.add(u2)
        db.session.add(u3)
        db.session.commit()
        follow = Follows(user_being_followed_id=u2.id, user_following_id=u.id)
        db.session.add(follow)
        db.session.commit()
        follows = u.following
        self.assertEqual(follows[0].username, 'testuser2')
        self.assertEqual(len(follows), 1)
        followers = u2.followers
        self.assertEqual(followers[0].username, 'testuser')
        self.assertEqual(len(followers), 1)

        self.assertTrue(u.is_following(u2))
        self.assertFalse(u.is_following(u3))
        self.assertTrue(u2.is_followed_by(u))
        self.assertFalse(u.is_followed_by(u2))

        u4 = User.signup(username="GeorgeFoo", email="foo@foo.com", password="abc123", image_url="")
        db.session.commit()
        self.assertIsInstance(u4, User)

        User.signup(username="FrankFoo", 
                    email=None, password="abc123", image_url="")
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
        db.session.rollback()

        User.signup(username="SimonFoo", 
                    email="foo@foo.com", password="abc123", image_url="")
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
        db.session.rollback()

        auth_user = User.authenticate("GeorgeFoo", "abc123")
        self.assertIsInstance(auth_user, User)
        self.assertEqual(auth_user.username, "GeorgeFoo") 
        self.assertEqual(auth_user.email, "foo@foo.com") 

        bad_user = User.authenticate("GeorgeFoo", "tryme")
        self.assertFalse(bad_user)

        bad_user = User.authenticate("PaulFoo", "abc123")
        self.assertFalse(bad_user)

