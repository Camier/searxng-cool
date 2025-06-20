"""
Discogs Music Search Engine for SearXNG

Features:
- Advanced search with filters (year, format, country, label)
- Marketplace data (want/have ratios)
- Master vs release distinction
- Aggressive caching (24h TTL)
"""

import os
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode
import logging

from .base import BaseMusicEngine, APIError

logger = logging.getLogger(__name__)

# Engine metadata for SearXNG
engine_type = 'music'
categories = ['music']
paging = True
time_range_support = True


class DiscogsEngine(BaseMusicEngine):
    """Discogs music search engine implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('discogs', config)
        
        # Get API token from environment or config
        self.api_token = os.environ.get('DISCOGS_API_TOKEN', config.get('api_token'))
        if not self.api_token:
            logger.warning("Discogs API token not configured")
            self.enabled = False
            
        # Discogs-specific configuration
        self.per_page = 50
        self.max_pages = 10
        
    def _search(self, query: str, params: Dict[str, Any]) -> Any:
        """
        Perform search on Discogs API
        
        Args:
            query: Search query
            params: Additional parameters (page, year, format, etc.)
            
        Returns:
            Raw API response
        """
        # Build search parameters
        search_params = {
            'q': query,
            'token': self.api_token,
            'per_page': self.per_page,
            'page': params.get('pageno', 1)
        }
        
        # Add filters if provided
        if params.get('year'):
            search_params['year'] = params['year']
        if params.get('format'):
            search_params['format'] = params['format']
        if params.get('country'):
            search_params['country'] = params['country']
        if params.get('label'):
            search_params['label'] = params['label']
        if params.get('genre'):
            search_params['genre'] = params['genre']
        if params.get('style'):
            search_params['style'] = params['style']
            
        # Determine search type
        search_type = params.get('type', 'all')
        if search_type == 'artist':
            endpoint = '/database/search'
            search_params['type'] = 'artist'
        elif search_type == 'label':
            endpoint = '/database/search'
            search_params['type'] = 'label'
        elif search_type == 'master':
            endpoint = '/database/search'
            search_params['type'] = 'master'
        elif search_type == 'release':
            endpoint = '/database/search'
            search_params['type'] = 'release'
        else:
            # General search
            endpoint = '/database/search'
            
        # Build URL
        url = f"{self.base_url}{endpoint}?{urlencode(search_params)}"
        
        try:
            # Make request with custom headers
            headers = {
                'Authorization': f'Discogs token={self.api_token}',
                'User-Agent': self.config.get('user_agent', 'SearXNG-Cool/1.0')
            }
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            # Check rate limit headers
            remaining = response.headers.get('X-Discogs-Ratelimit-Remaining')
            if remaining:
                logger.debug(f"Discogs rate limit remaining: {remaining}")
                
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 60)
                raise APIError(
                    "Discogs rate limit exceeded",
                    status_code=429
                )
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Discogs API error: {str(e)}")
            raise APIError(f"Discogs API request failed: {str(e)}")
            
    def _parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Discogs API response
        
        Args:
            response: Raw API response
            
        Returns:
            List of parsed results
        """
        results = []
        
        if 'results' not in response:
            return results
            
        for item in response['results']:
            result = {}
            
            # Common fields
            result['id'] = item.get('id')
            result['url'] = f"https://www.discogs.com{item.get('uri', '')}"
            result['thumbnail'] = item.get('thumb', '')
            
            # Parse based on type
            item_type = item.get('type', '')
            
            if item_type == 'release':
                result['title'] = item.get('title', '')
                result['artist'] = self._format_artists(item.get('artist'))
                result['year'] = item.get('year')
                result['format'] = ', '.join(item.get('format', []))
                result['country'] = item.get('country', '')
                result['label'] = ', '.join(item.get('label', []))
                result['catalog_number'] = item.get('catno', '')
                
                # Community data
                community = item.get('community', {})
                result['metadata'] = {
                    'want': community.get('want', 0),
                    'have': community.get('have', 0),
                    'format_details': item.get('format', []),
                    'genre': item.get('genre', []),
                    'style': item.get('style', []),
                    'barcode': item.get('barcode', []),
                    'resource_url': item.get('resource_url', '')
                }
                
                # Generate content
                content_parts = []
                if result['year']:
                    content_parts.append(f"Year: {result['year']}")
                if result['format']:
                    content_parts.append(f"Format: {result['format']}")
                if result['country']:
                    content_parts.append(f"Country: {result['country']}")
                if result['label']:
                    content_parts.append(f"Label: {result['label']}")
                if community:
                    content_parts.append(
                        f"Community: {community.get('have', 0)} have, "
                        f"{community.get('want', 0)} want"
                    )
                    
                result['content'] = ' | '.join(content_parts)
                
            elif item_type == 'master':
                result['title'] = item.get('title', '')
                result['artist'] = self._format_artists(item.get('artist'))
                result['year'] = item.get('year')
                
                result['metadata'] = {
                    'main_release': item.get('main_release'),
                    'versions_url': item.get('versions_url'),
                    'genre': item.get('genre', []),
                    'style': item.get('style', [])
                }
                
                result['content'] = f"Master Release - {result.get('year', 'Unknown Year')}"
                
            elif item_type == 'artist':
                result['title'] = item.get('title', '')
                result['artist'] = result['title']  # For consistency
                result['thumbnail'] = item.get('thumb', '')
                
                result['metadata'] = {
                    'profile': item.get('profile', ''),
                    'releases_url': item.get('releases_url'),
                    'resource_url': item.get('resource_url')
                }
                
                result['content'] = "Artist Profile"
                
            elif item_type == 'label':
                result['title'] = item.get('title', '')
                result['artist'] = 'Label'
                
                result['metadata'] = {
                    'profile': item.get('profile', ''),
                    'releases_url': item.get('releases_url'),
                    'resource_url': item.get('resource_url')
                }
                
                result['content'] = "Record Label"
                
            results.append(result)
            
        return results
        
    def _format_artists(self, artist_string: str) -> str:
        """Format artist string from Discogs format"""
        if not artist_string:
            return 'Unknown Artist'
            
        # Remove trailing numbers in parentheses (e.g., "Artist (2)")
        import re
        artist_string = re.sub(r'\s*\(\d+\)$', '', artist_string)
        
        # Handle "Various" for compilations
        if artist_string.lower() == 'various':
            return 'Various Artists'
            
        return artist_string
        
    def get_release_details(self, release_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific release
        
        Args:
            release_id: Discogs release ID
            
        Returns:
            Detailed release information
        """
        cache_key = f"release:{self.name}:{release_id}"
        
        # Check cache
        if self.cache:
            cached = self._get_cached_results(cache_key)
            if cached:
                return cached
                
        # Apply rate limiting
        if self.rate_limiter:
            self._apply_rate_limit()
            
        url = f"{self.base_url}/releases/{release_id}"
        
        try:
            headers = {
                'Authorization': f'Discogs token={self.api_token}',
                'User-Agent': self.config.get('user_agent', 'SearXNG-Cool/1.0')
            }
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Cache with longer TTL for release details
            if self.cache:
                self.cache.setex(
                    cache_key,
                    604800,  # 1 week
                    json.dumps(data)
                )
                
            return data
            
        except Exception as e:
            logger.error(f"Failed to get release {release_id}: {str(e)}")
            return None


# SearXNG engine interface
def request(query, params):
    """Build request for SearXNG"""
    # This will be called by SearXNG framework
    pass
    
def response(resp):
    """Parse response for SearXNG"""
    # This will be called by SearXNG framework
    pass