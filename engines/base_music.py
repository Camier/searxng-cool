"""
Base class for music engines with common functionality
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from searx import logger

logger = logger.getChild('base_music')


class MusicEngineBase:
    """Base class providing common functionality for music search engines"""
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """
        Convert various duration formats to milliseconds
        
        Examples:
        - "3:45" -> 225000
        - "1:02:30" -> 3750000
        - "225" -> 225000 (assumes seconds)
        - "3m 45s" -> 225000
        """
        if not duration_str:
            return None
            
        try:
            # Handle pure number (assume seconds)
            if duration_str.isdigit():
                return int(duration_str) * 1000
            
            # Handle MM:SS or HH:MM:SS format
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 2:  # MM:SS
                    minutes, seconds = map(int, parts)
                    return (minutes * 60 + seconds) * 1000
                elif len(parts) == 3:  # HH:MM:SS
                    hours, minutes, seconds = map(int, parts)
                    return (hours * 3600 + minutes * 60 + seconds) * 1000
            
            # Handle "3m 45s" format
            minutes = 0
            seconds = 0
            
            min_match = re.search(r'(\d+)\s*m', duration_str, re.IGNORECASE)
            if min_match:
                minutes = int(min_match.group(1))
            
            sec_match = re.search(r'(\d+)\s*s', duration_str, re.IGNORECASE)
            if sec_match:
                seconds = int(sec_match.group(1))
            
            if minutes or seconds:
                return (minutes * 60 + seconds) * 1000
                
        except Exception as e:
            logger.debug(f"Failed to parse duration '{duration_str}': {e}")
        
        return None
    
    def normalize_artist(self, artist_str: str) -> str:
        """
        Normalize artist names (feat., ft., &, etc.)
        
        Examples:
        - "Artist1 feat. Artist2" -> "Artist1"
        - "Artist1 ft. Artist2" -> "Artist1"
        - "Artist1 & Artist2" -> "Artist1 & Artist2" (keep collaborations)
        """
        if not artist_str:
            return ""
        
        # Remove featuring artists for primary artist
        artist = re.sub(r'\s+(?:feat\.|ft\.|featuring)\s+.*$', '', artist_str, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        artist = ' '.join(artist.split())
        
        return artist.strip()
    
    def extract_featured_artists(self, artist_str: str) -> List[str]:
        """Extract all artists including featured ones"""
        if not artist_str:
            return []
        
        artists = []
        
        # Get primary artist
        primary = self.normalize_artist(artist_str)
        if primary:
            artists.append(primary)
        
        # Extract featured artists
        feat_match = re.search(r'(?:feat\.|ft\.|featuring)\s+(.+)$', artist_str, re.IGNORECASE)
        if feat_match:
            featured = feat_match.group(1)
            # Split by common separators
            for artist in re.split(r'[,&]', featured):
                artist = artist.strip()
                if artist:
                    artists.append(artist)
        
        return artists
    
    def extract_year(self, date_str: str) -> Optional[int]:
        """
        Extract year from various date formats
        
        Examples:
        - "2023-04-15" -> 2023
        - "2023" -> 2023
        - "April 15, 2023" -> 2023
        """
        if not date_str:
            return None
        
        try:
            # Try to find 4-digit year
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', date_str)
            if year_match:
                return int(year_match.group(1))
            
            # Try parsing as date
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%B %d, %Y', '%d %B %Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.year
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.debug(f"Failed to extract year from '{date_str}': {e}")
        
        return None
    
    def build_thumbnail_url(self, image_id: str, size: str = 'medium', base_url: str = '') -> str:
        """
        Build thumbnail URL with size options
        
        Args:
            image_id: Image identifier
            size: Size option ('small', 'medium', 'large')
            base_url: Base URL for the image service
        """
        if not image_id:
            return ''
        
        # If already a full URL, return as is
        if image_id.startswith(('http://', 'https://')):
            return image_id
        
        # Build URL based on base_url
        if base_url:
            return f"{base_url}/{size}/{image_id}"
        
        return image_id
    
    def clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def standardize_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize result to match the required format
        
        Expected output format:
        {
            'url': str,
            'title': str,
            'artist': str,
            'artists': List[str],
            'album': str,
            'duration_ms': int,
            'preview_url': str,
            'thumbnail': str,
            'release_date': str,
            'genres': List[str],
            'isrc': str,
            'mbid': str,
            'engine_data': dict
        }
        """
        # Start with basic required fields
        result = {
            'url': raw_result.get('url', ''),
            'title': raw_result.get('title', ''),
            'content': '',  # For SearXNG compatibility
            'template': 'default.html'
        }
        
        # Extract artist information
        artist_str = raw_result.get('artist', '')
        result['artist'] = self.normalize_artist(artist_str)
        result['artists'] = self.extract_featured_artists(artist_str)
        
        # Add optional fields if available
        if 'album' in raw_result:
            result['album'] = raw_result['album']
        
        if 'duration' in raw_result:
            duration_ms = self.parse_duration(str(raw_result['duration']))
            if duration_ms:
                result['duration_ms'] = duration_ms
        
        if 'preview_url' in raw_result:
            result['preview_url'] = raw_result['preview_url']
        
        if 'thumbnail' in raw_result:
            result['thumbnail'] = raw_result['thumbnail']
        elif 'image' in raw_result:
            result['thumbnail'] = raw_result['image']
        
        if 'release_date' in raw_result:
            result['release_date'] = raw_result['release_date']
            year = self.extract_year(raw_result['release_date'])
            if year:
                result['year'] = year
        
        if 'genres' in raw_result:
            if isinstance(raw_result['genres'], list):
                result['genres'] = raw_result['genres']
            else:
                result['genres'] = [str(raw_result['genres'])]
        elif 'genre' in raw_result:
            result['genres'] = [str(raw_result['genre'])]
        
        # Add identifiers
        for id_field in ['isrc', 'mbid']:
            if id_field in raw_result:
                result[id_field] = raw_result[id_field]
        
        # Store any engine-specific data
        result['engine_data'] = {
            k: v for k, v in raw_result.items()
            if k not in result
        }
        
        # Build content field for display
        content_parts = []
        if result.get('artist'):
            content_parts.append(result['artist'])
        if result.get('album'):
            content_parts.append(f"Album: {result['album']}")
        if result.get('duration_ms'):
            duration_sec = result['duration_ms'] // 1000
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            content_parts.append(f"{minutes}:{seconds:02d}")
        
        result['content'] = ' • '.join(content_parts)
        
        # Add metadata for SearXNG
        result['metadata'] = {
            'artist': result.get('artist', ''),
            'track': result.get('title', ''),
            'album': result.get('album', ''),
            'duration': result.get('duration_ms'),
            'genres': result.get('genres', [])
        }
        
        
        # Add the 'key' field that SearXNG expects
        if 'key' not in result:
            # Generate a unique key from title and URL
            import hashlib
            key_string = f"{result.get('title', '')}{result.get('url', '')}"
            result['key'] = hashlib.md5(key_string.encode()).hexdigest()[:16]
        
        return result