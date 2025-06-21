"""
Rate limiting configuration for the application
"""
import os
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from orchestrator.utils.auth import jwt_required_with_user
from orchestrator.utils.error_handlers import log_security_event

def get_user_id():
    """Get user ID from JWT token if available"""
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        return str(user_id) if user_id else get_remote_address()
    except:
        return get_remote_address()

# Create limiter instance
limiter = Limiter(
    key_func=get_user_id,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=os.getenv('RATE_LIMIT_STORAGE_URL', 'redis://localhost:6379/2'),
    strategy="fixed-window-elastic-expiry"
)

# Define rate limit rules for different endpoints
RATE_LIMITS = {
    # Authentication endpoints - strict limits
    'auth.login': '5 per minute',
    'auth.register': '3 per hour',
    
    # API endpoints - moderate limits
    'api.api_search': '60 per minute',
    'api.api_engines': '30 per minute',
    
    # Music endpoints - generous limits for authenticated users
    'api.music_search': '100 per minute',
    'api.music_engines_status': '60 per minute',
    'api.playlists': '60 per minute',
    
    # WebSocket endpoints
    'websocket.connect': '10 per minute',
    
    # Health checks - very generous
    'api.music_health': '300 per minute',
    'api.api_status': '300 per minute',
}

def register_rate_limits(app):
    """Register rate limits with the Flask app"""
    
    # Initialize limiter with app
    limiter.init_app(app)
    
    # Configure rate limit exceeded handler
    @app.errorhandler(429)
    def rate_limit_handler(e):
        """Handle rate limit exceeded errors"""
        log_security_event(
            'RATE_LIMIT_EXCEEDED',
            details={
                'endpoint': request.endpoint,
                'limit': str(e.description)
            },
            user_id=get_user_id()
        )
        
        return {
            'error': {
                'message': 'Too many requests. Please try again later.',
                'code': 429,
                'retry_after': e.retry_after if hasattr(e, 'retry_after') else None
            }
        }, 429
    
    # Apply specific rate limits to endpoints
    for endpoint, limit in RATE_LIMITS.items():
        try:
            view_func = app.view_functions.get(endpoint)
            if view_func:
                app.view_functions[endpoint] = limiter.limit(limit)(view_func)
        except Exception as e:
            app.logger.warning(f"Could not apply rate limit to {endpoint}: {e}")
    
    app.logger.info("✅ Rate limiting configured")

# Decorators for custom rate limits
def strict_limit(limit_string):
    """Apply strict rate limiting to an endpoint"""
    def decorator(f):
        return limiter.limit(limit_string)(f)
    return decorator

def authenticated_limit(authenticated_limit, anonymous_limit):
    """Apply different rate limits for authenticated vs anonymous users"""
    def decorator(f):
        def get_limit():
            try:
                from flask_jwt_extended import get_jwt_identity
                if get_jwt_identity():
                    return authenticated_limit
            except:
                pass
            return anonymous_limit
        
        return limiter.limit(get_limit)(f)
    return decorator