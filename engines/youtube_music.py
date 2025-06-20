# SPDX-License-Identifier: AGPL-3.0-or-later
"""YouTube Music (Music Videos)

Search for music videos on YouTube using the YouTube Data API v3.
Requires an API key from Google Cloud Console.
"""

import json
from urllib.parse import urlencode
from datetime import datetime, timedelta
import re

# About
about = {
    'website': 'https://music.youtube.com',
    'wikidata_id': 'Q28404534',
    'official_api_documentation': 'https://developers.google.com/youtube/v3/docs/',
    'use_official_api': True,
    'require_api_key': True,
    'results': 'JSON',
}

# Engine configuration
engine_type = 'online'
categories = ['music', 'videos']
paging = True
time_range_support = True

# API configuration
api_key = None  # Set this in settings.yml
base_url = 'https://www.googleapis.com/youtube/v3'
search_url = base_url + '/search'
video_url = base_url + '/videos'

# Music category ID for YouTube
music_category_id = '10'

# Time range mapping
time_range_map = {
    'day': 'today',
    'week': 'thisWeek',
    'month': 'thisMonth',
    'year': 'thisYear',
}

# Results per page
page_size = 20


def request(query, params):
    """Build request parameters for YouTube Data API v3"""
    
    if not api_key:
        raise Exception("YouTube Data API requires an API key. Get one from https://console.cloud.google.com/")
    
    # Build search parameters
    search_params = {
        'q': query,
        'part': 'snippet',
        'type': 'video',
        'videoCategoryId': music_category_id,  # Music category
        'maxResults': page_size,
        'key': api_key,
        'safeSearch': 'none',
        'videoEmbeddable': 'true',
        'relevanceLanguage': params.get('language', 'en'),
    }
    
    # Add time range filter
    if params.get('time_range') in time_range_map:
        search_params['publishedAfter'] = _get_published_after(params['time_range'])
    
    # Handle pagination
    if params.get('pageno', 1) > 1:
        # YouTube uses pageToken for pagination
        # We'll need to implement proper token handling in a real implementation
        # For now, we'll skip pages by using offset simulation
        pass
    
    # Sort by relevance for music
    search_params['order'] = 'relevance'
    
    params['url'] = f"{search_url}?{urlencode(search_params)}"
    
    return params


def response(resp):
    """Parse response from YouTube Data API v3"""
    results = []
    
    if resp.status_code == 403:
        raise Exception("YouTube API quota exceeded or invalid API key")
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Check for API errors
    if 'error' in json_data:
        error_msg = json_data['error'].get('message', 'Unknown error')
        raise Exception(f"YouTube API error: {error_msg}")
    
    # Extract video IDs for additional details
    video_ids = []
    items_data = {}
    
    for item in json_data.get('items', []):
        video_id = item.get('id', {}).get('videoId')
        if video_id:
            video_ids.append(video_id)
            items_data[video_id] = item
    
    # Get additional video details (duration, view count, etc.)
    # This would require an additional API call in a real implementation
    # For now, we'll work with snippet data only
    
    for video_id, item in items_data.items():
        snippet = item.get('snippet', {})
        
        # Basic information
        title = snippet.get('title', '')
        channel = snippet.get('channelTitle', 'Unknown Artist')
        description = snippet.get('description', '')
        
        # Clean title - remove common suffixes
        clean_title = title
        for suffix in ['(Official Video)', '(Official Music Video)', '(Audio)', '(Lyrics)', '(Lyric Video)']:
            clean_title = clean_title.replace(suffix, '').strip()
        
        # URL
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Build content
        content_parts = []
        
        # Channel/Artist
        content_parts.append(f"Channel: {channel}")
        
        # Published date
        published_at = snippet.get('publishedAt')
        if published_at:
            try:
                pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                # Calculate age
                age = datetime.now() - pub_date.replace(tzinfo=None)
                if age.days < 1:
                    content_parts.append("Published: Today")
                elif age.days < 7:
                    content_parts.append(f"Published: {age.days} days ago")
                elif age.days < 30:
                    weeks = age.days // 7
                    content_parts.append(f"Published: {weeks} week{'s' if weeks > 1 else ''} ago")
                elif age.days < 365:
                    months = age.days // 30
                    content_parts.append(f"Published: {months} month{'s' if months > 1 else ''} ago")
                else:
                    years = age.days // 365
                    content_parts.append(f"Published: {years} year{'s' if years > 1 else ''} ago")
            except:
                pass
        
        # Extract potential artist and song from title
        # Common patterns: "Artist - Song", "Artist: Song", "Song by Artist"
        artist_match = re.match(r'^([^-:]+)\s*[-:]\s*(.+)$', clean_title)
        if artist_match:
            potential_artist = artist_match.group(1).strip()
            potential_song = artist_match.group(2).strip()
            display_title = f"{potential_artist} - {potential_song}"
        else:
            display_title = clean_title
        
        # Truncate description
        if description:
            desc_preview = description[:200]
            if len(description) > 200:
                desc_preview += '...'
            # Remove multiple newlines
            desc_preview = ' '.join(desc_preview.split())
            content_parts.append(desc_preview)
        
        # Quality indicators
        if 'HD' in title or '4K' in title or 'HQ' in title:
            content_parts.append("🎥 High Quality")
        
        # Type indicators
        if 'Official' in title:
            content_parts.append("✓ Official")
        if 'Live' in title or 'Concert' in title:
            content_parts.append("🎤 Live")
        if 'Acoustic' in title:
            content_parts.append("🎸 Acoustic")
        if 'Remix' in title:
            content_parts.append("🎛️ Remix")
        
        content = ' | '.join(content_parts)
        
        # Create result
        result = {
            'url': url,
            'title': display_title,
            'content': content,
        }
        
        # Add thumbnail
        thumbnails = snippet.get('thumbnails', {})
        # Prefer high quality thumbnail
        thumbnail = (thumbnails.get('maxres', {}).get('url') or
                    thumbnails.get('high', {}).get('url') or
                    thumbnails.get('medium', {}).get('url') or
                    thumbnails.get('default', {}).get('url'))
        
        if thumbnail:
            result['thumbnail'] = thumbnail
        
        # Add embedded player
        result['iframe_src'] = f"https://www.youtube.com/embed/{video_id}"
        
        # Add published date
        if published_at:
            try:
                result['publishedDate'] = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except:
                pass
        
        results.append(result)
    
    return results


def _get_published_after(time_range):
    """Calculate the publishedAfter parameter for time range filtering"""
    now = datetime.utcnow()
    
    if time_range == 'day':
        delta = timedelta(days=1)
    elif time_range == 'week':
        delta = timedelta(days=7)
    elif time_range == 'month':
        delta = timedelta(days=30)
    elif time_range == 'year':
        delta = timedelta(days=365)
    else:
        return None
    
    # YouTube API requires RFC 3339 formatted date-time
    published_after = now - delta
    return published_after.strftime('%Y-%m-%dT%H:%M:%SZ')