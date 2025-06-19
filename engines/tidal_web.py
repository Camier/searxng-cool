# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tidal Web Search

Search Tidal's web interface for high-quality music tracks, albums, and artists.
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
    'website': 'https://tidal.com',
    'wikidata_id': 'Q19711013',
    'official_api_documentation': None,
    'use_official_api': False,
    'require_api_key': False,
    'results': 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = False  # Tidal web interface doesn't easily support pagination

# Base URL
base_url = 'https://listen.tidal.com'
search_url = base_url + '/search?q={query}'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for Tidal web search"""
    
    # Clean query
    clean_query = query
    
    # Encode query
    encoded_query = quote(clean_query)
    
    # Build URL
    params['url'] = search_url.format(query=encoded_query)
    
    # Add headers to avoid bot detection
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
    """Parse response from Tidal web search"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    dom = html.fromstring(resp.text)
    
    # Tidal uses React and loads data dynamically
    # Look for embedded JSON data in script tags
    script_elements = eval_xpath_list(dom, '//script[contains(text(), "__INITIAL_STATE__") or contains(text(), "window.__")]')
    
    for script in script_elements:
        try:
            script_text = script.text_content()
            
            # Look for initial state data
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_text, re.DOTALL)
            if not json_match:
                # Try alternative patterns
                json_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', script_text, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group(1))
                
                # Navigate through the data structure
                # Tidal's structure varies, try multiple paths
                search_results = None
                
                # Try different possible paths
                paths = [
                    ['search', 'results'],
                    ['searchResults'],
                    ['content', 'searchResults'],
                    ['pages', 'search', 'results']
                ]
                
                for path in paths:
                    current = data
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        else:
                            break
                    else:
                        search_results = current
                        break
                
                if search_results:
                    # Parse tracks
                    if 'tracks' in search_results:
                        tracks = search_results['tracks']
                        if isinstance(tracks, dict) and 'items' in tracks:
                            tracks = tracks['items']
                        if isinstance(tracks, list):
                            for track in tracks[:5]:  # Limit results
                                result = parse_track(track)
                                if result:
                                    results.append(result)
                    
                    # Parse albums
                    if 'albums' in search_results:
                        albums = search_results['albums']
                        if isinstance(albums, dict) and 'items' in albums:
                            albums = albums['items']
                        if isinstance(albums, list):
                            for album in albums[:3]:  # Limit results
                                result = parse_album(album)
                                if result:
                                    results.append(result)
                    
                    # Parse artists
                    if 'artists' in search_results:
                        artists = search_results['artists']
                        if isinstance(artists, dict) and 'items' in artists:
                            artists = artists['items']
                        if isinstance(artists, list):
                            for artist in artists[:2]:  # Limit results
                                result = parse_artist(artist)
                                if result:
                                    results.append(result)
                
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    # Fallback: Try basic HTML scraping
    if not results:
        # Look for track elements
        track_selectors = [
            '//div[@data-test="track-item"]',
            '//div[contains(@class, "track-row")]',
            '//a[contains(@href, "/track/")]'
        ]
        
        for selector in track_selectors:
            elements = eval_xpath_list(dom, selector)
            if elements:
                for element in elements[:10]:
                    result = parse_html_track(element)
                    if result:
                        results.append(result)
                break
    
    return results

def parse_track(track_data):
    """Parse track data from Tidal JSON"""
    if not isinstance(track_data, dict):
        return None
    
    # Extract basic info
    title = track_data.get('title', 'Unknown Track')
    track_id = track_data.get('id', '')
    
    # Build URL
    url = f"{base_url}/track/{track_id}" if track_id else base_url
    
    # Get artists
    artists = []
    artist_data = track_data.get('artists', [])
    if isinstance(artist_data, list):
        for artist in artist_data:
            if isinstance(artist, dict):
                artists.append(artist.get('name', 'Unknown Artist'))
    elif 'artist' in track_data and isinstance(track_data['artist'], dict):
        artists.append(track_data['artist'].get('name', 'Unknown Artist'))
    
    # Get album
    album = ''
    album_data = track_data.get('album', {})
    if isinstance(album_data, dict):
        album = album_data.get('title', '')
    
    # Duration (Tidal provides in seconds)
    duration = track_data.get('duration', 0)
    duration_ms = duration * 1000 if duration else None
    
    # Audio quality
    audio_quality = track_data.get('audioQuality', '')
    audio_modes = track_data.get('audioModes', [])
    
    # Cover art
    cover = track_data.get('cover', '')
    if cover and not cover.startswith('http'):
        # Tidal uses image IDs that need to be formatted
        cover = f"https://resources.tidal.com/images/{cover.replace('-', '/')}/320x320.jpg"
    
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'album': album,
        'duration_ms': duration_ms,
        'thumbnail': cover,
        'engine_data': {
            'source': 'tidal',
            'track_id': track_id,
            'audio_quality': audio_quality,
            'audio_modes': audio_modes,
            'lossless': 'LOSSLESS' in audio_quality if audio_quality else False
        }
    })
    
    return result

def parse_album(album_data):
    """Parse album data from Tidal JSON"""
    if not isinstance(album_data, dict):
        return None
    
    title = album_data.get('title', 'Unknown Album')
    album_id = album_data.get('id', '')
    
    # Build URL
    url = f"{base_url}/album/{album_id}" if album_id else base_url
    
    # Get artists
    artists = []
    artist_data = album_data.get('artists', [])
    if isinstance(artist_data, list):
        for artist in artist_data:
            if isinstance(artist, dict):
                artists.append(artist.get('name', 'Unknown Artist'))
    elif 'artist' in album_data and isinstance(album_data['artist'], dict):
        artists.append(album_data['artist'].get('name', 'Unknown Artist'))
    
    # Release date
    release_date = album_data.get('releaseDate', '')
    
    # Track count
    track_count = album_data.get('numberOfTracks', 0)
    
    # Duration
    duration = album_data.get('duration', 0)
    
    # Cover art
    cover = album_data.get('cover', '')
    if cover and not cover.startswith('http'):
        cover = f"https://resources.tidal.com/images/{cover.replace('-', '/')}/320x320.jpg"
    
    # Audio quality
    audio_quality = album_data.get('audioQuality', '')
    
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'album': title,
        'thumbnail': cover,
        'release_date': release_date,
        'engine_data': {
            'source': 'tidal',
            'type': 'album',
            'album_id': album_id,
            'track_count': track_count,
            'duration_seconds': duration,
            'audio_quality': audio_quality
        }
    })
    
    return result

def parse_artist(artist_data):
    """Parse artist data from Tidal JSON"""
    if not isinstance(artist_data, dict):
        return None
    
    name = artist_data.get('name', 'Unknown Artist')
    artist_id = artist_data.get('id', '')
    
    # Build URL
    url = f"{base_url}/artist/{artist_id}" if artist_id else base_url
    
    # Picture
    picture = artist_data.get('picture', '')
    if picture and not picture.startswith('http'):
        picture = f"https://resources.tidal.com/images/{picture.replace('-', '/')}/320x320.jpg"
    
    result = {
        'url': url,
        'title': f"{name} (Artist)",
        'content': "High-fidelity music streaming artist",
        'thumbnail': picture,
        'template': 'music.html',
        'engine_data': {
            'source': 'tidal',
            'type': 'artist',
            'artist_id': artist_id
        }
    }
    
    return result

def parse_html_track(element):
    """Parse track from HTML element"""
    try:
        # Extract link
        link_elem = eval_xpath_getindex(element, './/a[@href and contains(@href, "/track/")]', 0)
        if link_elem is None:
            return None
        
        url = link_elem.get('href', '')
        if not url.startswith('http'):
            url = base_url + url
        
        # Extract title
        title = extract_text(link_elem)
        if not title:
            title_elem = eval_xpath_getindex(element, './/span[@class="track-name"] | .//div[@class="title"]', 0)
            if title_elem is not None:
                title = extract_text(title_elem)
        
        if not title:
            return None
        
        # Try to find artist
        artist = 'Unknown Artist'
        artist_elem = eval_xpath_getindex(element, './/a[contains(@href, "/artist/")] | .//span[@class="artist-name"]', 0)
        if artist_elem is not None:
            artist = extract_text(artist_elem)
        
        # Try to find duration
        duration_elem = eval_xpath_getindex(element, './/span[@class="duration"] | .//time', 0)
        duration_str = extract_text(duration_elem) if duration_elem is not None else None
        
        result = music_base.standardize_result({
            'url': url,
            'title': title,
            'artist': artist,
            'engine_data': {
                'source': 'tidal',
                'scraped': True
            }
        })
        
        if duration_str:
            duration_ms = music_base.parse_duration(duration_str)
            if duration_ms:
                result['duration_ms'] = duration_ms
        
        return result
        
    except Exception:
        return None