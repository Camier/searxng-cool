"""
Music Search Service
Aggregates search results from multiple music engines
"""
import asyncio
import concurrent.futures
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

from orchestrator.database import db
from orchestrator.models.music.track import Track, TrackSource
from orchestrator.models.music.artist import Artist
from orchestrator.models.music.album import Album
from orchestrator.services.content_classifier import classifier
from orchestrator.services.data_validator import validator

logger = logging.getLogger(__name__)


class MusicSearchService:
    """Service for searching and aggregating music from multiple engines"""
    
    # Active music engines - only enabled ones, using enhanced versions where available
    # Based on actual SearXNG /config API response
    ACTIVE_ENGINES = {
        # Core music engines
        'bandcamp': {'name': 'Bandcamp', 'shortcut': 'bc'},  # Using regular version (enhanced disabled)
        'soundcloud': {'name': 'SoundCloud', 'shortcut': 'sc'},  # Regular version
        'mixcloud': {'name': 'MixCloud', 'shortcut': 'mc'},  # Using regular version (enhanced disabled)
        
        # Music databases/catalogs
        'musicbrainz': {'name': 'MusicBrainz', 'shortcut': 'mb'},  # Open music encyclopedia
        'lastfm': {'name': 'Last.fm', 'shortcut': 'lfm'},  # Music discovery and stats
        'deezer': {'name': 'Deezer', 'shortcut': 'dz'},  # Music streaming search
        'free music archive': {'name': 'Free Music Archive', 'shortcut': 'fma'},  # CC-licensed music
        'beatport': {'name': 'Beatport', 'shortcut': 'bp'},  # Electronic music with BPM/key data
        'discogs music': {'name': 'Discogs Music', 'shortcut': 'disc'},
        'jamendo music': {'name': 'Jamendo Music', 'shortcut': 'jam'},
        'genius': {'name': 'Genius', 'shortcut': 'gen'},  # Regular genius is enabled, not lyrics version
        
        # Streaming/Archive sources
        'piped.music': {'name': 'Piped Music', 'shortcut': 'ppdm'},
        'archive.org audio': {'name': 'Archive.org Audio', 'shortcut': 'araud'},
        'radio paradise': {'name': 'Radio Paradise', 'shortcut': 'rp'},
        'youtube': {'name': 'YouTube', 'shortcut': 'yt'},  # Regular youtube, music version is disabled
        
        # Phase 3 Web Engines
        'spotify web': {'name': 'Spotify Web', 'shortcut': 'spw'},
        'apple music web': {'name': 'Apple Music Web', 'shortcut': 'amw'},
        'tidal web': {'name': 'Tidal Web', 'shortcut': 'tdw'},
        'musixmatch': {'name': 'Musixmatch', 'shortcut': 'mxm'},
        
        # Phase 4 Enhanced Engines
        'musictoscrape': {'name': 'MusicToScrape', 'shortcut': 'mts'},
        'allmusic': {'name': 'AllMusic', 'shortcut': 'am'},
        'pitchfork': {'name': 'Pitchfork', 'shortcut': 'pf'},
        
        # Note: Excluding 'radio browser' as it returns radio stations, not music tracks
    }
    
    def __init__(self, searxng_base_url: str = 'http://localhost:8888'):
        self.searxng_base_url = searxng_base_url
        self.timeout = 10  # seconds per engine
    
    def search(self, query: str, engines: Optional[List[str]] = None, 
               limit: int = 50) -> Dict[str, Any]:
        """
        Search for music across multiple engines
        
        Args:
            query: Search query string
            engines: List of engine names to use (None = all engines)
            limit: Maximum results to return
            
        Returns:
            Dictionary with aggregated search results
        """
        start_time = datetime.now()
        
        # Use specified engines or all active engines
        search_engines = engines if engines else list(self.ACTIVE_ENGINES.keys())
        search_engines = [e for e in search_engines if e in self.ACTIVE_ENGINES]
        
        # Perform parallel searches
        all_results = self._parallel_search(query, search_engines)
        
        # Sanitize and normalize results
        sanitized_results = [validator.sanitize_search_result(r) for r in all_results]
        normalized_results = self._normalize_results(sanitized_results)
        
        # Apply content classification to filter out radio stations
        classified_results = classifier.filter_results(normalized_results)
        
        # Deduplicate results
        deduplicated_results = self._deduplicate_results(classified_results)
        
        # Store results in database (only music tracks)
        self._store_results(deduplicated_results)
        
        # Limit results
        final_results = deduplicated_results[:limit]
        
        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            'success': True,
            'query': query,
            'engines_queried': len(search_engines),
            'total_results': len(deduplicated_results),
            'response_time_ms': response_time_ms,
            'results': final_results
        }
    
    def _parallel_search(self, query: str, engines: List[str]) -> List[Dict[str, Any]]:
        """Execute searches in parallel across multiple engines"""
        all_results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(engines)) as executor:
            future_to_engine = {
                executor.submit(self._search_engine, query, engine): engine 
                for engine in engines
            }
            
            for future in concurrent.futures.as_completed(future_to_engine):
                engine = future_to_engine[future]
                try:
                    results = future.result(timeout=self.timeout)
                    if results:
                        all_results.extend(results)
                        logger.info(f"✅ {engine}: {len(results)} results")
                except Exception as e:
                    logger.warning(f"❌ {engine} search failed: {e}")
        
        return all_results
    
    def _search_engine(self, query: str, engine: str) -> List[Dict[str, Any]]:
        """Search a single engine using SearXNG"""
        try:
            # Don't use shortcuts in query, use engines parameter instead
            url = f"{self.searxng_base_url}/search"
            params = {
                'q': query,
                'format': 'json',
                'engines': engine,
                'categories': 'music',
                'time_range': '',
                'language': 'en'
            }
            
            # Add headers to avoid 403 errors
            headers = {
                'User-Agent': 'SearXNG-Cool Orchestrator/1.0',
                'Accept': 'application/json',
                'X-Forwarded-For': '127.0.0.1'  # Indicate local request
            }
            
            logger.info(f"Searching {engine} with URL: {url}, query: '{query}'")
            
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            
            logger.info(f"Engine {engine}: Status {response.status_code}, Final URL: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Add engine info to each result
                for result in results:
                    result['_engine'] = engine
                    result['_engine_name'] = self.ACTIVE_ENGINES[engine]['name']
                
                return results
            else:
                logger.warning(f"Engine {engine} returned status {response.status_code}")
                if response.status_code == 403:
                    logger.warning(f"403 response body: {response.text[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching {engine}: {e}")
            return []
    
    def _normalize_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize results from different engines into consistent format"""
        normalized = []
        
        for result in raw_results:
            try:
                # Extract common fields
                normalized_result = {
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'engine': result.get('_engine', 'unknown'),
                    'engine_name': result.get('_engine_name', 'Unknown'),
                    'content': result.get('content', ''),
                    'thumbnail': result.get('img_src') or result.get('thumbnail', ''),
                    'metadata': {}
                }
                
                # Extract engine-specific metadata
                if 'duration' in result:
                    normalized_result['metadata']['duration'] = result['duration']
                if 'artist' in result:
                    normalized_result['metadata']['artist'] = result['artist']
                if 'album' in result:
                    normalized_result['metadata']['album'] = result['album']
                if 'publishedDate' in result:
                    normalized_result['metadata']['published_date'] = result['publishedDate']
                
                # Parse title for artist/track info if not provided
                if 'artist' not in normalized_result['metadata']:
                    parts = normalized_result['title'].split(' - ', 1)
                    if len(parts) == 2:
                        normalized_result['metadata']['artist'] = parts[0].strip()
                        normalized_result['metadata']['track'] = parts[1].strip()
                    else:
                        normalized_result['metadata']['track'] = normalized_result['title']
                
                # Enhance metadata using classifier
                normalized_result = classifier.enhance_metadata(normalized_result)
                
                normalized.append(normalized_result)
                
            except Exception as e:
                logger.warning(f"Failed to normalize result: {e}")
        
        return normalized
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate results based on title similarity"""
        seen = set()
        deduplicated = []
        
        for result in results:
            # Create a simple key for deduplication
            # In production, would use audio fingerprinting
            key = self._create_dedup_key(result)
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)
        
        return deduplicated
    
    def _create_dedup_key(self, result: Dict[str, Any]) -> str:
        """Create a key for deduplication"""
        title = result.get('title', '').lower()
        artist = result.get('metadata', {}).get('artist', '').lower()
        
        # Remove common words and punctuation
        import re
        title_clean = re.sub(r'[^\w\s]', '', title)
        artist_clean = re.sub(r'[^\w\s]', '', artist)
        
        return f"{artist_clean}:{title_clean}"
    
    def _store_results(self, results: List[Dict[str, Any]]) -> None:
        """Store search results in database for caching and analysis"""
        try:
            for result in results[:20]:  # Store top 20 results
                # Check if artist exists or create new one
                artist_name = result.get('metadata', {}).get('artist', 'Unknown Artist')
                artist = Artist.query.filter_by(name=artist_name).first()
                if not artist:
                    artist = Artist(name=artist_name)
                    db.session.add(artist)
                
                # Check if track exists or create new one
                track_title = result.get('metadata', {}).get('track', result.get('title', ''))
                track = Track.query.filter_by(
                    title=track_title,
                    artist_id=artist.id if artist else None
                ).first()
                
                if not track:
                    # Prepare track data for storage
                    # WORKAROUND: Truncate title to 255 chars until we can alter DB
                    truncated_title = track_title[:255]
                    if len(track_title) > 255:
                        logger.warning(f"Truncating long title: {track_title[:50]}...")
                    
                    track_data = {
                        'title': truncated_title,
                        'artist_id': artist.id if artist else None,
                        'search_vector': f"{artist_name} {truncated_title}",
                        'duration_ms': self._extract_duration_ms(result),
                        'preview_url': result.get('url', '')[:500],
                        'extra_metadata': result.get('metadata', {})
                    }
                    
                    # Validate before storage
                    is_valid, errors = validator.validate_for_storage(track_data)
                    if not is_valid:
                        logger.warning(f"Skipping invalid track: {errors}")
                        continue
                    
                    # Prepare and create track
                    prepared_data = validator.prepare_for_storage(track_data)
                    track = Track(**prepared_data)
                    db.session.add(track)
                    db.session.flush()  # Get track ID
                
                # Add track source with optional source_id
                source_data = {
                    'track_id': track.id,
                    'source_type': result.get('engine', 'unknown'),
                    'source_uri': result.get('url', '')[:500],
                    'is_available': True,
                    'last_synced': datetime.utcnow()
                }
                
                # Only add source_id if available
                source_id = result.get('id') or result.get('source_id')
                if source_id:
                    source_data['source_id'] = str(source_id)[:255]
                
                source = TrackSource(**source_data)
                db.session.add(source)
            
            db.session.commit()
            logger.info(f"Stored {len(results[:20])} results in database")
            
        except Exception as e:
            logger.error(f"Failed to store results: {e}")
            db.session.rollback()
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get status of all music engines"""
        engine_status = []
        
        for engine_id, engine_info in self.ACTIVE_ENGINES.items():
            engine_status.append({
                'id': engine_id,
                'name': engine_info['name'],
                'shortcut': engine_info['shortcut'],
                'status': 'active',
                'supported_features': self._get_engine_features(engine_id)
            })
        
        # Add failed engine
        engine_status.append({
            'id': 'archive_audio',
            'name': 'Archive.org Audio',
            'shortcut': '!arc',
            'status': 'failed',
            'supported_features': []
        })
        
        return {
            'total_engines': 12,
            'active_engines': 11,
            'failed_engines': 1,
            'engines': engine_status
        }
    
    def _get_engine_features(self, engine: str) -> List[str]:
        """Get supported features for each engine"""
        features_map = {
            'discogs': ['artist', 'album', 'vinyl', 'marketplace'],
            'jamendo': ['free_music', 'download', 'licensing'],
            'soundcloud': ['streaming', 'waveform', 'comments', 'likes'],
            'bandcamp': ['purchase', 'download', 'artist_direct'],
            'genius': ['lyrics', 'annotations', 'artist_info'],
            'youtube_music': ['video', 'playlist', 'recommendations'],
            'radio_paradise': ['curated', 'high_quality', 'live']
        }
        
        base_features = features_map.get(engine.replace('_enhanced', ''), ['search'])
        if '_enhanced' in engine:
            base_features.append('enhanced_metadata')
        
        return base_features
    
    def _extract_duration_ms(self, result: Dict[str, Any]) -> Optional[int]:
        """Extract duration in milliseconds from result"""
        # Check for direct duration field
        if 'duration' in result:
            duration = result['duration']
            if isinstance(duration, (int, float)):
                # Assume seconds if < 1000, otherwise milliseconds
                return int(duration * 1000) if duration < 1000 else int(duration)
            elif isinstance(duration, str):
                # Parse duration string
                return validator._parse_duration_string(duration)
        
        # Check in metadata
        if 'metadata' in result and 'duration' in result['metadata']:
            return self._extract_duration_ms({'duration': result['metadata']['duration']})
        
        return None