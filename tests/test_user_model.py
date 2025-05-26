import unittest
from app.models import User
from tests.base_test import BaseTestCase # Assuming BaseTestCase is in tests.base_test
from app import db

class TestUserModel(BaseTestCase):

    def test_password_hashing(self):
        u = User(username='testuser', email='test@example.com', role='parent')
        u.set_password('cat')
        self.assertIsNotNone(u.password_hash)
        self.assertNotEqual(u.password_hash, 'cat')

    def test_password_verification(self):
        u = User(username='susan', email='susan@example.com', role='parent')
        u.set_password('dog')
        self.assertTrue(u.check_password('dog'))
        self.assertFalse(u.check_password('cat'))

    def test_user_creation_defaults(self):
        parent = User(username='parent1', email='parent1@example.com', role='parent')
        parent.set_password('parentpass')
        db.session.add(parent)
        db.session.commit()
        
        # Test parent defaults (if any beyond what's explicitly set)
        self.assertEqual(parent.role, 'parent')

        child = User(username='child1', role='child', parent_id=parent.id)
        child.set_password('childpass') # Password is required
        db.session.add(child)
        db.session.commit()

        self.assertEqual(child.role, 'child')
        self.assertEqual(child.current_points_balance, 0)
        self.assertIsNone(child.email) # Email is nullable for children
        self.assertEqual(child.parent_id, parent.id)
        self.assertIsNotNone(child.parent)
        self.assertEqual(child.parent.username, 'parent1')


    def test_user_repr(self):
        u = User(username='john', email='john@example.com', role='parent')
        u.set_password('test')
        expected_repr = '<User john (parent)>'
        self.assertEqual(repr(u), expected_repr)

        c = User(username='jane', role='child')
        c.set_password('childtest')
        expected_child_repr = '<User jane (child)>'
        self.assertEqual(repr(c), expected_child_repr)

    def test_no_duplicate_usernames(self):
        u1 = User(username='uniqueuser', email='test1@example.com', role='parent')
        u1.set_password('test')
        db.session.add(u1)
        db.session.commit()

        u2 = User(username='uniqueuser', email='test2@example.com', role='parent')
        u2.set_password('test')
        
        # This should raise an IntegrityError or similar due to unique constraint
        # The exact error depends on the DB and SQLAlchemy version.
        # For SQLite, it's typically IntegrityError.
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            db.session.add(u2)
            db.session.commit()
        db.session.rollback() # Rollback the failed transaction

    def test_no_duplicate_emails_for_parents(self):
        # Note: Email is nullable for children, so uniqueness might only apply to parents
        # or where email is not None.
        p1 = User(username='parentA', email='unique_email@example.com', role='parent')
        p1.set_password('testA')
        db.session.add(p1)
        db.session.commit()

        p2 = User(username='parentB', email='unique_email@example.com', role='parent')
        p2.set_password('testB')
        
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            db.session.add(p2)
            db.session.commit()
        db.session.rollback()

    def test_child_parent_relationship(self):
        parent = User(username="parent_rel", email="parent_rel@example.com", role="parent")
        parent.set_password("secure")
        db.session.add(parent)
        db.session.commit()

        child1 = User(username="child_rel1", role="child", parent_id=parent.id)
        child1.set_password("childpass1")
        child2 = User(username="child_rel2", role="child", parent_id=parent.id)
        child2.set_password("childpass2")
        
        db.session.add_all([child1, child2])
        db.session.commit()

        self.assertEqual(parent.children.count(), 2)
        self.assertIn(child1, parent.children.all())
        self.assertIn(child2, parent.children.all())
        self.assertEqual(child1.parent, parent)
        self.assertEqual(child1.parent_id, parent.id)


if __name__ == '__main__':
    unittest.main()
