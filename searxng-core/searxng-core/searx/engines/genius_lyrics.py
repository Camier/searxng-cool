# SPDX-License-Identifier: AGPL-3.0-or-later
"""Genius (Music/Lyrics Metadata)

Search for song metadata, artist information, and links to lyrics on Genius.
Note: This engine provides metadata only - actual lyrics are not available through the API.
"""

import json
from urllib.parse import urlencode, quote
from datetime import datetime

# About
about = {
    'website': 'https://genius.com',
    'wikidata_id': 'Q3419343',
    'official_api_documentation': 'https://docs.genius.com/',
    'use_official_api': True,
    'require_api_key': True,
    'results': 'JSON',
}

# Engine configuration
engine_type = 'online'
categories = ['music', 'lyrics']
paging = True

# API configuration - requires a valid access token
# Get token from: https://genius.com/api-clients
api_key = None  # Set this in settings.yml
base_url = 'https://api.genius.com'
search_url = base_url + '/search'

# Number of results
page_size = 20


def request(query, params):
    """Build request parameters for Genius API"""
    
    if not api_key:
        raise Exception("Genius API requires an access token. Get one from https://genius.com/api-clients")
    
    # Calculate pagination
    page = params.get('pageno', 1)
    
    # Build request parameters
    request_params = {
        'q': query,
        'per_page': page_size,
        'page': page,
        'text_format': 'plain'  # Return plain text instead of DOM
    }
    
    params['url'] = f"{search_url}?{urlencode(request_params)}"
    
    # Add authorization header
    params['headers'] = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json',
    }
    
    return params


def response(resp):
    """Parse response from Genius API"""
    results = []
    
    if resp.status_code == 401:
        raise Exception("Invalid or missing Genius API token")
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Check if we have results
    if 'response' not in json_data or 'hits' not in json_data['response']:
        return []
    
    for hit in json_data['response']['hits']:
        # Skip non-song results
        if hit.get('type') != 'song':
            continue
            
        result_data = hit.get('result', {})
        
        # Basic information
        title = result_data.get('title', '')
        artist = result_data.get('artist_names', 'Unknown Artist')
        url = result_data.get('url', '')
        
        if not url:
            continue
        
        # Build display title
        display_title = f"{artist} - {title}"
        
        # Build content with metadata
        content_parts = []
        
        # Album information
        album = result_data.get('album')
        if album:
            album_name = album.get('name')
            if album_name:
                content_parts.append(f"Album: {album_name}")
        
        # Release date
        release_date = result_data.get('release_date_for_display')
        if release_date:
            content_parts.append(f"Released: {release_date}")
        
        # Stats
        stats = result_data.get('stats', {})
        pageviews = stats.get('pageviews')
        if pageviews:
            if pageviews > 1000000:
                content_parts.append(f"Views: {pageviews/1000000:.1f}M")
            elif pageviews > 1000:
                content_parts.append(f"Views: {pageviews/1000:.0f}K")
            else:
                content_parts.append(f"Views: {pageviews}")
        
        # Hot indicator
        if stats.get('hot', False):
            content_parts.append("🔥 Trending")
        
        # Primary artist details
        primary_artist = result_data.get('primary_artist', {})
        if primary_artist.get('is_verified'):
            content_parts.append("✓ Verified Artist")
        
        # Song relationships
        relationships = result_data.get('song_relationships')
        if relationships:
            for rel in relationships:
                rel_type = rel.get('relationship_type', '')
                songs = rel.get('songs', [])
                if rel_type and songs:
                    if rel_type == 'samples':
                        content_parts.append(f"Samples: {len(songs)} song(s)")
                    elif rel_type == 'sampled_in':
                        content_parts.append(f"Sampled in: {len(songs)} song(s)")
                    elif rel_type == 'interpolates':
                        content_parts.append(f"Interpolates: {len(songs)} song(s)")
        
        # Featured artists
        featured_artists = result_data.get('featured_artists', [])
        if featured_artists:
            featured_names = [artist.get('name') for artist in featured_artists if artist.get('name')]
            if featured_names:
                content_parts.append(f"Featuring: {', '.join(featured_names)}")
        
        # Annotation count (indicates community engagement)
        annotation_count = result_data.get('annotation_count', 0)
        if annotation_count > 0:
            content_parts.append(f"Annotations: {annotation_count}")
        
        content = ' | '.join(content_parts)
        
        # Create result
        result = {
            'url': url,
            'title': display_title,
            'content': content,
        }
        
        # Add thumbnail
        header_image = result_data.get('header_image_thumbnail_url') or result_data.get('song_art_image_thumbnail_url')
        if header_image:
            result['thumbnail'] = header_image
        
        # Note about lyrics
        result['content'] = result['content'] + " | Click to view lyrics on Genius"
        
        # Add published date if available
        release_date_components = result_data.get('release_date_components')
        if release_date_components:
            try:
                year = release_date_components.get('year')
                month = release_date_components.get('month', 1)
                day = release_date_components.get('day', 1)
                if year:
                    result['publishedDate'] = datetime(year, month, day)
            except (ValueError, TypeError):
                pass
        
        results.append(result)
    
    return results