"""
Content Classification Service
Identifies and filters music tracks from radio stations and other content
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContentClassifier:
    """Classifies search results to identify actual music tracks"""
    
    # Content type constants
    MUSIC_TRACK = 'music_track'
    RADIO_STATION = 'radio_station'
    PODCAST = 'podcast'
    LYRICS = 'lyrics'
    VIDEO = 'video'
    UNKNOWN = 'unknown'
    
    # Classification rules
    RADIO_PATTERNS = [
        r'\bradio\b', r'\bfm\b', r'\bam\b', r'\bstation\b', 
        r'\bbroadcast', r'\blive\s+stream', r'\bonline\s+radio',
        r'exclusive\.radio', r'radio\.com', r'tunein\.com',
        r'#\s*TOP\s*\d+\s*DJ', r'CHARTS\s*RADIO'
    ]
    
    MUSIC_PATTERNS = [
        r'^([^-]+)\s*-\s*([^-]+)$',  # Artist - Track
        r'^([^-]+)\s+by\s+([^-]+)$',  # Track by Artist
        r'feat\.?\s+', r'ft\.?\s+',  # Featuring
        r'\((original|remix|mix|edit|version)\)',  # Version indicators
        r'\[.*(?:remix|mix|edit)\]'  # Bracketed versions
    ]
    
    PODCAST_PATTERNS = [
        r'\bpodcast\b', r'\bepisode\b', r'\bep\.\s*\d+',
        r'\bshow\b', r'\binterview\b', r'\btalk\b'
    ]
    
    def __init__(self):
        self.compile_patterns()
    
    def compile_patterns(self):
        """Pre-compile regex patterns for performance"""
        self.radio_regex = [re.compile(p, re.IGNORECASE) for p in self.RADIO_PATTERNS]
        self.music_regex = [re.compile(p, re.IGNORECASE) for p in self.MUSIC_PATTERNS]
        self.podcast_regex = [re.compile(p, re.IGNORECASE) for p in self.PODCAST_PATTERNS]
    
    def classify(self, result: Dict[str, Any]) -> Tuple[str, float]:
        """
        Classify a search result and return content type with confidence score
        
        Returns:
            Tuple of (content_type, confidence_score)
        """
        title = result.get('title', '').strip()
        url = result.get('url', '').lower()
        content = result.get('content', '').lower()
        engine = result.get('engine', '').lower()
        
        # Engine-based classification
        if engine == 'radio browser':
            # Radio browser only returns radio stations
            return self.RADIO_STATION, 0.95
        elif engine in ['genius', 'genius lyrics']:
            # Genius only provides lyrics
            return self.LYRICS, 0.95
        
        # Check for radio station patterns
        radio_score = self._calculate_radio_score(title, url, content)
        if radio_score > 0.7:
            return self.RADIO_STATION, radio_score
        
        # Check for podcast patterns
        if self._is_podcast(title, content):
            return self.PODCAST, 0.8
        
        # Check for music track patterns
        music_score = self._calculate_music_score(result)
        if music_score > 0.5:
            return self.MUSIC_TRACK, music_score
        
        # Video content (YouTube, etc.)
        if engine == 'youtube' and 'youtube.com' in url:
            # Could be music video or other content
            if self._has_music_metadata(result):
                return self.VIDEO, 0.7
            else:
                return self.UNKNOWN, 0.3
        
        return self.UNKNOWN, 0.0
    
    def _calculate_radio_score(self, title: str, url: str, content: str) -> float:
        """Calculate probability that content is a radio station"""
        score = 0.0
        
        # Check title patterns
        for pattern in self.radio_regex:
            if pattern.search(title):
                score += 0.3
                break
        
        # Check URL patterns
        radio_domains = ['radio', 'fm', 'stream', 'live', 'broadcast']
        if any(domain in url for domain in radio_domains):
            score += 0.3
        
        # Check content patterns
        if any(pattern.search(content) for pattern in self.radio_regex[:5]):
            score += 0.2
        
        # Long or missing duration indicates streaming
        duration = self._parse_duration(content)
        if duration is None or duration > 3600:  # > 1 hour
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_music_score(self, result: Dict[str, Any]) -> float:
        """Calculate probability that content is a music track"""
        score = 0.0
        title = result.get('title', '')
        
        # Check for artist-track patterns
        for pattern in self.music_regex[:2]:  # Artist - Track patterns
            if pattern.match(title):
                score += 0.4
                break
        
        # Has music metadata
        if self._has_music_metadata(result):
            score += 0.3
        
        # Duration in typical song range (30s - 15min)
        duration = self._parse_duration(result.get('content', ''))
        if duration and 30 <= duration <= 900:
            score += 0.2
        
        # From music-specific engine
        music_engines = ['bandcamp', 'soundcloud', 'jamendo', 'mixcloud']
        if any(engine in result.get('engine', '').lower() for engine in music_engines):
            score += 0.3
        
        return min(score, 1.0)
    
    def _is_podcast(self, title: str, content: str) -> bool:
        """Check if content is likely a podcast"""
        combined = f"{title} {content}".lower()
        return any(pattern.search(combined) for pattern in self.podcast_regex)
    
    def _has_music_metadata(self, result: Dict[str, Any]) -> bool:
        """Check if result has music-specific metadata"""
        music_fields = ['artist', 'album', 'duration', 'track', 'isrc']
        return any(field in result for field in music_fields)
    
    def _parse_duration(self, text: str) -> Optional[int]:
        """Parse duration from text (returns seconds)"""
        if not text:
            return None
        
        # Match patterns like "3:45", "1:23:45"
        duration_match = re.search(r'(\d+):(\d{2})(?::(\d{2}))?', text)
        if duration_match:
            parts = duration_match.groups()
            if parts[2]:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
        
        return None
    
    def filter_results(self, results: List[Dict[str, Any]], 
                      allowed_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Filter results based on content classification
        
        Args:
            results: List of search results
            allowed_types: List of allowed content types (default: music tracks only)
        
        Returns:
            Filtered list of results with classification metadata
        """
        if allowed_types is None:
            allowed_types = [self.MUSIC_TRACK, self.VIDEO]
        
        filtered = []
        stats = {
            self.MUSIC_TRACK: 0,
            self.RADIO_STATION: 0,
            self.PODCAST: 0,
            self.LYRICS: 0,
            self.VIDEO: 0,
            self.UNKNOWN: 0
        }
        
        for result in results:
            content_type, confidence = self.classify(result)
            stats[content_type] += 1
            
            # Add classification metadata
            result['_content_type'] = content_type
            result['_confidence'] = confidence
            
            if content_type in allowed_types:
                filtered.append(result)
        
        logger.info(f"Content classification stats: {stats}")
        logger.info(f"Filtered {len(results)} results to {len(filtered)} music items")
        
        return filtered
    
    def enhance_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance result metadata based on classification
        
        Extracts artist/track info from title if not present
        """
        if result.get('_content_type') != self.MUSIC_TRACK:
            return result
        
        title = result.get('title', '')
        
        # Try to extract artist and track if not present
        if 'artist' not in result or 'track' not in result:
            # Pattern: Artist - Track
            match = re.match(r'^([^-]+)\s*-\s*(.+)$', title)
            if match:
                result.setdefault('artist', match.group(1).strip())
                result.setdefault('track', match.group(2).strip())
            else:
                # Pattern: Track by Artist
                match = re.match(r'^(.+)\s+by\s+([^-]+)$', title, re.IGNORECASE)
                if match:
                    result.setdefault('track', match.group(1).strip())
                    result.setdefault('artist', match.group(2).strip())
        
        # Clean up track name (remove version info for base track)
        if 'track' in result:
            base_track = re.sub(r'\s*\([^)]+\)\s*$', '', result['track'])
            result['base_track'] = base_track.strip()
        
        return result


# Singleton instance
classifier = ContentClassifier()