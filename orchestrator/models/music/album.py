"""
Album Model with Multi-Source Support
Part of SearXNG-Cool Music Database Foundation
"""
from datetime import datetime, date
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from orchestrator.database import db


class Album(db.Model):
    """
    Album model supporting multiple music sources
    with comprehensive metadata and version tracking
    """
    __tablename__ = 'albums'
    
    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    
    # Album identification
    upc = db.Column(db.String(12), index=True)  # Universal Product Code
    catalog_number = db.Column(db.String(100))  # Label catalog number
    musicbrainz_id = db.Column(db.String(36), unique=True, index=True)
    
    # Album information
    album_type = db.Column(db.String(20), default='album')  # album, single, compilation, ep
    release_date = db.Column(db.Date)
    release_precision = db.Column(db.String(10))  # year, month, day
    
    # Media
    cover_url = db.Column(db.String(500))
    cover_url_small = db.Column(db.String(500))
    cover_url_large = db.Column(db.String(500))
    
    # Album details
    label = db.Column(db.String(255))
    total_tracks = db.Column(db.Integer)
    total_discs = db.Column(db.Integer, default=1)
    
    # Metadata
    genres = db.Column(JSONB, default=[])
    styles = db.Column(JSONB, default=[])  # Sub-genres or musical styles
    moods = db.Column(JSONB, default=[])   # Happy, sad, energetic, etc.
    themes = db.Column(JSONB, default=[])  # Love, politics, party, etc.
    
    # Credits and contributors
    credits = db.Column(JSONB, default={})
    # Structure: {role: [person_names]}, e.g., {"producer": ["Rick Rubin"], "engineer": ["..."] }
    
    # Popularity and metrics
    popularity = db.Column(db.Float, default=0.0)  # Normalized 0-1
    rating = db.Column(db.Float)  # Average user rating
    rating_count = db.Column(db.Integer, default=0)
    
    # Additional metadata
    extra_metadata = db.Column(JSONB, default={})
    # Can include: recording_location, mastering_details, liner_notes, awards
    
    # Version tracking for different releases
    is_remaster = db.Column(db.Boolean, default=False)
    original_release_date = db.Column(db.Date)
    version_notes = db.Column(db.Text)  # e.g., "2020 Remaster", "Deluxe Edition"
    
    # Search optimization
    search_vector = db.Column(db.Text)  # For full-text search
    
    # Relationships
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), index=True)
    artist = db.relationship('Artist', back_populates='albums')
    tracks = db.relationship('Track', back_populates='album', lazy='dynamic', order_by='Track.id')
    sources = db.relationship('AlbumSource', back_populates='album', cascade='all, delete-orphan')
    user_collections = db.relationship('UserAlbumCollection', back_populates='album', cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = db.Column(db.DateTime)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_album_search', 'title', 'artist_id'),
        Index('idx_album_release', 'release_date'),
        Index('idx_album_type', 'album_type'),
    )
    
    def __repr__(self):
        return f'<Album {self.id}: {self.title}>'
    
    def to_dict(self, include_tracks=False, include_sources=False):
        """Convert album to dictionary for API responses"""
        data = {
            'id': self.id,
            'title': self.title,
            'artist_id': self.artist_id,
            'album_type': self.album_type,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'release_precision': self.release_precision,
            'cover_url': self.cover_url,
            'cover_url_small': self.cover_url_small,
            'cover_url_large': self.cover_url_large,
            'label': self.label,
            'total_tracks': self.total_tracks,
            'total_discs': self.total_discs,
            'genres': self.genres or [],
            'popularity': self.popularity,
            'rating': self.rating,
            'is_remaster': self.is_remaster,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_tracks:
            data['tracks'] = [track.to_dict() for track in self.tracks]
            
        if include_sources:
            data['sources'] = [source.to_dict() for source in self.sources]
            
        return data


class AlbumSource(db.Model):
    """
    Links albums to their sources across multiple music services
    """
    __tablename__ = 'album_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=False, index=True)
    
    # Source identification
    source_type = db.Column(db.String(50), nullable=False, index=True)
    source_id = db.Column(db.String(255), nullable=False)
    source_uri = db.Column(db.String(500))
    
    # Source-specific data
    source_extra_metadata = db.Column(JSONB, default={})
    # Can include: play_count, saves, source_specific_genres, editorial_notes
    
    # Availability
    is_available = db.Column(db.Boolean, default=True)
    geo_restrictions = db.Column(JSONB)  # List of country codes
    
    # Sync metadata
    is_primary = db.Column(db.Boolean, default=False)
    last_synced = db.Column(db.DateTime)
    sync_status = db.Column(db.String(20), default='active')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    album = db.relationship('Album', back_populates='sources')
    
    # Ensure unique source per album
    __table_args__ = (
        UniqueConstraint('album_id', 'source_type', 'source_id', name='uq_album_source'),
    )
    
    def __repr__(self):
        return f'<AlbumSource {self.source_type}:{self.source_id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_uri': self.source_uri,
            'is_available': self.is_available,
            'is_primary': self.is_primary,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
        }