# SPDX-License-Identifier: AGPL-3.0-or-later
"""Jamendo (Music)

Search free music on Jamendo using their API.
Requires API key for authentication.
"""

from urllib.parse import urlencode
from datetime import datetime

# About
about = {
    'website': 'https://www.jamendo.com',
    'wikidata_id': 'Q1026639',
    'official_api_documentation': 'https://developer.jamendo.com/v3.0',
    'use_official_api': True,
    'require_api_key': True,
    'results': 'JSON',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True
time_range_support = False

# API configuration
base_url = 'https://api.jamendo.com/v3.0'
api_key = None  # Will be set from settings.yml

def request(query, params):
    """Build request parameters for Jamendo API"""
    
    # Check if API key is available
    if not api_key:
        return None
        
    # Calculate offset from page number
    limit = 20
    offset = (params.get('pageno', 1) - 1) * limit
    
    # Build search parameters
    search_params = {
        'client_id': api_key,
        'format': 'json',
        'search': query,
        'limit': limit,
        'offset': offset,
        'include': 'musicinfo',  # Include additional music information
        'groupby': 'artist_id',  # Group by artist to avoid duplicates
    }
    
    # Build the request URL
    params['url'] = f"{base_url}/tracks/?{urlencode(search_params)}"
    
    # Set headers
    params['headers'] = {
        'User-Agent': 'SearXNG/1.0 (+https://searxng.org)',
        'Accept': 'application/json'
    }
    
    return params

def response(resp):
    """Parse response from Jamendo API"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Check for API errors
    if json_data.get('headers', {}).get('status') == 'error':
        return []
        
    if 'results' not in json_data:
        return []
        
    for track in json_data.get('results', []):
        # URL to the track page
        url = track.get('shareurl', '')
        if not url:
            continue
            
        # Build title - Artist - Track Name
        artist_name = track.get('artist_name', 'Unknown Artist')
        track_name = track.get('name', 'Unknown Track')
        title = f"{artist_name} - {track_name}"
        
        # Build content description
        content_parts = []
        
        # Album
        if track.get('album_name'):
            content_parts.append(f"Album: {track['album_name']}")
        
        # Duration
        if track.get('duration'):
            try:
                duration = int(track['duration'])
                minutes = duration // 60
                seconds = duration % 60
                content_parts.append(f"Duration: {minutes}:{seconds:02d}")
            except (ValueError, TypeError):
                pass
                
        # License
        if track.get('license_ccurl'):
            license_name = track['license_ccurl'].split('/')[-2].upper()
            content_parts.append(f"License: {license_name}")
            
        # Tags/Genre
        if track.get('musicinfo') and track['musicinfo'].get('tags'):
            genres = track['musicinfo']['tags'].get('genres', [])
            if genres:
                content_parts.append(f"Genre: {', '.join(genres[:2])}")
                
        content = ' | '.join(content_parts) if content_parts else ''
        
        # Create result
        result = {
            'url': url,
            'title': title,
            'content': content,
        }
        
        # Add thumbnail - album cover
        if track.get('album_image'):
            result['thumbnail'] = track['album_image']
        elif track.get('image'):
            result['thumbnail'] = track['image']
            
        # Add audio stream URL for potential iframe embedding
        if track.get('audio'):
            # Get the highest quality stream available
            audio_url = track['audio']
            if isinstance(audio_url, str):
                result['iframe_src'] = audio_url
                
        # Add published date if available
        if track.get('releasedate'):
            try:
                # Jamendo date format is YYYY-MM-DD
                result['publishedDate'] = datetime.strptime(track['releasedate'], '%Y-%m-%d')
            except (ValueError, TypeError):
                pass
                
        results.append(result)
        
    return results