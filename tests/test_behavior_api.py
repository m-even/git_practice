import json
from tests.base_test import BaseTestCase
from app.models import User, BehaviorLog
from app import db

class TestBehaviorAPI(BaseTestCase):

    def _create_user_direct_db(self, username, email, password, role='parent', parent_id=None):
        """Helper to create user directly in DB."""
        user = User(username=username, email=email, role=role, parent_id=parent_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def _login_user(self, username_or_email, password):
        """Helper to log in a user via API and return the client."""
        response = self.client.post('/api/login', json={
            'username': username_or_email,
            'password': password
        })
        self.assertEqual(response.status_code, 200, "Login failed in helper")
        return self.client # Return client with session cookie

    def _create_parent_and_child_users(self):
        """Creates a parent and a child, logs in the parent."""
        parent = self._create_user_direct_db('testparent_behavior', 'parent_behavior@example.com', 'parentpass')
        child = self._create_user_direct_db('testchild_behavior', None, 'childpass', role='child', parent_id=parent.id)
        # Log in as parent
        self._login_user('testparent_behavior', 'parentpass')
        return parent, child

    def _log_behavior_api(self, client, child_id, behavior_type, description, points_change):
        """Helper to make behavior logging API call."""
        payload = {
            'child_id': child_id,
            'behavior_type': behavior_type,
            'description': description,
            'points_change': points_change
        }
        return client.post('/api/behaviors', json=payload)

    # 1. Parent Logs Behavior
    def test_log_behavior_successfully(self):
        parent, child = self._create_parent_and_child_users()
        initial_points = child.current_points_balance

        # Positive behavior
        response_positive = self._log_behavior_api(self.client, child.id, "positive", "Helped with groceries", 5)
        self.assertEqual(response_positive.status_code, 201)
        data_positive = response_positive.get_json()
        self.assertIn("Behavior recorded successfully", data_positive['message'])
        self.assertEqual(data_positive['behavior_log']['description'], "Helped with groceries")
        self.assertEqual(data_positive['behavior_log']['points_change'], 5)
        self.assertEqual(data_positive['child_new_balance'], initial_points + 5)

        log_positive_db = BehaviorLog.query.filter_by(description="Helped with groceries").first()
        self.assertIsNotNone(log_positive_db)
        self.assertEqual(log_positive_db.child_id, child.id)
        self.assertEqual(log_positive_db.recorded_by_parent_id, parent.id)
        self.assertEqual(log_positive_db.points_change, 5)
        
        child_updated = User.query.get(child.id)
        self.assertEqual(child_updated.current_points_balance, initial_points + 5)

        # Negative behavior
        response_negative = self._log_behavior_api(self.client, child.id, "negative", "Didn't do homework", -3)
        self.assertEqual(response_negative.status_code, 201)
        data_negative = response_negative.get_json()
        self.assertIn("Behavior recorded successfully", data_negative['message'])
        self.assertEqual(data_negative['behavior_log']['description'], "Didn't do homework")
        self.assertEqual(data_negative['behavior_log']['points_change'], -3)
        self.assertEqual(data_negative['child_new_balance'], initial_points + 5 - 3)

        log_negative_db = BehaviorLog.query.filter_by(description="Didn't do homework").first()
        self.assertIsNotNone(log_negative_db)
        self.assertEqual(log_negative_db.points_change, -3)

        child_further_updated = User.query.get(child.id)
        self.assertEqual(child_further_updated.current_points_balance, initial_points + 2)

    def test_log_behavior_unauthorized_not_parent(self):
        _, child = self._create_parent_and_child_users() # Parent logged in initially
        self.client.post('/api/logout') # Logout parent
        self._login_user('testchild_behavior', 'childpass') # Login as child

        response = self._log_behavior_api(self.client, child.id, "positive", "Child trying to log", 5)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Only parents can record behaviors", response.get_json()['error'])

    def test_log_behavior_for_other_parents_child(self):
        parent1, _ = self._create_parent_and_child_users() # parent1 logged in

        other_parent = self._create_user_direct_db('otherparent_bh', 'other_bh@example.com', 'otherpass')
        other_child = self._create_user_direct_db('otherchild_bh', None, 'otherchildpass_bh', role='child', parent_id=other_parent.id)

        response = self._log_behavior_api(self.client, other_child.id, "positive", "Good deed for other child", 5)
        self.assertEqual(response.status_code, 403) # API returns 403 if child doesn't belong to parent
        self.assertIn("This child does not belong to you", response.get_json()['error'])
        
    def test_log_behavior_for_non_child_user(self):
        parent, _ = self._create_parent_and_child_users() # parent logged in
        
        # Attempt to log behavior for another parent
        another_parent = self._create_user_direct_db('another_parent_target', 'ap_target@example.com', 'pass')
        
        response = self._log_behavior_api(self.client, another_parent.id, "positive", "Logging for another parent", 5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("The specified user is not a child", response.get_json()['error'])


    def test_log_behavior_missing_fields(self):
        parent, child = self._create_parent_and_child_users()
        
        # Missing child_id
        response = self._log_behavior_api(self.client, None, "positive", "Desc", 5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required fields", response.get_json()['error'])

        # Missing behavior_type
        response = self._log_behavior_api(self.client, child.id, None, "Desc", 5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required fields", response.get_json()['error'])

        # Missing description
        response = self._log_behavior_api(self.client, child.id, "positive", None, 5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required fields", response.get_json()['error'])

        # Missing points_change
        response = self._log_behavior_api(self.client, child.id, "positive", "Desc", None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required fields", response.get_json()['error'])

    def test_log_behavior_invalid_type(self):
        _, child = self._create_parent_and_child_users()
        response = self._log_behavior_api(self.client, child.id, "neutral", "Neutral behavior", 0)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid behavior_type", response.get_json()['error'])

    def test_log_behavior_invalid_points(self):
        _, child = self._create_parent_and_child_users()
        response = self._log_behavior_api(self.client, child.id, "positive", "Invalid points", "five")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid points_change. Must be an integer", response.get_json()['error'])

    # 2. List Behavior Logs
    def test_list_behavior_logs_as_parent(self):
        parent, child = self._create_parent_and_child_users()
        child2 = self._create_user_direct_db('child_bh_2', None, 'pass', role='child', parent_id=parent.id)

        self._log_behavior_api(self.client, child.id, "positive", "Log 1 for child 1", 5)
        self._log_behavior_api(self.client, child.id, "negative", "Log 2 for child 1", -2)
        self._log_behavior_api(self.client, child2.id, "positive", "Log 3 for child 2", 3)
        
        # Log for another parent (should not appear)
        other_parent = self._create_user_direct_db('other_parent_list_bh', 'oplb@example.com', 'pass')
        other_child_of_other_parent = self._create_user_direct_db('other_child_oplb', None, 'pass', role='child', parent_id=other_parent.id)
        # Need to login as other_parent to log behavior for their child
        self.client.post('/api/logout')
        other_client = self._login_user('other_parent_list_bh', 'pass')
        self._log_behavior_api(other_client, other_child_of_other_parent.id, "positive", "Other parent log", 10)
        
        # Log back in as original parent
        self.client.post('/api/logout')
        self._login_user('testparent_behavior', 'parentpass')


        response = self.client.get('/api/behaviors')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 3) # Should only see logs recorded by testparent_behavior
        self.assertTrue(all(log['recorded_by_parent_id'] == parent.id for log in data))

        # Test filter by child_id
        response_child1 = self.client.get(f'/api/behaviors?child_id={child.id}')
        self.assertEqual(response_child1.status_code, 200)
        data_child1 = response_child1.get_json()
        self.assertEqual(len(data_child1), 2)
        self.assertTrue(all(log['child_id'] == child.id for log in data_child1))

        # Test filter by behavior_type
        response_positive = self.client.get('/api/behaviors?behavior_type=positive')
        self.assertEqual(response_positive.status_code, 200)
        data_positive = response_positive.get_json()
        self.assertEqual(len(data_positive), 2) # Log 1 and Log 3
        self.assertTrue(all(log['behavior_type'] == 'positive' for log in data_positive))

    def test_list_behavior_logs_as_child(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        self._log_behavior_api(self.client, child.id, "positive", "Good job", 5)
        self._log_behavior_api(self.client, child.id, "negative", "Room messy", -3)
        
        # Log for another child of the same parent (should not appear for 'child')
        child2 = self._create_user_direct_db('child_bh_list2', None, 'pass2', role='child', parent_id=parent.id)
        self._log_behavior_api(self.client, child2.id, "positive", "Child 2 good", 4)

        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user('testchild_behavior', 'childpass') # Login as child

        response = child_client.get('/api/child/behaviorlogs')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(log['child_id'] == child.id for log in data))
        
        # Test filter by behavior_type
        response_negative = child_client.get('/api/child/behaviorlogs?behavior_type=negative')
        self.assertEqual(response_negative.status_code, 200)
        data_negative = response_negative.get_json()
        self.assertEqual(len(data_negative), 1)
        self.assertEqual(data_negative[0]['description'], "Room messy")

    def test_list_behavior_logs_unauthorized(self):
        response_parent = self.client.get('/api/behaviors') # No login
        self.assertEqual(response_parent.status_code, 401)
        
        response_child = self.client.get('/api/child/behaviorlogs') # No login
        self.assertEqual(response_child.status_code, 401)

if __name__ == '__main__':
    unittest.main()
