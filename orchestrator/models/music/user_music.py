"""
User Music Extensions - Music profiles, interactions, and discovery sessions
Part of SearXNG-Cool Music Database Foundation
"""
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid
from orchestrator.database import db


class UserMusicProfile(db.Model):
    """
    Extended music profile for users with preferences and listening habits
    """
    __tablename__ = 'user_music_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Music preferences
    favorite_genres = db.Column(JSONB, default=[])
    disliked_genres = db.Column(JSONB, default=[])
    favorite_decades = db.Column(JSONB, default=[])  # e.g., ["1980s", "1990s", "2020s"]
    
    # Listening preferences
    preferred_audio_quality = db.Column(db.String(20), default='high')  # low, medium, high, lossless
    explicit_content_allowed = db.Column(db.Boolean, default=True)
    discovery_mode = db.Column(db.String(20), default='balanced')  # conservative, balanced, adventurous
    
    # Personalization settings
    energy_preference = db.Column(db.Float, default=0.5)  # 0-1, preferred energy level
    mood_preferences = db.Column(JSONB, default={})  # {"happy": 0.7, "melancholic": 0.3, ...}
    language_preferences = db.Column(JSONB, default=[])  # ISO language codes
    
    # Listening statistics
    total_listening_time_ms = db.Column(db.BigInteger, default=0)
    tracks_played = db.Column(db.Integer, default=0)
    unique_tracks_played = db.Column(db.Integer, default=0)
    unique_artists_played = db.Column(db.Integer, default=0)
    average_session_duration_ms = db.Column(db.BigInteger, default=0)
    
    # Discovery statistics
    discovery_ratio = db.Column(db.Float, default=0.0)  # Ratio of new vs familiar tracks
    genre_diversity_score = db.Column(db.Float, default=0.0)  # 0-1, how diverse their taste is
    
    # Time-based preferences
    time_based_preferences = db.Column(JSONB, default={})
    # Example: {"morning": {"energy": 0.3, "genres": ["ambient", "classical"]}, ...}
    
    # Device preferences
    device_preferences = db.Column(JSONB, default={})
    # Example: {"mobile": {"quality": "medium"}, "desktop": {"quality": "high"}}
    
    # ML/AI features
    taste_vector = db.Column(JSONB)  # Computed taste embedding for recommendations
    last_taste_update = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='music_profile', uselist=False)
    
    def __repr__(self):
        return f'<UserMusicProfile {self.user_id}>'


class UserLibrary(db.Model):
    """
    User's personal music library with saved tracks
    """
    __tablename__ = 'user_library'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False, index=True)
    
    # Library metadata
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    tags = db.Column(JSONB, default=[])  # User-defined tags
    rating = db.Column(db.Integer)  # 1-5 star rating
    
    # Playback statistics
    play_count = db.Column(db.Integer, default=0)
    skip_count = db.Column(db.Integer, default=0)
    last_played_at = db.Column(db.DateTime)
    total_play_time_ms = db.Column(db.BigInteger, default=0)
    
    # User metadata
    notes = db.Column(db.Text)  # Personal notes about the track
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='library_tracks')
    track = db.relationship('Track', back_populates='user_libraries')
    
    # Ensure unique track per user library
    __table_args__ = (
        UniqueConstraint('user_id', 'track_id', name='uq_user_library_track'),
        Index('idx_user_library_favorites', 'user_id', 'is_favorite'),
    )
    
    def __repr__(self):
        return f'<UserLibrary {self.user_id}:{self.track_id}>'


class UserInteraction(db.Model):
    """
    Detailed user interactions with tracks for analytics and recommendations
    """
    __tablename__ = 'user_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False, index=True)
    
    # Interaction type and context
    interaction_type = db.Column(db.String(50), nullable=False, index=True)
    # Types: play, skip, like, dislike, share, add_to_playlist, remove_from_playlist
    
    # Context information
    context_type = db.Column(db.String(50))  # playlist, album, radio, search, discovery
    context_id = db.Column(db.String(255))   # ID of playlist, album, etc.
    
    # Playback details (for play interactions)
    play_duration_ms = db.Column(db.Integer)  # How long they listened
    track_duration_ms = db.Column(db.Integer)  # Total track duration
    completion_percentage = db.Column(db.Float)  # % of track played
    
    # Skip details (for skip interactions)
    skip_position_ms = db.Column(db.Integer)  # When in the track they skipped
    skip_reason = db.Column(db.String(50))  # manual, auto_next, error
    
    # Device and session info
    device_type = db.Column(db.String(50))  # mobile, desktop, tablet, smart_speaker
    session_id = db.Column(UUID(as_uuid=True))
    
    # Additional metadata
    extra_metadata = db.Column(JSONB, default={})
    # Can include: audio_quality, network_type, volume_level, shuffle_state
    
    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='track_interactions')
    track = db.relationship('Track', back_populates='interactions')
    
    # Indexes for analytics
    __table_args__ = (
        Index('idx_user_interaction_analytics', 'user_id', 'interaction_type', 'created_at'),
        Index('idx_user_interaction_session', 'session_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<UserInteraction {self.user_id}:{self.interaction_type}:{self.track_id}>'


class DiscoverySession(db.Model):
    """
    Music discovery sessions for tracking and improving recommendations
    """
    __tablename__ = 'discovery_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Session details
    session_type = db.Column(db.String(50), nullable=False)  # radio, daily_mix, discover_weekly, genre_explore
    session_name = db.Column(db.String(255))
    
    # Discovery parameters
    seed_type = db.Column(db.String(50))  # track, artist, genre, mood
    seed_data = db.Column(JSONB)  # IDs or values used as seeds
    discovery_params = db.Column(JSONB, default={})
    # Example: {"energy_range": [0.4, 0.8], "popularity_weight": 0.3, "diversity": 0.7}
    
    # Session statistics
    tracks_presented = db.Column(db.Integer, default=0)
    tracks_played = db.Column(db.Integer, default=0)
    tracks_skipped = db.Column(db.Integer, default=0)
    tracks_liked = db.Column(db.Integer, default=0)
    tracks_added_to_library = db.Column(db.Integer, default=0)
    
    # Engagement metrics
    total_play_time_ms = db.Column(db.BigInteger, default=0)
    average_play_percentage = db.Column(db.Float, default=0.0)
    discovery_score = db.Column(db.Float)  # Calculated engagement score
    
    # ML/AI feedback
    user_satisfaction = db.Column(db.Float)  # Explicit or implicit feedback
    algorithm_version = db.Column(db.String(50))  # Track which recommendation algorithm was used
    
    # Session state
    is_active = db.Column(db.Boolean, default=True)
    current_position = db.Column(db.Integer, default=0)  # Current track in session
    
    # Timestamps
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    last_interaction_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='discovery_sessions')
    session_tracks = db.relationship('DiscoverySessionTrack', back_populates='session', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_discovery_session_user', 'user_id', 'is_active'),
        Index('idx_discovery_session_type', 'session_type', 'started_at'),
    )
    
    def __repr__(self):
        return f'<DiscoverySession {self.id}: {self.session_type}>'


class DiscoverySessionTrack(db.Model):
    """
    Tracks presented in discovery sessions with interaction data
    """
    __tablename__ = 'discovery_session_tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('discovery_sessions.id'), nullable=False, index=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # Order in session
    
    # Recommendation metadata
    recommendation_score = db.Column(db.Float)  # Algorithm's confidence
    recommendation_reasons = db.Column(JSONB, default=[])
    # Example: ["similar_to_liked_artist", "trending_in_genre", "collaborative_filtering"]
    
    # User interaction
    was_played = db.Column(db.Boolean, default=False)
    play_duration_ms = db.Column(db.Integer)
    was_skipped = db.Column(db.Boolean, default=False)
    skip_time_ms = db.Column(db.Integer)
    was_liked = db.Column(db.Boolean, default=False)
    was_added_to_library = db.Column(db.Boolean, default=False)
    
    # Presentation metadata
    presented_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    interacted_at = db.Column(db.DateTime)
    
    # Relationships
    session = db.relationship('DiscoverySession', back_populates='session_tracks')
    track = db.relationship('Track')
    
    # Ensure unique track position per session
    __table_args__ = (
        UniqueConstraint('session_id', 'position', name='uq_session_track_position'),
    )
    
    def __repr__(self):
        return f'<DiscoverySessionTrack {self.session_id}:{self.position}>'


class UserArtistFollow(db.Model):
    """
    Users following artists
    """
    __tablename__ = 'user_artist_follows'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False, index=True)
    
    # Follow metadata
    followed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    follow_source = db.Column(db.String(50))  # How they discovered the artist
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='followed_artists')
    artist = db.relationship('Artist', back_populates='followers')
    
    # Ensure unique follow
    __table_args__ = (
        UniqueConstraint('user_id', 'artist_id', name='uq_user_artist_follow'),
    )


class PlaylistFollow(db.Model):
    """
    Users following playlists
    """
    __tablename__ = 'playlist_follows'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False, index=True)
    
    # Follow metadata
    followed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='followed_playlists')
    playlist = db.relationship('Playlist', back_populates='followers')
    
    # Ensure unique follow
    __table_args__ = (
        UniqueConstraint('user_id', 'playlist_id', name='uq_user_playlist_follow'),
    )


class UserAlbumCollection(db.Model):
    """
    Users saving albums to their collection
    """
    __tablename__ = 'user_album_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=False, index=True)
    
    # Collection metadata
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tags = db.Column(JSONB, default=[])
    play_count = db.Column(db.Integer, default=0)
    
    # Relationships
    user = db.relationship('User', backref='album_collection')
    album = db.relationship('Album', back_populates='user_collections')
    
    # Ensure unique album per user
    __table_args__ = (
        UniqueConstraint('user_id', 'album_id', name='uq_user_album_collection'),
    )


class PlaylistTrackVote(db.Model):
    """
    Voting system for collaborative playlists
    """
    __tablename__ = 'playlist_track_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_track_id = db.Column(db.Integer, db.ForeignKey('playlist_tracks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    vote_type = db.Column(db.Integer, nullable=False)  # 1 for upvote, -1 for downvote
    voted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    playlist_track = db.relationship('PlaylistTrack', back_populates='votes')
    user = db.relationship('User')
    
    # Ensure one vote per user per track
    __table_args__ = (
        UniqueConstraint('playlist_track_id', 'user_id', name='uq_playlist_track_vote'),
    )