"""
Music Aggregation Service for SearXNG-Cool
Implements the aggregation layer on top of SearXNG
"""

import requests
import json
import hashlib
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import logging
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UnifiedTrack:
    """Universal track representation across all platforms"""
    # Core identifiers
    unified_id: str
    title: str
    artist: str
    album: Optional[str] = None
    
    # Platform availability - maps platform name to details
    platforms: Dict[str, Dict] = field(default_factory=dict)
    
    # Aggregated metadata
    genres: Set[str] = field(default_factory=set)
    release_date: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Aggregated metrics
    popularity_score: float = 0.0
    play_count_total: int = 0
    
    # Enhanced features
    tags: Set[str] = field(default_factory=set)
    first_seen: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'unified_id': self.unified_id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'platforms': self.platforms,
            'genres': list(self.genres),
            'tags': list(self.tags),
            'release_date': self.release_date,
            'duration_ms': self.duration_ms,
            'popularity_score': self.popularity_score,
            'play_count_total': self.play_count_total,
            'first_seen': self.first_seen.isoformat()
        }


class MusicAggregationService:
    """
    Aggregates music search results from multiple SearXNG engines
    Provides deduplication, enrichment, and cross-platform features
    """
    
    def __init__(self, searxng_url: str = "http://localhost:8888"):
        self.searxng_url = searxng_url
        self.supported_engines = [
            'soundcloud', 'soundcloud enhanced',
            'bandcamp', 'bandcamp enhanced',
            'youtube', 'youtube music',
            'mixcloud', 'mixcloud enhanced',
            'genius', 'spotify', 'deezer'
        ]
        
    def search_all_platforms(self, query: str, limit: int = 50) -> List[UnifiedTrack]:
        """
        Search across all music platforms and return unified results
        """
        logger.info(f"Starting aggregated search for: {query}")
        
        # Get raw results from SearXNG
        raw_results = self._search_searxng(query)
        
        if not raw_results:
            logger.warning("No results from SearXNG")
            return []
        
        # Group by platform
        platform_groups = self._group_by_platform(raw_results)
        logger.info(f"Found results from {len(platform_groups)} platforms")
        
        # Deduplicate and create unified tracks
        unified_tracks = self._create_unified_tracks(platform_groups)
        
        # Enrich with additional data
        for track in unified_tracks:
            self._enrich_track(track)
            self._calculate_popularity(track)
        
        # Sort by relevance/popularity
        unified_tracks.sort(key=lambda t: t.popularity_score, reverse=True)
        
        return unified_tracks[:limit]
    
    def _search_searxng(self, query: str) -> List[Dict]:
        """Execute search on SearXNG"""
        try:
            # Search without specifying engines to get all results
            response = requests.get(
                f"{self.searxng_url}/search",
                params={
                    'q': query,
                    'format': 'json',
                    'categories': 'music'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Filter out radio stations
                music_results = [
                    r for r in results 
                    if 'radio' not in r.get('engine', '').lower()
                    and 'radio' not in r.get('url', '').lower()
                ]
                
                logger.info(f"Got {len(music_results)} music results (filtered from {len(results)})")
                return music_results
            else:
                logger.error(f"SearXNG returned status {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching SearXNG: {e}")
            return []
    
    def _group_by_platform(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group search results by platform"""
        groups = defaultdict(list)
        
        for result in results:
            engine = result.get('engine', 'unknown')
            # Normalize engine names
            engine = engine.replace(' enhanced', '').lower()
            groups[engine].append(result)
            
        return dict(groups)
    
    def _create_unified_tracks(self, platform_groups: Dict[str, List[Dict]]) -> List[UnifiedTrack]:
        """Create unified track objects from platform-specific results"""
        track_map = {}  # unified_id -> UnifiedTrack
        
        for platform, results in platform_groups.items():
            for result in results:
                # Extract basic info
                title = result.get('title', '').strip()
                
                # Try to extract artist from title (common format: "Artist - Title")
                artist = 'Unknown Artist'
                if ' - ' in title:
                    parts = title.split(' - ', 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                
                # Generate unified ID
                unified_id = self._generate_unified_id(title, artist)
                
                # Create or update track
                if unified_id in track_map:
                    track = track_map[unified_id]
                else:
                    track = UnifiedTrack(
                        unified_id=unified_id,
                        title=title,
                        artist=artist
                    )
                    track_map[unified_id] = track
                
                # Add platform data
                track.platforms[platform] = {
                    'url': result.get('url', ''),
                    'engine': result.get('engine', ''),
                    'content': result.get('content', ''),
                    'publishedDate': result.get('publishedDate', '')
                }
                
                # Extract additional metadata
                if result.get('embedded'):
                    track.platforms[platform]['embedded'] = result['embedded']
                    
        return list(track_map.values())
    
    def _generate_unified_id(self, title: str, artist: str) -> str:
        """Generate a unique ID for a track across platforms"""
        # Normalize and create hash
        normalized = f"{artist.lower().strip()}:{title.lower().strip()}"
        # Remove common variations
        normalized = normalized.replace('feat.', '').replace('ft.', '')
        normalized = ' '.join(normalized.split())  # Normalize whitespace
        
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def _enrich_track(self, track: UnifiedTrack):
        """Add enriched metadata to track"""
        # Extract genres from content/tags
        for platform, data in track.platforms.items():
            content = data.get('content', '').lower()
            
            # Simple genre detection (could be enhanced)
            genres = ['electronic', 'rock', 'pop', 'jazz', 'classical', 'hip hop', 'metal']
            for genre in genres:
                if genre in content:
                    track.genres.add(genre)
            
            # Extract tags
            if 'tag' in content:
                # Simple tag extraction
                words = content.split()
                for word in words:
                    if word.startswith('#'):
                        track.tags.add(word[1:])
    
    def _calculate_popularity(self, track: UnifiedTrack):
        """Calculate aggregate popularity score"""
        # Simple scoring based on platform presence
        platform_scores = {
            'youtube': 30,
            'spotify': 25,
            'soundcloud': 20,
            'bandcamp': 15,
            'deezer': 10,
            'mixcloud': 10,
            'genius': 5
        }
        
        score = 0
        for platform in track.platforms:
            score += platform_scores.get(platform, 5)
            
        # Bonus for being on multiple platforms
        score += len(track.platforms) * 10
        
        # Normalize to 0-100
        track.popularity_score = min(100, score)
    
    def find_on_all_platforms(self, track_title: str, artist: str) -> UnifiedTrack:
        """Find a specific track across all platforms"""
        query = f"{artist} {track_title}"
        results = self.search_all_platforms(query, limit=10)
        
        # Find best match
        for track in results:
            if (track.title.lower() in track_title.lower() or 
                track_title.lower() in track.title.lower()):
                return track
                
        return results[0] if results else None
    
    def get_platform_availability(self, unified_track: UnifiedTrack) -> Dict[str, bool]:
        """Check which platforms have this track available"""
        availability = {}
        
        for platform in self.supported_engines:
            platform_key = platform.replace(' enhanced', '').lower()
            availability[platform] = platform_key in unified_track.platforms
            
        return availability


class UniversalPlaylist:
    """
    Playlist that can contain tracks from multiple platforms
    """
    
    def __init__(self, name: str, description: str = ""):
        self.id = hashlib.md5(f"{name}{datetime.now()}".encode()).hexdigest()[:8]
        self.name = name
        self.description = description
        self.tracks: List[UnifiedTrack] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def add_track(self, track: UnifiedTrack):
        """Add a track to the playlist"""
        self.tracks.append(track)
        self.updated_at = datetime.now()
        
    def add_track_by_url(self, url: str, aggregation_service: MusicAggregationService):
        """Add a track by its URL from any platform"""
        # Detect platform from URL
        platform = self._detect_platform(url)
        
        # Extract info and search for universal version
        # This is simplified - in production would parse the URL properly
        if 'soundcloud.com' in url:
            # Extract from SoundCloud URL
            query = url.split('/')[-1].replace('-', ' ')
        elif 'youtube.com' in url or 'youtu.be' in url:
            # Extract from YouTube URL
            query = "music"  # Would need proper extraction
        else:
            query = "unknown track"
            
        # Find on all platforms
        results = aggregation_service.search_all_platforms(query, limit=5)
        if results:
            self.add_track(results[0])
            
    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        platforms = {
            'soundcloud.com': 'soundcloud',
            'youtube.com': 'youtube',
            'youtu.be': 'youtube',
            'bandcamp.com': 'bandcamp',
            'mixcloud.com': 'mixcloud',
            'spotify.com': 'spotify'
        }
        
        for domain, platform in platforms.items():
            if domain in url:
                return platform
                
        return 'unknown'
    
    def export_to_m3u(self) -> str:
        """Export playlist to M3U format"""
        m3u_content = "#EXTM3U\n"
        m3u_content += f"#PLAYLIST:{self.name}\n\n"
        
        for track in self.tracks:
            # Use the first available platform URL
            url = None
            for platform, data in track.platforms.items():
                if data.get('url'):
                    url = data['url']
                    break
                    
            if url:
                duration = track.duration_ms // 1000 if track.duration_ms else -1
                m3u_content += f"#EXTINF:{duration},{track.artist} - {track.title}\n"
                m3u_content += f"{url}\n\n"
                
        return m3u_content
    
    def to_dict(self):
        """Convert playlist to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'track_count': len(self.tracks),
            'tracks': [t.to_dict() for t in self.tracks],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize aggregation service
    aggregator = MusicAggregationService()
    
    # Test search
    print("🔍 Testing music aggregation...")
    results = aggregator.search_all_platforms("daft punk", limit=10)
    
    if results:
        print(f"\n✅ Found {len(results)} unified tracks\n")
        
        for i, track in enumerate(results[:5], 1):
            print(f"{i}. {track.artist} - {track.title}")
            print(f"   Popularity: {track.popularity_score}/100")
            print(f"   Available on: {', '.join(track.platforms.keys())}")
            print(f"   Genres: {', '.join(track.genres) if track.genres else 'Unknown'}")
            print()
    else:
        print("❌ No results found - check if SearXNG is running properly")
        
    # Test playlist creation
    print("\n📋 Testing universal playlist...")
    playlist = UniversalPlaylist("My Electronic Mix", "Best electronic tracks")
    
    # Add tracks to playlist
    for track in results[:3]:
        playlist.add_track(track)
        
    print(f"Created playlist: {playlist.name}")
    print(f"Tracks: {len(playlist.tracks)}")
    
    # Export playlist
    m3u_content = playlist.export_to_m3u()
    print("\nM3U Export preview:")
    print(m3u_content[:200] + "...")
