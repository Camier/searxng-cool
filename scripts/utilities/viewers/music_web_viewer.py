#!/usr/bin/env python3
"""
Simple Web Interface for Music Database
Provides a basic web UI to view and search music
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, jsonify
from migration_app import app as db_app
from orchestrator.database import db
from orchestrator.models import Track, Artist, TrackSource

# Create a simple Flask app for the web interface
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://searxng_user:searxng_music_2024@/searxng_cool_music'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SearXNG Music Library</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .search-box {
            margin: 20px 0;
            text-align: center;
        }
        .search-box input {
            padding: 10px;
            width: 300px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .search-box button {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .search-box button:hover {
            background-color: #45a049;
        }
        .stats {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            text-align: center;
        }
        .stats span {
            margin: 0 20px;
            font-size: 18px;
        }
        .track-list {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .track {
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
        }
        .track:last-child {
            border-bottom: none;
        }
        .track-info {
            flex: 1;
        }
        .track-title {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 5px;
        }
        .track-artist {
            color: #666;
            margin-bottom: 5px;
        }
        .track-meta {
            font-size: 12px;
            color: #999;
        }
        .track-actions {
            margin-left: 20px;
        }
        .youtube-link {
            background-color: #ff0000;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
        }
        .youtube-link:hover {
            background-color: #cc0000;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>🎵 SearXNG Music Library</h1>
    
    <div class="search-box">
        <form method="get" action="/">
            <input type="text" name="q" placeholder="Search for music..." value="{{ query }}">
            <button type="submit">Search</button>
        </form>
    </div>
    
    <div class="stats">
        <span>📀 {{ stats.tracks }} Tracks</span>
        <span>👤 {{ stats.artists }} Artists</span>
        <span>📋 {{ stats.playlists }} Playlists</span>
    </div>
    
    <div class="track-list">
        {% if tracks %}
            {% for track in tracks %}
            <div class="track">
                <div class="track-info">
                    <div class="track-title">{{ track.title }}</div>
                    <div class="track-artist">{{ track.artist_name }}</div>
                    <div class="track-meta">
                        Duration: {{ track.duration }} | 
                        {% if track.views %}Views: {{ "{:,}".format(track.views) }}{% endif %}
                    </div>
                </div>
                <div class="track-actions">
                    {% if track.youtube_url %}
                    <a href="{{ track.youtube_url }}" target="_blank" class="youtube-link">Play on YouTube</a>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="no-results">
                {% if query %}
                    No results found for "{{ query }}"
                {% else %}
                    No tracks in database yet
                {% endif %}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page - show tracks or search results"""
    query = request.args.get('q', '').strip()
    
    # Get stats
    stats = {
        'tracks': Track.query.count(),
        'artists': Artist.query.count(),
        'playlists': db.session.execute(db.text("SELECT COUNT(*) FROM playlists")).scalar()
    }
    
    # Get tracks
    if query:
        # Search
        tracks = Track.query.join(Artist, Track.artist_id == Artist.id, isouter=True).filter(
            db.or_(
                Track.title.ilike(f'%{query}%'),
                Artist.name.ilike(f'%{query}%')
            )
        ).order_by(Track.created_at.desc()).limit(50).all()
    else:
        # Show recent
        tracks = Track.query.order_by(Track.created_at.desc()).limit(50).all()
    
    # Format tracks for display
    track_data = []
    for track in tracks:
        # Get YouTube source
        youtube_source = next((s for s in track.sources if s.source_type == 'youtube'), None)
        
        # Format duration
        if track.duration_ms:
            total_seconds = track.duration_ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration = f"{minutes}:{seconds:02d}"
        else:
            duration = "Unknown"
        
        track_data.append({
            'title': track.title,
            'artist_name': track.artist.name if track.artist else 'Unknown Artist',
            'duration': duration,
            'views': track.extra_metadata.get('youtube_view_count', 0) if track.extra_metadata else 0,
            'youtube_url': youtube_source.source_uri if youtube_source else None
        })
    
    return render_template_string(HTML_TEMPLATE, 
                                tracks=track_data, 
                                stats=stats,
                                query=query)

@app.route('/api/stats')
def api_stats():
    """API endpoint for database statistics"""
    stats = {
        'tracks': Track.query.count(),
        'artists': Artist.query.count(),
        'playlists': db.session.execute(db.text("SELECT COUNT(*) FROM playlists")).scalar(),
        'sources': {
            'youtube': TrackSource.query.filter_by(source_type='youtube').count()
        }
    }
    return jsonify(stats)

@app.route('/api/tracks')
def api_tracks():
    """API endpoint for tracks"""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)
    
    if query:
        tracks = Track.query.join(Artist, Track.artist_id == Artist.id, isouter=True).filter(
            db.or_(
                Track.title.ilike(f'%{query}%'),
                Artist.name.ilike(f'%{query}%')
            )
        ).limit(limit).all()
    else:
        tracks = Track.query.order_by(Track.created_at.desc()).limit(limit).all()
    
    results = []
    for track in tracks:
        youtube_source = next((s for s in track.sources if s.source_type == 'youtube'), None)
        results.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist.name if track.artist else None,
            'duration_ms': track.duration_ms,
            'youtube_url': youtube_source.source_uri if youtube_source else None,
            'metadata': track.extra_metadata
        })
    
    return jsonify({'tracks': results, 'count': len(results)})

if __name__ == '__main__':
    print("🎵 Starting SearXNG Music Web Viewer")
    print("📍 Access at: http://localhost:5555")
    print("🔍 API endpoints:")
    print("   - /api/stats - Database statistics")
    print("   - /api/tracks?q=search - Track search API")
    app.run(host='0.0.0.0', port=5555, debug=True)