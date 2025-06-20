# SPDX-License-Identifier: AGPL-3.0-or-later
"""SoundCloud Enhanced (Music)

Enhanced SoundCloud engine with additional features and metadata.
Uses the unofficial API endpoints that the SoundCloud website uses.
"""

import re
from json import loads
from urllib.parse import quote_plus, urlencode
from datetime import datetime, timedelta

# About
about = {
    "website": 'https://soundcloud.com',
    "wikidata_id": 'Q568769',
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": 'JSON',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True
time_range_support = True

# SoundCloud uses a client_id for API access
# This needs to be extracted from their website
client_id = None
guest_client_id = None

# Base URLs
base_url = 'https://soundcloud.com'
api_base_url = 'https://api-v2.soundcloud.com'

# Track metadata we want to fetch
track_fields = [
    'artwork_url',
    'created_at',
    'description',
    'duration',
    'genre',
    'id',
    'kind',
    'label_name',
    'last_modified',
    'license',
    'likes_count',
    'media',
    'permalink',
    'permalink_url',
    'playback_count',
    'purchase_title',
    'purchase_url',
    'release_date',
    'reposts_count',
    'state',
    'tag_list',
    'title',
    'track_format',
    'uri',
    'user',
    'user_id',
    'visuals',
    'waveform_url',
    'display_date',
    'media',
    'station_urn',
    'station_permalink',
    'comment_count',
    'full_duration',
    'downloadable',
    'download_url',
    'download_count',
]

# Time range filters
time_range_map = {
    'day': 86400,      # 24 hours
    'week': 604800,    # 7 days
    'month': 2592000,  # 30 days
    'year': 31536000,  # 365 days
}


def get_client_id():
    """Get the SoundCloud client_id"""
    # In a real implementation, this would fetch and parse the SoundCloud
    # website to extract the current client_id
    # For now, return a placeholder
    return "iZIs9mchVcX5lhVRyQGGAYlNPVldzAoX"  # This changes periodically


def request(query, params):
    """Build request for enhanced SoundCloud search"""
    
    # Get client ID
    cid = get_client_id()
    
    # Search parameters
    search_params = {
        'q': query,
        'client_id': cid,
        'limit': 20,
        'offset': (params.get('pageno', 1) - 1) * 20,
        'linked_partitioning': 1,
        'app_version': '1679922870',
        'app_locale': 'en',
    }
    
    # Add filter parameters
    # Filter by tracks (not playlists or users)
    search_params['filter.content_tier'] = 'SUB_HIGH_TIER'
    
    # Time range filter
    if params.get('time_range') in time_range_map:
        # Calculate the date range
        seconds_ago = time_range_map[params['time_range']]
        created_at_from = datetime.utcnow() - timedelta(seconds=seconds_ago)
        search_params['filter.created_at'] = f"from {created_at_from.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Build the search URL
    params['url'] = f"{api_base_url}/search/tracks?{urlencode(search_params)}"
    
    # Add necessary headers
    params['headers'] = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://soundcloud.com/',
        'Origin': 'https://soundcloud.com',
    }
    
    return params


def response(resp):
    """Parse enhanced response from SoundCloud"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Extract tracks from collection
    tracks = json_data.get('collection', [])
    
    for track in tracks:
        # Skip non-track items
        if track.get('kind') != 'track':
            continue
        
        # Basic information
        title = track.get('title', 'Unknown Title')
        url = track.get('permalink_url', '')
        
        if not url:
            continue
        
        # User/Artist information
        user = track.get('user', {})
        artist = user.get('username', 'Unknown Artist')
        verified = user.get('verified', False)
        
        # Format title with artist
        display_title = f"{artist} - {title}"
        if verified:
            display_title = f"✓ {display_title}"
        
        # Build rich content
        content_parts = []
        
        # Duration
        duration = track.get('duration') or track.get('full_duration')
        if duration:
            # Convert milliseconds to readable format
            seconds = duration // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            content_parts.append(f"Duration: {minutes}:{seconds:02d}")
        
        # Play count
        play_count = track.get('playback_count', 0)
        if play_count:
            if play_count > 1000000:
                content_parts.append(f"▶ {play_count/1000000:.1f}M plays")
            elif play_count > 1000:
                content_parts.append(f"▶ {play_count/1000:.0f}K plays")
            else:
                content_parts.append(f"▶ {play_count} plays")
        
        # Likes
        likes = track.get('likes_count', 0) or track.get('favoritings_count', 0)
        if likes:
            if likes > 1000:
                content_parts.append(f"❤️ {likes/1000:.0f}K")
            else:
                content_parts.append(f"❤️ {likes}")
        
        # Reposts
        reposts = track.get('reposts_count', 0)
        if reposts:
            if reposts > 1000:
                content_parts.append(f"🔄 {reposts/1000:.0f}K")
            else:
                content_parts.append(f"🔄 {reposts}")
        
        # Comments
        comments = track.get('comment_count', 0)
        if comments:
            content_parts.append(f"💬 {comments}")
        
        # Genre
        genre = track.get('genre')
        if genre and genre.lower() not in ['none', 'all music', 'other']:
            content_parts.append(f"Genre: {genre}")
        
        # Tags
        tag_list = track.get('tag_list')
        if tag_list:
            # Parse tags (they come as a string)
            tags = [tag.strip() for tag in tag_list.split(' ') if tag.strip()][:3]
            if tags:
                content_parts.append(f"Tags: {', '.join(tags)}")
        
        # License
        license_map = {
            'no-rights-reserved': 'CC0',
            'all-rights-reserved': '©',
            'cc-by': 'CC BY',
            'cc-by-nc': 'CC BY-NC',
            'cc-by-nd': 'CC BY-ND',
            'cc-by-sa': 'CC BY-SA',
            'cc-by-nc-nd': 'CC BY-NC-ND',
            'cc-by-nc-sa': 'CC BY-NC-SA',
        }
        license_type = track.get('license')
        if license_type and license_type in license_map:
            content_parts.append(f"License: {license_map[license_type]}")
        
        # Download info
        if track.get('downloadable'):
            download_count = track.get('download_count', 0)
            if download_count:
                content_parts.append(f"⬇ {download_count} downloads")
            else:
                content_parts.append("⬇ Downloadable")
        
        # Purchase info
        purchase_url = track.get('purchase_url')
        if purchase_url:
            purchase_title = track.get('purchase_title', 'Buy')
            content_parts.append(f"🛒 {purchase_title}")
        
        # Label
        label = track.get('label_name')
        if label:
            content_parts.append(f"Label: {label}")
        
        # Description (truncated)
        description = track.get('description', '')
        if description:
            desc_preview = description[:100]
            if len(description) > 100:
                desc_preview += '...'
            # Clean up newlines
            desc_preview = ' '.join(desc_preview.split())
            content_parts.append(desc_preview)
        
        content = ' | '.join(content_parts)
        
        # Build result
        result = {
            'url': url,
            'title': display_title,
            'content': content,
        }
        
        # Thumbnail
        artwork_url = track.get('artwork_url')
        if artwork_url:
            # Get higher resolution version
            result['thumbnail'] = artwork_url.replace('-large', '-t500x500')
        elif user.get('avatar_url'):
            result['thumbnail'] = user['avatar_url']
        
        # Embedded player
        track_id = track.get('id')
        if track_id:
            # SoundCloud embed URL
            result['iframe_src'] = f"https://w.soundcloud.com/player/?url={quote_plus(url)}&color=%23ff5500&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=true"
        
        # Published date
        created_at = track.get('created_at')
        if created_at:
            try:
                # SoundCloud uses ISO format
                result['publishedDate'] = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                pass
        
        # Waveform URL (for potential visualization)
        waveform_url = track.get('waveform_url')
        if waveform_url:
            result['waveform_url'] = waveform_url
        
        results.append(result)
    
    return results