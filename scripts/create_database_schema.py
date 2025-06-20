#!/usr/bin/env python3
"""
Create Database Schema
Creates all tables from SQLAlchemy models
"""
import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from orchestrator.database import db
from orchestrator.config_loader import load_config
from orchestrator.models import *  # Import all models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_schema():
    """Create all database tables from models"""
    app = Flask(__name__)
    
    # Load configuration
    config = load_config()
    app.config['SQLALCHEMY_DATABASE_URI'] = config['DATABASE']['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logger.info("✅ Database schema created successfully")
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"📊 Created {len(tables)} tables: {', '.join(sorted(tables))}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create schema: {e}")
            raise

if __name__ == "__main__":
    create_schema()