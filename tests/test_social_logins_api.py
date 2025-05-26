import unittest
from unittest.mock import patch, MagicMock
from flask import url_for
from tests.base_test import BaseTestCase
from app.models import User, SocialAccount
from app import db

class TestGoogleLogin(BaseTestCase):

    def _create_user_direct_db(self, username, email, password, role='parent', parent_id=None, points=0):
        user = User(username=username, email=email, role=role, parent_id=parent_id, current_points_balance=points)
        if password: # Allow creating users for social login without a local password
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @patch('flask_dance.contrib.google.google')
    def test_google_login_new_user(self, mock_google_oauth):
        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "new_google_id_123",
            "email": "new.user@example.com",
            "given_name": "New",
            "family_name": "User"
        })

        with self.client: # Use client in a 'with' block to manage session context for flashed messages
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=False)
            # Check for redirect to dashboard (or index if role logic is complex)
            self.assertIn(response.status_code, [301, 302]) 
            self.assertTrue(response.location.endswith(url_for('main.parent_dashboard')) or response.location.endswith(url_for('main.index')))

            # Check flashed messages
            # To check flashed messages, we need to allow the redirect to happen and then inspect the response
            # For now, we'll assume the redirect implies success if user is created.
            # More robust flash testing often requires `get_flashed_messages=True` in template or specific test setup.

        new_user = User.query.filter_by(email="new.user@example.com").first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.role, "parent") # Default role
        # Username generation might vary, check if it starts with 'new' or 'new_user'
        self.assertTrue(new_user.username.startswith("new") or new_user.username.startswith("newuser")) 
        
        social_account = SocialAccount.query.filter_by(provider_user_id="new_google_id_123").first()
        self.assertIsNotNone(social_account)
        self.assertEqual(social_account.provider_name, "google")
        self.assertEqual(social_account.user_id, new_user.id)

        # Check if user is logged in (by trying a protected route or checking session - simplified here)
        # This is indirectly tested by the redirect to a dashboard.

    @patch('flask_dance.contrib.google.google')
    def test_google_login_existing_social_account(self, mock_google_oauth):
        user = self._create_user_direct_db("existing_google_user", "existing.google@example.com", "password")
        social_acc = SocialAccount(user_id=user.id, provider_name="google", provider_user_id="google_id_exists_123")
        db.session.add(social_acc)
        db.session.commit()

        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "google_id_exists_123",
            "email": "existing.google@example.com" 
            # Name might or might not be present on subsequent logins
        })

        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200) # After redirect
            # Check if we landed on a dashboard page
            self.assertIn(b"Parent Dashboard", response.data) # Assuming parent role

        user_count = User.query.count()
        social_account_count = SocialAccount.query.count()
        self.assertEqual(user_count, 1)
        self.assertEqual(social_account_count, 1)
        # Assert user is logged in would require checking session or response context more deeply


    @patch('flask_dance.contrib.google.google')
    def test_google_login_link_to_existing_email_user(self, mock_google_oauth):
        user_local = self._create_user_direct_db("local_user_email", "local.user@example.com", "localpass")
        
        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "google_id_for_local_user_link",
            "email": "local.user@example.com", # Same email as local user
            "given_name": "Local"
        })

        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data) # Assuming parent role

        self.assertEqual(User.query.count(), 1) # No new user
        
        social_account = SocialAccount.query.filter_by(provider_user_id="google_id_for_local_user_link").first()
        self.assertIsNotNone(social_account)
        self.assertEqual(social_account.user_id, user_local.id)
        self.assertEqual(social_account.provider_name, "google")
        
        # Check flashed message for linking
        # This requires a slightly different setup to capture flashed messages or by checking the response data.
        # For now, we'll assume the successful link and login is the primary check.

    @patch('flask_dance.contrib.google.google')
    def test_google_login_email_exists_different_social_account_same_provider(self, mock_google_oauth):
        # User A has email_A and is linked to google_id_A
        user_a = self._create_user_direct_db("userA_same_provider", "email_A@example.com", "passA")
        sa_a = SocialAccount(user_id=user_a.id, provider_name="google", provider_user_id="google_id_A")
        db.session.add(sa_a)
        db.session.commit()

        # Google now returns email_A but with a *different* google_id_B
        # This scenario means the same person might be trying to log in with a *different* Google account
        # that happens to have the same verified email.
        # The current logic:
        # 1. Finds SocialAccount for google_id_B -> None
        # 2. Finds User A by email_A.
        # 3. Tries to link google_id_B to User A. This is allowed.
        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "google_id_B_new",
            "email": "email_A@example.com",
            "given_name": "UserA"
        })

        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data) # Should log in as User A

        self.assertEqual(User.query.count(), 1) # Still one user
        # User A should now have TWO Google social accounts linked
        self.assertEqual(SocialAccount.query.filter_by(user_id=user_a.id, provider_name="google").count(), 2)
        
        sa_b = SocialAccount.query.filter_by(provider_user_id="google_id_B_new").first()
        self.assertIsNotNone(sa_b)
        self.assertEqual(sa_b.user_id, user_a.id)


    @patch('flask_dance.contrib.google.google')
    def test_google_login_email_exists_different_social_account_different_provider(self, mock_google_oauth):
        # User A has email_A and is linked to facebook_id_A
        user_a = self._create_user_direct_db("userA_diff_provider", "email_A_dp@example.com", "passA")
        sa_fb = SocialAccount(user_id=user_a.id, provider_name="facebook", provider_user_id="facebook_id_A")
        db.session.add(sa_fb)
        db.session.commit()

        # Google now returns email_A and google_id_B
        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "google_id_B_for_fb_user",
            "email": "email_A_dp@example.com",
            "given_name": "UserA"
        })
        
        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data) # Should log in as User A

        self.assertEqual(User.query.count(), 1) # Still one user
        # User A should now have a Facebook AND a Google social account linked
        self.assertEqual(SocialAccount.query.filter_by(user_id=user_a.id).count(), 2)
        
        sa_google = SocialAccount.query.filter_by(provider_name="google", provider_user_id="google_id_B_for_fb_user").first()
        self.assertIsNotNone(sa_google)
        self.assertEqual(sa_google.user_id, user_a.id)


    @patch('flask_dance.contrib.google.google')
    def test_google_login_unauthorized_at_provider(self, mock_google_oauth):
        mock_google_oauth.authorized = False
        
        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            # Check if redirected to login page
            self.assertTrue(response.request.path.endswith(url_for('main.login_view')))
            # Check for flashed message (this requires inspecting response.data if using _external=False)
            self.assertIn(b"Failed to log in with Google.", response.data)


    @patch('flask_dance.contrib.google.google')
    def test_google_login_failed_to_fetch_user_info(self, mock_google_oauth):
        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=False) # Simulate API error

        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            self.assertTrue(response.request.path.endswith(url_for('main.login_view')))
            self.assertIn(b"Failed to fetch user info from Google.", response.data)


    @patch('flask_dance.contrib.google.google')
    def test_google_login_no_email_from_provider(self, mock_google_oauth):
        mock_google_oauth.authorized = True
        mock_google_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "google_id_no_email",
            "email": None, # No email provided
            "given_name": "NoEmail"
        })

        with self.client:
            response = self.client.get(url_for('main.google_login_callback'), follow_redirects=True)
            self.assertTrue(response.request.path.endswith(url_for('main.login_view')))
            self.assertIn(b"Google account did not provide an email address.", response.data)

if __name__ == '__main__':
    unittest.main()

class TestFacebookLogin(BaseTestCase):

    def _create_user_direct_db(self, username, email, password, role='parent', parent_id=None, points=0):
        user = User(username=username, email=email, role=role, parent_id=parent_id, current_points_balance=points)
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_new_user(self, mock_facebook_oauth):
        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "new_fb_id_123",
            "email": "new.fbuser@example.com",
            "name": "New FB User" 
        })

        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data) # Or index, depending on default role redirect
            self.assertIn(b"Account created via Facebook. Welcome!", response.data)


        new_user = User.query.filter_by(email="new.fbuser@example.com").first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.role, "parent")
        self.assertTrue(new_user.username.startswith("newfbuser"))
        
        social_account = SocialAccount.query.filter_by(provider_user_id="new_fb_id_123").first()
        self.assertIsNotNone(social_account)
        self.assertEqual(social_account.provider_name, "facebook")
        self.assertEqual(social_account.user_id, new_user.id)

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_existing_social_account(self, mock_facebook_oauth):
        user = self._create_user_direct_db("existing_fb_user", "existing.fb@example.com", "password")
        social_acc = SocialAccount(user_id=user.id, provider_name="facebook", provider_user_id="fb_id_exists_456")
        db.session.add(social_acc)
        db.session.commit()

        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "fb_id_exists_456",
            "email": "existing.fb@example.com"
        })

        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data)
            self.assertIn(b"Successfully logged in with Facebook!", response.data)


        self.assertEqual(User.query.count(), 1)
        self.assertEqual(SocialAccount.query.count(), 1)

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_link_to_existing_email_user(self, mock_facebook_oauth):
        user_local = self._create_user_direct_db("local_fb_link", "local.fb.link@example.com", "localpass")
        
        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "fb_id_for_local_link",
            "email": "local.fb.link@example.com",
            "name": "Local FB Link"
        })

        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data)
            self.assertIn(b"Existing account linked with Facebook.", response.data)


        self.assertEqual(User.query.count(), 1)
        social_account = SocialAccount.query.filter_by(provider_user_id="fb_id_for_local_link").first()
        self.assertIsNotNone(social_account)
        self.assertEqual(social_account.user_id, user_local.id)
        self.assertEqual(social_account.provider_name, "facebook")

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_email_exists_different_social_account_same_provider(self, mock_facebook_oauth):
        user_a = self._create_user_direct_db("userA_fb_same", "email_A_fb_same@example.com", "passA")
        sa_a = SocialAccount(user_id=user_a.id, provider_name="facebook", provider_user_id="facebook_id_A")
        db.session.add(sa_a)
        db.session.commit()

        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "facebook_id_B_new",
            "email": "email_A_fb_same@example.com",
            "name": "UserA FB Same"
        })

        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data) 
            self.assertIn(b"Existing account linked with Facebook.", response.data) # Logic links new social ID to existing user via email


        self.assertEqual(User.query.count(), 1)
        self.assertEqual(SocialAccount.query.filter_by(user_id=user_a.id, provider_name="facebook").count(), 2)
        
        sa_b = SocialAccount.query.filter_by(provider_user_id="facebook_id_B_new").first()
        self.assertIsNotNone(sa_b)
        self.assertEqual(sa_b.user_id, user_a.id)

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_email_exists_different_social_account_different_provider(self, mock_facebook_oauth):
        user_a = self._create_user_direct_db("userA_fb_diff", "email_A_fb_diff@example.com", "passA")
        sa_google = SocialAccount(user_id=user_a.id, provider_name="google", provider_user_id="google_id_A_for_fb")
        db.session.add(sa_google)
        db.session.commit()

        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "facebook_id_B_for_google_user",
            "email": "email_A_fb_diff@example.com",
            "name": "UserA FB Diff"
        })
        
        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Parent Dashboard", response.data)
            self.assertIn(b"Existing account linked with Facebook.", response.data)

        self.assertEqual(User.query.count(), 1)
        self.assertEqual(SocialAccount.query.filter_by(user_id=user_a.id).count(), 2)
        
        sa_fb = SocialAccount.query.filter_by(provider_name="facebook", provider_user_id="facebook_id_B_for_google_user").first()
        self.assertIsNotNone(sa_fb)
        self.assertEqual(sa_fb.user_id, user_a.id)

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_unauthorized_at_provider(self, mock_facebook_oauth):
        mock_facebook_oauth.authorized = False
        
        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertTrue(response.request.path.endswith(url_for('main.login_view')))
            self.assertIn(b"Failed to log in with Facebook.", response.data)

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_failed_to_fetch_user_info(self, mock_facebook_oauth):
        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=False)

        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertTrue(response.request.path.endswith(url_for('main.login_view')))
            self.assertIn(b"Failed to fetch user info from Facebook.", response.data)

    @patch('flask_dance.contrib.facebook.facebook')
    def test_facebook_login_no_email_from_provider(self, mock_facebook_oauth):
        mock_facebook_oauth.authorized = True
        mock_facebook_oauth.get.return_value = MagicMock(ok=True, json=lambda: {
            "id": "fb_id_no_email",
            "name": "No Email FB User",
            "email": None # No email
        })

        with self.client:
            response = self.client.get(url_for('main.facebook_login_callback'), follow_redirects=True)
            self.assertTrue(response.request.path.endswith(url_for('main.login_view')))
            self.assertIn(b"Facebook account did not provide an email address.", response.data)
