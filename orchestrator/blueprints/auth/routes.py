"""
Authentication Blueprint - Handles user authentication and JWT tokens
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    TODO: Implement proper user authentication with database
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Temporary hardcoded auth for development
    if username == 'admin' and password == 'password':
        access_token = create_access_token(identity=username)
        return jsonify({
            'success': True,
            'access_token': access_token,
            'user': username
        })
    
    return jsonify({
        'success': False,
        'message': 'Invalid credentials'
    }), 401

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify JWT token validity
    """
    current_user = get_jwt_identity()
    return jsonify({
        'success': True,
        'user': current_user
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