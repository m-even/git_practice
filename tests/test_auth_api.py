import json
from tests.base_test import BaseTestCase
from app.models import User
from app import db

class TestAuthAPI(BaseTestCase):

    def _register_user(self, username, email, password, role="parent"):
        """Helper function to register a user via API."""
        return self.client.post('/api/register', json={
            'username': username,
            'email': email,
            'password': password,
            'role': role
        })

    def _login_user(self, username_or_email, password):
        """Helper function to log in a user via API."""
        return self.client.post('/api/login', json={
            'username': username_or_email,
            'password': password
        })

    def _create_user_direct_db(self, username, email, password, role='parent', parent_id=None):
        """Helper function to create a user directly in the DB for setup."""
        user = User(username=username, email=email, role=role, parent_id=parent_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    # 1. Test Parent Registration
    def test_register_parent_successfully(self):
        response = self._register_user('testparent1', 'parent1@example.com', 'password123')
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('Parent registered successfully', data['message'])
        self.assertEqual(data['user']['username'], 'testparent1')
        self.assertEqual(data['user']['role'], 'parent')

        user = User.query.filter_by(username='testparent1').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'parent1@example.com')
        self.assertEqual(user.role, 'parent')
        self.assertTrue(user.check_password('password123'))

    # 2. Test Parent Registration - Duplicate Username
    def test_register_parent_duplicate_username(self):
        self._create_user_direct_db('existinguser', 'existing@example.com', 'password')
        response = self._register_user('existinguser', 'newemail@example.com', 'newpassword')
        self.assertIn(response.status_code, [400, 409]) # API returns 409
        data = response.get_json()
        self.assertIn('Username already exists', data['error'])

    def test_register_parent_duplicate_email(self):
        self._create_user_direct_db('anotheruser', 'existingemail@example.com', 'password')
        response = self._register_user('newuser', 'existingemail@example.com', 'newpassword')
        self.assertIn(response.status_code, [400, 409]) # API returns 409
        data = response.get_json()
        self.assertIn('Email already exists', data['error'])


    # 3. Test Parent Registration - Missing Fields
    def test_register_parent_missing_fields(self):
        # Missing username
        response = self._register_user(None, 'missing@example.com', 'password123')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing username, email, or password', response.get_json()['error'])
        
        # Missing email
        response = self._register_user('testparent2', None, 'password123')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing username, email, or password', response.get_json()['error'])

        # Missing password
        response = self._register_user('testparent3', 'parent3@example.com', None)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing username, email, or password', response.get_json()['error'])

    # 4. Test Login Successfully
    def test_login_successfully(self):
        self._create_user_direct_db('loginuser', 'login@example.com', 'testpass')
        
        response = self._login_user('loginuser', 'testpass')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Login successful', data['message'])
        self.assertEqual(data['user']['username'], 'loginuser')
        self.assertEqual(data['user']['role'], 'parent') # Default role in helper

        # Check for session cookie (name depends on Flask-Login config, often 'session')
        self.assertTrue(any(cookie.name == 'session' for cookie in self.client.cookie_jar))

    def test_login_successfully_with_email(self):
        self._create_user_direct_db('loginuser_email', 'login_email@example.com', 'testpass_email')
        
        response = self._login_user('login_email@example.com', 'testpass_email')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Login successful', data['message'])
        self.assertEqual(data['user']['username'], 'loginuser_email')

    # 5. Test Login - Invalid Credentials
    def test_login_invalid_credentials(self):
        self._create_user_direct_db('authuser', 'auth@example.com', 'correctpassword')

        # Valid username, incorrect password
        response = self._login_user('authuser', 'wrongpassword')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid credentials', response.get_json()['error'])

        # Non-existent username
        response = self._login_user('nosuchuser', 'anypassword')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid credentials', response.get_json()['error'])

    # 6. Test Logout
    def test_logout_successfully(self):
        self._create_user_direct_db('logoutuser', 'logout@example.com', 'logoutpass')
        login_response = self._login_user('logoutuser', 'logoutpass')
        self.assertEqual(login_response.status_code, 200) # Ensure login first

        logout_response = self.client.post('/api/logout') # API uses POST
        self.assertEqual(logout_response.status_code, 200)
        self.assertIn('Logout successful', logout_response.get_json()['message'])

        # Try accessing a protected route
        profile_response = self.client.get('/api/profile')
        self.assertEqual(profile_response.status_code, 401) # Unauthorized

    # 7. Test Create Child Account Successfully
    def test_create_child_successfully(self):
        # Register and log in parent
        self._register_user('parentforchild', 'parentforchild@example.com', 'parentpass')
        login_response = self._login_user('parentforchild', 'parentpass')
        self.assertEqual(login_response.status_code, 200)

        # Create child
        response = self.client.post('/api/parent/add_child', json={
            'username': 'testchild1',
            'password': 'childpassword'
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('Child account created successfully', data['message'])
        self.assertEqual(data['child']['username'], 'testchild1')
        
        child_user = User.query.filter_by(username='testchild1').first()
        self.assertIsNotNone(child_user)
        self.assertEqual(child_user.role, 'child')
        self.assertEqual(child_user.current_points_balance, 0)
        parent_user = User.query.filter_by(username='parentforchild').first()
        self.assertEqual(child_user.parent_id, parent_user.id)

    # 8. Test Create Child Account - Unauthorized
    def test_create_child_unauthorized(self):
        # Not logged in
        response = self.client.post('/api/parent/add_child', json={
            'username': 'child_no_auth', 'password': 'password'
        })
        self.assertEqual(response.status_code, 401) # Expect redirect to login or 401 for API

        # Logged in as child (cannot create other children)
        parent = self._create_user_direct_db('parent_for_child_test', 'p_child_test@example.com', 'test')
        child_actor = self._create_user_direct_db('child_actor', None, 'childpass', role='child', parent_id=parent.id)
        
        self._login_user('child_actor', 'childpass') # Log in as child_actor
        
        response_child_creates = self.client.post('/api/parent/add_child', json={
            'username': 'another_child', 'password': 'password'
        })
        self.assertEqual(response_child_creates.status_code, 403) # Forbidden

    # 9. Test Create Child Account - Duplicate Child Username
    def test_create_child_duplicate_username(self):
        # Register and log in parent
        self._register_user('parent_dup_child', 'p_dup_child@example.com', 'parentpass')
        login_response = self._login_user('parent_dup_child', 'parentpass')
        self.assertEqual(login_response.status_code, 200)

        # Create first child
        self.client.post('/api/parent/add_child', json={
            'username': 'duplicatechild', 'password': 'password1'
        }) # Assume 201

        # Attempt to create second child with same username
        response = self.client.post('/api/parent/add_child', json={
            'username': 'duplicatechild', 'password': 'password2'
        })
        self.assertIn(response.status_code, [400, 409]) # API returns 409
        data = response.get_json()
        self.assertIn('Username already exists', data['error'])

if __name__ == '__main__':
    unittest.main()
