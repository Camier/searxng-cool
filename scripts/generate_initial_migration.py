#!/usr/bin/env python3
"""
Generate Initial Migration Script
Creates a proper Alembic migration file capturing the current database state
"""
import os
import sys
import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, MetaData, inspect
from orchestrator.database import db
from orchestrator.models import *


def generate_migration_file(tables_sql: List[str], indexes_sql: List[str]) -> str:
    """Generate the migration file content"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    revision_id = f"{timestamp}_initial_schema"
    
    template = f'''"""Initial database schema capture

Revision ID: {revision_id}
Revises: manual_creation_20250617
Create Date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This migration captures the existing database schema that was manually created.
It serves as the baseline for future migrations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = 'manual_creation_20250617'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    This upgrade function is intentionally empty because the schema
    already exists in the database. This migration serves as a checkpoint
    to establish the current state for future migrations.
    """
    pass


def downgrade() -> None:
    """
    Drop all tables and indexes. Use with extreme caution!
    """
    # Drop indexes first
    {"".join(f"    op.execute('DROP INDEX IF EXISTS {idx}')" + chr(10) for idx in reversed(indexes_sql))}
    
    # Drop tables in reverse order to handle foreign key constraints
    tables_to_drop = [
        'playlist_track_votes',
        'playlist_activities', 
        'playlist_collaborators',
        'playlist_follows',
        'user_album_collections',
        'user_artist_follows',
        'discovery_session_tracks',
        'discovery_sessions',
        'user_interactions',
        'user_library',
        'user_music_profiles',
        'playlist_tracks',
        'playlists',
        'track_sources',
        'album_sources',
        'artist_sources',
        'tracks',
        'albums',
        'artists',
        'users',
        'alembic_version'
    ]
    
    for table in tables_to_drop:
        op.drop_table(table, if_exists=True)
'''
    
    return template


def analyze_database():
    """Analyze the current database state"""
    import os
    from urllib.parse import quote_plus
    
    # Get database URL from environment
    if db_url := os.environ.get('DATABASE_URL'):
        engine = create_engine(db_url)
    else:
        user = os.environ.get('DB_USER', 'searxng_user')
        password = os.environ.get('DB_PASSWORD', '')
        if not password:
            raise ValueError("DB_PASSWORD environment variable must be set")
        password = quote_plus(password)
        host = os.environ.get('DB_HOST', 'localhost')
        port = os.environ.get('DB_PORT', '5432')
        database = os.environ.get('DB_NAME', 'searxng_cool_music')
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(db_url)
    
    inspector = inspect(engine)
    
    # Get all tables
    tables = inspector.get_table_names()
    print(f"Found {len(tables)} tables in the database")
    
    # Get indexes
    all_indexes = []
    for table in tables:
        indexes = inspector.get_indexes(table)
        for idx in indexes:
            if not idx['name'].startswith('pk_'):  # Skip primary keys
                all_indexes.append(idx['name'])
    
    print(f"Found {len(all_indexes)} indexes")
    
    return tables, all_indexes


def main():
    """Main function"""
    print("Analyzing current database state...")
    tables, indexes = analyze_database()
    
    print("\nGenerating migration file...")
    migration_content = generate_migration_file(tables, indexes)
    
    # Create the migration file
    migration_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations', 'versions')
    os.makedirs(migration_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_initial_schema.py"
    filepath = os.path.join(migration_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write(migration_content)
    
    print(f"\nMigration file created: {filepath}")
    print("\nNext steps:")
    print("1. Review the generated migration file")
    print("2. Run: cd /home/mik/SEARXNG/searxng-cool")
    print("3. Run: FLASK_APP=migrations/migration_app.py flask db upgrade")


if __name__ == "__main__":
    main()