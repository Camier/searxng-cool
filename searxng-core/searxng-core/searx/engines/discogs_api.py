# SPDX-License-Identifier: AGPL-3.0-or-later
"""Discogs (Music)

Search music releases, artists, and labels using the Discogs API.
Requires API token for authentication.
"""

from urllib.parse import urlencode
from datetime import datetime

# About
about = {
    'website': 'https://www.discogs.com',
    'wikidata_id': 'Q504063',
    'official_api_documentation': 'https://www.discogs.com/developers/',
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
base_url = 'https://api.discogs.com'
api_key = None  # Will be set from settings.yml

def request(query, params):
    """Build request parameters for Discogs API"""
    
    # Check if API key is available
    if not api_key:
        return None
        
    # Build search parameters
    search_params = {
        'q': query,
        'token': api_key,
        'per_page': 20,
        'page': params.get('pageno', 1),
        'type': 'all'  # Search all types (releases, artists, labels)
    }
    
    # Build the request URL
    params['url'] = f"{base_url}/database/search?{urlencode(search_params)}"
    
    # Set headers
    params['headers'] = {
        'User-Agent': 'SearXNG/1.0 (+https://searxng.org)',
        'Accept': 'application/json'
    }
    
    return params

def response(resp):
    """Parse response from Discogs API"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Check for API errors
    if 'message' in json_data and 'error' in json_data.get('message', '').lower():
        return []
        
    if 'results' not in json_data:
        return []
        
    for item in json_data.get('results', []):
        # Build the web URL from the URI
        if 'uri' in item:
            url = f"https://www.discogs.com{item['uri']}"
        else:
            continue
            
        # Build title - combine artist and title
        title_parts = []
        if item.get('artist'):
            title_parts.append(item['artist'])
        if item.get('title'):
            title_parts.append(item['title'])
            
        if not title_parts:
            continue
            
        title = ' - '.join(title_parts)
        
        # Build content description
        content_parts = []
        
        # Type (Release, Artist, Label, etc.)
        if item.get('type'):
            content_parts.append(item['type'].title())
        
        # Year
        if item.get('year'):
            content_parts.append(str(item['year']))
            
        # Format (Vinyl, CD, etc.)
        if item.get('format'):
            formats = item['format']
            if isinstance(formats, list):
                format_str = ', '.join(formats[:3])  # Limit to first 3 formats
                if len(formats) > 3:
                    format_str += '...'
                content_parts.append(format_str)
                
        # Label
        if item.get('label'):
            labels = item['label']
            if isinstance(labels, list) and labels:
                content_parts.append(labels[0])  # Just first label
            elif isinstance(labels, str):
                content_parts.append(labels)
                
        # Country
        if item.get('country'):
            content_parts.append(item['country'])
            
        # Genre/Style
        if item.get('genre'):
            genres = item['genre']
            if isinstance(genres, list) and genres:
                content_parts.append(f"Genre: {genres[0]}")
                
        content = ' | '.join(content_parts) if content_parts else ''
        
        # Create result
        result = {
            'url': url,
            'title': title,
            'content': content,
        }
        
        # Add thumbnail if available
        if item.get('thumb'):
            result['thumbnail'] = item['thumb']
            
        # Add published date if we have a year
        if item.get('year'):
            try:
                # Create a date object for January 1st of that year
                result['publishedDate'] = datetime(int(item['year']), 1, 1)
            except (ValueError, TypeError):
                pass
                
        results.append(result)
        
    return results