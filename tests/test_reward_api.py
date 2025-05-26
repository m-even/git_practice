import json
from tests.base_test import BaseTestCase
from app.models import User, Reward, RewardRedemptionLog
from app import db
from datetime import datetime

class TestRewardAPI(BaseTestCase):

    def _create_user_direct_db(self, username, email, password, role='parent', parent_id=None, points=0):
        """Helper to create user directly in DB."""
        user = User(username=username, email=email, role=role, parent_id=parent_id, current_points_balance=points)
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
        self.assertEqual(response.status_code, 200, f"Login failed in helper for user {username_or_email}")
        return self.client

    def _create_parent_and_child_users(self, parent_username="testparent_reward", child_username="testchild_reward", child_points=100):
        """Creates a parent and a child, logs in the parent."""
        parent = self._create_user_direct_db(parent_username, f'{parent_username}@example.com', 'parentpass')
        child = self._create_user_direct_db(child_username, None, 'childpass', role='child', parent_id=parent.id, points=child_points)
        self._login_user(parent_username, 'parentpass') # Parent is logged in by default
        return parent, child

    def _create_reward_api(self, client, name, point_cost, description=None, availability="available", stock_quantity=None):
        """Helper to make reward creation API call."""
        payload = {
            'name': name,
            'point_cost': point_cost,
        }
        if description is not None: payload['description'] = description
        payload['availability'] = availability
        if stock_quantity is not None: payload['stock_quantity'] = stock_quantity
        
        return client.post('/api/rewards', json=payload)

    def _request_redemption_api(self, child_client, reward_id):
        """Helper for child to request redemption."""
        return child_client.post(f'/api/child/rewards/{reward_id}/redeem')

    def _process_redemption_api(self, parent_client, redemption_id, action):
        """Helper for parent to process redemption."""
        return parent_client.patch(f'/api/parent/redemptions/{redemption_id}/process', json={'action': action})

    # 1. Parent Creates Reward
    def test_create_reward_successfully(self):
        parent, _ = self._create_parent_and_child_users() # Parent logged in
        response = self._create_reward_api(self.client, "New Bike", 500, description="A shiny new bike")
        self.assertEqual(response.status_code, 201)
        data = response.get_json()['reward']
        self.assertEqual(data['name'], "New Bike")
        self.assertEqual(data['point_cost'], 500)
        self.assertEqual(data['created_by_parent_id'], parent.id)
        reward_db = Reward.query.get(data['id'])
        self.assertIsNotNone(reward_db)
        self.assertEqual(reward_db.name, "New Bike")

    def test_create_reward_unauthorized_not_parent(self):
        _, child = self._create_parent_and_child_users() # Parent logged in initially
        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user(child.username, 'childpass') # Login as child
        
        response = self._create_reward_api(child_client, "Child's Reward", 50)
        self.assertEqual(response.status_code, 403)

    def test_create_reward_missing_fields(self):
        self._create_parent_and_child_users() # Parent logged in
        response_no_name = self._create_reward_api(self.client, None, 100)
        self.assertEqual(response_no_name.status_code, 400)
        response_no_points = self._create_reward_api(self.client, "Gift Card", None)
        self.assertEqual(response_no_points.status_code, 400)

    def test_create_reward_invalid_points(self):
        self._create_parent_and_child_users() # Parent logged in
        response_zero_points = self._create_reward_api(self.client, "Zero Point Reward", 0)
        self.assertEqual(response_zero_points.status_code, 400)
        response_neg_points = self._create_reward_api(self.client, "Negative Point Reward", -10)
        self.assertEqual(response_neg_points.status_code, 400)

    def test_create_reward_limited_stock_validation(self):
        self._create_parent_and_child_users() # Parent logged in
        # Missing stock_quantity
        response = self._create_reward_api(self.client, "Limited Item", 100, availability="limited_stock")
        self.assertEqual(response.status_code, 400)
        # Negative stock_quantity
        response_neg_stock = self._create_reward_api(self.client, "Limited Item Neg Stock", 100, availability="limited_stock", stock_quantity=-1)
        self.assertEqual(response_neg_stock.status_code, 400)
        # Valid limited stock
        response_valid_stock = self._create_reward_api(self.client, "Limited Item Valid", 100, availability="limited_stock", stock_quantity=5)
        self.assertEqual(response_valid_stock.status_code, 201)
        self.assertEqual(response_valid_stock.get_json()['reward']['stock_quantity'], 5)

    # 2. List/Manage Rewards (Parent)
    def test_list_my_rewards_parent(self):
        parent, _ = self._create_parent_and_child_users() # Parent logged in
        self._create_reward_api(self.client, "Reward Alpha", 10)
        self._create_reward_api(self.client, "Reward Beta", 20)
        
        response = self.client.get('/api/rewards/my')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(r['created_by_parent_id'] == parent.id for r in data))

    def test_update_reward_successfully(self):
        parent, _ = self._create_parent_and_child_users() # Parent logged in
        create_resp = self._create_reward_api(self.client, "Old Reward Name", 50)
        reward_id = create_resp.get_json()['reward']['id']
        
        update_payload = {'name': "New Reward Name", 'point_cost': 75, 'availability': 'unavailable'}
        response = self.client.put(f'/api/rewards/{reward_id}', json=update_payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "New Reward Name")
        self.assertEqual(data['point_cost'], 75)
        self.assertEqual(data['availability'], 'unavailable')
        reward_db = Reward.query.get(reward_id)
        self.assertEqual(reward_db.name, "New Reward Name")

    def test_update_reward_unauthorized(self):
        parent1, _ = self._create_parent_and_child_users(parent_username="parent1_upd_rew")
        create_resp = self._create_reward_api(self.client, "P1 Reward", 100)
        reward_id = create_resp.get_json()['reward']['id']
        
        self.client.post('/api/logout') # Logout parent1
        parent2 = self._create_user_direct_db("parent2_upd_rew", "p2_upd_rew@example.com", "p2pass")
        self._login_user("parent2_upd_rew", "p2pass") # Login as parent2

        response = self.client.put(f'/api/rewards/{reward_id}', json={'name': "Attempted Update"})
        self.assertIn(response.status_code, [403, 404]) # API returns 403

    def test_delete_reward_successfully(self):
        self._create_parent_and_child_users() # Parent logged in
        create_resp = self._create_reward_api(self.client, "Reward to Delete", 10)
        reward_id = create_resp.get_json()['reward']['id']
        
        response = self.client.delete(f'/api/rewards/{reward_id}')
        self.assertEqual(response.status_code, 200) # API returns 200 with message
        self.assertIsNone(Reward.query.get(reward_id))

    def test_delete_reward_unauthorized(self):
        parent1, _ = self._create_parent_and_child_users(parent_username="parent1_del_rew")
        create_resp = self._create_reward_api(self.client, "P1 Reward Del", 10)
        reward_id = create_resp.get_json()['reward']['id']

        self.client.post('/api/logout') # Logout parent1
        self._create_user_direct_db("parent2_del_rew", "p2_del_rew@example.com", "p2pass")
        self._login_user("parent2_del_rew", "p2pass") # Login as parent2

        response = self.client.delete(f'/api/rewards/{reward_id}')
        self.assertIn(response.status_code, [403, 404]) # API returns 403

    # 3. List Available Rewards (All Users)
    def test_list_available_rewards_parent_and_child(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        
        self._create_reward_api(self.client, "Available Reward 1", 50, availability="available")
        self._create_reward_api(self.client, "Unavailable Reward", 100, availability="unavailable")
        self._create_reward_api(self.client, "Available Reward 2", 25, availability="available")
        
        # Parent's view
        response_parent = self.client.get('/api/rewards/available')
        self.assertEqual(response_parent.status_code, 200)
        data_parent = response_parent.get_json()
        self.assertEqual(len(data_parent), 2)
        self.assertTrue(all(r['availability'] == "available" for r in data_parent))
        self.assertTrue(all(r['created_by_parent_id'] == parent.id for r in data_parent))

        # Child's view
        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user(child.username, 'childpass')
        response_child = child_client.get('/api/rewards/available')
        self.assertEqual(response_child.status_code, 200)
        data_child = response_child.get_json()
        self.assertEqual(len(data_child), 2)
        self.assertTrue(all(r['availability'] == "available" for r in data_child))
        self.assertTrue(all(r['created_by_parent_id'] == parent.id for r in data_child)) # Check if parent_id is included for child view, API does include it

    # 4. Child Requests Reward Redemption
    def test_child_requests_redemption_successfully(self):
        parent, child = self._create_parent_and_child_users(child_points=100) # Parent logged in
        reward_resp = self._create_reward_api(self.client, "Toy Car", 50, availability="available", stock_quantity=10)
        reward_id = reward_resp.get_json()['reward']['id']
        
        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user(child.username, 'childpass')

        response = self._request_redemption_api(child_client, reward_id)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("Redemption requested successfully", data['message'])
        log_id = data['redemption_request']['id']
        
        log_db = RewardRedemptionLog.query.get(log_id)
        self.assertIsNotNone(log_db)
        self.assertEqual(log_db.child_id, child.id)
        self.assertEqual(log_db.reward_id, reward_id)
        self.assertEqual(log_db.status, "pending_approval")
        self.assertEqual(log_db.points_at_redemption, 50)

    def test_child_requests_redemption_insufficient_points(self):
        parent, child = self._create_parent_and_child_users(child_points=10) # Parent logged in
        reward_resp = self._create_reward_api(self.client, "Big Prize", 100)
        reward_id = reward_resp.get_json()['reward']['id']
        
        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')
        
        response = self._request_redemption_api(child_client, reward_id)
        self.assertEqual(response.status_code, 400) # API returns 400
        self.assertIn("Not enough points", response.get_json()['error'])

    def test_child_requests_redemption_reward_unavailable_or_out_of_stock(self):
        parent, child = self._create_parent_and_child_users(child_points=200) # Parent logged in
        
        # Unavailable
        reward_unavail_resp = self._create_reward_api(self.client, "Unavailable Item", 50, availability="unavailable")
        reward_unavail_id = reward_unavail_resp.get_json()['reward']['id']
        
        # Out of stock
        reward_stock_resp = self._create_reward_api(self.client, "Stock Item", 50, availability="limited_stock", stock_quantity=0)
        reward_stock_id = reward_stock_resp.get_json()['reward']['id']

        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')

        response_unavail = self._request_redemption_api(child_client, reward_unavail_id)
        self.assertEqual(response_unavail.status_code, 400)
        self.assertIn("currently unavailable", response_unavail.get_json()['error'])

        response_stock = self._request_redemption_api(child_client, reward_stock_id)
        self.assertEqual(response_stock.status_code, 400)
        self.assertIn("out of stock", response_stock.get_json()['error'])

    def test_child_requests_redemption_for_other_parents_reward(self):
        parent1, child1 = self._create_parent_and_child_users(parent_username="parent1_redeem", child_username="child1_redeem", child_points=100)
        
        # Create another parent and their reward
        parent2 = self._create_user_direct_db("parent2_redeem", "p2r@example.com", "p2pass")
        self.client.post('/api/logout') # Logout parent1
        parent2_client = self._login_user("parent2_redeem", "p2pass")
        parent2_reward_resp = self._create_reward_api(parent2_client, "Parent2 Reward", 50)
        parent2_reward_id = parent2_reward_resp.get_json()['reward']['id']
        
        # Log back in as child1
        self.client.post('/api/logout')
        child1_client = self._login_user("child1_redeem", "childpass")
        
        response = self._request_redemption_api(child1_client, parent2_reward_id)
        self.assertEqual(response.status_code, 403) # API returns 403
        self.assertIn("not available to you", response.get_json()['error'])

    def test_child_requests_redemption_already_pending(self):
        parent, child = self._create_parent_and_child_users(child_points=100)
        reward_resp = self._create_reward_api(self.client, "Unique Reward", 50)
        reward_id = reward_resp.get_json()['reward']['id']

        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')

        self._request_redemption_api(child_client, reward_id) # First request
        response_second = self._request_redemption_api(child_client, reward_id) # Second request
        self.assertEqual(response_second.status_code, 409) # Conflict
        self.assertIn("already have a pending request", response_second.get_json()['error'])

    # 5. Parent Processes Reward Redemption
    def test_parent_approves_redemption_successfully(self):
        parent, child = self._create_parent_and_child_users(child_points=100) # Parent logged in by helper
        reward_resp = self._create_reward_api(self.client, "Cool Toy", 70, availability="limited_stock", stock_quantity=5)
        reward_id = reward_resp.get_json()['reward']['id']
        
        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user(child.username, 'childpass')
        req_resp = self._request_redemption_api(child_client, reward_id)
        redemption_id = req_resp.get_json()['redemption_request']['id']
        
        self.client.post('/api/logout') # Logout child
        parent_client = self._login_user(parent.username, 'parentpass') # Login as parent

        response = self._process_redemption_api(parent_client, redemption_id, "approve")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("approved successfully", data['message'])
        self.assertEqual(data['redemption_log']['status'], "approved")
        self.assertEqual(data['child_new_balance'], 30) # 100 - 70
        self.assertEqual(data['reward_new_stock'], 4)

        log_db = RewardRedemptionLog.query.get(redemption_id)
        self.assertEqual(log_db.status, "approved")
        child_db = User.query.get(child.id)
        self.assertEqual(child_db.current_points_balance, 30)
        reward_db = Reward.query.get(reward_id)
        self.assertEqual(reward_db.stock_quantity, 4)

    def test_parent_rejects_redemption_successfully(self):
        parent, child = self._create_parent_and_child_users(child_points=100)
        reward_resp = self._create_reward_api(self.client, "Ice Cream", 20, stock_quantity=10, availability="limited_stock")
        reward_id = reward_resp.get_json()['reward']['id']
        
        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')
        req_resp = self._request_redemption_api(child_client, reward_id)
        redemption_id = req_resp.get_json()['redemption_request']['id']
        
        self.client.post('/api/logout')
        parent_client = self._login_user(parent.username, 'parentpass')

        response = self._process_redemption_api(parent_client, redemption_id, "reject")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("rejected successfully", data['message'])
        self.assertEqual(data['redemption_log']['status'], "rejected")
        self.assertEqual(data['child_new_balance'], 100) # Points unchanged
        self.assertEqual(data['reward_new_stock'], 10) # Stock unchanged

        log_db = RewardRedemptionLog.query.get(redemption_id)
        self.assertEqual(log_db.status, "rejected")
        child_db = User.query.get(child.id)
        self.assertEqual(child_db.current_points_balance, 100)
        reward_db = Reward.query.get(reward_id)
        self.assertEqual(reward_db.stock_quantity, 10)

    def test_parent_processes_redemption_unauthorized(self):
        parent1, child1 = self._create_parent_and_child_users(parent_username="parent1_proc", child_username="child1_proc", child_points=50)
        reward_resp = self._create_reward_api(self.client, "P1 Reward Proc", 30)
        reward_id = reward_resp.get_json()['reward']['id']

        self.client.post('/api/logout')
        child1_client = self._login_user(child1.username, 'childpass')
        req_resp = self._request_redemption_api(child1_client, reward_id)
        redemption_id = req_resp.get_json()['redemption_request']['id']

        self.client.post('/api/logout')
        parent2 = self._create_user_direct_db("parent2_proc", "p2_proc@example.com", "p2pass")
        parent2_client = self._login_user(parent2.username, "p2pass")

        response = self._process_redemption_api(parent2_client, redemption_id, "approve")
        self.assertIn(response.status_code, [403, 404]) # API returns 403


    def test_parent_processes_redemption_invalid_status(self):
        parent, child = self._create_parent_and_child_users(child_points=50)
        reward_resp = self._create_reward_api(self.client, "Reward Invalid Status", 30)
        reward_id = reward_resp.get_json()['reward']['id']

        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')
        req_resp = self._request_redemption_api(child_client, reward_id)
        redemption_id = req_resp.get_json()['redemption_request']['id']

        # Manually approve it first
        log_db = RewardRedemptionLog.query.get(redemption_id)
        log_db.status = "approved" 
        log_db.timestamp_processed = datetime.utcnow()
        db.session.commit()

        self.client.post('/api/logout')
        parent_client = self._login_user(parent.username, 'parentpass')
        
        response = self._process_redemption_api(parent_client, redemption_id, "approve")
        self.assertEqual(response.status_code, 409) # Conflict
        self.assertIn("Current status is 'approved'", response.get_json()['error'])

    def test_parent_approves_insufficient_points_at_approval_time(self):
        parent, child = self._create_parent_and_child_users(child_points=50) # Parent logged in
        reward_resp = self._create_reward_api(self.client, "Expensive Item", 40)
        reward_id = reward_resp.get_json()['reward']['id']

        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user(child.username, 'childpass')
        req_resp = self._request_redemption_api(child_client, reward_id) # Child has 50, cost 40. Request made.
        redemption_id = req_resp.get_json()['redemption_request']['id']
        
        # Child's points decrease before parent approves
        child_db = User.query.get(child.id)
        child_db.current_points_balance = 10 # Now has 10 points
        db.session.commit()

        self.client.post('/api/logout') # Logout child
        parent_client = self._login_user(parent.username, 'parentpass') # Login as parent
        
        response = self._process_redemption_api(parent_client, redemption_id, "approve")
        self.assertEqual(response.status_code, 409) # API auto-rejects, conflict
        self.assertIn("Child no longer has enough points", response.get_json()['error'])
        log_db = RewardRedemptionLog.query.get(redemption_id)
        self.assertEqual(log_db.status, "rejected")


    def test_parent_approves_reward_unavailable_at_approval_time(self):
        parent, child = self._create_parent_and_child_users(child_points=100)
        reward_resp = self._create_reward_api(self.client, "Limited Time Offer", 50, availability="available", stock_quantity=1)
        reward_id = reward_resp.get_json()['reward']['id']

        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')
        req_resp = self._request_redemption_api(child_client, reward_id)
        redemption_id = req_resp.get_json()['redemption_request']['id']
        
        # Reward becomes unavailable/out of stock before parent approves
        reward_db = Reward.query.get(reward_id)
        reward_db.availability = "unavailable" 
        # Or reward_db.stock_quantity = 0
        db.session.commit()

        self.client.post('/api/logout')
        parent_client = self._login_user(parent.username, 'parentpass')
        
        response = self._process_redemption_api(parent_client, redemption_id, "approve")
        self.assertEqual(response.status_code, 400) # API returns 400
        self.assertIn("currently unavailable", response.get_json()['error'])
        log_db = RewardRedemptionLog.query.get(redemption_id)
        self.assertEqual(log_db.status, "pending_approval") # Status unchanged

    # 6. List Redemption Logs
    def test_list_redemption_logs_parent(self):
        parent, child1 = self._create_parent_and_child_users(child_points=100)
        child2 = self._create_user_direct_db("child_redeem2", None, "pass", role="child", parent_id=parent.id, points=100)
        
        reward1_resp = self._create_reward_api(self.client, "R1", 10)
        reward1_id = reward1_resp.get_json()['reward']['id']
        reward2_resp = self._create_reward_api(self.client, "R2", 20)
        reward2_id = reward2_resp.get_json()['reward']['id']

        # Child1 requests R1
        self.client.post('/api/logout')
        child1_client = self._login_user(child1.username, 'childpass')
        self._request_redemption_api(child1_client, reward1_id)
        
        # Child2 requests R2
        self.client.post('/api/logout')
        child2_client = self._login_user(child2.username, 'pass')
        self._request_redemption_api(child2_client, reward2_id)

        # Parent views logs
        self.client.post('/api/logout')
        parent_client = self._login_user(parent.username, 'parentpass')
        response = parent_client.get('/api/redemptions')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

        # Filter by child1
        response_child1 = parent_client.get(f'/api/redemptions?child_id={child1.id}')
        self.assertEqual(len(response_child1.get_json()), 1)
        self.assertEqual(response_child1.get_json()[0]['child_id'], child1.id)

        # Filter by status (pending)
        response_pending = parent_client.get('/api/redemptions?status=pending_approval')
        self.assertEqual(len(response_pending.get_json()), 2)

    def test_list_redemption_logs_child(self):
        parent, child = self._create_parent_and_child_users(child_points=100)
        reward1_resp = self._create_reward_api(self.client, "R1 Child", 10)
        reward1_id = reward1_resp.get_json()['reward']['id']
        
        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')
        req1_resp = self._request_redemption_api(child_client, reward1_id)
        req1_id = req1_resp.get_json()['redemption_request']['id']
        
        # Parent approves it
        self.client.post('/api/logout')
        parent_client = self._login_user(parent.username, 'parentpass')
        self._process_redemption_api(parent_client, req1_id, "approve")

        # Child views logs
        self.client.post('/api/logout')
        child_client = self._login_user(child.username, 'childpass')
        response = child_client.get('/api/child/redemptions')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], req1_id)
        self.assertEqual(data[0]['status'], "approved")

        # Filter by status
        response_approved = child_client.get('/api/child/redemptions?status=approved')
        self.assertEqual(len(response_approved.get_json()), 1)
        response_pending = child_client.get('/api/child/redemptions?status=pending_approval')
        self.assertEqual(len(response_pending.get_json()), 0)

if __name__ == '__main__':
    unittest.main()
