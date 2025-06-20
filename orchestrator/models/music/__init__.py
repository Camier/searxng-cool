"""
Music Models Package - SearXNG-Cool Music Database Foundation
Comprehensive music database models with multi-source support
"""

# Track and source models
from .track import Track, TrackSource

# Artist models
from .artist import Artist, ArtistSource

# Album models
from .album import Album, AlbumSource

# Playlist models
from .playlist import (
    Playlist,
    PlaylistTrack,
    PlaylistCollaborator,
    PlaylistActivity
)

# User music extensions
from .user_music import (
    UserMusicProfile,
    UserLibrary,
    UserInteraction,
    DiscoverySession,
    DiscoverySessionTrack,
    UserArtistFollow,
    PlaylistFollow,
    UserAlbumCollection,
    PlaylistTrackVote
)

__all__ = [
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