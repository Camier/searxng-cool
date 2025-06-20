#!/usr/bin/env python3
"""
SearXNG-Cool Production Orchestrator
Uses the Application Factory pattern for robustness and testability.
"""

import os
import sys
import yaml
import logging
from datetime import timedelta
from flask import Flask, request, jsonify, Response
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import redis
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 1. Extension Initialization ---
# Import the decoupled database instance
from orchestrator.database import db
# Instantiate other extensions in the global scope without an app.
# They will be connected to the app inside the factory.
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO()

# Redis connection variables
redis_client = None
redis_pool = None

def load_config():
    """Load configuration with validation"""
    # Use the config loader that handles environment variables
    from orchestrator.config_loader import load_config as config_load
    try:
        config = config_load()
        logger.info("✅ Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        sys.exit(1)

def get_redis():
    """Get Redis connection with production-grade connection pooling"""
    global redis_client, redis_pool
    if redis_client is None:
        try:
            # Production Redis connection pool
            redis_pool = redis.ConnectionPool(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                socket_keepalive=True,
                socket_keepalive_options={},
                connection_pool_class_kwargs={
                    'max_connections': 50,  # Production: higher connection limit
                    'retry_on_timeout': True
                }
            )
            redis_client = redis.Redis(connection_pool=redis_pool)
            redis_client.ping()  # Test connection
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            redis_client = None
    return redis_client

def create_app():
    """Application Factory: Creates and configures the Flask app."""
    
    # Initialize Flask app without static folder
    app = Flask(__name__, static_folder=None)
    
    # --- 2. Configuration Loading ---
    config = load_config()
    
    # Flask configuration with production settings
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = config['DATABASE']['SQLALCHEMY_DATABASE_URI']
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config['DATABASE']['SQLALCHEMY_TRACK_MODIFICATIONS']
        app.config['JWT_SECRET_KEY'] = config['JWT']['JWT_SECRET_KEY']
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=int(config['JWT']['JWT_ACCESS_TOKEN_EXPIRES']))
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_timeout': 20,
            'pool_recycle': 299,
            'pool_pre_ping': True,
            'pool_size': 10,
            'max_overflow': 20
        }
        # Production security settings
        app.config['SECRET_KEY'] = config['JWT']['JWT_SECRET_KEY']
        if not config['SERVER']['DEBUG']:
            app.config['PREFERRED_URL_SCHEME'] = 'https'
    except KeyError as e:
        logger.error(f"❌ Missing configuration key: {e}")
        sys.exit(1)
    
    # Store config for later use
    app.config['SEARXNG_CONFIG'] = config
    
    # --- 3. Initialize Extensions with the App ---
    db.init_app(app)
    migrate.init_app(app, db)  # Correctly initialize Migrate here
    jwt.init_app(app)
    cors = CORS(app, origins=config['CORS']['ORIGINS'])
    
    # Initialize SocketIO with Redis message queue for production
    redis_url = config['REDIS']['REDIS_URL']
    try:
        socketio.init_app(
            app, 
            message_queue=redis_url,
            async_mode='eventlet',
            cors_allowed_origins=config['CORS']['ORIGINS'],
            logger=True,
            engineio_logger=True
        )
        logger.info("✅ Production SocketIO initialized with Redis message queue")
        logger.info(f"📡 Message queue: {redis_url}")
        logger.info("🚀 Ready for multi-process deployment")
    except Exception as e:
        logger.error(f"❌ SocketIO initialization failed: {e}")
        socketio.init_app(app, async_mode='threading')  # Fallback mode
    
    # --- 4. Import and Register Blueprints & Models ---
    with app.app_context():
        # Import models so that Flask-Migrate can see them
        from . import models
        
        # Track blueprint loading status
        blueprints_loaded = {
            'auth': False,
            'api': False,
            'proxy': False,
            'websocket': False
        }
        
        # Import and register blueprints with error handling
        try:
            from .blueprints.auth.routes import auth_bp
            app.register_blueprint(auth_bp, url_prefix='/auth')
            blueprints_loaded['auth'] = True
            logger.info("✅ Auth blueprint registered")
        except Exception as e:
            logger.warning(f"⚠️ Auth blueprint failed: {e}")
        
        try:
            from .blueprints.api.routes import api_bp
            app.register_blueprint(api_bp, url_prefix='/api')
            blueprints_loaded['api'] = True
            logger.info("✅ API blueprint registered")
        except Exception as e:
            logger.warning(f"⚠️ Api blueprint failed: {e}")
        
        try:
            from .blueprints.api.music_routes import music_api_bp
            app.register_blueprint(music_api_bp)  # Already has /api/music prefix
            blueprints_loaded['music_api'] = True
            logger.info("✅ Music API blueprint registered")
        except Exception as e:
            logger.warning(f"⚠️ Music API blueprint failed: {e}")
        
        try:
            from .blueprints.api.music_aggregation_routes import music_aggregation_bp
            app.register_blueprint(music_aggregation_bp, url_prefix='/api/music/aggregation')
            blueprints_loaded['music_aggregation'] = True
            logger.info("✅ Music Aggregation blueprint registered")
        except Exception as e:
            logger.warning(f"⚠️ Music Aggregation blueprint failed: {e}")
        
        try:
            from .blueprints.proxy.routes import proxy_bp
            app.register_blueprint(proxy_bp, url_prefix='/proxy')
            blueprints_loaded['proxy'] = True
            logger.info("✅ Proxy blueprint registered")
        except Exception as e:
            logger.warning(f"⚠️ Proxy blueprint failed: {e}")
        
        try:
            from .blueprints.websocket.routes import websocket_bp, register_websocket_events
            app.register_blueprint(websocket_bp)
            # Register WebSocket events after socketio is initialized
            register_websocket_events(socketio)
            blueprints_loaded['websocket'] = True
            logger.info("✅ WebSocket blueprint registered")
            logger.info("✅ WebSocket event handlers registered successfully")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket blueprint failed: {e}")
        
        # Store blueprint status in app config
        app.config['BLUEPRINTS_LOADED'] = blueprints_loaded
        logger.info(f"📊 Blueprints loaded: {sum(blueprints_loaded.values())}/{len(blueprints_loaded)}")
    
    # --- 5. Register Routes ---
    register_routes(app)
    
    # --- 6. SocketIO Events are now registered in the WebSocket blueprint ---
    # register_socketio_events() - Moved to WebSocket blueprint
    
    return app

def register_routes(app):
    """Register application routes"""
    
    @app.route('/')
    def index():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'searxng-cool-orchestrator',
            'version': '1.0.0',
            'mode': 'production',
            'features': {
                'websocket': True,
                'redis': redis_client is not None,
                'multi_process': True
            }
        })
    
    @app.route('/status')
    def status():
        """Detailed status endpoint"""
        blueprints_loaded = app.config.get('BLUEPRINTS_LOADED', {})
        config = app.config['SEARXNG_CONFIG']
        
        # Test Redis connection
        redis_status = False
        try:
            if get_redis():
                redis_client.ping()
                redis_status = True
        except:
            redis_status = False
        
        return jsonify({
            'status': 'operational',
            'redis': redis_status,
            'database': True,  # Basic check
            'blueprints': blueprints_loaded,
            'server': {
                'host': config['SERVER']['HOST'],
                'port': config['SERVER']['PORT'],
                'debug': config['SERVER']['DEBUG'],
                'multi_process_ready': True,
                'async_mode': 'eventlet'
            }
        })
    
    @app.route('/config')
    def get_config():
        """Get safe configuration details"""
        config = app.config['SEARXNG_CONFIG']
        
        # Return safe configuration (no secrets)
        safe_config = {
            'cors_origins': config['CORS']['ORIGINS'],
            'searxng_core_url': config['SEARXNG']['CORE_URL'],
            'websocket_enabled': True,
            'redis_enabled': redis_client is not None,
            'server': {
                'host': config['SERVER']['HOST'],
                'port': config['SERVER']['PORT'],
                'debug': config['SERVER']['DEBUG'],
                'multi_process_ready': True,
                'async_mode': 'eventlet'
            }
        }
        
        # Remove debug info in production
        if not config['SERVER']['DEBUG']:
            safe_config['server']['debug'] = False
        
        return jsonify(safe_config)
    
    # Fallback proxy (enhanced from app_minimal)
    @app.route('/fallback-proxy/', defaults={'path': ''})
    @app.route('/fallback-proxy/<path:path>')
    def fallback_proxy(path):
        """Production fallback proxy to SearXNG"""
        try:
            config = app.config['SEARXNG_CONFIG']
            SEARXNG_BASE_URL = config['SEARXNG']['CORE_URL']
            
            url = urljoin(SEARXNG_BASE_URL, path)
            params = request.args.to_dict()
            headers = {key: value for (key, value) in request.headers if key.lower() != 'host'}
            
            # Production timeout settings
            timeout = 30
            if request.method == 'POST':
                resp = requests.post(url, params=params, headers=headers, 
                                   data=request.get_data(), timeout=timeout)
            else:
                resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            # Build response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            response_headers = [(name, value) for (name, value) in resp.headers.items()
                               if name.lower() not in excluded_headers]
            
            response = Response(resp.content, resp.status_code, response_headers)
            return response
        except Exception as e:
            logger.error(f"Fallback proxy error: {e}")
            return jsonify({'error': f'Proxy error: {str(e)}'}), 500

def register_socketio_events():
    """Register SocketIO event handlers"""
    
    @socketio.on('connect')
    def on_connect():
        """Handle client connection"""
        logger.info(f"Client connected: {request.sid}")
        emit('status', {'status': 'connected', 'server': 'production'})
    
    @socketio.on('disconnect')
    def on_disconnect():
        """Handle client disconnection"""
        logger.info(f"Client disconnected: {request.sid}")
    
    @socketio.on('ping')
    def on_ping():
        """Handle ping from client"""
        import time
        emit('pong', {'timestamp': time.time()})