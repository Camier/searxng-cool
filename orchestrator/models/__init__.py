"""Database models for SearXNG-Cool"""
from orchestrator.database import db  # Import from database.py, NOT app.py

# Import all models here
from .user import User

# Import all music models
from .music import (
    # Track models
    Track,
    TrackSource,
    
    # Artist models
    Artist,
    ArtistSource,
    
    # Album models
    Album,
    AlbumSource,
    
    # Playlist models
    Playlist,
    PlaylistTrack,
    PlaylistCollaborator,
    PlaylistActivity,
    
    # User music models
    UserMusicProfile,
    UserLibrary,
    UserInteraction,
    DiscoverySession,
    DiscoverySessionTrack,
    UserArtistFollow,
    PlaylistFollow,
    UserAlbumCollection,
    PlaylistTrackVote,
)

__all__ = [
    'User',
    
    # Track models
    'Track',
    'TrackSource',
    
    # Artist models
    'Artist',
    'ArtistSource',
    
    # Album models
    'Album',
    'AlbumSource',
    
    # Playlist models
    'Playlist',
    'PlaylistTrack',
    'PlaylistCollaborator',
    'PlaylistActivity',
    
    # User music models
    'UserMusicProfile',
    'UserLibrary',
    'UserInteraction',
    'DiscoverySession',
    'DiscoverySessionTrack',
    'UserArtistFollow',
    'PlaylistFollow',
    'UserAlbumCollection',
    'PlaylistTrackVote',
]