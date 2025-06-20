"""
Data Validation Service
Ensures data integrity and quality throughout the pipeline
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import html
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates and sanitizes data at various stages of processing"""
    
    # Validation constants
    MAX_TITLE_LENGTH = 500  # After migration to TEXT
    MAX_URL_LENGTH = 2000
    MAX_CONTENT_LENGTH = 5000
    MIN_DURATION_MS = 1000  # 1 second
    MAX_DURATION_MS = 14400000  # 4 hours
    
    # Dangerous patterns to sanitize
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'data:text/html',  # Data URLs with HTML
    ]
    
    def __init__(self):
        self.compile_patterns()
    
    def compile_patterns(self):
        """Pre-compile regex patterns"""
        self.dangerous_regex = [
            re.compile(p, re.IGNORECASE | re.DOTALL) 
            for p in self.DANGEROUS_PATTERNS
        ]
        self.whitespace_regex = re.compile(r'\s+')
        self.url_regex = re.compile(
            r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}'
            r'\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'
        )
    
    def validate_search_input(self, query: str, engines: List[str] = None) -> Tuple[bool, str]:
        """
        Validate search input parameters
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate query
        if not query or not query.strip():
            return False, "Search query cannot be empty"
        
        query = query.strip()
        if len(query) < 2:
            return False, "Search query must be at least 2 characters"
        
        if len(query) > 200:
            return False, "Search query too long (max 200 characters)"
        
        # Check for malicious patterns
        if self._contains_dangerous_content(query):
            return False, "Search query contains invalid characters"
        
        # Validate engines if provided
        if engines:
            valid_engines = {
                'bandcamp enhanced', 'soundcloud', 'mixcloud enhanced',
                'discogs music', 'jamendo music', 'genius',
                'piped.music', 'archive.org audio', 'radio paradise', 'youtube'
            }
            
            invalid_engines = [e for e in engines if e not in valid_engines]
            if invalid_engines:
                return False, f"Invalid engines: {', '.join(invalid_engines)}"
        
        return True, ""
    
    def sanitize_search_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a search result before processing
        
        Removes dangerous content and normalizes data
        """
        sanitized = result.copy()
        
        # Sanitize text fields
        text_fields = ['title', 'content', 'artist', 'album', 'track']
        for field in text_fields:
            if field in sanitized and sanitized[field]:
                sanitized[field] = self._sanitize_text(sanitized[field])
        
        # Validate and sanitize URL
        if 'url' in sanitized:
            sanitized['url'] = self._sanitize_url(sanitized['url'])
        
        # Validate duration
        if 'duration' in sanitized:
            sanitized['duration'] = self._validate_duration(sanitized['duration'])
        
        # Clean metadata
        if 'metadata' in sanitized and isinstance(sanitized['metadata'], dict):
            sanitized['metadata'] = self._sanitize_metadata(sanitized['metadata'])
        
        return sanitized
    
    def validate_for_storage(self, track_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate data before database storage
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        if not track_data.get('title'):
            errors.append("Title is required")
        elif len(track_data['title']) > self.MAX_TITLE_LENGTH:
            errors.append(f"Title too long (max {self.MAX_TITLE_LENGTH} chars)")
        
        # Duration validation
        duration = track_data.get('duration_ms')
        if duration is not None:
            if not isinstance(duration, (int, float)):
                errors.append("Duration must be a number")
            elif duration < self.MIN_DURATION_MS:
                errors.append("Duration too short (min 1 second)")
            elif duration > self.MAX_DURATION_MS:
                errors.append("Duration too long (max 4 hours)")
        
        # URL validation
        urls = ['preview_url', 'source_uri']
        for url_field in urls:
            if url_field in track_data and track_data[url_field]:
                url = track_data[url_field]
                if len(url) > self.MAX_URL_LENGTH:
                    errors.append(f"{url_field} too long (max {self.MAX_URL_LENGTH} chars)")
                elif not self._is_valid_url(url):
                    errors.append(f"{url_field} is not a valid URL")
        
        # ISRC validation
        if 'isrc' in track_data and track_data['isrc']:
            if not self._is_valid_isrc(track_data['isrc']):
                errors.append("Invalid ISRC code format")
        
        return len(errors) == 0, errors
    
    def prepare_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for database storage
        
        Truncates fields, converts types, and ensures compatibility
        """
        prepared = data.copy()
        
        # Ensure title fits even after migration (safety check)
        if 'title' in prepared and prepared['title']:
            prepared['title'] = prepared['title'][:self.MAX_TITLE_LENGTH]
        
        # Convert duration to milliseconds if needed
        if 'duration' in prepared and 'duration_ms' not in prepared:
            duration = prepared.pop('duration')
            if isinstance(duration, str):
                # Parse duration string (e.g., "3:45")
                ms = self._parse_duration_string(duration)
                if ms:
                    prepared['duration_ms'] = ms
            elif isinstance(duration, (int, float)):
                # Assume seconds, convert to ms
                prepared['duration_ms'] = int(duration * 1000)
        
        # Ensure URLs are strings
        url_fields = ['preview_url', 'source_uri']
        for field in url_fields:
            if field in prepared and prepared[field]:
                prepared[field] = str(prepared[field])[:self.MAX_URL_LENGTH]
        
        # Clean metadata for JSONB storage
        if 'extra_metadata' in prepared:
            prepared['extra_metadata'] = self._clean_json_data(prepared['extra_metadata'])
        
        if 'audio_features' in prepared:
            prepared['audio_features'] = self._clean_json_data(prepared['audio_features'])
        
        # Set timestamps
        now = datetime.utcnow()
        prepared.setdefault('created_at', now)
        prepared.setdefault('updated_at', now)
        
        return prepared
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content"""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove dangerous patterns
        for pattern in self.dangerous_regex:
            text = pattern.sub('', text)
        
        # Normalize whitespace
        text = self.whitespace_regex.sub(' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _sanitize_url(self, url: str) -> str:
        """Sanitize and validate URL"""
        if not url:
            return ""
        
        url = url.strip()
        
        # Basic validation
        if not url.startswith(('http://', 'https://')):
            return ""
        
        # Remove dangerous URL patterns
        if any(pattern in url.lower() for pattern in ['javascript:', 'data:', 'vbscript:']):
            return ""
        
        return url[:self.MAX_URL_LENGTH]
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata dictionary"""
        clean_metadata = {}
        
        for key, value in metadata.items():
            # Sanitize keys
            clean_key = self._sanitize_text(str(key))[:50]
            
            # Sanitize values based on type
            if isinstance(value, str):
                clean_metadata[clean_key] = self._sanitize_text(value)[:500]
            elif isinstance(value, (int, float, bool)):
                clean_metadata[clean_key] = value
            elif isinstance(value, list):
                # Limit list size and sanitize string elements
                clean_list = []
                for item in value[:20]:  # Max 20 items
                    if isinstance(item, str):
                        clean_list.append(self._sanitize_text(item)[:100])
                    elif isinstance(item, (int, float, bool)):
                        clean_list.append(item)
                clean_metadata[clean_key] = clean_list
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts (1 level deep)
                clean_metadata[clean_key] = {
                    self._sanitize_text(str(k))[:50]: self._sanitize_text(str(v))[:100]
                    for k, v in list(value.items())[:10]
                }
        
        return clean_metadata
    
    def _contains_dangerous_content(self, text: str) -> bool:
        """Check if text contains dangerous patterns"""
        return any(pattern.search(text) for pattern in self.dangerous_regex)
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _is_valid_isrc(self, isrc: str) -> bool:
        """Validate ISRC format (e.g., USRC17607839)"""
        if not isrc:
            return True  # Optional field
        
        # ISRC format: CC-XXX-YY-NNNNN
        # Often stored without hyphens: CCXXXYYNNNNN
        isrc_pattern = re.compile(r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$')
        return bool(isrc_pattern.match(isrc.replace('-', '').upper()))
    
    def _validate_duration(self, duration: Any) -> Optional[int]:
        """Validate and normalize duration to milliseconds"""
        if duration is None:
            return None
        
        if isinstance(duration, str):
            ms = self._parse_duration_string(duration)
            if ms and self.MIN_DURATION_MS <= ms <= self.MAX_DURATION_MS:
                return ms
        elif isinstance(duration, (int, float)):
            ms = int(duration * 1000) if duration < 1000 else int(duration)
            if self.MIN_DURATION_MS <= ms <= self.MAX_DURATION_MS:
                return ms
        
        return None
    
    def _parse_duration_string(self, duration_str: str) -> Optional[int]:
        """Parse duration string to milliseconds"""
        # Match patterns like "3:45", "1:23:45"
        match = re.match(r'^(?:(\d+):)?(\d+):(\d{2})$', duration_str.strip())
        if match:
            parts = match.groups()
            if parts[0]:  # HH:MM:SS
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
            else:  # MM:SS
                hours = 0
                minutes = int(parts[1])
                seconds = int(parts[2])
            
            return (hours * 3600 + minutes * 60 + seconds) * 1000
        
        return None
    
    def _clean_json_data(self, data: Any) -> Any:
        """Clean data for JSONB storage"""
        if data is None:
            return {}
        
        if isinstance(data, dict):
            return self._sanitize_metadata(data)
        elif isinstance(data, list):
            return [self._clean_json_data(item) for item in data[:50]]
        elif isinstance(data, str):
            return self._sanitize_text(data)[:1000]
        elif isinstance(data, (int, float, bool)):
            return data
        else:
            return str(data)[:100]


# Singleton instance
validator = DataValidator()