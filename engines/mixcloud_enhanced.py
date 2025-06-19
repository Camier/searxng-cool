# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mixcloud Enhanced (Music/DJ Mixes)

Enhanced version with additional metadata and filtering options.
"""

from urllib.parse import urlencode, quote
from dateutil import parser
from datetime import timedelta

# about
about = {
    "website": 'https://www.mixcloud.com/',
    "wikidata_id": 'Q6883832',
    "official_api_documentation": 'http://www.mixcloud.com/developers/',
    "use_official_api": True,
    "require_api_key": False,
    "results": 'JSON',
}

# engine dependent config
categories = ['music']
paging = True
time_range_support = True

# search-url
base_url = 'https://api.mixcloud.com/'
search_url = base_url + 'search/?{query}&type={search_type}&limit={limit}&offset={offset}'
iframe_src = "https://www.mixcloud.com/widget/iframe/?feed={url}&hide_cover=1&mini=1&light=1"

# Time range options for filtering
time_range_map = {
    'day': 1,
    'week': 7,
    'month': 30,
    'year': 365,
}

# Search types
search_types = {
    'cloudcast': 'Shows & DJ Sets',
    'user': 'DJs & Creators',
    'tag': 'Genres & Tags',
}


def request(query, params):
    """Build request parameters for enhanced Mixcloud search"""
    
    # Pagination
    limit = 20
    offset = (params.get('pageno', 1) - 1) * limit
    
    # Default search type is cloudcast (audio content)
    search_type = params.get('search_type', 'cloudcast')
    
    # Build query parameters
    query_params = {
        'q': query,
        'type': search_type,
        'limit': limit,
        'offset': offset
    }
    
    # Add time filtering if specified
    # Note: Mixcloud API doesn't support direct date filtering in search,
    # but we'll implement client-side filtering in response()
    
    params['url'] = base_url + f'search/?{urlencode(query_params)}'
    
    # Store time range for filtering in response
    if params.get('time_range'):
        params['mixcloud_time_range'] = params['time_range']
    
    return params


def response(resp):
    """Parse enhanced response from Mixcloud API"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    try:
        search_res = resp.json()
    except ValueError:
        return []
    
    # Get time filter if specified
    time_filter_days = None
    if hasattr(resp, 'search_params') and 'mixcloud_time_range' in resp.search_params:
        time_range = resp.search_params.get('mixcloud_time_range')
        time_filter_days = time_range_map.get(time_range)
    
    for result in search_res.get('data', []):
        # Parse created time
        try:
            created_time = parser.parse(result.get('created_time', ''))
            
            # Apply time filtering if specified
            if time_filter_days:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if (now - created_time).days > time_filter_days:
                    continue
        except:
            created_time = None
        
        # Extract basic information
        r_url = result.get('url', '')
        if not r_url:
            continue
        
        # Build enhanced content
        content_parts = []
        
        # User/DJ information
        user = result.get('user', {})
        username = user.get('name', 'Unknown')
        user_url = user.get('url', '')
        
        # For cloudcasts (audio content)
        if result.get('type') == 'cloudcast':
            # Duration
            audio_length = result.get('audio_length')
            if audio_length:
                duration = str(timedelta(seconds=audio_length))
                content_parts.append(f"Duration: {duration}")
            
            # Play count
            play_count = result.get('play_count', 0)
            if play_count:
                if play_count > 1000000:
                    content_parts.append(f"Plays: {play_count/1000000:.1f}M")
                elif play_count > 1000:
                    content_parts.append(f"Plays: {play_count/1000:.0f}K")
                else:
                    content_parts.append(f"Plays: {play_count}")
            
            # Likes/Favorites
            favorite_count = result.get('favorite_count', 0)
            if favorite_count:
                content_parts.append(f"❤️ {favorite_count}")
            
            # Repost count
            repost_count = result.get('repost_count', 0)
            if repost_count:
                content_parts.append(f"🔄 {repost_count}")
            
            # Comments
            comment_count = result.get('comment_count', 0)
            if comment_count:
                content_parts.append(f"💬 {comment_count}")
            
            # Tags/Genres
            tags = result.get('tags', [])
            if tags:
                tag_names = [tag.get('name', '') for tag in tags[:5] if tag.get('name')]
                if tag_names:
                    content_parts.append(f"Tags: {', '.join(tag_names)}")
            
            # DJ/Creator
            content_parts.insert(0, f"By {username}")
            
            # Title includes mix name
            title = result.get('name', 'Unknown Mix')
            
        # For users (DJs/Creators)
        elif result.get('type') == 'user':
            title = username
            
            # User stats
            follower_count = user.get('follower_count', 0)
            if follower_count:
                if follower_count > 1000000:
                    content_parts.append(f"Followers: {follower_count/1000000:.1f}M")
                elif follower_count > 1000:
                    content_parts.append(f"Followers: {follower_count/1000:.0f}K")
                else:
                    content_parts.append(f"Followers: {follower_count}")
            
            # Cloudcast count
            cloudcast_count = user.get('cloudcast_count', 0)
            if cloudcast_count:
                content_parts.append(f"Mixes: {cloudcast_count}")
            
            # Bio/Description
            biog = user.get('biog', '')
            if biog:
                # Truncate long bios
                if len(biog) > 150:
                    biog = biog[:147] + '...'
                content_parts.append(biog)
        
        # Format content
        content = ' | '.join(content_parts)
        
        # Build result
        res = {
            'url': r_url,
            'title': title,
            'content': content,
        }
        
        # Add iframe for audio content
        if result.get('type') == 'cloudcast':
            res['iframe_src'] = iframe_src.format(url=quote(r_url, safe=''))
        
        # Add thumbnail
        pictures = result.get('pictures', {})
        thumbnail = (pictures.get('large') or 
                    pictures.get('medium') or 
                    pictures.get('small'))
        
        # For users, use their picture
        if result.get('type') == 'user' and user.get('pictures'):
            user_pics = user.get('pictures', {})
            thumbnail = (user_pics.get('large') or 
                        user_pics.get('medium') or 
                        user_pics.get('small'))
        
        if thumbnail:
            res['thumbnail'] = thumbnail
        
        # Add published date
        if created_time:
            res['publishedDate'] = created_time
        
        results.append(res)
    
    return results