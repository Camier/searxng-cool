"""
Authentication utilities and decorators
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from orchestrator.models.user import User

def jwt_required_with_user(optional=False):
    """
    Custom JWT decorator that also loads the user object
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                if optional:
                    verify_jwt_in_request(optional=True)
                else:
                    verify_jwt_in_request()
                
                user_id = get_jwt_identity()
                if user_id:
                    user = User.query.get(user_id)
                    if not user or not user.is_active:
                        return jsonify({'error': 'Invalid or inactive user'}), 401
                    kwargs['current_user'] = user
                elif not optional:
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    kwargs['current_user'] = None
                    
            except Exception as e:
                if not optional:
                    return jsonify({'error': 'Authentication failed'}), 401
                kwargs['current_user'] = None
                
            return f(*args, **kwargs)
        return wrapper
    return decorator

def admin_required():
    """
    Decorator that requires admin privileges
    """
    def decorator(f):
        @wraps(f)
        @jwt_required_with_user()
        def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user or not user.is_admin:
                return jsonify({'error': 'Admin privileges required'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator