from flask_login import UserMixin
from app import db, login_manager
import bcrypt

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True) # Nullable for children
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='child') # e.g., "parent", "child"
    
    # For children, to link to their parent
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    children = db.relationship('User',
                               backref=db.backref('parent', remote_side=[id]),
                               lazy='dynamic')
    
    # For child users
    current_points_balance = db.Column(db.Integer, default=0)

    def set_password(self, password):
        # Hash the password using bcrypt and store it
        # The password needs to be encoded to bytes before hashing
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        # Decode back to string to store in the database
        self.password_hash = hashed_password.decode('utf-8')

    def check_password(self, password):
        # Check a given password against the stored hash
        # Encode the stored hash and the provided password to bytes
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

from datetime import datetime

class Chore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    points_value = db.Column(db.Integer, nullable=False, default=0)
    
    assigned_to_child_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by_parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    date_assigned = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    date_due = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(30), nullable=False, default="pending_assignment") 
    # Possible statuses: "pending_assignment", "assigned", "completed_pending_approval", "approved", "overdue"

    recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50), nullable=True) # e.g., "daily", "weekly_monday"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_child = db.relationship('User', foreign_keys=[assigned_to_child_id], backref=db.backref('assigned_chores', lazy='dynamic'))
    created_by_parent = db.relationship('User', foreign_keys=[created_by_parent_id], backref=db.backref('created_chores', lazy='dynamic'))

    def __repr__(self):
        return f'<Chore {self.name} - Status: {self.status}>'

class BehaviorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recorded_by_parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    behavior_type = db.Column(db.String(30), nullable=False) # e.g., "positive", "negative"
    description = db.Column(db.Text, nullable=False)
    points_change = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Specific time of behavior if different from record time
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Time of recording

    # Relationships
    child = db.relationship('User', foreign_keys=[child_id], backref=db.backref('behavior_logs', lazy='dynamic'))
    recorded_by_parent = db.relationship('User', foreign_keys=[recorded_by_parent_id], backref=db.backref('recorded_behaviors', lazy='dynamic'))

    def __repr__(self):
        return f'<BehaviorLog {self.id} - Child {self.child_id} - Type {self.behavior_type} - Points {self.points_change}>'

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    point_cost = db.Column(db.Integer, nullable=False) # Validated as positive in routes
    
    created_by_parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    availability = db.Column(db.String(50), nullable=False, default="available") 
    # e.g., "available", "unavailable", "limited_stock"
    
    stock_quantity = db.Column(db.Integer, nullable=True) # Relevant if availability is "limited_stock"
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    created_by_parent = db.relationship('User', foreign_keys=[created_by_parent_id], backref=db.backref('created_rewards', lazy='dynamic'))
    
    # Potentially, a relationship to track claimed rewards by children
    # claimed_by_children = db.relationship('User', secondary='reward_claims', backref=db.backref('claimed_rewards', lazy='dynamic'))
    # This would require a secondary association table 'reward_claims'. For now, keeping it simple as per task.

    def __repr__(self):
        return f'<Reward {self.name} - Cost: {self.point_cost}>'
