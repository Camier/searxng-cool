"""
WebSocket Blueprint - Handles real-time communication
"""

from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token

websocket_bp = Blueprint('websocket', __name__)

def register_websocket_events(socketio_instance):
    """
    Registers all SocketIO event handlers with the given socketio instance.
    This function is called from the main app factory after socketio is initialized.
    """
    
    @socketio_instance.on('connect')
    def handle_connect(auth=None):
        """Handle client connection"""
        print(f'Client connected: {request.sid}')
        emit('status', {'message': 'Connected to SearXNG-Cool WebSocket'})
    
    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f'Client disconnected: {request.sid}')
    
    @socketio_instance.on('join_room')
    def handle_join_room(data):
        """Handle client joining a room"""
        room = data.get('room')
        join_room(room)
        emit('status', {'message': f'Joined room: {room}'})
    
    @socketio_instance.on('leave_room')
    def handle_leave_room(data):
        """Handle client leaving a room"""
        room = data.get('room')
        leave_room(room)
        emit('status', {'message': f'Left room: {room}'})
    
    @socketio_instance.on('search_query')
    def handle_search_query(data):
        """Handle real-time search queries"""
        query = data.get('query', '')
        emit('search_status', {
            'message': f'Processing search: {query}',
            'query': query
        })
        
        # TODO: Implement real-time search results streaming
        # For now, just acknowledge the query
        emit('search_complete', {
            'message': 'Search completed',
            'query': query
        })
    
    @socketio_instance.on('ping')
    def handle_ping():
        """Handle ping from client"""
        emit('pong', {'timestamp': request.sid})

# Blueprint route for WebSocket status
@websocket_bp.route('/status')
def websocket_status():
    """
    WebSocket service status
    """
    return jsonify({
        'service': 'websocket',
        'status': 'healthy',
        'features': ['real-time search', 'room management']
    })