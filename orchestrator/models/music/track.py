"""
Track Model with Multi-Source Support and Audio Analysis
Part of SearXNG-Cool Music Database Foundation
"""
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from orchestrator.database import db


class Track(db.Model):
    """
    Universal track model supporting multiple music sources
    with comprehensive metadata and audio analysis capabilities
    """
    __tablename__ = 'tracks'
    
    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False, index=True)
    duration_ms = db.Column(db.Integer)  # Duration in milliseconds
    isrc = db.Column(db.String(12), index=True)  # International Standard Recording Code
    
    # Audio fingerprinting for deduplication
    audio_fingerprint = db.Column(db.String(255), index=True)
    fingerprint_algorithm = db.Column(db.String(50))  # e.g., 'chromaprint', 'echoprint'
    
    # Audio analysis metadata (stored as JSONB for flexibility)
    audio_features = db.Column(JSONB, default={})
    # Expected keys: bpm, key, key_confidence, time_signature, loudness, 
    # energy, danceability, valence, acousticness, instrumentalness
    
    # Relationships
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), index=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), index=True)
    
    # Rich metadata
    explicit = db.Column(db.Boolean, default=False)
    popularity = db.Column(db.Float, default=0.0)  # Normalized 0-1
    preview_url = db.Column(db.String(500))
    lyrics = db.Column(db.Text)
    
    # Additional metadata as JSONB
    extra_metadata = db.Column(JSONB, default={})
    # Can include: genres, moods, themes, instruments, recording_date, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = db.Column(db.DateTime)  # When audio analysis was last performed
    
    # Search optimization
    search_vector = db.Column(db.Text)  # For full-text search
    
    # Relationships
    artist = db.relationship('Artist', back_populates='tracks')
    album = db.relationship('Album', back_populates='tracks')
    sources = db.relationship('TrackSource', back_populates='track', cascade='all, delete-orphan')
    playlists = db.relationship('PlaylistTrack', back_populates='track', cascade='all, delete-orphan')
    user_libraries = db.relationship('UserLibrary', back_populates='track', cascade='all, delete-orphan')
    interactions = db.relationship('UserInteraction', back_populates='track', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_track_search', 'title', 'artist_id'),
        Index('idx_track_audio', 'audio_fingerprint'),
        Index('idx_track_popularity', 'popularity'),
    )
    
    def __repr__(self):
        return f'<Track {self.id}: {self.title}>'
    
    def to_dict(self, include_sources=False, include_audio_features=False):
        """Convert track to dictionary for API responses"""
        data = {
            'id': self.id,
            'title': self.title,
            'duration_ms': self.duration_ms,
            'isrc': self.isrc,
            'artist_id': self.artist_id,
            'album_id': self.album_id,
            'explicit': self.explicit,
            'popularity': self.popularity,
            'preview_url': self.preview_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_audio_features and self.audio_features:
            data['audio_features'] = self.audio_features
            
        if include_sources:
            data['sources'] = [source.to_dict() for source in self.sources]
            
        return data


class TrackSource(db.Model):
    """
    Links tracks to their sources across multiple music services
    Enables multi-source aggregation and fallback playback
    """
    __tablename__ = 'track_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False, index=True)
    
    # Source identification
    source_type = db.Column(db.String(50), nullable=False, index=True)  # spotify, youtube, soundcloud, etc.
    source_id = db.Column(db.String(255), nullable=True)  # ID in the source system (optional)
    source_uri = db.Column(db.String(500))  # Full URI for the source
    
    # Source-specific data
    source_extra_metadata = db.Column(JSONB, default={})
    # Can include: play_count, likes, comments, source_specific_features
    
    # Quality and availability
    audio_quality = db.Column(db.String(20))  # high, medium, low
    is_available = db.Column(db.Boolean, default=True)
    geo_restrictions = db.Column(JSONB)  # List of country codes where available
    
    # Sync metadata
    last_synced = db.Column(db.DateTime)
    sync_status = db.Column(db.String(20), default='active')  # active, failed, removed
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    track = db.relationship('Track', back_populates='sources')
    
    # Ensure unique source per track
    __table_args__ = (
        UniqueConstraint('track_id', 'source_type', 'source_id', name='uq_track_source'),
        Index('idx_source_availability', 'source_type', 'is_available'),
    )
    
    def __repr__(self):
        return f'<TrackSource {self.source_type}:{self.source_id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_uri': self.source_uri,
            'audio_quality': self.audio_quality,
            'is_available': self.is_available,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
        }