"""Database instance - completely independent of Flask app"""
from flask_sqlalchemy import SQLAlchemy

# This is THE database instance for the entire application
db = SQLAlchemy()