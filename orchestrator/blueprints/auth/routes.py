"""
Authentication Blueprint - Handles user authentication and JWT tokens
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from orchestrator.database import db
from orchestrator.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint with database authentication
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    username_or_email = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username_or_email or not password:
        return jsonify({'success': False, 'message': 'Username/email and password required'}), 400
    
    # Find user by username or email
    user = User.query.filter(
        db.or_(
            User.username == username_or_email,
            User.email == username_or_email
        )
    ).first()
    
    if not user or not user.check_password(password):
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401
    
    if not user.is_active:
        return jsonify({
            'success': False,
            'message': 'Account is disabled'
        }), 403
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Create tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    # Validate input
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    if len(password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
    
    # Check if user exists
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 409
    
    # Create new user
    user = User(
        username=username,
        email=email,
        is_active=True,
        is_admin=False
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'User created successfully',
        'user': user.to_dict()
    }), 201

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify JWT token validity
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return jsonify({'success': False, 'message': 'Invalid user'}), 401
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    User logout endpoint
    TODO: Implement token blacklisting
    """
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

@auth_bp.route('/status')
def auth_status():
    """
    Authentication service status
    """
    return jsonify({
        'service': 'auth',
        'status': 'healthy',
        'features': ['jwt', 'login', 'logout']
    })