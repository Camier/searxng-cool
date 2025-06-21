"""
Music API Routes
Provides music-specific search and management endpoints
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from orchestrator.utils.auth import jwt_required_with_user

from orchestrator.services.music_search_service import MusicSearchService
from orchestrator.database import db
from orchestrator.models.music.playlist import Playlist, PlaylistTrack
from orchestrator.models.music.track import Track
from orchestrator.models.user import User

logger = logging.getLogger(__name__)

music_api_bp = Blueprint('music_api', __name__, url_prefix='/api/music')

# Initialize music search service
music_search_service = MusicSearchService()


@music_api_bp.route('/search', methods=['GET', 'POST'])
@jwt_required_with_user()
def music_search(current_user):
    """
    Search for music across multiple engines
    
    GET params or POST JSON:
    - q: Search query (required)
    - engines: List of engines to use (optional)
    - limit: Max results (default 50)
    """
    
    # Get parameters
    if request.method == 'POST':
        data = request.get_json() or {}
        query = data.get('q', '')
        engines = data.get('engines', None)
        limit = data.get('limit', 50)
    else:
        query = request.args.get('q', '')
        engines = request.args.getlist('engines') or None
        limit = int(request.args.get('limit', 50))
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required'
        }), 400
    
    try:
        # Perform search
        results = music_search_service.search(query, engines, limit)
        
        # Add user context
        results['user'] = current_user.username
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"Music search error: {e}")
        return jsonify({
            'error': 'Search failed. Please try again later.'
        }), 500


@music_api_bp.route('/engines/status', methods=['GET'])
@jwt_required_with_user()
def music_engines_status(current_user):
    """Get status of all music engines"""
    try:
        status = music_search_service.get_engine_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Engine status error: {e}")
        return jsonify({
            'error': 'Failed to get engine status. Please try again later.'
        }), 500


@music_api_bp.route('/playlists', methods=['GET', 'POST'])
@jwt_required_with_user()
def playlists(current_user):
    """
    Get user playlists or create new playlist
    """
    current_user_id = current_user.id
    
    if request.method == 'GET':
        # Get user playlists
        try:
            user_playlists = Playlist.query.filter_by(
                owner_id=current_user_id
            ).order_by(Playlist.updated_at.desc()).all()
            
            return jsonify({
                'playlists': [p.to_dict() for p in user_playlists]
            })
        except Exception as e:
            logger.error(f"Get playlists error: {e}")
            return jsonify({'error': 'Failed to retrieve playlists. Please try again later.'}), 500
    
    else:  # POST - Create playlist
        try:
            data = request.get_json() or {}
            
            # Validate required fields
            if not data.get('name'):
                return jsonify({'error': 'Playlist name is required'}), 400
            
            # Create playlist
            playlist = Playlist(
                name=data['name'],
                description=data.get('description', ''),
                owner_id=current_user_id,
                is_public=data.get('is_public', False),
                is_collaborative=data.get('is_collaborative', False),
                tags=data.get('tags', {})
            )
            
            db.session.add(playlist)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'playlist': playlist.to_dict()
            }), 201
            
        except Exception as e:
            logger.error(f"Create playlist error: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to create playlist. Please try again later.'}), 500


@music_api_bp.route('/playlists/<int:playlist_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required_with_user()
def playlist_detail(playlist_id, current_user):
    """Get, update, or delete a specific playlist"""
    current_user_id = current_user.id
    
    # Get playlist
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check permissions
    if playlist.owner_id != current_user_id and not playlist.is_public:
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'GET':
        return jsonify(playlist.to_dict(include_tracks=True))
    
    elif request.method == 'PUT':
        # Only owner can update
        if playlist.owner_id != current_user_id:
            return jsonify({'error': 'Only owner can update playlist'}), 403
        
        try:
            data = request.get_json() or {}
            
            # Update fields
            if 'name' in data:
                playlist.name = data['name']
            if 'description' in data:
                playlist.description = data['description']
            if 'is_public' in data:
                playlist.is_public = data['is_public']
            if 'is_collaborative' in data:
                playlist.is_collaborative = data['is_collaborative']
            if 'tags' in data:
                playlist.tags = data['tags']
            
            db.session.commit()
            return jsonify(playlist.to_dict())
            
        except Exception as e:
            logger.error(f"Update playlist error: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to update playlist. Please try again later.'}), 500
    
    else:  # DELETE
        # Only owner can delete
        if playlist.owner_id != current_user_id:
            return jsonify({'error': 'Only owner can delete playlist'}), 403
        
        try:
            db.session.delete(playlist)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Playlist deleted'})
            
        except Exception as e:
            logger.error(f"Delete playlist error: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to delete playlist. Please try again later.'}), 500


@music_api_bp.route('/playlists/<int:playlist_id>/tracks', methods=['POST', 'DELETE'])
@jwt_required_with_user()
def playlist_tracks(playlist_id, current_user):
    """Add or remove tracks from playlist"""
    current_user_id = current_user.id
    
    # Get playlist
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check permissions
    if playlist.owner_id != current_user_id:
        if not playlist.is_collaborative:
            return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json() or {}
    
    if request.method == 'POST':
        # Add track
        try:
            track_id = data.get('track_id')
            if not track_id:
                return jsonify({'error': 'track_id is required'}), 400
            
            # Verify track exists
            track = Track.query.get(track_id)
            if not track:
                return jsonify({'error': 'Track not found'}), 404
            
            # Get next position
            last_track = PlaylistTrack.query.filter_by(
                playlist_id=playlist_id
            ).order_by(PlaylistTrack.position.desc()).first()
            
            position = (last_track.position + 1) if last_track else 0
            
            # Add track to playlist
            playlist_track = PlaylistTrack(
                playlist_id=playlist_id,
                track_id=track_id,
                position=position,
                added_by=current_user_id
            )
            
            db.session.add(playlist_track)
            
            # Update playlist duration
            playlist.update_total_duration()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'position': position
            })
            
        except Exception as e:
            logger.error(f"Add track error: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to add track. Please try again later.'}), 500
    
    else:  # DELETE
        # Remove track
        try:
            track_id = data.get('track_id')
            position = data.get('position')
            
            if track_id:
                playlist_track = PlaylistTrack.query.filter_by(
                    playlist_id=playlist_id,
                    track_id=track_id
                ).first()
            elif position is not None:
                playlist_track = PlaylistTrack.query.filter_by(
                    playlist_id=playlist_id,
                    position=position
                ).first()
            else:
                return jsonify({'error': 'track_id or position required'}), 400
            
            if not playlist_track:
                return jsonify({'error': 'Track not found in playlist'}), 404
            
            db.session.delete(playlist_track)
            
            # Reorder remaining tracks
            remaining_tracks = PlaylistTrack.query.filter(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.position > playlist_track.position
            ).all()
            
            for track in remaining_tracks:
                track.position -= 1
            
            # Update playlist duration
            playlist.update_total_duration()
            
            db.session.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Remove track error: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to remove track. Please try again later.'}), 500


@music_api_bp.route('/tracks/<int:track_id>', methods=['GET'])
@jwt_required_with_user()
def track_detail(track_id, current_user):
    """Get track details including sources and metadata"""
    track = Track.query.get_or_404(track_id)
    return jsonify(track.to_dict(include_sources=True, include_audio_features=True))


@music_api_bp.route('/profile/preferences', methods=['GET', 'POST'])
@jwt_required_with_user()
def user_music_preferences(current_user):
    """Get or update user music preferences"""
    current_user_id = current_user.id
    
    if request.method == 'GET':
        # Get user preferences
        from orchestrator.models.music.user_music import UserMusicProfile
        profile = UserMusicProfile.query.filter_by(user_id=current_user_id).first()
        
        if profile:
            return jsonify(profile.to_dict())
        else:
            return jsonify({
                'audio_preferences': {},
                'genre_preferences': {},
                'discovery_settings': {}
            })
    
    else:  # POST - Update preferences
        try:
            from orchestrator.models.music.user_music import UserMusicProfile
            data = request.get_json() or {}
            
            profile = UserMusicProfile.query.filter_by(user_id=current_user_id).first()
            if not profile:
                profile = UserMusicProfile(user_id=current_user_id)
                db.session.add(profile)
            
            # Update preferences
            if 'audio_preferences' in data:
                profile.audio_preferences = data['audio_preferences']
            if 'genre_preferences' in data:
                profile.genre_preferences = data['genre_preferences']
            if 'discovery_settings' in data:
                profile.discovery_settings = data['discovery_settings']
            
            profile.last_updated = datetime.utcnow()
            db.session.commit()
            
            return jsonify(profile.to_dict())
            
        except Exception as e:
            logger.error(f"Update preferences error: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to update preferences. Please try again later.'}), 500


# Health check endpoint
@music_api_bp.route('/health', methods=['GET'])
@jwt_required_with_user(optional=True)
def music_health(current_user=None):
    """Music API health check"""
    return jsonify({
        'service': 'music_api',
        'status': 'healthy',
        'endpoints': [
            '/search',
            '/engines/status',
            '/playlists',
            '/tracks',
            '/profile/preferences'
        ]
    })