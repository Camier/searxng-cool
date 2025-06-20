#!/usr/bin/env python3
"""
Migration-Only Flask App
Minimal Flask app for database migrations without SocketIO
Loads configuration securely from orchestrator.yml with environment variable support
"""
import os
import sys
import logging
from flask import Flask
from flask_migrate import Migrate

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database and models
from orchestrator.database import db
from orchestrator.models import *  # Import all models to register them
from orchestrator.config_loader import load_config, get_database_uri, validate_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """
    Create minimal Flask app for migrations only.
    
    Loads configuration from orchestrator.yml with environment variable substitution.
    Validates configuration before proceeding.
    
    Returns:
        Flask: Configured Flask application instance
        
    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If configuration file is missing
    """
    app = Flask(__name__)
    
    try:
        # Load and validate configuration
        config = load_config()
        validate_config(config)
        
        # Configure database
        app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(config)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config['DATABASE'].get('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        
        # Additional migration-specific settings
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'connect_args': {
                'connect_timeout': 30,
                'application_name': 'searxng_migrations'
            }
        }
        
        logger.info("✅ Database configuration loaded successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        raise
    
    # Initialize only database and migrate
    db.init_app(app)
    migrate = Migrate(app, db, compare_type=True, compare_server_default=True)
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    print("Migration app created. Use: FLASK_APP=migration_app.py flask db ...")
