#!/usr/bin/env python3
"""
YouTube Music Import Script
Imports music from YouTube into the SearXNG-Cool database
"""
import os
import sys
import re
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migration_app import app
from orchestrator.database import db
from orchestrator.models import (
    Track, TrackSource, Artist, ArtistSource, 
    Playlist, PlaylistTrack, User
)

# YouTube API Configuration
YOUTUBE_API_KEY = 'AIzaSyCY15dY_oGINJTibAYNwELSOKlfcL0g3vk'
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def parse_duration(duration_str):
    """Convert YouTube duration (PT15M33S) to milliseconds"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return (hours * 3600 + minutes * 60 + seconds) * 1000

def search_youtube_music(query, max_results=10):
    """Search YouTube for music videos"""
    try:
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video',
            videoCategoryId='10'  # Music category
        ).execute()
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        # Get video details including duration
        videos_response = youtube.videos().list(
            part='contentDetails,snippet,statistics',
            id=','.join(video_ids)
        ).execute()
        
        return videos_response['items']
    
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return []

def import_youtube_video(video_data):
    """Import a single YouTube video as a track"""
    snippet = video_data['snippet']
    content_details = video_data['contentDetails']
    statistics = video_data.get('statistics', {})
    
    # Extract artist and title from video title
    title = snippet['title']
    channel = snippet['channelTitle']
    
    # Simple parsing - could be improved
    if ' - ' in title:
        parts = title.split(' - ', 1)
        artist_name = parts[0].strip()
        track_title = parts[1].strip()
    else:
        artist_name = channel
        track_title = title
    
    # Check if artist exists or create new
    artist = Artist.query.filter_by(name=artist_name).first()
    if not artist:
        artist = Artist(
            name=artist_name,
            extra_metadata={
                'youtube_channel': channel,
                'youtube_channel_id': snippet['channelId']
            }
        )
        db.session.add(artist)
        db.session.flush()
        
        # Add artist source
        artist_source = ArtistSource(
            artist_id=artist.id,
            source_type='youtube',
            source_id=snippet['channelId'],
            source_uri=f"https://youtube.com/channel/{snippet['channelId']}"
        )
        db.session.add(artist_source)
    
    # Check if track already exists
    existing_track = Track.query.join(TrackSource).filter(
        TrackSource.source_type == 'youtube',
        TrackSource.source_id == video_data['id']
    ).first()
    
    if existing_track:
        print(f"⚠️  Track already exists: {track_title}")
        return existing_track
    
    # Create track
    track = Track(
        title=track_title,
        artist_id=artist.id,
        duration_ms=parse_duration(content_details['duration']),
        extra_metadata={
            'youtube_description': snippet.get('description', ''),
            'youtube_tags': snippet.get('tags', []),
            'youtube_view_count': int(statistics.get('viewCount', 0)),
            'youtube_like_count': int(statistics.get('likeCount', 0)),
            'youtube_published_at': snippet['publishedAt'],
            'thumbnail_url': snippet['thumbnails']['high']['url']
        }
    )
    db.session.add(track)
    db.session.flush()
    
    # Add track source
    track_source = TrackSource(
        track_id=track.id,
        source_type='youtube',
        source_id=video_data['id'],
        source_uri=f"https://youtube.com/watch?v={video_data['id']}",
        is_available=True,
        source_extra_metadata={
            'thumbnail_url': snippet['thumbnails']['high']['url'],
            'channel_id': snippet['channelId']
        }
    )
    db.session.add(track_source)
    
    print(f"✅ Imported: {artist_name} - {track_title}")
    return track

def create_youtube_playlist(name, description, track_ids):
    """Create a playlist from imported tracks"""
    # Get or create a default user
    user = User.query.filter_by(username='youtube_importer').first()
    if not user:
        user = User(
            username='youtube_importer',
            email='importer@searxng.local'
        )
        user.set_password('import123')
        db.session.add(user)
        db.session.flush()
    
    playlist = Playlist(
        name=name,
        description=description,
        user_id=user.id,
        is_public=True,
        extra_metadata={
            'source': 'youtube_import',
            'import_date': datetime.utcnow().isoformat()
        }
    )
    db.session.add(playlist)
    db.session.flush()
    
    # Add tracks to playlist
    for position, track_id in enumerate(track_ids):
        playlist_track = PlaylistTrack(
            playlist_id=playlist.id,
            track_id=track_id,
            position=position,
            added_by=user.id
        )
        db.session.add(playlist_track)
    
    return playlist

def main():
    """Main import function"""
    print("🎵 YouTube Music Importer for SearXNG-Cool")
    print("=" * 50)
    
    with app.app_context():
        while True:
            print("\nOptions:")
            print("1. Search and import tracks")
            print("2. Import playlist by ID")
            print("3. View imported tracks")
            print("4. Create playlist from imported tracks")
            print("5. Exit")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '1':
                query = input("Enter search query: ").strip()
                if not query:
                    continue
                
                print(f"\n🔍 Searching YouTube for: {query}")
                videos = search_youtube_music(query)
                
                if not videos:
                    print("❌ No results found")
                    continue
                
                print(f"\n📋 Found {len(videos)} results:")
                for i, video in enumerate(videos):
                    print(f"{i+1}. {video['snippet']['title']} - {video['snippet']['channelTitle']}")
                
                selection = input("\nSelect videos to import (comma-separated numbers, or 'all'): ").strip()
                
                if selection.lower() == 'all':
                    selected_videos = videos
                else:
                    try:
                        indices = [int(x.strip())-1 for x in selection.split(',')]
                        selected_videos = [videos[i] for i in indices if 0 <= i < len(videos)]
                    except:
                        print("❌ Invalid selection")
                        continue
                
                print(f"\n📥 Importing {len(selected_videos)} tracks...")
                imported_tracks = []
                
                for video in selected_videos:
                    try:
                        track = import_youtube_video(video)
                        imported_tracks.append(track)
                    except Exception as e:
                        print(f"❌ Error importing {video['snippet']['title']}: {e}")
                
                db.session.commit()
                print(f"\n✅ Successfully imported {len(imported_tracks)} tracks!")
            
            elif choice == '2':
                playlist_id = input("Enter YouTube playlist ID: ").strip()
                if not playlist_id:
                    continue
                
                try:
                    # Get playlist items
                    playlist_response = youtube.playlistItems().list(
                        part='snippet',
                        playlistId=playlist_id,
                        maxResults=50
                    ).execute()
                    
                    video_ids = [item['snippet']['resourceId']['videoId'] 
                                for item in playlist_response['items']]
                    
                    # Get video details
                    videos_response = youtube.videos().list(
                        part='contentDetails,snippet,statistics',
                        id=','.join(video_ids)
                    ).execute()
                    
                    print(f"\n📥 Importing {len(videos_response['items'])} tracks from playlist...")
                    imported_tracks = []
                    
                    for video in videos_response['items']:
                        try:
                            track = import_youtube_video(video)
                            imported_tracks.append(track)
                        except Exception as e:
                            print(f"❌ Error: {e}")
                    
                    db.session.commit()
                    print(f"\n✅ Successfully imported {len(imported_tracks)} tracks!")
                    
                except HttpError as e:
                    print(f"❌ Error fetching playlist: {e}")
            
            elif choice == '3':
                tracks = Track.query.join(TrackSource).filter(
                    TrackSource.source_type == 'youtube'
                ).order_by(Track.created_at.desc()).limit(20).all()
                
                print(f"\n📋 Recent YouTube imports ({len(tracks)} tracks):")
                for track in tracks:
                    artist_name = track.artist.name if track.artist else 'Unknown'
                    duration = track.duration_ms // 1000 if track.duration_ms else 0
                    print(f"- {artist_name} - {track.title} ({duration}s)")
            
            elif choice == '4':
                name = input("Playlist name: ").strip()
                if not name:
                    continue
                
                description = input("Playlist description: ").strip()
                
                # Get recent tracks
                tracks = Track.query.join(TrackSource).filter(
                    TrackSource.source_type == 'youtube'
                ).order_by(Track.created_at.desc()).limit(50).all()
                
                if not tracks:
                    print("❌ No tracks available")
                    continue
                
                print(f"\n📋 Available tracks:")
                for i, track in enumerate(tracks):
                    artist_name = track.artist.name if track.artist else 'Unknown'
                    print(f"{i+1}. {artist_name} - {track.title}")
                
                selection = input("\nSelect tracks (comma-separated numbers, or 'all'): ").strip()
                
                if selection.lower() == 'all':
                    selected_tracks = tracks
                else:
                    try:
                        indices = [int(x.strip())-1 for x in selection.split(',')]
                        selected_tracks = [tracks[i] for i in indices if 0 <= i < len(tracks)]
                    except:
                        print("❌ Invalid selection")
                        continue
                
                playlist = create_youtube_playlist(
                    name, 
                    description, 
                    [t.id for t in selected_tracks]
                )
                db.session.commit()
                
                print(f"\n✅ Created playlist '{playlist.name}' with {len(selected_tracks)} tracks!")
                print(f"🔗 Playlist ID: {playlist.uuid}")
            
            elif choice == '5':
                print("\n👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid option")

if __name__ == "__main__":
    main()