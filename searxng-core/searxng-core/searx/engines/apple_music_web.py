# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apple Music Web Search

Search Apple Music's web interface for tracks, albums, and artists.
This engine scrapes the public web search without using the API.
"""

from urllib.parse import quote
import json
import re
from lxml import html
from searx.utils import extract_text, eval_xpath_list, eval_xpath_getindex
from searx.engines.base_music import MusicEngineBase

# About
about = {
    'website': 'https://music.apple.com',
    'wikidata_id': 'Q20056642',
    'official_api_documentation': None,
    'use_official_api': False,
    'require_api_key': False,
    'results': 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = False  # Apple Music web search doesn't support pagination easily

# Allow redirects for regional domains
max_redirects = 2

# Base URL
base_url = 'https://music.apple.com'
search_url = base_url + '/search?term={query}'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for Apple Music web search"""
    
    # Clean query for special searches
    clean_query = query
    if query.startswith(('artist:', 'album:', 'song:')):
        prefix, clean_query = query.split(':', 1)
        clean_query = clean_query.strip()
    
    # Encode query
    encoded_query = quote(clean_query)
    
    # Build URL
    params['url'] = search_url.format(query=encoded_query)
    
    # Add headers to avoid bot detection
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
    }
    
    return params

def response(resp):
    """Parse response from Apple Music web search"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    dom = html.fromstring(resp.text)
    
    # Apple Music loads content dynamically, but includes initial data
    # Look for the schema.org JSON-LD data
    script_elements = eval_xpath_list(dom, '//script[@type="application/ld+json"]')
    
    for script in script_elements:
        try:
            data = json.loads(script.text_content())
            
            # Check if it's a search results schema
            if isinstance(data, dict) and data.get('@type') == 'SearchResultsPage':
                # Parse the main entity
                if 'mainEntity' in data:
                    items = data['mainEntity'].get('itemListElement', [])
                    for item in items:
                        if 'item' in item:
                            results.append(parse_schema_item(item['item']))
            
            # Also check for MusicRecording, MusicAlbum, or MusicGroup types
            elif isinstance(data, dict) and data.get('@type') in ['MusicRecording', 'MusicAlbum', 'MusicGroup']:
                results.append(parse_schema_item(data))
            
            # Check for arrays of items
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') in ['MusicRecording', 'MusicAlbum', 'MusicGroup']:
                        results.append(parse_schema_item(item))
                        
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    # Fallback: Try to scrape visible content
    if not results:
        # Look for search result items
        # Apple Music uses various class names, try multiple selectors
        selectors = [
            '//div[contains(@class, "search-result-item")]',
            '//div[contains(@class, "track-lockup")]',
            '//div[contains(@class, "song-lockup")]',
            '//a[contains(@class, "link-list__item")]'
        ]
        
        for selector in selectors:
            elements = eval_xpath_list(dom, selector)
            if elements:
                for element in elements[:10]:  # Limit results
                    result = parse_html_element(element)
                    if result:
                        results.append(result)
                break
    
    return results

def parse_schema_item(item):
    """Parse schema.org structured data item"""
    item_type = item.get('@type', '')
    
    if item_type == 'MusicRecording':
        return parse_track_schema(item)
    elif item_type == 'MusicAlbum':
        return parse_album_schema(item)
    elif item_type == 'MusicGroup' or item_type == 'Person':
        return parse_artist_schema(item)
    
    return None

def parse_track_schema(track):
    """Parse track from schema.org data"""
    title = track.get('name', 'Unknown Track')
    url = track.get('url', base_url)
    
    # Get artist info
    artists = []
    by_artist = track.get('byArtist', {})
    if isinstance(by_artist, dict):
        artists.append(by_artist.get('name', 'Unknown Artist'))
    elif isinstance(by_artist, list):
        for artist in by_artist:
            if isinstance(artist, dict):
                artists.append(artist.get('name', 'Unknown Artist'))
    
    # Get album info
    album = ''
    album_data = track.get('inAlbum', {})
    if isinstance(album_data, dict):
        album = album_data.get('name', '')
    
    # Duration
    duration_str = track.get('duration', '')
    duration_ms = None
    if duration_str:
        # ISO 8601 duration format: PT3M45S
        duration_ms = parse_iso_duration(duration_str)
    
    # Image
    image = ''
    if 'image' in track:
        if isinstance(track['image'], str):
            image = track['image']
        elif isinstance(track['image'], dict):
            image = track['image'].get('url', '')
    
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'album': album,
        'duration_ms': duration_ms,
        'thumbnail': image,
        'engine_data': {
            'source': 'apple_music',
            'type': 'track'
        }
    })
    
    return result

def parse_album_schema(album):
    """Parse album from schema.org data"""
    name = album.get('name', 'Unknown Album')
    url = album.get('url', base_url)
    
    # Get artist info
    artists = []
    by_artist = album.get('byArtist', {})
    if isinstance(by_artist, dict):
        artists.append(by_artist.get('name', 'Unknown Artist'))
    elif isinstance(by_artist, list):
        for artist in by_artist:
            if isinstance(artist, dict):
                artists.append(artist.get('name', 'Unknown Artist'))
    
    # Release date
    release_date = album.get('datePublished', '')
    
    # Track count
    track_count = album.get('numTracks', 0)
    
    # Image
    image = ''
    if 'image' in album:
        if isinstance(album['image'], str):
            image = album['image']
        elif isinstance(album['image'], dict):
            image = album['image'].get('url', '')
    
    result = music_base.standardize_result({
        'url': url,
        'title': name,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'album': name,
        'thumbnail': image,
        'release_date': release_date,
        'engine_data': {
            'source': 'apple_music',
            'type': 'album',
            'track_count': track_count
        }
    })
    
    return result

def parse_artist_schema(artist):
    """Parse artist from schema.org data"""
    name = artist.get('name', 'Unknown Artist')
    url = artist.get('url', base_url)
    
    # Genre
    genres = []
    genre_data = artist.get('genre', [])
    if isinstance(genre_data, str):
        genres = [genre_data]
    elif isinstance(genre_data, list):
        genres = genre_data
    
    # Image
    image = ''
    if 'image' in artist:
        if isinstance(artist['image'], str):
            image = artist['image']
        elif isinstance(artist['image'], dict):
            image = artist['image'].get('url', '')
    
    result = music_base.standardize_result({
        'url': url,
        'title': f"{name} (Artist)",
        'thumbnail': image,
        'engine_data': {
            'source': 'apple_music',
            'type': 'artist',
            'genres': genres
        }
    })
    
    # Add content after standardization
    result['content'] = f"Genres: {', '.join(genres)}" if genres else "Music Artist"
    
    return result

def parse_html_element(element):
    """Parse search result from HTML element"""
    try:
        # Try to find link
        link_elem = eval_xpath_getindex(element, './/a[@href]', 0)
        if link_elem is None:
            return None
        
        url = link_elem.get('href', '')
        if not url.startswith('http'):
            url = base_url + url
        
        # Extract text content
        title = extract_text(link_elem)
        if not title:
            return None
        
        # Try to determine type from URL or content
        result_type = 'track'
        if '/album/' in url:
            result_type = 'album'
        elif '/artist/' in url:
            result_type = 'artist'
        
        # Get additional metadata from nearby elements
        parent = element.getparent()
        content = ''
        
        # Look for artist info
        artist_elem = eval_xpath_getindex(parent, './/a[contains(@href, "/artist/")]', 0)
        if artist_elem is not None:
            artist = extract_text(artist_elem)
            content = f"by {artist}"
        
        result = music_base.standardize_result({
            'url': url,
            'title': title,
            'engine_data': {
                'source': 'apple_music',
                'type': result_type,
                'scraped': True
            }
        })
        
        # Add content after standardization
        result['content'] = content
        
        return result
        
    except Exception:
        return None

def parse_iso_duration(duration):
    """Parse ISO 8601 duration to milliseconds"""
    # Format: PT3M45S (3 minutes 45 seconds)
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return (hours * 3600 + minutes * 60 + seconds) * 1000
    return None