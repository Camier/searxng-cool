# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spotify Web Search

Search Spotify's web interface for tracks, albums, and artists.
This engine scrapes the public web search without using the API.
"""

from urllib.parse import quote, urlencode
import json
import re
from lxml import html
from searx.utils import extract_text, eval_xpath_list, eval_xpath_getindex
from searx.engines.base_music import MusicEngineBase

# About
about = {
    'website': 'https://open.spotify.com',
    'wikidata_id': 'Q689141',
    'official_api_documentation': None,
    'use_official_api': False,
    'require_api_key': False,
    'results': 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True

# Base URL
base_url = 'https://open.spotify.com'
search_url = base_url + '/search/{query}/{search_type}'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for Spotify web search"""
    
    # Determine search type based on query
    search_type = 'tracks'  # Default to tracks
    clean_query = query
    
    if query.startswith('artist:'):
        search_type = 'artists'
        clean_query = query[7:].strip()
    elif query.startswith('album:'):
        search_type = 'albums'
        clean_query = query[6:].strip()
    elif query.startswith('playlist:'):
        search_type = 'playlists'
        clean_query = query[9:].strip()
    
    # Encode query
    encoded_query = quote(clean_query)
    
    # Build URL
    params['url'] = search_url.format(query=encoded_query, search_type=search_type)
    
    # Add headers to avoid bot detection
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    return params

def response(resp):
    """Parse response from Spotify web search"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    # Spotify loads content dynamically, but initial data is in a script tag
    # Look for the Spotify data in the page
    dom = html.fromstring(resp.text)
    
    # Find the script tag containing initial data
    script_elements = eval_xpath_list(dom, '//script[@id="initial-state"]')
    
    if not script_elements:
        # Try alternative method - look for data in other script tags
        script_elements = eval_xpath_list(dom, '//script[contains(text(), "Spotify.Entity")]')
    
    if script_elements:
        try:
            script_content = script_elements[0].text_content()
            
            # Extract JSON data from script
            # Look for patterns like window.Spotify = {...} or similar
            json_match = re.search(r'window\.Spotify\s*=\s*({.*?});', script_content, re.DOTALL)
            if not json_match:
                # Try alternative pattern
                json_match = re.search(r'{"entities":{.*?}}\s*;', script_content, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group(1))
                
                # Parse tracks
                if 'tracks' in data.get('entities', {}):
                    for track_id, track in data['entities']['tracks'].items():
                        results.append(parse_track(track))
                
                # Parse artists
                if 'artists' in data.get('entities', {}):
                    for artist_id, artist in data['entities']['artists'].items():
                        results.append(parse_artist(artist))
                
                # Parse albums
                if 'albums' in data.get('entities', {}):
                    for album_id, album in data['entities']['albums'].items():
                        results.append(parse_album(album))
        except (json.JSONDecodeError, AttributeError, KeyError):
            pass
    
    # Fallback: Try to scrape visible content
    if not results:
        # Look for track/album/artist cards in the HTML
        track_elements = eval_xpath_list(dom, '//div[@data-testid="track-entity-link"]//ancestor::div[@role="row"]')
        
        for element in track_elements[:10]:  # Limit to 10 results
            try:
                # Extract track info
                title_elem = eval_xpath_getindex(element, './/a[@data-testid="track-entity-link"]', 0)
                artist_elem = eval_xpath_getindex(element, './/a[@data-testid="artist-entity-link"]', 0)
                
                if title_elem is not None:
                    title = extract_text(title_elem)
                    url = title_elem.get('href', '')
                    if not url.startswith('http'):
                        url = base_url + url
                    
                    artist = extract_text(artist_elem) if artist_elem is not None else 'Unknown Artist'
                    
                    # Try to get duration
                    duration_elem = eval_xpath_getindex(element, './/div[contains(@class, "duration")]', 0)
                    duration_str = extract_text(duration_elem) if duration_elem is not None else None
                    
                    result = music_base.standardize_result({
                        'url': url,
                        'title': title,
                        'artist': artist,
                        'engine_data': {
                            'source': 'spotify',
                            'scraped': True
                        }
                    })
                    
                    if duration_str:
                        duration_ms = music_base.parse_duration(duration_str)
                        if duration_ms:
                            result['duration_ms'] = duration_ms
                    
                    results.append(result)
            except Exception:
                continue
    
    return results

def parse_track(track_data):
    """Parse track data from Spotify JSON"""
    # Extract track info
    title = track_data.get('name', 'Unknown Track')
    uri = track_data.get('uri', '')
    track_id = uri.split(':')[-1] if uri else ''
    
    # Build URL
    url = f"{base_url}/track/{track_id}" if track_id else base_url
    
    # Get artists
    artists = []
    if 'artists' in track_data:
        for artist in track_data['artists']:
            artists.append(artist.get('name', 'Unknown Artist'))
    
    # Get album info
    album = track_data.get('album', {}).get('name', '')
    album_image = ''
    if 'album' in track_data and 'images' in track_data['album']:
        images = track_data['album']['images']
        if images:
            album_image = images[0].get('url', '')
    
    # Duration
    duration_ms = track_data.get('duration_ms', 0)
    
    # Popularity (0-100)
    popularity = track_data.get('popularity', 0)
    
    # Create result
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'album': album,
        'duration_ms': duration_ms,
        'thumbnail': album_image,
        'engine_data': {
            'source': 'spotify',
            'popularity': popularity,
            'uri': uri,
            'track_id': track_id
        }
    })
    
    # Add preview URL if available
    if 'preview_url' in track_data and track_data['preview_url']:
        result['preview_url'] = track_data['preview_url']
    
    return result

def parse_artist(artist_data):
    """Parse artist data from Spotify JSON"""
    name = artist_data.get('name', 'Unknown Artist')
    uri = artist_data.get('uri', '')
    artist_id = uri.split(':')[-1] if uri else ''
    
    # Build URL
    url = f"{base_url}/artist/{artist_id}" if artist_id else base_url
    
    # Get image
    image = ''
    if 'images' in artist_data and artist_data['images']:
        image = artist_data['images'][0].get('url', '')
    
    # Followers
    followers = artist_data.get('followers', {}).get('total', 0)
    
    # Genres
    genres = artist_data.get('genres', [])
    
    # Create result
    result = {
        'url': url,
        'title': f"{name} (Artist)",
        'content': f"Followers: {followers:,}" + (f" | Genres: {', '.join(genres[:3])}" if genres else ""),
        'thumbnail': image,
        'template': 'music.html',
        'engine_data': {
            'source': 'spotify',
            'type': 'artist',
            'followers': followers,
            'genres': genres,
            'uri': uri,
            'artist_id': artist_id
        }
    }
    
    return result

def parse_album(album_data):
    """Parse album data from Spotify JSON"""
    name = album_data.get('name', 'Unknown Album')
    uri = album_data.get('uri', '')
    album_id = uri.split(':')[-1] if uri else ''
    
    # Build URL
    url = f"{base_url}/album/{album_id}" if album_id else base_url
    
    # Get artists
    artists = []
    if 'artists' in album_data:
        for artist in album_data['artists']:
            artists.append(artist.get('name', 'Unknown Artist'))
    
    # Get image
    image = ''
    if 'images' in album_data and album_data['images']:
        image = album_data['images'][0].get('url', '')
    
    # Release date
    release_date = album_data.get('release_date', '')
    
    # Total tracks
    total_tracks = album_data.get('total_tracks', 0)
    
    # Create result
    result = music_base.standardize_result({
        'url': url,
        'title': name,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'album': name,
        'thumbnail': image,
        'release_date': release_date,
        'engine_data': {
            'source': 'spotify',
            'type': 'album',
            'total_tracks': total_tracks,
            'uri': uri,
            'album_id': album_id
        }
    })
    
    return result