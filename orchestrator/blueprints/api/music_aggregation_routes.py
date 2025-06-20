"""
Music Aggregation API Routes for Flask Orchestrator
Provides endpoints for unified music search and playlist management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, jwt_optional
from datetime import datetime
import logging

from orchestrator.services.music_aggregation_service import (
    MusicAggregationService, UniversalPlaylist, UnifiedTrack
)

logger = logging.getLogger(__name__)

# Create blueprint
music_aggregation_bp = Blueprint('music_aggregation', __name__)

# Initialize service (would be better as dependency injection)
aggregation_service = MusicAggregationService()

# In-memory storage for playlists (should be database in production)
playlists_storage = {}


@music_aggregation_bp.route('/search/unified', methods=['POST'])
@jwt_optional
def unified_search():
    """
    Search across all music platforms and return unified results
    
    Request body:
    {
        "q": "search query",
        "limit": 50  # optional, default 50
    }
    
    Returns unified tracks with cross-platform availability
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('q'):
            return jsonify({
                'success': False,
                'error': 'Missing search query'
            }), 400
            
        query = data['q']
        limit = data.get('limit', 50)
        
        # Perform aggregated search
        start_time = datetime.now()
        results = aggregation_service.search_all_platforms(query, limit=limit)
        search_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Convert to response format
        response = {
            'success': True,
            'query': query,
            'total_results': len(results),
            'search_time_ms': round(search_time_ms, 2),
            'results': [track.to_dict() for track in results]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in unified search: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@music_aggregation_bp.route('/track/<track_id>/availability', methods=['GET'])
def check_track_availability(track_id):
    """
    Check which platforms have a specific track available
    
    This is a simplified version - in production would look up track by ID
    """
    # For demo, search for the track
    query = request.args.get('q', 'unknown')
    
    results = aggregation_service.search_all_platforms(query, limit=1)
    
    if not results:
        return jsonify({
            'success': False,
            'error': 'Track not found'
        }), 404
        
    track = results[0]
    availability = aggregation_service.get_platform_availability(track)
    
    return jsonify({
        'success': True,
        'track': {
            'title': track.title,
            'artist': track.artist,
            'unified_id': track.unified_id
        },
        'availability': availability,
        'platforms_count': sum(1 for v in availability.values() if v)
    }), 200


@music_aggregation_bp.route('/playlists', methods=['GET'])
@jwt_required
def list_playlists():
    """List all playlists for the current user"""
    user_id = get_jwt_identity()
    
    user_playlists = [
        p.to_dict() for p in playlists_storage.values() 
        if p.to_dict().get('user_id') == user_id
    ]
    
    return jsonify({
        'success': True,
        'playlists': user_playlists,
        'total': len(user_playlists)
    }), 200


@music_aggregation_bp.route('/playlists', methods=['POST'])
@jwt_required
def create_playlist():
    """
    Create a new universal playlist
    
    Request body:
    {
        "name": "Playlist name",
        "description": "Optional description"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Playlist name is required'
            }), 400
            
        name = data['name']
        description = data.get('description', '')
        
        # Create playlist
        playlist = UniversalPlaylist(name, description)
        
        # Add user_id to playlist data (hack for demo)
        playlist_dict = playlist.to_dict()
        playlist_dict['user_id'] = get_jwt_identity()
        
        # Store playlist
        playlists_storage[playlist.id] = playlist
        
        return jsonify({
            'success': True,
            'playlist': playlist_dict
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create playlist'
        }), 500


@music_aggregation_bp.route('/playlists/<playlist_id>', methods=['GET'])
@jwt_required
def get_playlist(playlist_id):
    """Get a specific playlist with all tracks"""
    if playlist_id not in playlists_storage:
        return jsonify({
            'success': False,
            'error': 'Playlist not found'
        }), 404
        
    playlist = playlists_storage[playlist_id]
    
    return jsonify({
        'success': True,
        'playlist': playlist.to_dict()
    }), 200


@music_aggregation_bp.route('/playlists/<playlist_id>/tracks', methods=['POST'])
@jwt_required
def add_track_to_playlist(playlist_id):
    """
    Add a track to a playlist
    
    Request body (option 1 - by search):
    {
        "query": "artist - track name"
    }
    
    Request body (option 2 - by URL):
    {
        "url": "https://soundcloud.com/..."
    }
    
    Request body (option 3 - by unified track):
    {
        "unified_track": { ... }  # Full track object
    }
    """
    try:
        if playlist_id not in playlists_storage:
            return jsonify({
                'success': False,
                'error': 'Playlist not found'
            }), 404
            
        playlist = playlists_storage[playlist_id]
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No track data provided'
            }), 400
            
        # Handle different input types
        if data.get('query'):
            # Search for track
            results = aggregation_service.search_all_platforms(data['query'], limit=1)
            if results:
                playlist.add_track(results[0])
            else:
                return jsonify({
                    'success': False,
                    'error': 'Track not found'
                }), 404
                
        elif data.get('url'):
            # Add by URL
            playlist.add_track_by_url(data['url'], aggregation_service)
            
        elif data.get('unified_track'):
            # Add full track object
            track_data = data['unified_track']
            track = UnifiedTrack(
                unified_id=track_data['unified_id'],
                title=track_data['title'],
                artist=track_data['artist']
            )
            # Restore other fields...
            playlist.add_track(track)
            
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid track data'
            }), 400
            
        return jsonify({
            'success': True,
            'playlist': playlist.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding track to playlist: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to add track'
        }), 500


@music_aggregation_bp.route('/playlists/<playlist_id>/export', methods=['GET'])
@jwt_required
def export_playlist(playlist_id):
    """
    Export playlist in various formats
    
    Query params:
    - format: m3u, json, csv (default: m3u)
    """
    if playlist_id not in playlists_storage:
        return jsonify({
            'success': False,
            'error': 'Playlist not found'
        }), 404
        
    playlist = playlists_storage[playlist_id]
    export_format = request.args.get('format', 'm3u').lower()
    
    if export_format == 'm3u':
        content = playlist.export_to_m3u()
        return content, 200, {
            'Content-Type': 'audio/x-mpegurl',
            'Content-Disposition': f'attachment; filename="{playlist.name}.m3u"'
        }
        
    elif export_format == 'json':
        return jsonify({
            'success': True,
            'playlist': playlist.to_dict()
        }), 200
        
    elif export_format == 'csv':
        # Simple CSV export
        csv_content = "Title,Artist,Platforms,URL\n"
        for track in playlist.tracks:
            # Get first URL
            url = ""
            for platform, data in track.platforms.items():
                if data.get('url'):
                    url = data['url']
                    break
            csv_content += f'"{track.title}","{track.artist}","{",".join(track.platforms.keys())}","{url}"\n'
            
        return csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename="{playlist.name}.csv"'
        }
        
    else:
        return jsonify({
            'success': False,
            'error': f'Unsupported export format: {export_format}'
        }), 400


@music_aggregation_bp.route('/compare', methods=['POST'])
def compare_platforms():
    """
    Compare track availability and metadata across platforms
    
    Request body:
    {
        "tracks": ["query1", "query2", ...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('tracks'):
            return jsonify({
                'success': False,
                'error': 'No tracks provided'
            }), 400
            
        queries = data['tracks'][:10]  # Limit to 10 tracks
        
        comparison_results = []
        
        for query in queries:
            results = aggregation_service.search_all_platforms(query, limit=1)
            
            if results:
                track = results[0]
                comparison_results.append({
                    'query': query,
                    'found': True,
                    'track': {
                        'title': track.title,
                        'artist': track.artist,
                        'platforms': list(track.platforms.keys()),
                        'platform_count': len(track.platforms),
                        'popularity_score': track.popularity_score
                    }
                })
            else:
                comparison_results.append({
                    'query': query,
                    'found': False
                })
                
        # Calculate statistics
        total_found = sum(1 for r in comparison_results if r['found'])
        platform_counts = {}
        
        for result in comparison_results:
            if result['found']:
                for platform in result['track']['platforms']:
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1
                    
        return jsonify({
            'success': True,
            'comparison': comparison_results,
            'statistics': {
                'total_queries': len(queries),
                'tracks_found': total_found,
                'platform_coverage': platform_counts
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in platform comparison: {e}")
        return jsonify({
            'success': False,
            'error': 'Comparison failed'
        }), 500


# Health check endpoint
@music_aggregation_bp.route('/health', methods=['GET'])
def health_check():
    """Check if aggregation service is working"""
    return jsonify({
        'success': True,
        'service': 'music_aggregation',
        'status': 'operational',
        'searxng_url': aggregation_service.searxng_url,
        'supported_platforms': aggregation_service.supported_engines
    }), 200
