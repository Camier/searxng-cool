#!/usr/bin/env python3
"""
Simple Music Database Viewer
Shows what's in the database without user authentication
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migration_app import app
from orchestrator.database import db
from orchestrator.models import Track, Artist, Playlist, TrackSource

def view_music_data():
    """Display music database contents"""
    with app.app_context():
        print("🎵 SearXNG-Cool Music Database")
        print("=" * 50)
        
        # Count totals
        track_count = Track.query.count()
        artist_count = Artist.query.count()
        playlist_count = Playlist.query.count()
        
        print(f"\n📊 Database Summary:")
        print(f"  - Total tracks: {track_count}")
        print(f"  - Total artists: {artist_count}")
        print(f"  - Total playlists: {playlist_count}")
        
        if track_count > 0:
            print(f"\n🎵 Tracks in database:")
            tracks = Track.query.order_by(Track.created_at.desc()).limit(10).all()
            
            for track in tracks:
                artist_name = track.artist.name if track.artist else 'Unknown'
                duration = track.duration_ms // 1000 if track.duration_ms else 0
                minutes = duration // 60
                seconds = duration % 60
                
                print(f"\n  📀 {artist_name} - {track.title}")
                print(f"     Duration: {minutes}:{seconds:02d}")
                
                # Show sources
                for source in track.sources:
                    if source.source_type == 'youtube':
                        print(f"     🔗 YouTube: {source.source_uri}")
                
                # Show metadata
                if track.extra_metadata:
                    views = track.extra_metadata.get('youtube_view_count', 0)
                    if views:
                        print(f"     👀 Views: {views:,}")
        
        print("\n" + "=" * 50)
        print("✅ Database viewing complete!")

def search_tracks(query):
    """Search for tracks by title or artist"""
    with app.app_context():
        print(f"\n🔍 Searching for: {query}")
        
        # Search in track titles
        tracks = Track.query.filter(
            Track.title.ilike(f'%{query}%')
        ).limit(10).all()
        
        # Also search by artist name
        artist_tracks = Track.query.join(Artist).filter(
            Artist.name.ilike(f'%{query}%')
        ).limit(10).all()
        
        # Combine results (remove duplicates)
        all_tracks = list({track.id: track for track in tracks + artist_tracks}.values())
        
        if all_tracks:
            print(f"\n📋 Found {len(all_tracks)} results:")
            for track in all_tracks:
                artist_name = track.artist.name if track.artist else 'Unknown'
                print(f"  - {artist_name} - {track.title}")
                
                # Show YouTube URL if available
                youtube_source = next((s for s in track.sources if s.source_type == 'youtube'), None)
                if youtube_source:
                    print(f"    🔗 {youtube_source.source_uri}")
        else:
            print("❌ No results found")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # If argument provided, search for it
        query = ' '.join(sys.argv[1:])
        search_tracks(query)
    else:
        # Otherwise show all data
        view_music_data()

if __name__ == "__main__":
    main()