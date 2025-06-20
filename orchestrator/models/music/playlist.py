"""
Playlist Management System with Collaborative and Hierarchical Support
Part of SearXNG-Cool Music Database Foundation
"""
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid
from orchestrator.database import db


class Playlist(db.Model):
    """
    Advanced playlist model supporting collaboration, hierarchy,
    and real-time synchronization
    """
    __tablename__ = 'playlists'
    
    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False, index=True)
    
    # Ownership and collaboration
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False, index=True)
    is_collaborative = db.Column(db.Boolean, default=False)
    
    # Hierarchy support
    parent_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), index=True)
    folder_type = db.Column(db.Boolean, default=False)  # True if this is a folder, not a playlist
    
    # Playlist metadata
    description = db.Column(db.Text)
    cover_url = db.Column(db.String(500))
    tags = db.Column(JSONB, default=[])  # User-defined tags
    
    # Auto-playlist features
    is_dynamic = db.Column(db.Boolean, default=False)  # Auto-updating based on rules
    dynamic_rules = db.Column(JSONB)  # Rules for dynamic playlists
    # Example: {"genre": ["rock", "indie"], "year_range": [2020, 2024], "min_popularity": 0.7}
    
    # Collaboration settings
    collaboration_mode = db.Column(db.String(20), default='open')  # open, approval_required, invite_only
    max_tracks_per_user = db.Column(db.Integer)  # Limit tracks per collaborator
    voting_enabled = db.Column(db.Boolean, default=False)  # Enable track voting
    
    # Privacy and sharing
    share_token = db.Column(db.String(32), unique=True, index=True)  # For sharing via link
    password_hash = db.Column(db.String(255))  # Optional password protection
    expires_at = db.Column(db.DateTime)  # Optional expiration date
    
    # Statistics
    play_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    total_duration_ms = db.Column(db.BigInteger, default=0)
    
    # Metadata and features
    extra_metadata = db.Column(JSONB, default={})
    # Can include: mood_profile, energy_curve, genre_distribution, decade_distribution
    
    # Version tracking for collaborative editing
    version = db.Column(db.Integer, default=1)
    last_modified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Search optimization
    search_vector = db.Column(db.Text)  # For full-text search
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_played_at = db.Column(db.DateTime)
    
    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_playlists')
    parent = db.relationship('Playlist', remote_side=[id], backref='children')
    tracks = db.relationship('PlaylistTrack', back_populates='playlist', cascade='all, delete-orphan', order_by='PlaylistTrack.position')
    collaborators = db.relationship('PlaylistCollaborator', back_populates='playlist', cascade='all, delete-orphan')
    followers = db.relationship('PlaylistFollow', back_populates='playlist', cascade='all, delete-orphan')
    activities = db.relationship('PlaylistActivity', back_populates='playlist', cascade='all, delete-orphan')
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_playlist_owner', 'owner_id', 'is_public'),
        Index('idx_playlist_hierarchy', 'parent_id'),
        Index('idx_playlist_collaborative', 'is_collaborative', 'is_public'),
        CheckConstraint('NOT (folder_type = true AND is_dynamic = true)', name='ck_folder_not_dynamic'),
    )
    
    def __repr__(self):
        return f'<Playlist {self.id}: {self.name}>'
    
    def to_dict(self, include_tracks=False, include_stats=False):
        """Convert playlist to dictionary for API responses"""
        data = {
            'id': self.id,
            'uuid': str(self.uuid),
            'name': self.name,
            'owner_id': self.owner_id,
            'is_public': self.is_public,
            'is_collaborative': self.is_collaborative,
            'description': self.description,
            'cover_url': self.cover_url,
            'tags': self.tags or [],
            'is_dynamic': self.is_dynamic,
            'folder_type': self.folder_type,
            'parent_id': self.parent_id,
            'track_count': len(self.tracks),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_stats:
            data.update({
                'play_count': self.play_count,
                'like_count': self.like_count,
                'share_count': self.share_count,
                'total_duration_ms': self.total_duration_ms,
                'collaborator_count': len(self.collaborators),
                'follower_count': len(self.followers),
            })
            
        if include_tracks:
            data['tracks'] = [pt.to_dict() for pt in self.tracks]
            
        return data


class PlaylistTrack(db.Model):
    """
    Tracks within playlists with position and metadata
    """
    __tablename__ = 'playlist_tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False, index=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    
    # Who added the track and when
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Collaborative features
    vote_count = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)  # Prevent removal/reordering
    
    # Track-specific metadata within playlist context
    custom_note = db.Column(db.String(500))  # User note about why track was added
    start_time_ms = db.Column(db.Integer)  # Custom start time for the track
    end_time_ms = db.Column(db.Integer)    # Custom end time for the track
    
    # Relationships
    playlist = db.relationship('Playlist', back_populates='tracks')
    track = db.relationship('Track', back_populates='playlists')
    added_by_user = db.relationship('User', foreign_keys=[added_by])
    votes = db.relationship('PlaylistTrackVote', back_populates='playlist_track', cascade='all, delete-orphan')
    
    # Ensure unique track per position in playlist
    __table_args__ = (
        UniqueConstraint('playlist_id', 'position', name='uq_playlist_position'),
        Index('idx_playlist_track', 'playlist_id', 'track_id'),
    )
    
    def __repr__(self):
        return f'<PlaylistTrack {self.playlist_id}:{self.position}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'position': self.position,
            'added_by': self.added_by,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'vote_count': self.vote_count,
            'is_locked': self.is_locked,
            'custom_note': self.custom_note,
        }


class PlaylistCollaborator(db.Model):
    """
    Manages playlist collaborators and their permissions
    """
    __tablename__ = 'playlist_collaborators'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Permissions
    can_add_tracks = db.Column(db.Boolean, default=True)
    can_remove_tracks = db.Column(db.Boolean, default=True)
    can_reorder_tracks = db.Column(db.Boolean, default=True)
    can_invite_others = db.Column(db.Boolean, default=False)
    can_change_details = db.Column(db.Boolean, default=False)  # Name, description, cover
    
    # Collaboration metadata
    role = db.Column(db.String(20), default='editor')  # owner, admin, editor, viewer
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    invitation_status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    
    # Activity tracking
    tracks_added = db.Column(db.Integer, default=0)
    tracks_removed = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime)
    
    # Timestamps
    invited_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    joined_at = db.Column(db.DateTime)
    
    # Relationships
    playlist = db.relationship('Playlist', back_populates='collaborators')
    user = db.relationship('User', foreign_keys=[user_id], backref='playlist_collaborations')
    inviter = db.relationship('User', foreign_keys=[invited_by])
    
    # Ensure unique user per playlist
    __table_args__ = (
        UniqueConstraint('playlist_id', 'user_id', name='uq_playlist_collaborator'),
    )
    
    def __repr__(self):
        return f'<PlaylistCollaborator {self.user_id} on {self.playlist_id}>'


class PlaylistActivity(db.Model):
    """
    Tracks all activities on collaborative playlists for real-time updates
    """
    __tablename__ = 'playlist_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Activity details
    activity_type = db.Column(db.String(50), nullable=False)  # track_added, track_removed, track_moved, etc.
    activity_data = db.Column(JSONB, default={})
    # Example: {"track_id": 123, "position": 5, "old_position": 10}
    
    # For real-time sync
    playlist_version = db.Column(db.Integer, nullable=False)  # Playlist version after this activity
    
    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    playlist = db.relationship('Playlist', back_populates='activities')
    user = db.relationship('User')
    
    # Index for efficient activity queries
    __table_args__ = (
        Index('idx_playlist_activity_time', 'playlist_id', 'created_at'),
    )