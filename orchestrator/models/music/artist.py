"""
Artist Model with Multi-Source Support
Part of SearXNG-Cool Music Database Foundation
"""
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from orchestrator.database import db


class Artist(db.Model):
    """
    Artist model supporting multiple music sources
    with comprehensive metadata and relationship tracking
    """
    __tablename__ = 'artists'
    
    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    sort_name = db.Column(db.String(255))  # For proper sorting (e.g., "Beatles, The")
    
    # Multi-source identification
    musicbrainz_id = db.Column(db.String(36), unique=True, index=True)  # UUID format
    spotify_id = db.Column(db.String(255), index=True)
    
    # Artist information
    bio = db.Column(db.Text)
    country = db.Column(db.String(2))  # ISO country code
    formed_year = db.Column(db.Integer)
    disbanded_year = db.Column(db.Integer)
    
    # Media
    image_url = db.Column(db.String(500))
    thumbnail_url = db.Column(db.String(500))
    banner_url = db.Column(db.String(500))
    
    # Metadata
    genres = db.Column(JSONB, default=[])  # Array of genre names
    aliases = db.Column(JSONB, default=[])  # Alternative names
    members = db.Column(JSONB, default=[])  # For bands: current and past members
    social_links = db.Column(JSONB, default={})  # website, twitter, instagram, etc.
    
    # Popularity and metrics
    popularity = db.Column(db.Float, default=0.0)  # Normalized 0-1
    follower_count = db.Column(db.Integer, default=0)
    monthly_listeners = db.Column(db.Integer)
    
    # Verification status
    is_verified = db.Column(db.Boolean, default=False)
    verification_source = db.Column(db.String(50))  # Which platform verified them
    
    # Additional metadata
    extra_metadata = db.Column(JSONB, default={})
    # Can include: awards, associated_acts, influences, label_history
    
    # Search optimization
    search_vector = db.Column(db.Text)  # For full-text search
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = db.Column(db.DateTime)  # Last sync with external sources
    
    # Relationships
    tracks = db.relationship('Track', back_populates='artist', lazy='dynamic')
    albums = db.relationship('Album', back_populates='artist', lazy='dynamic')
    sources = db.relationship('ArtistSource', back_populates='artist', cascade='all, delete-orphan')
    followers = db.relationship('UserArtistFollow', back_populates='artist', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_artist_search', 'name', 'sort_name'),
        Index('idx_artist_popularity', 'popularity'),
        Index('idx_artist_country', 'country'),
    )
    
    def __repr__(self):
        return f'<Artist {self.id}: {self.name}>'
    
    def to_dict(self, include_stats=False, include_sources=False):
        """Convert artist to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name,
            'sort_name': self.sort_name,
            'bio': self.bio,
            'country': self.country,
            'formed_year': self.formed_year,
            'disbanded_year': self.disbanded_year,
            'image_url': self.image_url,
            'thumbnail_url': self.thumbnail_url,
            'genres': self.genres or [],
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_stats:
            data.update({
                'popularity': self.popularity,
                'follower_count': self.follower_count,
                'monthly_listeners': self.monthly_listeners,
                'track_count': self.tracks.count(),
                'album_count': self.albums.count(),
            })
            
        if include_sources:
            data['sources'] = [source.to_dict() for source in self.sources]
            
        return data


class ArtistSource(db.Model):
    """
    Links artists to their profiles across multiple music services
    """
    __tablename__ = 'artist_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False, index=True)
    
    # Source identification
    source_type = db.Column(db.String(50), nullable=False, index=True)
    source_id = db.Column(db.String(255), nullable=False)
    source_uri = db.Column(db.String(500))
    
    # Source-specific data
    source_extra_metadata = db.Column(JSONB, default={})
    # Can include: follower_count, play_count, verified_status, bio
    
    # Sync metadata
    is_primary = db.Column(db.Boolean, default=False)  # Primary source for this artist
    last_synced = db.Column(db.DateTime)
    sync_status = db.Column(db.String(20), default='active')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    artist = db.relationship('Artist', back_populates='sources')
    
    # Ensure unique source per artist
    __table_args__ = (
        UniqueConstraint('artist_id', 'source_type', 'source_id', name='uq_artist_source'),
    )
    
    def __repr__(self):
        return f'<ArtistSource {self.source_type}:{self.source_id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_uri': self.source_uri,
            'is_primary': self.is_primary,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
        }