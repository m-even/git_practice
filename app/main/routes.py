from flask import render_template, current_app, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Chore, BehaviorLog, Reward, RewardRedemptionLog # Import all models
from app.main import bp # Import the blueprint
from datetime import datetime # Ensure datetime is imported

# --- Page Routes (Frontend Views) ---

@bp.route('/')
@bp.route('/index')
def index():
    # current_user is automatically available in templates if LoginManager is configured
    return render_template('index.html', title='Home')

@bp.route('/login', methods=['GET', 'POST']) # Renamed to login_view
def login_view():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    # For simplicity, we are not implementing WTForms here, API is primary for form handling
    # This page would ideally have a form that POSTs to /api/login
    return render_template('login.html', title='Login')

@bp.route('/register', methods=['GET', 'POST']) # Renamed to register_view
def register_view():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    # This page would ideally have a form that POSTs to /api/register
    return render_template('register.html', title='Register')

@bp.route('/logout') # Renamed to logout_view
@login_required
def logout_view():
    # The actual logout logic is handled by the API, this is just a view if needed
    # Or, it can directly call the API logout and then redirect
    logout_user() # Assuming direct logout from Flask-Login for web context
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# Parent Routes
@bp.route('/parent/dashboard')
@login_required
def parent_dashboard():
    if current_user.role != 'parent':
        flash('Access denied: Parent role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('parent_dashboard.html', title='Parent Dashboard')

@bp.route('/parent/chores')
@login_required
def parent_chores_view():
    if current_user.role != 'parent':
        flash('Access denied: Parent role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('parent_manage_chores.html', title='Manage Chores')

@bp.route('/parent/log_behavior')
@login_required
def parent_log_behavior_view():
    if current_user.role != 'parent':
        flash('Access denied: Parent role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('parent_log_behavior.html', title='Log Behavior')

@bp.route('/parent/rewards')
@login_required
def parent_rewards_view():
    if current_user.role != 'parent':
        flash('Access denied: Parent role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('parent_rewards.html', title='Manage Rewards')

@bp.route('/parent/children')
@login_required
def parent_children_view():
    if current_user.role != 'parent':
        flash('Access denied: Parent role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('parent_children.html', title='Manage Children')

@bp.route('/parent/redemptions')
@login_required
def parent_process_redemptions_view():
    if current_user.role != 'parent':
        flash('Access denied: Parent role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('parent_process_redemptions.html', title='Process Redemptions')

# Child Routes
@bp.route('/child/chores')
@login_required
def child_chores_view():
    if current_user.role != 'child':
        flash('Access denied: Child role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('child_view_chores.html', title='My Chores')

@bp.route('/child/rewards')
@login_required
def child_rewards_view():
    if current_user.role != 'child':
        flash('Access denied: Child role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('child_rewards.html', title='Available Rewards')

@bp.route('/child/history')
@login_required
def child_history_view():
    if current_user.role != 'child':
        flash('Access denied: Child role required.', 'danger')
        return redirect(url_for('main.index'))
    return render_template('child_history.html', title='My History')


# --- API Routes (Backend Logic) ---
# (Existing API routes remain below this section)

@bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'parent') # Default to 'parent' if not specified

    if not username or not password or not email:
        return jsonify({"error": "Missing username, email, or password"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    if role == 'parent':
        user = User(username=username, email=email, role='parent')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "Parent registered successfully", "user": {"username": user.username, "email": user.email, "role": user.role}}), 201
    elif role == 'child':
        # For now, we'll keep child registration simple, assuming parent_id might be passed directly
        # or handled by a parent user in a different endpoint.
        # This part can be expanded based on how child accounts are to be linked.
        # For this iteration, let's assume a child cannot self-register without a parent link established elsewhere.
        # Or, a simplified version:
        parent_username = data.get('parent_username')
        parent = None
        if parent_username:
            parent = User.query.filter_by(username=parent_username, role='parent').first()
            if not parent:
                return jsonify({"error": "Specified parent username not found or is not a parent"}), 400
        
        # For now, let's require a parent for child registration for simplicity, or make it optional
        # and let children register without a parent initially.
        # The prompt focuses on parent registration first, so this child part is a placeholder.
        # Acknowledging the prompt: "For simplicity in this step, assume parent registers first, then adds children."
        # So, direct child registration via this endpoint might be disabled or limited.
        # Let's adjust to focus on parent registration and return an error for direct child registration.
        return jsonify({"error": "Child registration should be done by a parent."}), 400
    else:
        return jsonify({"error": "Invalid role specified"}), 400


@bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    username = data.get('username') # Can be username or email
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username/email or password"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User.query.filter_by(email=username).first()

    if user and user.check_password(password):
        login_user(user) # Add 'remember=True' if you want "remember me" functionality
        return jsonify({"message": "Login successful", "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

@bp.route('/api/logout', methods=['POST']) # Changed to POST as logout modifies state
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

# Example of a protected route
@bp.route('/api/profile')
@login_required
def profile():
    return jsonify({
        "message": "This is a protected profile page.",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "points": current_user.current_points_balance if hasattr(current_user, 'current_points_balance') else None,
            "parent_id": current_user.parent_id
        }
    }), 200

@bp.route('/api/parent/add_child', methods=['POST'])
@login_required
def add_child():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can add children."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password for the child"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
    
    # Optional: Check children limit (e.g., 10)
    # For example: if current_user.children.count() >= 10:
    #     return jsonify({"error": "Maximum number of child accounts reached"}), 400

    child_user = User(
        username=username,
        role='child',
        parent_id=current_user.id
        # current_points_balance defaults to 0 as per model definition
        # email can be null for a child
    )
    child_user.set_password(password)

    db.session.add(child_user)
    db.session.commit()

    return jsonify({
        "message": "Child account created successfully",
        "child": {
            "id": child_user.id,
            "username": child_user.username,
            "role": child_user.role,
            "parent_id": child_user.parent_id
        }
    }), 201

# Helper function for chore serialization
def serialize_chore(chore, user_role="parent"):
    data = {
        "id": chore.id,
        "name": chore.name,
        "description": chore.description,
        "points_value": chore.points_value,
        "status": chore.status,
        "date_assigned": chore.date_assigned.isoformat() if chore.date_assigned else None,
        "date_due": chore.date_due.isoformat() if chore.date_due else None,
        "recurring": chore.recurring,
        "recurrence_pattern": chore.recurrence_pattern,
        "created_at": chore.created_at.isoformat(),
        "updated_at": chore.updated_at.isoformat()
    }
    if chore.assigned_child:
        data["assigned_child_username"] = chore.assigned_child.username
        data["assigned_to_child_id"] = chore.assigned_to_child_id
    else:
        data["assigned_child_username"] = None
        data["assigned_to_child_id"] = None

    if user_role == "parent":
        data["created_by_parent_id"] = chore.created_by_parent_id
        if chore.created_by_parent: # Should always exist for a parent viewing
             data["created_by_parent_username"] = chore.created_by_parent.username


    # For children, we might not want to expose created_by_parent_id directly,
    # but it's part of the model. The key is what's included in the response.
    # The current structure includes it if the role is parent.

    return data

@bp.route('/api/chores', methods=['GET']) # For parents to list chores they created
@login_required
def list_parent_chores():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can view this list."}), 403

    query = Chore.query.filter_by(created_by_parent_id=current_user.id)

    # Optional filtering
    status_filter = request.args.get('status')
    child_id_filter = request.args.get('child_id')

    if status_filter:
        query = query.filter(Chore.status == status_filter)
    
    if child_id_filter:
        try:
            child_id_int = int(child_id_filter)
            # Further check if this child_id is one of the parent's children for security
            child = User.query.filter_by(id=child_id_int, parent_id=current_user.id).first()
            if not child:
                return jsonify({"error": "Invalid child_id specified or child does not belong to this parent."}), 400
            query = query.filter(Chore.assigned_to_child_id == child_id_int)
        except ValueError:
            return jsonify({"error": "Invalid child_id format."}), 400


    chores = query.order_by(Chore.created_at.desc()).all()
    serialized_chores = [serialize_chore(chore, user_role="parent") for chore in chores]
    
    return jsonify(serialized_chores), 200

@bp.route('/api/child/chores', methods=['GET']) # For children to list their assigned chores
@login_required
def list_child_chores():
    if current_user.role != 'child':
        return jsonify({"error": "Unauthorized. Only children can view this list."}), 403

    query = Chore.query.filter_by(assigned_to_child_id=current_user.id)

    # Optional filtering by status
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter(Chore.status == status_filter)

    chores = query.order_by(Chore.date_due.asc().nulls_last(), Chore.created_at.desc()).all() # Order by due date, then creation
    
    # Use a more restricted serialization for children
    serialized_chores = [serialize_chore(chore, user_role="child") for chore in chores]

    return jsonify(serialized_chores), 200

@bp.route('/api/chores/<int:chore_id>', methods=['PUT'])
@login_required
def update_chore(chore_id):
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can update chores."}), 403

    chore = Chore.query.get_or_404(chore_id)

    if chore.created_by_parent_id != current_user.id:
        return jsonify({"error": "Forbidden. You can only update chores you created."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    # Fields that can be updated
    if 'name' in data:
        chore.name = data['name']
    if 'description' in data:
        chore.description = data['description']
    if 'points_value' in data:
        chore.points_value = data['points_value']
    
    if 'assigned_to_child_id' in data:
        new_child_id = data['assigned_to_child_id']
        if new_child_id is not None: # Assigning or changing assignment
            child = User.query.filter_by(id=new_child_id, parent_id=current_user.id).first()
            if not child:
                return jsonify({"error": "Assigned child not found or does not belong to this parent."}), 404
            if child.role != 'child':
                return jsonify({"error": "Assigned user is not a child."}), 400
            chore.assigned_to_child_id = new_child_id
            # Optionally, update status if assigning a previously unassigned chore
            if chore.status == "pending_assignment":
                 chore.status = "assigned"
        else: # Unassigning the chore
            chore.assigned_to_child_id = None
            # Optionally, update status if unassigning
            # chore.status = "pending_assignment" # Or handle as per specific app logic

    if 'date_due' in data:
        date_due_str = data['date_due']
        if date_due_str:
            try:
                chore.date_due = datetime.fromisoformat(date_due_str.replace('Z', '+00:00'))
            except ValueError:
                try:
                    chore.date_due = datetime.strptime(date_due_str, '%Y-%m-%d')
                except ValueError:
                    return jsonify({"error": "Invalid date_due format. Use YYYY-MM-DD or ISO format."}), 400
        else:
            chore.date_due = None # Allow clearing the due date

    if 'status' in data:
        # Define valid statuses to prevent arbitrary values
        valid_statuses = ["pending_assignment", "assigned", "completed_pending_approval", "approved", "overdue"]
        if data['status'] not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
        chore.status = data['status']

    if 'recurring' in data:
        chore.recurring = data['recurring']
    
    if 'recurrence_pattern' in data: # Can be updated independently or with 'recurring'
        chore.recurrence_pattern = data['recurrence_pattern']
    
    if chore.recurring and not chore.recurrence_pattern:
         return jsonify({"error": "Recurrence pattern is required for recurring chores."}), 400
    if not chore.recurring:
        chore.recurrence_pattern = None


    # updated_at is handled by onupdate=datetime.utcnow in the model
    db.session.commit()

    return jsonify(serialize_chore(chore, user_role="parent")), 200


@bp.route('/api/chores/<int:chore_id>', methods=['DELETE'])
@login_required
def delete_chore(chore_id):
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can delete chores."}), 403

    chore = Chore.query.get_or_404(chore_id)

    if chore.created_by_parent_id != current_user.id:
        return jsonify({"error": "Forbidden. You can only delete chores you created."}), 403

    db.session.delete(chore)
    db.session.commit()

    return jsonify({"message": "Chore deleted successfully"}), 200

@bp.route('/api/child/chores/<int:chore_id>/complete', methods=['PATCH'])
@login_required
def child_mark_chore_complete(chore_id):
    if current_user.role != 'child':
        return jsonify({"error": "Unauthorized. Only children can mark chores complete."}), 403

    chore = Chore.query.get_or_404(chore_id)

    if chore.assigned_to_child_id != current_user.id:
        return jsonify({"error": "Forbidden. This chore is not assigned to you."}), 403

    if chore.status != 'assigned':
        return jsonify({"error": f"Cannot mark chore complete. Current status is '{chore.status}'. Expected 'assigned'."}), 409 # Conflict

    chore.status = "completed_pending_approval"
    # chore.updated_at is handled by onupdate in the model
    db.session.commit()

    return jsonify(serialize_chore(chore, user_role="child")), 200

@bp.route('/api/parent/chores/<int:chore_id>/approve', methods=['PATCH'])
@login_required
def parent_approve_chore(chore_id):
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can approve chores."}), 403

    chore = Chore.query.get_or_404(chore_id)

    if chore.created_by_parent_id != current_user.id:
        return jsonify({"error": "Forbidden. You can only approve chores you created."}), 403

    if chore.status != 'completed_pending_approval':
        return jsonify({"error": f"Cannot approve chore. Current status is '{chore.status}'. Expected 'completed_pending_approval'."}), 409 # Conflict

    if not chore.assigned_to_child_id:
        return jsonify({"error": "Chore cannot be approved as it is not assigned to any child."}), 400
        
    child_user = User.query.get(chore.assigned_to_child_id)
    if not child_user:
        # This should ideally not happen if assigned_to_child_id is valid
        return jsonify({"error": "Assigned child not found."}), 500 
    
    if child_user.parent_id != current_user.id: # Double check child belongs to this parent
        return jsonify({"error": "Assigned child does not belong to this parent."}), 403


    chore.status = "approved"
    child_user.current_points_balance += chore.points_value
    
    # chore.updated_at is handled by onupdate in the model
    db.session.add(child_user) # Add child_user to session if it was modified
    db.session.commit()

    response_data = {
        "message": "Chore approved successfully and points awarded.",
        "chore": serialize_chore(chore, user_role="parent"),
        "child_new_balance": child_user.current_points_balance
    }
    return jsonify(response_data), 200

# Helper function for behavior log serialization
def serialize_behavior_log(log):
    return {
        "id": log.id,
        "child_id": log.child_id,
        "child_username": log.child.username if log.child else None,
        "recorded_by_parent_id": log.recorded_by_parent_id,
        "recorded_by_parent_username": log.recorded_by_parent.username if log.recorded_by_parent else None,
        "behavior_type": log.behavior_type,
        "description": log.description,
        "points_change": log.points_change,
        "timestamp": log.timestamp.isoformat(),
        "created_at": log.created_at.isoformat()
    }

@bp.route('/api/behaviors', methods=['POST'])
@login_required
def record_behavior():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can record behaviors."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    child_id = data.get('child_id')
    behavior_type = data.get('behavior_type')
    description = data.get('description')
    points_change_str = data.get('points_change') # Keep as string initially for validation

    if not all([child_id, behavior_type, description, points_change_str is not None]):
        return jsonify({"error": "Missing required fields: child_id, behavior_type, description, and points_change"}), 400

    if behavior_type not in ["positive", "negative"]:
        return jsonify({"error": "Invalid behavior_type. Must be 'positive' or 'negative'."}), 400

    try:
        points_change = int(points_change_str)
    except ValueError:
        return jsonify({"error": "Invalid points_change. Must be an integer."}), 400

    # Validate points_change sign based on behavior_type (optional, but good practice)
    # if behavior_type == "positive" and points_change < 0:
    #     return jsonify({"error": "Positive behavior should generally have non-negative points_change."}), 400
    # if behavior_type == "negative" and points_change > 0:
    #     return jsonify({"error": "Negative behavior should generally have non-positive points_change."}), 400


    child = User.query.get(child_id)
    if not child:
        return jsonify({"error": "Child not found."}), 404
    
    if child.parent_id != current_user.id:
        return jsonify({"error": "Forbidden. This child does not belong to you."}), 403
    
    if child.role != 'child':
        return jsonify({"error": "The specified user is not a child."}), 400


    behavior_log = BehaviorLog(
        child_id=child_id,
        recorded_by_parent_id=current_user.id,
        behavior_type=behavior_type,
        description=description,
        points_change=points_change
        # timestamp and created_at will use default values from the model
    )

    child.current_points_balance += points_change

    db.session.add(behavior_log)
    # child is already in session or will be added due to points change
    db.session.commit()

    return jsonify({
        "message": "Behavior recorded successfully and points updated.",
        "behavior_log": serialize_behavior_log(behavior_log),
        "child_new_balance": child.current_points_balance
    }), 201

@bp.route('/api/parent/children', methods=['GET'])
@login_required
def list_parent_children():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can view this list."}), 403
    
    children = User.query.filter_by(parent_id=current_user.id).all()
    children_data = [{"id": child.id, "username": child.username} for child in children]
    return jsonify(children_data), 200

@bp.route('/api/behaviors', methods=['GET']) # For parents to list behavior logs they recorded
@login_required
def list_parent_behavior_logs():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can view this list."}), 403

    query = BehaviorLog.query.filter_by(recorded_by_parent_id=current_user.id)

    # Optional filtering
    child_id_filter = request.args.get('child_id')
    behavior_type_filter = request.args.get('behavior_type')

    if child_id_filter:
        try:
            child_id_int = int(child_id_filter)
            # Verify the child belongs to the parent
            child = User.query.filter_by(id=child_id_int, parent_id=current_user.id).first()
            if not child:
                return jsonify({"error": "Invalid child_id specified or child does not belong to this parent."}), 400
            query = query.filter(BehaviorLog.child_id == child_id_int)
        except ValueError:
            return jsonify({"error": "Invalid child_id format."}), 400
            
    if behavior_type_filter:
        if behavior_type_filter not in ["positive", "negative"]:
            return jsonify({"error": "Invalid behavior_type. Must be 'positive' or 'negative'."}), 400
        query = query.filter(BehaviorLog.behavior_type == behavior_type_filter)

    logs = query.order_by(BehaviorLog.timestamp.desc()).all()
    serialized_logs = [serialize_behavior_log(log) for log in logs]
    
    return jsonify(serialized_logs), 200

@bp.route('/api/child/behaviorlogs', methods=['GET']) # For children to list their behavior logs
@login_required
def list_child_behavior_logs():
    if current_user.role != 'child':
        return jsonify({"error": "Unauthorized. Only children can view this list."}), 403

    query = BehaviorLog.query.filter_by(child_id=current_user.id)

    # Optional filtering by behavior_type
    behavior_type_filter = request.args.get('behavior_type')
    if behavior_type_filter:
        if behavior_type_filter not in ["positive", "negative"]:
            return jsonify({"error": "Invalid behavior_type. Must be 'positive' or 'negative'."}), 400
        query = query.filter(BehaviorLog.behavior_type == behavior_type_filter)

    logs = query.order_by(BehaviorLog.timestamp.desc()).all()
    serialized_logs = [serialize_behavior_log(log) for log in logs]

    return jsonify(serialized_logs), 200

# Helper function for reward serialization
def serialize_reward(reward, user_role="parent"): # user_role for future use if needed
    data = {
        "id": reward.id,
        "name": reward.name,
        "description": reward.description,
        "point_cost": reward.point_cost,
        "availability": reward.availability,
        "stock_quantity": reward.stock_quantity,
        "created_at": reward.created_at.isoformat(),
        "updated_at": reward.updated_at.isoformat()
    }
    if user_role == "parent": # Only parents should see who created it
        data["created_by_parent_id"] = reward.created_by_parent_id
        if reward.created_by_parent:
            data["created_by_parent_username"] = reward.created_by_parent.username
    return data

@bp.route('/api/rewards', methods=['POST'])
@login_required
def create_reward():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can create rewards."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    name = data.get('name')
    point_cost_str = data.get('point_cost')

    if not name or point_cost_str is None:
        return jsonify({"error": "Missing required fields: name and point_cost"}), 400

    try:
        point_cost = int(point_cost_str)
        if point_cost <= 0:
            raise ValueError("Point cost must be positive.")
    except ValueError:
        return jsonify({"error": "Invalid point_cost. Must be a positive integer."}), 400

    description = data.get('description')
    availability = data.get('availability', 'available')
    stock_quantity_str = data.get('stock_quantity')

    valid_availabilities = ["available", "unavailable", "limited_stock"]
    if availability not in valid_availabilities:
        return jsonify({"error": f"Invalid availability status. Must be one of: {', '.join(valid_availabilities)}"}), 400

    stock_quantity = None
    if availability == "limited_stock":
        if stock_quantity_str is None:
            return jsonify({"error": "stock_quantity is required when availability is 'limited_stock'."}), 400
        try:
            stock_quantity = int(stock_quantity_str)
            if stock_quantity < 0:
                raise ValueError("Stock quantity must be non-negative.")
        except ValueError:
            return jsonify({"error": "Invalid stock_quantity. Must be a non-negative integer."}), 400
    else:
        stock_quantity = None # Ensure it's None if not limited_stock

    new_reward = Reward(
        name=name,
        description=description,
        point_cost=point_cost,
        created_by_parent_id=current_user.id,
        availability=availability,
        stock_quantity=stock_quantity
        # created_at and updated_at will use default values from the model
    )

    db.session.add(new_reward)
    db.session.commit()

    return jsonify({
        "message": "Reward created successfully",
        "reward": serialize_reward(new_reward, user_role="parent")
    }), 201

@bp.route('/api/rewards/my', methods=['GET']) # Parent: List Own Rewards
@login_required
def list_my_rewards():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can view this list."}), 403

    rewards = Reward.query.filter_by(created_by_parent_id=current_user.id).order_by(Reward.name).all()
    return jsonify([serialize_reward(reward, user_role="parent") for reward in rewards]), 200

@bp.route('/api/rewards/<int:reward_id>', methods=['PUT']) # Parent: Update Reward
@login_required
def update_reward(reward_id):
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can update rewards."}), 403

    reward = Reward.query.get_or_404(reward_id)

    if reward.created_by_parent_id != current_user.id:
        return jsonify({"error": "Forbidden. You can only update rewards you created."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    if 'name' in data:
        reward.name = data['name']
    if 'description' in data:
        reward.description = data['description']
    
    if 'point_cost' in data:
        try:
            point_cost = int(data['point_cost'])
            if point_cost <= 0:
                raise ValueError("Point cost must be positive.")
            reward.point_cost = point_cost
        except ValueError:
            return jsonify({"error": "Invalid point_cost. Must be a positive integer."}), 400
            
    if 'availability' in data:
        valid_availabilities = ["available", "unavailable", "limited_stock"]
        if data['availability'] not in valid_availabilities:
            return jsonify({"error": f"Invalid availability status. Must be one of: {', '.join(valid_availabilities)}"}), 400
        reward.availability = data['availability']

    if 'stock_quantity' in data or reward.availability == "limited_stock":
        # If availability is set to limited_stock, stock_quantity must be provided
        # If availability is changed from limited_stock, stock_quantity might be cleared or kept
        stock_quantity_str = data.get('stock_quantity')
        if reward.availability == "limited_stock":
            if stock_quantity_str is None:
                 return jsonify({"error": "stock_quantity is required when availability is 'limited_stock'."}), 400
            try:
                stock_quantity = int(stock_quantity_str)
                if stock_quantity < 0:
                    raise ValueError("Stock quantity must be non-negative.")
                reward.stock_quantity = stock_quantity
            except ValueError:
                return jsonify({"error": "Invalid stock_quantity. Must be a non-negative integer."}), 400
        elif stock_quantity_str is not None: # Allow setting stock_quantity even if not limited_stock (might be preparing to change availability)
            try:
                reward.stock_quantity = int(stock_quantity_str)
                if reward.stock_quantity < 0:
                    raise ValueError("Stock quantity must be non-negative.")
            except ValueError:
                return jsonify({"error": "Invalid stock_quantity. Must be a non-negative integer."}), 400
        else: # If not limited_stock and no stock_quantity provided, clear it
             reward.stock_quantity = None


    # updated_at is handled by onupdate in the model
    db.session.commit()
    return jsonify(serialize_reward(reward, user_role="parent")), 200

@bp.route('/api/rewards/<int:reward_id>', methods=['DELETE']) # Parent: Delete Reward
@login_required
def delete_reward(reward_id):
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can delete rewards."}), 403

    reward = Reward.query.get_or_404(reward_id)

    if reward.created_by_parent_id != current_user.id:
        return jsonify({"error": "Forbidden. You can only delete rewards you created."}), 403

    db.session.delete(reward)
    db.session.commit()

    return jsonify({"message": "Reward deleted successfully"}), 200

@bp.route('/api/rewards/available', methods=['GET']) # All Users: List Available Rewards
@login_required
def list_available_rewards():
    query = Reward.query.filter_by(availability="available")

    if current_user.role == 'child':
        if not current_user.parent_id:
            # Child not linked to a parent, should not see any rewards or this is an error state
            return jsonify({"error": "Child account not linked to a parent."}), 400 
        query = query.filter_by(created_by_parent_id=current_user.parent_id)
    elif current_user.role == 'parent':
        # Parents see their own available rewards
        query = query.filter_by(created_by_parent_id=current_user.id)
    else: # Should not happen with current roles
        return jsonify({"error": "Unauthorized role."}), 403
        
    rewards = query.order_by(Reward.point_cost).all()
    
    # Determine user_role for serialization based on the actual current_user.role
    # The serialize_reward function hides parent_id/username for non-parents anyway.
    # For children, they are seeing their parent's rewards, so created_by_parent_id is implicit.
    # For parents, they are seeing their own.
    serialized_rewards = [serialize_reward(reward, user_role=current_user.role) for reward in rewards]
    
    return jsonify(serialized_rewards), 200

# Helper function for reward redemption log serialization
def serialize_redemption_log(log, user_role="parent"): # user_role for context
    data = {
        "id": log.id,
        "child_id": log.child_id,
        "reward_id": log.reward_id,
        "parent_id": log.parent_id, # Parent might want to see this
        "points_at_redemption": log.points_at_redemption,
        "status": log.status,
        "timestamp_requested": log.timestamp_requested.isoformat(),
        "timestamp_processed": log.timestamp_processed.isoformat() if log.timestamp_processed else None,
        "created_at": log.created_at.isoformat()
    }
    if log.child:
        data["child_username"] = log.child.username
    if log.reward:
        data["reward_name"] = log.reward.name
    if user_role == "parent" and log.parent: # May not always be needed if parent is current_user
        data["parent_username"] = log.parent.username
    return data

@bp.route('/api/child/rewards/<int:reward_id>/redeem', methods=['POST'])
@login_required
def child_request_redemption(reward_id):
    if current_user.role != 'child':
        return jsonify({"error": "Unauthorized. Only children can request rewards."}), 403

    if not current_user.parent_id:
        return jsonify({"error": "Child account not linked to a parent."}), 400

    reward = Reward.query.get(reward_id)

    if not reward:
        return jsonify({"error": "Reward not found."}), 404
    
    if reward.created_by_parent_id != current_user.parent_id:
        return jsonify({"error": "This reward is not available to you."}), 403

    if reward.availability != "available":
        return jsonify({"error": f"Reward '{reward.name}' is currently unavailable."}), 400
    
    if current_user.current_points_balance < reward.point_cost:
        return jsonify({"error": "Not enough points to redeem this reward."}), 400

    if reward.availability == "limited_stock": # This check is technically redundant if availability is 'available'
        if reward.stock_quantity is None or reward.stock_quantity <= 0:
            return jsonify({"error": f"Reward '{reward.name}' is out of stock."}), 400
    
    # Check if there's already a pending request for this reward by this child
    existing_pending_request = RewardRedemptionLog.query.filter_by(
        child_id=current_user.id,
        reward_id=reward.id,
        status="pending_approval"
    ).first()
    if existing_pending_request:
        return jsonify({"error": "You already have a pending request for this reward."}), 409


    redemption_log = RewardRedemptionLog(
        child_id=current_user.id,
        reward_id=reward.id,
        parent_id=current_user.parent_id,
        points_at_redemption=reward.point_cost,
        status="pending_approval"
        # timestamp_requested and created_at will use default values
    )

    db.session.add(redemption_log)
    db.session.commit()

    return jsonify({
        "message": "Reward redemption requested successfully. Waiting for parent approval.",
        "redemption_request": serialize_redemption_log(redemption_log, user_role="child")
    }), 201

@bp.route('/api/parent/redemptions/<int:redemption_id>/process', methods=['PATCH'])
@login_required
def parent_process_redemption(redemption_id):
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can process redemptions."}), 403

    redemption_log = RewardRedemptionLog.query.get_or_404(redemption_id)

    if redemption_log.parent_id != current_user.id:
        return jsonify({"error": "Forbidden. This redemption request is not for your child."}), 403

    if redemption_log.status != "pending_approval":
        return jsonify({"error": f"Cannot process redemption. Current status is '{redemption_log.status}'."}), 409

    data = request.get_json()
    if not data or 'action' not in data:
        return jsonify({"error": "Missing 'action' in request body."}), 400

    action = data['action'].lower()

    if action not in ["approve", "reject"]:
        return jsonify({"error": "Invalid action. Must be 'approve' or 'reject'."}), 400

    child_user = User.query.get(redemption_log.child_id)
    reward = Reward.query.get(redemption_log.reward_id)

    if not child_user or not reward:
        # Should not happen if DB integrity is maintained
        return jsonify({"error": "Child or Reward associated with this redemption not found."}), 500

    if action == "approve":
        if child_user.current_points_balance < redemption_log.points_at_redemption:
            # Child no longer has enough points, parent might reject or it's an issue to resolve
            redemption_log.status = "rejected" # Auto-reject if points are insufficient
            redemption_log.timestamp_processed = datetime.utcnow()
            db.session.commit()
            return jsonify({
                "error": "Child no longer has enough points. Redemption automatically rejected.",
                "redemption_log": serialize_redemption_log(redemption_log, user_role="parent")
            }), 409 # Conflict or Bad Request

        if reward.availability != "available":
            return jsonify({"error": f"Reward '{reward.name}' is currently unavailable."}), 400

        if reward.availability == "limited_stock":
            if reward.stock_quantity is None or reward.stock_quantity <= 0:
                return jsonify({"error": f"Reward '{reward.name}' is out of stock."}), 400
            reward.stock_quantity -= 1
        
        child_user.current_points_balance -= redemption_log.points_at_redemption
        redemption_log.status = "approved"
    
    elif action == "reject":
        redemption_log.status = "rejected"

    redemption_log.timestamp_processed = datetime.utcnow()
    
    db.session.add(child_user) # ensure changes to child are staged
    db.session.add(reward) # ensure changes to reward are staged
    db.session.commit()

    return jsonify({
        "message": f"Redemption request {action}d successfully.",
        "redemption_log": serialize_redemption_log(redemption_log, user_role="parent"),
        "child_new_balance": child_user.current_points_balance,
        "reward_new_stock": reward.stock_quantity if reward.availability == "limited_stock" else None
    }), 200

@bp.route('/api/redemptions', methods=['GET']) # For parents to list all redemption logs for their children
@login_required
def list_parent_redemption_logs():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can view this list."}), 403

    query = RewardRedemptionLog.query.filter_by(parent_id=current_user.id)
    
    status_filter = request.args.get('status')
    child_id_filter = request.args.get('child_id')

    if status_filter:
        if status_filter not in ["pending_approval", "approved", "rejected"]:
             return jsonify({"error": "Invalid status filter."}), 400
        query = query.filter(RewardRedemptionLog.status == status_filter)

    if child_id_filter:
        try:
            child_id_int = int(child_id_filter)
            # Verify the child belongs to the parent
            child = User.query.filter_by(id=child_id_int, parent_id=current_user.id).first()
            if not child:
                return jsonify({"error": "Invalid child_id specified or child does not belong to this parent."}), 400
            query = query.filter(RewardRedemptionLog.child_id == child_id_int)
        except ValueError:
            return jsonify({"error": "Invalid child_id format."}), 400

    logs = query.order_by(RewardRedemptionLog.timestamp_requested.desc()).all()
    return jsonify([serialize_redemption_log(log, user_role="parent") for log in logs]), 200

@bp.route('/api/child/redemptions', methods=['GET']) # For children to list their own redemption logs
@login_required
def list_child_redemption_logs():
    if current_user.role != 'child':
        return jsonify({"error": "Unauthorized. Only children can view this list."}), 403

    query = RewardRedemptionLog.query.filter_by(child_id=current_user.id)
    
    status_filter = request.args.get('status')
    if status_filter:
        if status_filter not in ["pending_approval", "approved", "rejected"]:
             return jsonify({"error": "Invalid status filter."}), 400
        query = query.filter(RewardRedemptionLog.status == status_filter)

    logs = query.order_by(RewardRedemptionLog.timestamp_requested.desc()).all()
    return jsonify([serialize_redemption_log(log, user_role="child") for log in logs]), 200


from datetime import datetime

@bp.route('/api/chores', methods=['POST'])
@login_required
def create_chore():
    if current_user.role != 'parent':
        return jsonify({"error": "Unauthorized. Only parents can create chores."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    name = data.get('name')
    points_value = data.get('points_value')

    if not name or points_value is None: # points_value can be 0, so check for None
        return jsonify({"error": "Missing required fields: name and points_value"}), 400

    description = data.get('description')
    assigned_to_child_id = data.get('assigned_to_child_id')
    date_due_str = data.get('date_due')
    recurring = data.get('recurring', False)
    recurrence_pattern = data.get('recurrence_pattern')

    status = "pending_assignment"
    assigned_child = None

    if assigned_to_child_id:
        child = User.query.filter_by(id=assigned_to_child_id, parent_id=current_user.id).first()
        if not child:
            return jsonify({"error": "Assigned child not found or does not belong to this parent."}), 404
        if child.role != 'child':
             return jsonify({"error": "Assigned user is not a child."}), 400
        status = "assigned"
        assigned_child = child

    if recurring and not recurrence_pattern:
        return jsonify({"error": "Recurrence pattern is required for recurring chores."}), 400
    
    if not recurring:
        recurrence_pattern = None # Ensure it's null if not recurring

    date_due = None
    if date_due_str:
        try:
            date_due = datetime.fromisoformat(date_due_str.replace('Z', '+00:00')) # Handles ISO format like YYYY-MM-DDTHH:MM:SSZ
        except ValueError:
            try:
                date_due = datetime.strptime(date_due_str, '%Y-%m-%d') # Handles YYYY-MM-DD
            except ValueError:
                 return jsonify({"error": "Invalid date_due format. Use YYYY-MM-DD or ISO format."}), 400


    new_chore = Chore(
        name=name,
        description=description,
        points_value=points_value,
        assigned_to_child_id=assigned_to_child_id,
        created_by_parent_id=current_user.id,
        date_due=date_due,
        status=status,
        recurring=recurring,
        recurrence_pattern=recurrence_pattern
        # date_assigned and created_at will use default values
    )

    db.session.add(new_chore)
    db.session.commit()

    return jsonify({
        "message": "Chore created successfully",
        "chore": {
            "id": new_chore.id,
            "name": new_chore.name,
            "description": new_chore.description,
            "points_value": new_chore.points_value,
            "assigned_to_child_id": new_chore.assigned_to_child_id,
            "created_by_parent_id": new_chore.created_by_parent_id,
            "date_assigned": new_chore.date_assigned.isoformat() if new_chore.date_assigned else None,
            "date_due": new_chore.date_due.isoformat() if new_chore.date_due else None,
            "status": new_chore.status,
            "recurring": new_chore.recurring,
            "recurrence_pattern": new_chore.recurrence_pattern,
            "created_at": new_chore.created_at.isoformat()
        }
    }), 201
