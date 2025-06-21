# SPDX-License-Identifier: AGPL-3.0-or-later
"""Radio Paradise (Music Radio)

Search the Radio Paradise playlist history and song database.
Radio Paradise is a unique blend of many styles and genres of music, carefully selected and mixed by real humans.
"""

import json
from urllib.parse import urlencode
from datetime import datetime, timedelta
from searx.utils import searx_useragent

# About
about = {
    'website': 'https://radioparadise.com',
    'wikidata_id': 'Q7280529',
    'official_api_documentation': 'https://radioparadise.com/developers',
    'use_official_api': True,
    'require_api_key': False,
    'results': 'JSON',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True
time_range_support = False  # Radio Paradise shows recent plays

# API configuration
base_url = 'https://api.radioparadise.com'
nowplaying_url = base_url + '/api/nowplaying'
history_url = base_url + '/api/playlist'
song_info_url = base_url + '/api/song'

# Radio Paradise channels
channels = {
    'main': 0,      # Main Mix
    'mellow': 1,    # Mellow Mix
    'rock': 2,      # Rock Mix
    'world': 3,     # World/Etc Mix
}


def request(query, params):
    """Build request for Radio Paradise search"""
    
    # Radio Paradise doesn't have a traditional search API
    # Instead, we'll search through their playlist history
    
    # For now, we'll get the recent playlist history
    # In a full implementation, we might cache and search through more history
    
    channel = params.get('channel', 'main')
    channel_id = channels.get(channel, 0)
    
    # Get playlist history (last 50 songs)
    params['url'] = f"{history_url}?chan={channel_id}"
    
    # Store the query for filtering in response
    params['rp_query'] = query.lower()
    params['rp_channel'] = channel
    
    # Add proper user agent
    params['headers'] = {
        'User-Agent': searx_useragent(),
        'Accept': 'application/json',
    }
    
    return params


def response(resp):
    """Parse response from Radio Paradise API"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Get the search query
    search_query = resp.search_params.get('rp_query', '').lower()
    channel_name = resp.search_params.get('rp_channel', 'main').title()
    
    # Process playlist data
    # Handle both list and dict responses
    if isinstance(json_data, list):
        songs = json_data
    elif isinstance(json_data, dict):
        songs = json_data.get('songs', json_data.get('items', []))
    else:
        songs = []
    
    for song in songs:
        # Extract basic info
        artist = song.get('artist', '')
        title = song.get('title', '')
        album = song.get('album', '') or ''
        
        # Filter by search query
        if search_query:
            # Search in artist, title, and album
            if not (search_query in artist.lower() or 
                   search_query in title.lower() or 
                   search_query in album.lower()):
                continue
        
        # Skip if no basic info
        if not (artist and title):
            continue
        
        # Build display title
        display_title = f"{artist} - {title}"
        
        # Build content
        content_parts = []
        
        # Album info
        if album:
            content_parts.append(f"Album: {album}")
        
        # Year
        year = song.get('year')
        if year:
            content_parts.append(f"Year: {year}")
        
        # Play time
        play_time = song.get('time')
        if play_time:
            try:
                # Convert timestamp to readable format
                played_at = datetime.fromtimestamp(play_time)
                now = datetime.now()
                time_diff = now - played_at
                
                if time_diff < timedelta(hours=1):
                    minutes = int(time_diff.total_seconds() / 60)
                    content_parts.append(f"Played {minutes} minutes ago")
                elif time_diff < timedelta(days=1):
                    hours = int(time_diff.total_seconds() / 3600)
                    content_parts.append(f"Played {hours} hour{'s' if hours > 1 else ''} ago")
                else:
                    content_parts.append(f"Played on {played_at.strftime('%Y-%m-%d %H:%M')}")
            except:
                pass
        
        # Duration
        duration = song.get('duration')
        if duration:
            minutes = duration // 60
            seconds = duration % 60
            content_parts.append(f"Duration: {minutes}:{seconds:02d}")
        
        # Rating
        rating = song.get('rating')
        if rating:
            # Convert to stars (rating is usually 1-10)
            stars = int(rating / 2)
            content_parts.append(f"Rating: {'★' * stars}{'☆' * (5 - stars)}")
        
        # Channel
        content_parts.append(f"Channel: Radio Paradise {channel_name}")
        
        # Song ID for potential future features
        song_id = song.get('song_id')
        if song_id:
            content_parts.append(f"ID: {song_id}")
        
        # Tags/Genre
        genre = song.get('genre')
        if genre:
            content_parts.append(f"Genre: {genre}")
        
        content = ' | '.join(content_parts)
        
        # Build URL - Radio Paradise doesn't have individual song pages
        # We'll link to their main site with a search
        url = f"https://radioparadise.com/search?q={artist}+{title}"
        
        # Create result
        result = {
            'url': url,
            'title': display_title,
            'content': content,
        }
        
        # Cover art
        cover = song.get('cover')
        if cover:
            # Radio Paradise provides different sizes
            # Use medium size for thumbnail
            if not cover.startswith('http'):
                cover = f"https://img.radioparadise.com/{cover}"
            result['thumbnail'] = cover.replace('s.jpg', 'm.jpg')
        
        # Audio sample URL if available
        sample_url = song.get('sample_url')
        if sample_url:
            result['audio_url'] = sample_url
        
        # Add metadata for potential player integration
        result['metadata'] = {
            'artist': artist,
            'title': title,
            'album': album,
            'year': year,
            'song_id': song_id,
        }
        
        results.append(result)
    
    # If no results found, add a message
    if not results and search_query:
        # Provide helpful message
        result = {
            'url': 'https://radioparadise.com',
            'title': f'No results for "{search_query}" in recent Radio Paradise playlist',
            'content': f'Try searching without filters or check the Radio Paradise {channel_name} channel directly. Radio Paradise is a curated, eclectic mix of music from many genres and time periods.',
        }
        results.append(result)
    
    return results