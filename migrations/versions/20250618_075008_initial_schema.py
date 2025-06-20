"""Initial database schema capture

Revision ID: 20250618_075008_initial_schema
Revises: manual_creation_20250617
Create Date: 2025-06-18 07:50:08

This migration captures the existing database schema that was manually created.
It serves as the baseline for future migrations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250618_075008_initial_schema'
down_revision = None
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
    op.execute('DROP INDEX IF EXISTS uq_playlist_track_vote')
    op.execute('DROP INDEX IF EXISTS uq_user_album_collection')
    op.execute('DROP INDEX IF EXISTS uq_user_artist_follow')
    op.execute('DROP INDEX IF EXISTS uq_session_track_position')
    op.execute('DROP INDEX IF EXISTS uq_user_playlist_follow')
    op.execute('DROP INDEX IF EXISTS idx_discovery_session_user')
    op.execute('DROP INDEX IF EXISTS idx_discovery_session_type')
    op.execute('DROP INDEX IF EXISTS discovery_sessions_uuid_key')
    op.execute('DROP INDEX IF EXISTS idx_user_interaction_session')
    op.execute('DROP INDEX IF EXISTS idx_user_interaction_analytics')
    op.execute('DROP INDEX IF EXISTS uq_user_library_track')
    op.execute('DROP INDEX IF EXISTS idx_user_library_favorites')
    op.execute('DROP INDEX IF EXISTS idx_playlist_activity_time')
    op.execute('DROP INDEX IF EXISTS uq_playlist_collaborator')
    op.execute('DROP INDEX IF EXISTS uq_playlist_position')
    op.execute('DROP INDEX IF EXISTS idx_playlist_track')
    op.execute('DROP INDEX IF EXISTS uq_album_source')
    op.execute('DROP INDEX IF EXISTS uq_artist_source')
    op.execute('DROP INDEX IF EXISTS uq_track_source')
    op.execute('DROP INDEX IF EXISTS idx_source_availability')
    op.execute('DROP INDEX IF EXISTS user_music_profiles_user_id_key')
    op.execute('DROP INDEX IF EXISTS playlists_uuid_key')
    op.execute('DROP INDEX IF EXISTS playlists_share_token_key')
    op.execute('DROP INDEX IF EXISTS idx_playlist_owner')
    op.execute('DROP INDEX IF EXISTS idx_playlist_hierarchy')
    op.execute('DROP INDEX IF EXISTS idx_playlist_collaborative')
    op.execute('DROP INDEX IF EXISTS users_username_key')
    op.execute('DROP INDEX IF EXISTS users_email_key')
    op.execute('DROP INDEX IF EXISTS idx_track_search')
    op.execute('DROP INDEX IF EXISTS idx_track_popularity')
    op.execute('DROP INDEX IF EXISTS idx_track_audio')
    op.execute('DROP INDEX IF EXISTS idx_album_type')
    op.execute('DROP INDEX IF EXISTS idx_album_search')
    op.execute('DROP INDEX IF EXISTS idx_album_release')
    op.execute('DROP INDEX IF EXISTS albums_musicbrainz_id_key')
    op.execute('DROP INDEX IF EXISTS idx_artist_search')
    op.execute('DROP INDEX IF EXISTS idx_artist_popularity')
    op.execute('DROP INDEX IF EXISTS idx_artist_country')
    op.execute('DROP INDEX IF EXISTS artists_musicbrainz_id_key')

    
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
