# Flask Production Patterns for SearXNG-Cool

## Table of Contents
1. [Blueprint Architecture](#blueprint-architecture)
2. [Authentication & Security](#authentication-security)
3. [CORS Configuration](#cors-configuration)
4. [Session Management with Redis](#session-management)
5. [Error Handling Patterns](#error-handling)
6. [API Versioning](#api-versioning)
7. [Waitress WSGI Deployment](#waitress-deployment)
8. [Flask-SocketIO Integration](#socketio-integration)
9. [Performance Optimization](#performance-optimization)
10. [Testing Strategies](#testing-strategies)

## Blueprint Architecture {#blueprint-architecture}

### Modular Blueprint Structure
```python
# app/blueprints/__init__.py
from flask import Blueprint

# Create blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
websocket_bp = Blueprint('websocket', __name__, url_prefix='/ws')
proxy_bp = Blueprint('proxy', __name__, url_prefix='/proxy')

# Blueprint registration with error handling
def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    blueprints = [
        (api_bp, 'api'),
        (auth_bp, 'auth'),
        (websocket_bp, 'websocket'),
        (proxy_bp, 'proxy')
    ]
    
    for blueprint, name in blueprints:
        try:
            app.register_blueprint(blueprint)
            app.logger.info(f"✅ {name.capitalize()} blueprint loaded")
        except Exception as e:
            app.logger.warning(f"⚠️ {name.capitalize()} blueprint failed: {str(e)}")
```

### Blueprint Organization Pattern
```python
# app/blueprints/api/__init__.py
from flask import Blueprint, jsonify, request
from functools import wraps
import time

api_bp = Blueprint('api', __name__)

# Decorator for API timing
def timed_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start_time
        
        if isinstance(result, tuple):
            response, status_code = result
            response['_meta'] = {
                'duration': duration,
                'timestamp': time.time()
            }
            return jsonify(response), status_code
        return result
    return decorated_function

# Import routes after blueprint creation
from . import search_routes
from . import health_routes
from . import config_routes
```

### Advanced Blueprint Error Handling
```python
# app/blueprints/api/errors.py
from flask import jsonify
from werkzeug.exceptions import HTTPException

class APIError(Exception):
    """Base API Exception"""
    status_code = 500
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = {
            'message': self.message,
            'code': self.status_code
        }
        return rv

# Register error handlers on blueprint
@api_bp.errorhandler(APIError)
def handle_api_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
```

## Authentication & Security {#authentication-security}

### JWT Authentication Pattern
```python
# app/auth/jwt_auth.py
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from datetime import timedelta
import redis

class JWTAuth:
    def __init__(self, app=None, redis_client=None):
        self.jwt = JWTManager()
        self.redis_client = redis_client
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # JWT Configuration
        app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY')
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
        app.config['JWT_ALGORITHM'] = 'HS256'
        
        self.jwt.init_app(app)
        
        # Token blacklist checking
        @self.jwt.token_in_blocklist_loader
        def check_if_token_revoked(jwt_header, jwt_payload):
            jti = jwt_payload["jti"]
            token_in_redis = self.redis_client.get(f"blocklist:{jti}")
            return token_in_redis is not None
        
        # Custom claims
        @self.jwt.additional_claims_loader
        def add_claims_to_jwt(identity):
            return {
                'user_id': identity,
                'roles': self.get_user_roles(identity)
            }
    
    def get_user_roles(self, user_id):
        # Fetch from database or cache
        return ['user']  # Default role
```

### Authentication Decorators
```python
# app/auth/decorators.py
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def require_auth(optional=False):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request(optional=optional)
            except Exception as e:
                if not optional:
                    return jsonify({'error': 'Authentication required'}), 401
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        @require_auth()
        def decorated_function(*args, **kwargs):
            claims = get_jwt()
            user_roles = claims.get('roles', [])
            
            if not any(role in allowed_roles for role in user_roles):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### Security Middleware
```python
# app/middleware/security.py
from flask import request, abort
import re
import hashlib

class SecurityMiddleware:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self.validate_request)
        app.after_request(self.secure_response)
    
    def validate_request(self):
        # CSRF Protection for state-changing methods
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.headers.get('X-CSRF-Token')
            if not self.validate_csrf_token(token):
                abort(403, 'Invalid CSRF token')
        
        # SQL Injection Protection
        if self.detect_sql_injection(request.values):
            abort(400, 'Invalid request parameters')
        
        # XSS Protection
        if self.detect_xss_attempt(request.values):
            abort(400, 'Invalid request content')
    
    def secure_response(self, response):
        # Security headers are handled by nginx, but we can add app-specific ones
        response.headers['X-Request-ID'] = request.headers.get('X-Request-ID', '')
        return response
    
    def validate_csrf_token(self, token):
        # Implement CSRF validation logic
        return True  # Placeholder
    
    def detect_sql_injection(self, values):
        sql_patterns = [
            r"(union.*select|select.*from|insert.*into|delete.*from)",
            r"(drop\s+table|alter\s+table|create\s+table)",
            r"(exec\(|execute\s)",
            r"(script.*>|<.*script)",
        ]
        
        for value in values.values():
            if isinstance(value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
        return False
    
    def detect_xss_attempt(self, values):
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
        ]
        
        for value in values.values():
            if isinstance(value, str):
                for pattern in xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
        return False
```

## CORS Configuration {#cors-configuration}

### Advanced CORS Setup
```python
# app/extensions/cors.py
from flask_cors import CORS
from urllib.parse import urlparse

class SmartCORS:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Dynamic CORS configuration
        def get_cors_origins():
            # Base allowed origins
            origins = [
                'https://alfredisgone.duckdns.org',
                'http://localhost:3000',  # Development
            ]
            
            # Add dynamic origins from environment
            if app.config.get('ADDITIONAL_CORS_ORIGINS'):
                origins.extend(app.config['ADDITIONAL_CORS_ORIGINS'])
            
            return origins
        
        # Configure CORS with dynamic origins
        CORS(app, 
             resources={
                 r"/api/*": {
                     "origins": get_cors_origins(),
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
                     "expose_headers": ["X-Total-Count", "X-Page", "X-Per-Page"],
                     "supports_credentials": True,
                     "max_age": 3600
                 },
                 r"/ws/*": {
                     "origins": get_cors_origins(),
                     "methods": ["GET"],
                     "allow_headers": ["Content-Type"],
                     "supports_credentials": True
                 }
             })
        
        # Custom CORS headers for specific routes
        @app.after_request
        def after_request(response):
            origin = request.headers.get('Origin')
            if origin and self.is_origin_allowed(origin):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Vary'] = 'Origin'
            return response
    
    def is_origin_allowed(self, origin):
        # Custom origin validation logic
        parsed = urlparse(origin)
        
        # Allow all subdomains of main domain
        if parsed.hostname and parsed.hostname.endswith('.duckdns.org'):
            return True
        
        # Check against whitelist
        return origin in self.get_cors_origins()
```

## Session Management with Redis {#session-management}

### Redis Session Store
```python
# app/extensions/session.py
import redis
from flask_session import Session
import pickle
from datetime import timedelta

class RedisSessionStore:
    def __init__(self, app=None, redis_client=None):
        self.redis_client = redis_client
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Configure Flask-Session with Redis
        app.config.update({
            'SESSION_TYPE': 'redis',
            'SESSION_REDIS': self.redis_client,
            'SESSION_KEY_PREFIX': 'searxng:session:',
            'SESSION_PERMANENT': False,
            'SESSION_USE_SIGNER': True,
            'SESSION_COOKIE_SECURE': True,  # HTTPS only
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=24)
        })
        
        Session(app)
        
        # Custom session handling
        @app.before_request
        def load_user_session():
            if 'user_id' in session:
                # Load user data from cache
                user_data = self.get_user_data(session['user_id'])
                g.user = user_data
        
        @app.after_request
        def save_session_data(response):
            if hasattr(g, 'user') and g.user:
                # Update last activity
                self.update_last_activity(g.user['id'])
            return response
    
    def get_user_data(self, user_id):
        key = f"user:{user_id}"
        data = self.redis_client.get(key)
        if data:
            return pickle.loads(data)
        return None
    
    def update_last_activity(self, user_id):
        key = f"user:activity:{user_id}"
        self.redis_client.setex(key, timedelta(minutes=30), time.time())
```

### Session Security
```python
# app/security/session_security.py
import hmac
import hashlib
from datetime import datetime, timedelta

class SessionSecurity:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.secret_key = app.config['SECRET_KEY']
        
        @app.before_request
        def validate_session():
            if 'session_token' in session:
                if not self.validate_session_token(session['session_token']):
                    session.clear()
                    abort(401, 'Invalid session')
            
            # Session fixation protection
            if 'user_id' in session and 'session_created' not in session:
                session.regenerate()  # Custom method to regenerate session ID
    
    def generate_session_token(self, user_id):
        """Generate secure session token"""
        data = f"{user_id}:{datetime.utcnow().isoformat()}"
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def validate_session_token(self, token):
        """Validate session token"""
        # Implement token validation logic
        return True
```

## Error Handling Patterns {#error-handling}

### Comprehensive Error Handler
```python
# app/errors/handlers.py
from flask import jsonify, request, current_app
import traceback
import sys

class ErrorHandlers:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Register all error handlers
        app.register_error_handler(400, self.bad_request)
        app.register_error_handler(401, self.unauthorized)
        app.register_error_handler(403, self.forbidden)
        app.register_error_handler(404, self.not_found)
        app.register_error_handler(405, self.method_not_allowed)
        app.register_error_handler(422, self.unprocessable_entity)
        app.register_error_handler(429, self.too_many_requests)
        app.register_error_handler(500, self.internal_error)
        app.register_error_handler(502, self.bad_gateway)
        app.register_error_handler(503, self.service_unavailable)
        app.register_error_handler(504, self.gateway_timeout)
        
        # Generic exception handler
        app.register_error_handler(Exception, self.handle_exception)
    
    def create_error_response(self, status_code, message, details=None):
        response = {
            'error': {
                'code': status_code,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'path': request.path,
                'method': request.method
            }
        }
        
        if details:
            response['error']['details'] = details
        
        if current_app.debug and status_code == 500:
            response['error']['traceback'] = traceback.format_exc()
        
        return jsonify(response), status_code
    
    def bad_request(self, error):
        return self.create_error_response(400, 'Bad Request', str(error))
    
    def unauthorized(self, error):
        return self.create_error_response(401, 'Unauthorized', 
                                        'Authentication required')
    
    def forbidden(self, error):
        return self.create_error_response(403, 'Forbidden', 
                                        'Insufficient permissions')
    
    def not_found(self, error):
        return self.create_error_response(404, 'Not Found', 
                                        f"Resource {request.path} not found")
    
    def method_not_allowed(self, error):
        return self.create_error_response(405, 'Method Not Allowed',
                                        f"{request.method} not allowed for {request.path}")
    
    def internal_error(self, error):
        # Log the full error
        current_app.logger.error(f"Internal error: {str(error)}")
        current_app.logger.error(traceback.format_exc())
        
        return self.create_error_response(500, 'Internal Server Error',
                                        'An unexpected error occurred')
    
    def handle_exception(self, error):
        # Handle non-HTTP exceptions
        if isinstance(error, HTTPException):
            return self.create_error_response(error.code, error.name, 
                                            error.description)
        
        # Log unknown exceptions
        current_app.logger.error(f"Unhandled exception: {str(error)}")
        current_app.logger.error(traceback.format_exc())
        
        return self.internal_error(error)
```

## API Versioning {#api-versioning}

### URL-Based Versioning
```python
# app/api/versioning.py
from flask import Blueprint, current_app
from functools import wraps

class APIVersioning:
    def __init__(self, app=None):
        self.versions = {}
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Register versioned blueprints
        v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
        v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')
        
        self.versions['v1'] = v1
        self.versions['v2'] = v2
        
        # Import versioned routes
        from .v1 import routes as v1_routes
        from .v2 import routes as v2_routes
        
        app.register_blueprint(v1)
        app.register_blueprint(v2)
    
    def deprecated(self, message="This endpoint is deprecated"):
        """Decorator to mark deprecated endpoints"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                response = make_response(f(*args, **kwargs))
                response.headers['X-API-Deprecation'] = message
                response.headers['X-API-Deprecation-Date'] = '2024-12-31'
                return response
            return decorated_function
        return decorator
```

### Header-Based Versioning
```python
# app/api/header_versioning.py
from flask import request, abort

class HeaderVersioning:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self.check_api_version)
    
    def check_api_version(self):
        if request.path.startswith('/api/'):
            version = request.headers.get('X-API-Version', 'v1')
            
            if version not in ['v1', 'v2']:
                abort(400, 'Invalid API version')
            
            # Store version in request context
            g.api_version = version
            
            # Modify behavior based on version
            if version == 'v1' and request.path.startswith('/api/users'):
                # Redirect v1 calls to v1 endpoint
                request.url_rule.rule = request.url_rule.rule.replace('/api/', '/api/v1/')
```

## Waitress WSGI Deployment {#waitress-deployment}

### Production Waitress Configuration
```python
# wsgi.py
from app import create_app
import os

# Create application instance
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    from waitress import serve
    
    # Waitress configuration
    serve(
        app,
        host='0.0.0.0',
        port=8889,
        threads=4,  # Number of threads
        connection_limit=1000,  # Max connections
        cleanup_interval=30,  # Cleanup interval in seconds
        channel_timeout=120,  # Channel timeout
        
        # Unix socket support (alternative to TCP)
        # unix_socket='/tmp/searxng-cool.sock',
        # unix_socket_perms='600',
        
        # Request limits
        max_request_body_size=10 * 1024 * 1024,  # 10MB
        max_request_header_size=8192,
        
        # Logging
        log_socket_errors=True,
        
        # URL scheme fixup for proxy
        url_scheme='https' if os.environ.get('HTTPS') else 'http',
        
        # Trusted proxy settings
        trusted_proxy='127.0.0.1',
        trusted_proxy_count=1,
        trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-port'}
    )
```

### Gunicorn Alternative
```python
# gunicorn_config.py
import multiprocessing

# Gunicorn configuration
bind = "0.0.0.0:8889"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # or "gevent" for async
worker_connections = 1000
keepalive = 5

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = 'searxng-cool'

# Server mechanics
daemon = False
pidfile = '/var/run/gunicorn/searxng-cool.pid'
user = 'www-data'
group = 'www-data'
tmp_upload_dir = None

# SSL (if not using nginx)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Server hooks
def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
```

## Flask-SocketIO Integration {#socketio-integration}

### Production SocketIO Setup
```python
# app/websocket/socketio_setup.py
from flask_socketio import SocketIO, emit, join_room, leave_room
import functools

class SocketIOManager:
    def __init__(self, app=None, redis_client=None):
        self.socketio = None
        self.redis_client = redis_client
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Initialize SocketIO with Redis message queue
        self.socketio = SocketIO(
            app,
            async_mode='threading',  # or 'eventlet' for better performance
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True,
            message_queue=app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
            channel=app.config.get('SOCKETIO_CHANNEL', 'searxng-cool')
        )
        
        # Register event handlers
        self.register_handlers()
        
        return self.socketio
    
    def register_handlers(self):
        # Authentication decorator for SocketIO
        def authenticated_only(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                if not current_user.is_authenticated:
                    emit('error', {'message': 'Authentication required'})
                    return False
                return f(*args, **kwargs)
            return wrapped
        
        @self.socketio.on('connect')
        def handle_connect():
            emit('connected', {'data': 'Connected to SearXNG-Cool'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            # Clean up user rooms
            if hasattr(current_user, 'id'):
                leave_room(f"user:{current_user.id}")
        
        @self.socketio.on('join')
        @authenticated_only
        def handle_join(data):
            room = data.get('room')
            join_room(room)
            emit('joined', {'room': room}, room=room)
        
        @self.socketio.on('search')
        @authenticated_only
        def handle_search(data):
            query = data.get('query')
            # Emit search progress
            emit('search_started', {'query': query})
            
            # Perform search asynchronously
            self.socketio.start_background_task(
                self.async_search,
                query,
                request.sid
            )
    
    def async_search(self, query, sid):
        """Background task for async search"""
        # Simulate search progress
        for progress in [25, 50, 75, 100]:
            self.socketio.sleep(0.5)
            self.socketio.emit(
                'search_progress',
                {'progress': progress},
                room=sid
            )
        
        # Emit results
        results = {'query': query, 'results': []}
        self.socketio.emit('search_complete', results, room=sid)
```

## Performance Optimization {#performance-optimization}

### Response Caching
```python
# app/cache/caching.py
from flask_caching import Cache
from functools import wraps
import hashlib

cache = Cache()

class CacheManager:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Configure cache
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': app.config.get('REDIS_URL'),
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_KEY_PREFIX': 'searxng:cache:',
            'CACHE_REDIS_DB': 1
        }
        
        cache.init_app(app, config=cache_config)
    
    @staticmethod
    def cached_route(timeout=300, key_prefix='view'):
        """Cache route responses"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Create cache key from route and arguments
                cache_key = f"{key_prefix}:{request.path}:{request.query_string.decode()}"
                
                # Check cache
                cached = cache.get(cache_key)
                if cached:
                    return cached
                
                # Generate response
                response = f(*args, **kwargs)
                
                # Cache response
                cache.set(cache_key, response, timeout=timeout)
                
                return response
            return decorated_function
        return decorator
    
    @staticmethod
    def invalidate_pattern(pattern):
        """Invalidate cache keys matching pattern"""
        # Redis-specific cache invalidation
        redis_client = cache.cache._write_client
        keys = redis_client.keys(f"{cache.config['CACHE_KEY_PREFIX']}{pattern}*")
        if keys:
            redis_client.delete(*keys)
```

### Database Query Optimization
```python
# app/database/optimization.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import time
import logging

logger = logging.getLogger(__name__)

class DatabaseOptimization:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Enable query logging in development
        if app.debug:
            self.enable_query_logging()
        
        # Configure connection pool
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 20,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'max_overflow': 40,
            'connect_args': {
                'connect_timeout': 10,
            }
        }
    
    def enable_query_logging(self):
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            logger.debug("Query: %s", statement)
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            logger.debug("Query time: %.3fs", total)
            
            # Log slow queries
            if total > 1.0:
                logger.warning("Slow query (%.3fs): %s", total, statement)
```

## Testing Strategies {#testing-strategies}

### Comprehensive Test Setup
```python
# tests/conftest.py
import pytest
from app import create_app, db
from app.models import User
import tempfile

@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'RATELIMIT_ENABLED': False
    })
    
    with app.app_context():
        db.create_all()
        
        # Create test data
        test_user = User(username='test', email='test@example.com')
        test_user.set_password('password')
        db.session.add(test_user)
        db.session.commit()
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope='function')
def authenticated_client(client):
    """Create authenticated test client"""
    client.post('/auth/login', json={
        'username': 'test',
        'password': 'password'
    })
    return client

@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()
```

### API Testing
```python
# tests/test_api.py
import pytest
import json

class TestSearchAPI:
    def test_search_requires_auth(self, client):
        response = client.get('/api/v1/search?q=test')
        assert response.status_code == 401
    
    def test_search_success(self, authenticated_client):
        response = authenticated_client.get('/api/v1/search?q=python')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'results' in data
        assert 'meta' in data
        assert data['meta']['query'] == 'python'
    
    def test_search_validation(self, authenticated_client):
        # Empty query
        response = authenticated_client.get('/api/v1/search?q=')
        assert response.status_code == 400
        
        # Query too long
        response = authenticated_client.get('/api/v1/search?q=' + 'a' * 1001)
        assert response.status_code == 400
    
    def test_search_rate_limiting(self, authenticated_client):
        # Make multiple requests
        for i in range(10):
            response = authenticated_client.get('/api/v1/search?q=test')
            if i < 5:
                assert response.status_code == 200
            else:
                # Should be rate limited
                assert response.status_code == 429
```

### Performance Testing
```python
# tests/test_performance.py
import time
import concurrent.futures

def test_concurrent_requests(client):
    """Test handling of concurrent requests"""
    def make_request():
        return client.get('/api/v1/health')
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    duration = end_time - start_time
    
    # All requests should succeed
    assert all(r.status_code == 200 for r in results)
    
    # Should complete within reasonable time
    assert duration < 5.0  # 100 requests in 5 seconds
```

## Production Checklist

1. **Environment Variables**: All sensitive config in environment
2. **Database Migrations**: Use Flask-Migrate for schema management
3. **Logging**: Structured logging with proper levels
4. **Monitoring**: Application metrics and health checks
5. **Rate Limiting**: Protect all endpoints
6. **Input Validation**: Validate all user inputs
7. **Error Handling**: Graceful error responses
8. **Security Headers**: Set by application or nginx
9. **Session Security**: Secure cookie settings
10. **Testing**: Comprehensive test coverage

This guide provides production-ready patterns for Flask applications in the SearXNG-Cool architecture.