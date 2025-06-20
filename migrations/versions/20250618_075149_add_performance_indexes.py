"""Add performance indexes and optimizations

Revision ID: 20250618_075149_add_performance_indexes
Revises: 20250618_075149_initial_schema
Create Date: 2025-06-18 07:51:49

This migration adds critical performance indexes, JSONB indexes,
full-text search configuration, and other optimizations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250618_075149_add_performance_indexes'
down_revision = '20250618_075008_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes and optimizations"""
    
    # Foreign Key Indexes (Critical for JOIN performance)
    op.create_index('idx_tracks_artist_id', 'tracks', ['artist_id'])
    op.create_index('idx_tracks_album_id', 'tracks', ['album_id'])
    op.create_index('idx_playlist_tracks_playlist_id', 'playlist_tracks', ['playlist_id'])
    op.create_index('idx_playlist_tracks_track_id', 'playlist_tracks', ['track_id'])
    op.create_index('idx_user_interactions_user_id', 'user_interactions', ['user_id'])
    op.create_index('idx_user_interactions_track_id', 'user_interactions', ['track_id'])
    op.create_index('idx_user_library_user_id', 'user_library', ['user_id'])
    op.create_index('idx_user_library_track_id', 'user_library', ['track_id'])
    op.create_index('idx_discovery_sessions_user_id', 'discovery_sessions', ['user_id'])
    op.create_index('idx_discovery_session_tracks_session_id', 'discovery_session_tracks', ['session_id'])
    op.create_index('idx_discovery_session_tracks_track_id', 'discovery_session_tracks', ['track_id'])
    op.create_index('idx_playlist_collaborators_playlist_id', 'playlist_collaborators', ['playlist_id'])
    op.create_index('idx_playlist_collaborators_user_id', 'playlist_collaborators', ['user_id'])
    op.create_index('idx_playlist_activities_playlist_id', 'playlist_activities', ['playlist_id'])
    op.create_index('idx_playlist_activities_user_id', 'playlist_activities', ['user_id'])
    op.create_index('idx_track_sources_track_id', 'track_sources', ['track_id'])
    op.create_index('idx_artist_sources_artist_id', 'artist_sources', ['artist_id'])
    op.create_index('idx_album_sources_album_id', 'album_sources', ['album_id'])
    
    # Composite Indexes for Common Query Patterns
    op.create_index('idx_tracks_artist_album', 'tracks', ['artist_id', 'album_id'])
    op.create_index('idx_user_interactions_composite', 'user_interactions', 
                    ['user_id', 'track_id', 'interaction_type'])
    op.create_index('idx_playlist_tracks_position', 'playlist_tracks', ['playlist_id', 'position'])
    op.create_index('idx_user_library_composite', 'user_library', ['user_id', 'added_at'])
    op.create_index('idx_discovery_sessions_user_type', 'discovery_sessions', 
                    ['user_id', 'session_type'])
    
    # Time-based Query Indexes
    op.create_index('idx_user_interactions_created', 'user_interactions', [sa.text('created_at DESC')])
    op.create_index('idx_discovery_sessions_started', 'discovery_sessions', [sa.text('started_at DESC')])
    op.create_index('idx_playlist_activities_created', 'playlist_activities', [sa.text('created_at DESC')])
    op.create_index('idx_user_library_added', 'user_library', [sa.text('added_at DESC')])
    
    # JSONB GIN Indexes for Flexible Queries
    op.execute("CREATE INDEX idx_tracks_audio_features ON tracks USING GIN (audio_features)")
    op.execute("CREATE INDEX idx_artists_genres ON artists USING GIN (genres)")
    op.execute("CREATE INDEX idx_artists_aliases ON artists USING GIN (aliases)")
    op.execute("CREATE INDEX idx_artists_social_links ON artists USING GIN (social_links)")
    op.execute("CREATE INDEX idx_albums_genres ON albums USING GIN (genres)")
    op.execute("CREATE INDEX idx_albums_credits ON albums USING GIN (credits)")
    op.execute("CREATE INDEX idx_playlists_tags ON playlists USING GIN (tags)")
    op.execute("CREATE INDEX idx_playlists_dynamic_rules ON playlists USING GIN (dynamic_rules)")
    
    # Partial Indexes for Specific Queries
    # Note: Commented out due to syntax issues with :: in Alembic
    # These can be added manually later if needed
    # op.execute("""
    #     CREATE INDEX idx_tracks_high_energy 
    #     ON tracks ((audio_features->>'energy')::float) 
    #     WHERE (audio_features->>'energy')::float > 0.8
    # """)
    
    # op.execute("""
    #     CREATE INDEX idx_tracks_danceable 
    #     ON tracks ((audio_features->>'danceability')::float) 
    #     WHERE (audio_features->>'danceability')::float > 0.7
    # """)
    
    op.execute("""
        CREATE INDEX idx_playlists_public_collab 
        ON playlists (is_collaborative, is_public) 
        WHERE is_public = true AND is_collaborative = true
    """)
    
    # Full-Text Search Indexes
    op.execute("""
        CREATE INDEX idx_tracks_search 
        ON tracks USING GIN (to_tsvector('english', 
            COALESCE(title, '') || ' ' || COALESCE(search_vector, '')))
    """)
    
    op.execute("""
        CREATE INDEX idx_artists_search 
        ON artists USING GIN (to_tsvector('english', 
            COALESCE(name, '') || ' ' || COALESCE(search_vector, '')))
    """)
    
    op.execute("""
        CREATE INDEX idx_albums_search 
        ON albums USING GIN (to_tsvector('english', 
            COALESCE(title, '') || ' ' || COALESCE(search_vector, '')))
    """)
    
    op.execute("""
        CREATE INDEX idx_playlists_search 
        ON playlists USING GIN (to_tsvector('english', 
            COALESCE(name, '') || ' ' || COALESCE(description, '')))
    """)
    
    # Unique Constraint Indexes (if not already present)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_track_sources_unique 
        ON track_sources (track_id, source_type, source_id)
    """)
    
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_artist_sources_unique 
        ON artist_sources (artist_id, source_type, source_id)
    """)
    
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_album_sources_unique 
        ON album_sources (album_id, source_type, source_id)
    """)
    
    # Create helper function for updated_at triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Add updated_at triggers to all tables that have the column
    tables_with_updated_at = [
        'tracks', 'artists', 'albums', 'playlists', 'users',
        'user_music_profiles', 'discovery_sessions', 'playlist_activities'
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at 
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """.format(table=table))
    
    # Add check constraints for data validation
    op.execute("ALTER TABLE tracks ADD CONSTRAINT check_duration CHECK (duration_ms >= 0)")
    op.execute("ALTER TABLE user_interactions ADD CONSTRAINT check_play_duration CHECK (play_duration_ms >= 0)")
    op.execute("ALTER TABLE playlists ADD CONSTRAINT check_playlist_duration CHECK (total_duration_ms >= 0)")
    op.execute("ALTER TABLE albums ADD CONSTRAINT check_total_tracks CHECK (total_tracks >= 0)")
    
    # Create materialized view for track popularity
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_track_popularity AS
        SELECT 
            t.id,
            t.title,
            t.artist_id,
            COUNT(DISTINCT ui.user_id) as unique_listeners,
            COUNT(ui.id) FILTER (WHERE ui.interaction_type = 'play') as total_plays,
            COUNT(ui.id) FILTER (WHERE ui.interaction_type = 'like') as total_likes,
            COUNT(ui.id) FILTER (WHERE ui.interaction_type = 'skip') as total_skips,
            AVG(ui.play_duration_ms) FILTER (WHERE ui.interaction_type = 'play') as avg_play_duration,
            MAX(ui.created_at) as last_played_at
        FROM tracks t
        LEFT JOIN user_interactions ui ON t.id = ui.track_id
        GROUP BY t.id, t.title, t.artist_id
    """)
    
    op.execute("CREATE INDEX idx_mv_track_popularity_listeners ON mv_track_popularity(unique_listeners DESC)")
    op.execute("CREATE INDEX idx_mv_track_popularity_plays ON mv_track_popularity(total_plays DESC)")
    
    # Create indexes for the materialized view refresh
    op.execute("CREATE INDEX idx_user_interactions_track_type ON user_interactions(track_id, interaction_type)")


def downgrade() -> None:
    """Remove all optimization indexes and features"""
    
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_track_popularity CASCADE")
    
    # Drop triggers
    tables_with_updated_at = [
        'tracks', 'artists', 'albums', 'playlists', 'users',
        'user_music_profiles', 'discovery_sessions', 'playlist_activities'
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}".format(table=table))
    
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop check constraints
    op.execute("ALTER TABLE tracks DROP CONSTRAINT IF EXISTS check_duration")
    op.execute("ALTER TABLE user_interactions DROP CONSTRAINT IF EXISTS check_play_duration")
    op.execute("ALTER TABLE playlists DROP CONSTRAINT IF EXISTS check_playlist_duration")
    op.execute("ALTER TABLE albums DROP CONSTRAINT IF EXISTS check_total_tracks")
    
    # Drop all indexes created in upgrade
    indexes_to_drop = [
        # Foreign key indexes
        'idx_tracks_artist_id', 'idx_tracks_album_id',
        'idx_playlist_tracks_playlist_id', 'idx_playlist_tracks_track_id',
        'idx_user_interactions_user_id', 'idx_user_interactions_track_id',
        'idx_user_library_user_id', 'idx_user_library_track_id',
        'idx_discovery_sessions_user_id', 'idx_discovery_session_tracks_session_id',
        'idx_discovery_session_tracks_track_id', 'idx_playlist_collaborators_playlist_id',
        'idx_playlist_collaborators_user_id', 'idx_playlist_activities_playlist_id',
        'idx_playlist_activities_user_id', 'idx_track_sources_track_id',
        'idx_artist_sources_artist_id', 'idx_album_sources_album_id',
        
        # Composite indexes
        'idx_tracks_artist_album', 'idx_user_interactions_composite',
        'idx_playlist_tracks_position', 'idx_user_library_composite',
        'idx_discovery_sessions_user_type',
        
        # Time-based indexes
        'idx_user_interactions_created', 'idx_discovery_sessions_started',
        'idx_playlist_activities_created', 'idx_user_library_added',
        
        # JSONB indexes
        'idx_tracks_audio_features', 'idx_artists_genres', 'idx_artists_aliases',
        'idx_artists_social_links', 'idx_albums_genres', 'idx_albums_credits',
        'idx_playlists_tags', 'idx_playlists_dynamic_rules',
        
        # Partial indexes
        'idx_playlists_public_collab',
        
        # Full-text search indexes
        'idx_tracks_search', 'idx_artists_search', 'idx_albums_search', 'idx_playlists_search',
        
        # Unique constraint indexes
        'idx_track_sources_unique', 'idx_artist_sources_unique', 'idx_album_sources_unique',
        
        # Other indexes
        'idx_user_interactions_track_type'
    ]
    
    for idx in indexes_to_drop:
        op.drop_index(idx, if_exists=True)
