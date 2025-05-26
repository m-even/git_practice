import json
from tests.base_test import BaseTestCase
from app.models import User, Chore
from app import db
from datetime import datetime, timedelta

class TestChoreAPI(BaseTestCase):

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
        parent = self._create_user_direct_db('testparent_chore', 'parent_chore@example.com', 'parentpass')
        child = self._create_user_direct_db('testchild_chore', None, 'childpass', role='child', parent_id=parent.id)
        # Log in as parent
        self._login_user('testparent_chore', 'parentpass')
        return parent, child

    def _create_chore_api(self, client, name, points_value, description=None, assigned_to_child_id=None, date_due=None):
        """Helper to make chore creation API call."""
        payload = {
            'name': name,
            'points_value': points_value,
        }
        if description is not None:
            payload['description'] = description
        if assigned_to_child_id is not None:
            payload['assigned_to_child_id'] = assigned_to_child_id
        if date_due is not None: # Expects YYYY-MM-DD string
            payload['date_due'] = date_due
        return client.post('/api/chores', json=payload)

    # 1. Parent Creates Chore
    def test_create_chore_for_child_successfully(self):
        parent, child = self._create_parent_and_child_users()
        
        response = self._create_chore_api(
            self.client, "Clean Room", 10, description="Clean your room thoroughly", 
            assigned_to_child_id=child.id, date_due=(datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d')
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()['chore']
        self.assertEqual(data['name'], "Clean Room")
        self.assertEqual(data['points_value'], 10)
        self.assertEqual(data['assigned_to_child_id'], child.id)
        self.assertEqual(data['created_by_parent_id'], parent.id)
        self.assertEqual(data['status'], 'assigned')

        chore_in_db = Chore.query.get(data['id'])
        self.assertIsNotNone(chore_in_db)
        self.assertEqual(chore_in_db.name, "Clean Room")
        self.assertEqual(chore_in_db.assigned_to_child_id, child.id)
        self.assertEqual(chore_in_db.created_by_parent_id, parent.id)

    def test_create_chore_unassigned_successfully(self):
        parent, _ = self._create_parent_and_child_users() # Parent logged in
        
        response = self._create_chore_api(self.client, "Wash Dishes", 5)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()['chore']
        self.assertEqual(data['name'], "Wash Dishes")
        self.assertIsNone(data['assigned_to_child_id'])
        self.assertEqual(data['created_by_parent_id'], parent.id)
        self.assertEqual(data['status'], 'pending_assignment')

        chore_in_db = Chore.query.get(data['id'])
        self.assertIsNotNone(chore_in_db)
        self.assertEqual(chore_in_db.name, "Wash Dishes")
        self.assertIsNone(chore_in_db.assigned_to_child_id)

    def test_create_chore_unauthorized_not_parent(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        self.client.post('/api/logout') # Logout parent
        self._login_user('testchild_chore', 'childpass') # Login as child

        response = self._create_chore_api(self.client, "Child trying to create", 5)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Only parents can create chores", response.get_json()['error'])

    def test_create_chore_assign_to_other_parents_child(self):
        parent1, _ = self._create_parent_and_child_users() # parent1 logged in

        other_parent = self._create_user_direct_db('otherparent', 'other@example.com', 'otherpass')
        other_child = self._create_user_direct_db('otherchild', None, 'otherchildpass', role='child', parent_id=other_parent.id)

        response = self._create_chore_api(self.client, "Mischief Chore", 5, assigned_to_child_id=other_child.id)
        self.assertIn(response.status_code, [400, 403, 404]) # API returns 404 for child not found under this parent
        self.assertIn("Assigned child not found or does not belong to this parent", response.get_json()['error'])


    def test_create_chore_missing_fields(self):
        self._create_parent_and_child_users() # Parent logged in
        
        response_no_name = self._create_chore_api(self.client, None, 5)
        self.assertEqual(response_no_name.status_code, 400)
        self.assertIn("Missing required fields", response_no_name.get_json()['error'])

        response_no_points = self._create_chore_api(self.client, "Chore No Points", None)
        self.assertEqual(response_no_points.status_code, 400)
        self.assertIn("Missing required fields", response_no_points.get_json()['error'])

    # 2. List Chores
    def test_list_chores_as_parent(self):
        parent, child = self._create_parent_and_child_users() # parent logged in
        self._create_chore_api(self.client, "Chore 1", 10, assigned_to_child_id=child.id, status="assigned")
        self._create_chore_api(self.client, "Chore 2", 5, status="pending_assignment")
        
        # Another parent's chore
        other_parent = self._create_user_direct_db('other_parent_list', 'other_list@example.com', 'pass')
        Chore.query.delete() # Clear previous direct creations if any interfere
        db.session.commit()
        
        # Re-create and login parent to isolate client session
        parent_client = self.app.test_client()
        self._login_user('testparent_chore', 'parentpass') # Use original parent credentials

        # Create chores for the logged-in parent
        chore1_resp = self._create_chore_api(parent_client, "Parent Chore 1", 10, assigned_to_child_id=child.id)
        self.assertEqual(chore1_resp.status_code, 201)
        chore2_resp = self._create_chore_api(parent_client, "Parent Chore 2", 5)
        self.assertEqual(chore2_resp.status_code, 201)
        
        # Create chore for other_parent (not through API with current client)
        other_chore = Chore(name="Other Parent Chore", points_value=7, created_by_parent_id=other_parent.id)
        db.session.add(other_chore)
        db.session.commit()


        response = parent_client.get('/api/chores')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(c['created_by_parent_id'] == parent.id for c in data))
        self.assertNotIn("Other Parent Chore", [c['name'] for c in data])

        # Test filter by status
        response_assigned = parent_client.get('/api/chores?status=assigned')
        self.assertEqual(response_assigned.status_code, 200)
        data_assigned = response_assigned.get_json()
        self.assertEqual(len(data_assigned), 1)
        self.assertEqual(data_assigned[0]['name'], "Parent Chore 1")

        # Test filter by child_id
        response_child = parent_client.get(f'/api/chores?child_id={child.id}')
        self.assertEqual(response_child.status_code, 200)
        data_child = response_child.get_json()
        self.assertEqual(len(data_child), 1)
        self.assertEqual(data_child[0]['name'], "Parent Chore 1")


    def test_list_chores_as_child(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        
        # Create chores, assign some to this child
        chore1_resp = self._create_chore_api(self.client, "Child Chore 1", 10, assigned_to_child_id=child.id)
        self.assertEqual(chore1_resp.status_code, 201)
        chore1_id = chore1_resp.get_json()['chore']['id']
        
        self._create_chore_api(self.client, "Parent Chore Unassigned", 5) # Not for child
        
        # Chore for another child of the same parent
        child2 = self._create_user_direct_db('testchild_chore2', None, 'child2pass', role='child', parent_id=parent.id)
        self._create_chore_api(self.client, "Child 2 Chore", 8, assigned_to_child_id=child2.id)

        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user('testchild_chore', 'childpass') # Login as child

        response = child_client.get('/api/child/chores')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Child Chore 1")
        self.assertEqual(data[0]['id'], chore1_id)
        
        # Test filter by status (child marks it complete later)
        chore_db = Chore.query.get(chore1_id)
        chore_db.status = "completed_pending_approval"
        db.session.commit()
        
        response_completed = child_client.get('/api/child/chores?status=completed_pending_approval')
        self.assertEqual(response_completed.status_code, 200)
        data_completed = response_completed.get_json()
        self.assertEqual(len(data_completed), 1)
        self.assertEqual(data_completed[0]['status'], "completed_pending_approval")


    def test_list_chores_unauthorized(self):
        response = self.client.get('/api/chores') # No login
        self.assertEqual(response.status_code, 401)
        response_child = self.client.get('/api/child/chores') # No login
        self.assertEqual(response_child.status_code, 401)

    # 3. Update Chore
    def test_update_chore_successfully(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        create_response = self._create_chore_api(self.client, "Old Name", 10, assigned_to_child_id=child.id)
        chore_id = create_response.get_json()['chore']['id']

        update_payload = {
            'name': "New Name",
            'points_value': 15,
            'description': "Updated description",
            'assigned_to_child_id': None, # Unassign
            'status': 'pending_assignment'
        }
        response = self.client.put(f'/api/chores/{chore_id}', json=update_payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "New Name")
        self.assertEqual(data['points_value'], 15)
        self.assertIsNone(data['assigned_to_child_id'])
        self.assertEqual(data['status'], 'pending_assignment')

        chore_db = Chore.query.get(chore_id)
        self.assertEqual(chore_db.name, "New Name")
        self.assertIsNone(chore_db.assigned_to_child_id)

    def test_update_chore_unauthorized_not_owner(self):
        parent1, child1 = self._create_parent_and_child_users() # parent1 logged in
        chore_resp = self._create_chore_api(self.client, "P1 Chore", 10, assigned_to_child_id=child1.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        self.client.post('/api/logout') # Logout parent1

        parent2 = self._create_user_direct_db('parent2_update', 'p2update@example.com', 'p2pass')
        self._login_user('parent2_update', 'p2pass') # Login as parent2

        response = self.client.put(f'/api/chores/{chore_id}', json={'name': "Attempted Update"})
        self.assertEqual(response.status_code, 403) # Or 404 if chore not found for this parent

    def test_update_chore_assign_to_other_parents_child(self):
        parent1, _ = self._create_parent_and_child_users() # parent1 logged in
        chore_resp = self._create_chore_api(self.client, "P1 Chore To Reassign", 10)
        chore_id = chore_resp.get_json()['chore']['id']

        other_parent = self._create_user_direct_db('otherparent_update', 'other_up@example.com', 'otherpass')
        other_child = self._create_user_direct_db('otherchild_update', None, 'otherchildpass_up', role='child', parent_id=other_parent.id)

        response = self.client.put(f'/api/chores/{chore_id}', json={'assigned_to_child_id': other_child.id})
        self.assertIn(response.status_code, [400, 403, 404])
        self.assertIn("Assigned child not found or does not belong to this parent", response.get_json()['error'])


    # 4. Delete Chore
    def test_delete_chore_successfully(self):
        parent, _ = self._create_parent_and_child_users() # Parent logged in
        create_response = self._create_chore_api(self.client, "To Be Deleted", 5)
        chore_id = create_response.get_json()['chore']['id']
        
        response = self.client.delete(f'/api/chores/{chore_id}')
        self.assertEqual(response.status_code, 200) # API returns 200 with message
        self.assertIn("Chore deleted successfully", response.get_json()['message'])
        self.assertIsNone(Chore.query.get(chore_id))

    def test_delete_chore_unauthorized_not_owner(self):
        parent1, child1 = self._create_parent_and_child_users() # parent1 logged in
        chore_resp = self._create_chore_api(self.client, "P1 Chore Del", 10)
        chore_id = chore_resp.get_json()['chore']['id']
        
        self.client.post('/api/logout') # Logout parent1

        self._create_user_direct_db('parent2_delete', 'p2delete@example.com', 'p2pass')
        self._login_user('parent2_delete', 'p2pass') # Login as parent2

        response = self.client.delete(f'/api/chores/{chore_id}')
        self.assertEqual(response.status_code, 403) # Or 404

    # 5. Child Marks Chore Complete
    def test_child_marks_chore_complete_successfully(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        chore_resp = self._create_chore_api(self.client, "Child Task", 10, assigned_to_child_id=child.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user('testchild_chore', 'childpass') # Login as child

        response = child_client.patch(f'/api/child/chores/{chore_id}/complete')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'completed_pending_approval')
        
        chore_db = Chore.query.get(chore_id)
        self.assertEqual(chore_db.status, 'completed_pending_approval')

    def test_child_marks_chore_complete_not_assigned_to_them(self):
        parent, child1 = self._create_parent_and_child_users() # Parent logged in
        child2 = self._create_user_direct_db('other_child_complete', None, 'pass', role='child', parent_id=parent.id)
        
        chore_resp = self._create_chore_api(self.client, "Task for Child2", 10, assigned_to_child_id=child2.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        self.client.post('/api/logout') # Logout parent
        child1_client = self._login_user('testchild_chore', 'childpass') # Login as child1

        response = child1_client.patch(f'/api/child/chores/{chore_id}/complete') # child1 tries to complete child2's chore
        self.assertEqual(response.status_code, 403)

    def test_child_marks_chore_complete_wrong_status(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        chore_resp = self._create_chore_api(self.client, "Child Task Wrong Status", 10, assigned_to_child_id=child.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        chore_db = Chore.query.get(chore_id)
        chore_db.status = 'pending_assignment' # Not 'assigned'
        db.session.commit()

        self.client.post('/api/logout') # Logout parent
        child_client = self._login_user('testchild_chore', 'childpass') # Login as child

        response = child_client.patch(f'/api/child/chores/{chore_id}/complete')
        self.assertEqual(response.status_code, 409) # Conflict
        self.assertIn("Expected 'assigned'", response.get_json()['error'])


    # 6. Parent Approves Chore
    def test_parent_approves_chore_successfully(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        initial_points = child.current_points_balance
        chore_points = 15
        
        chore_resp = self._create_chore_api(self.client, "Task to Approve", chore_points, assigned_to_child_id=child.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        chore_db = Chore.query.get(chore_id)
        chore_db.status = 'completed_pending_approval' # Simulate child marked it
        db.session.commit()

        response = self.client.patch(f'/api/parent/chores/{chore_id}/approve')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['chore']['status'], 'approved')
        self.assertEqual(data['child_new_balance'], initial_points + chore_points)
        
        chore_db = Chore.query.get(chore_id)
        self.assertEqual(chore_db.status, 'approved')
        child_db = User.query.get(child.id)
        self.assertEqual(child_db.current_points_balance, initial_points + chore_points)

    def test_parent_approves_chore_unauthorized_not_owner(self):
        parent1, child1 = self._create_parent_and_child_users() # parent1 logged in
        chore_resp = self._create_chore_api(self.client, "P1 Chore to Approve", 10, assigned_to_child_id=child1.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        chore_db = Chore.query.get(chore_id)
        chore_db.status = 'completed_pending_approval'
        db.session.commit()

        self.client.post('/api/logout') # Logout parent1

        self._create_user_direct_db('parent2_approve', 'p2approve@example.com', 'p2pass')
        self._login_user('parent2_approve', 'p2pass') # Login as parent2

        response = self.client.patch(f'/api/parent/chores/{chore_id}/approve')
        self.assertEqual(response.status_code, 403) # Or 404


    def test_parent_approves_chore_wrong_status(self):
        parent, child = self._create_parent_and_child_users() # Parent logged in
        chore_resp = self._create_chore_api(self.client, "Task Wrong Status Approve", 10, assigned_to_child_id=child.id)
        chore_id = chore_resp.get_json()['chore']['id']
        
        # Chore status is 'assigned', not 'completed_pending_approval'
        response = self.client.patch(f'/api/parent/chores/{chore_id}/approve')
        self.assertEqual(response.status_code, 409) # Conflict
        self.assertIn("Expected 'completed_pending_approval'", response.get_json()['error'])

    def test_parent_approves_unassigned_chore(self):
        parent, _ = self._create_parent_and_child_users() # Parent logged in
        chore_resp = self._create_chore_api(self.client, "Unassigned Task Approve", 10) # Not assigned
        chore_id = chore_resp.get_json()['chore']['id']
        
        chore_db = Chore.query.get(chore_id)
        chore_db.status = 'completed_pending_approval' # Manually set for testing this edge case
        db.session.commit()
        
        response = self.client.patch(f'/api/parent/chores/{chore_id}/approve')
        self.assertEqual(response.status_code, 400)
        self.assertIn("not assigned to any child", response.get_json()['error'])

if __name__ == '__main__':
    unittest.main()
