"""
MusicBrainz Music Search Engine

MusicBrainz is an open music encyclopedia that collects music metadata
and makes it available to the public. This engine searches for recordings,
artists, and releases.

No API key required, but rate limiting is enforced (1 request per second).
"""

from json import loads
from urllib.parse import quote_plus
from datetime import datetime
import re

# Engine metadata
about = {
    "website": "https://musicbrainz.org",
    "wikidata_id": "Q14005",
    "official_api_documentation": "https://musicbrainz.org/doc/MusicBrainz_API",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON"
}

# Engine configuration
categories = ['music']
paging = True
page_size = 20

# Base URL for the API
base_url = "https://musicbrainz.org/ws/2"
web_url = "https://musicbrainz.org"

# Rate limiting: 1 request per second
time_range_support = False
language_support = False


def request(query, params):
    """Build request parameters for MusicBrainz API"""
    
    # Calculate offset from page number
    offset = (params['pageno'] - 1) * page_size
    
    # Build query - search recordings by default
    # Advanced users can search specific entities with prefixes like "artist:" or "release:"
    search_type = 'recording'  # Default search type
    search_query = query
    
    # Check for specific search types
    if query.startswith('artist:'):
        search_type = 'artist'
        search_query = query[7:].strip()
    elif query.startswith('album:') or query.startswith('release:'):
        search_type = 'release'
        search_query = query.split(':', 1)[1].strip()
    
    # Build API URL
    params['url'] = f"{base_url}/{search_type}/?query={quote_plus(search_query)}&fmt=json&limit={page_size}&offset={offset}"
    
    # MusicBrainz requires a proper User-Agent
    params['headers'] = {
        'User-Agent': 'SearXNG/1.0 (https://github.com/searxng/searxng)',
        'Accept': 'application/json'
    }
    
    return params


def parse_duration(milliseconds):
    """Convert milliseconds to human-readable duration"""
    if not milliseconds:
        return None
    
    seconds = int(milliseconds) // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    
    if minutes > 0:
        return f"{minutes}:{seconds:02d}"
    return f"0:{seconds:02d}"


def parse_artist_credit(artist_credit):
    """Parse MusicBrainz artist credit format"""
    if not artist_credit:
        return "Unknown Artist", []
    
    artists = []
    artist_string = ""
    
    for credit in artist_credit:
        if 'artist' in credit:
            artists.append(credit['artist']['name'])
            artist_string += credit['artist']['name']
        
        # Add join phrase (like " feat. " or " & ")
        if 'joinphrase' in credit and credit['joinphrase']:
            artist_string += credit['joinphrase']
    
    return artist_string.strip(), artists


def response(resp):
    """Parse MusicBrainz API response"""
    results = []
    
    try:
        data = loads(resp.text)
    except:
        return []
    
    # Handle different entity types
    if 'recordings' in data:
        results = parse_recordings(data['recordings'])
    elif 'artists' in data:
        results = parse_artists(data['artists'])
    elif 'releases' in data:
        results = parse_releases(data['releases'])
    
    return results


def parse_recordings(recordings):
    """Parse recording search results"""
    results = []
    
    for recording in recordings:
        # Parse artist information
        artist_string, artist_list = parse_artist_credit(recording.get('artist-credit', []))
        
        # Get first release info if available
        release_info = ""
        album = None
        date = None
        
        if 'releases' in recording and recording['releases']:
            first_release = recording['releases'][0]
            album = first_release.get('title', '')
            
            if 'date' in first_release:
                date = first_release['date']
                release_info = f" • {album} ({date[:4]})" if len(date) >= 4 else f" • {album}"
            else:
                release_info = f" • {album}" if album else ""
        
        # Build content description
        content_parts = []
        
        # Add duration
        duration = parse_duration(recording.get('length'))
        if duration:
            content_parts.append(f"Duration: {duration}")
        
        # Add primary artist
        content_parts.append(f"Artist: {artist_string}")
        
        # Add album info
        if album:
            content_parts.append(f"Album: {album}")
        
        # Add release date
        if date:
            content_parts.append(f"Released: {date}")
        
        # Create result
        result = {
            'url': f"{web_url}/recording/{recording['id']}",
            'title': recording.get('title', 'Unknown Title'),
            'content': ' • '.join(content_parts),
            'template': 'default.html',
            'metadata': {
                'mbid': recording['id'],
                'artist': artist_string,
                'artists': artist_list,
                'album': album,
                'duration_ms': recording.get('length'),
                'release_date': date
            }
        }
        
        # Add disambiguation if present
        if 'disambiguation' in recording and recording['disambiguation']:
            result['content'] += f" • {recording['disambiguation']}"
        
        results.append(result)
    
    return results


def parse_artists(artists):
    """Parse artist search results"""
    results = []
    
    for artist in artists:
        content_parts = []
        
        # Add type
        if 'type' in artist:
            content_parts.append(f"Type: {artist['type']}")
        
        # Add area (country/location)
        if 'area' in artist and artist['area']:
            content_parts.append(f"Area: {artist['area']['name']}")
        
        # Add life span
        if 'life-span' in artist:
            life_span = artist['life-span']
            if 'begin' in life_span:
                if 'ended' in life_span and life_span['ended']:
                    content_parts.append(f"Active: {life_span.get('begin', '?')} - {life_span.get('end', '?')}")
                else:
                    content_parts.append(f"Active since: {life_span.get('begin', '?')}")
        
        # Add tags if present
        if 'tags' in artist and artist['tags']:
            tags = [tag['name'] for tag in artist['tags'][:5]]  # Limit to 5 tags
            content_parts.append(f"Tags: {', '.join(tags)}")
        
        result = {
            'url': f"{web_url}/artist/{artist['id']}",
            'title': artist.get('name', 'Unknown Artist'),
            'content': ' • '.join(content_parts) if content_parts else artist.get('disambiguation', ''),
            'template': 'default.html',
            'metadata': {
                'mbid': artist['id'],
                'type': artist.get('type'),
                'country': artist.get('country')
            }
        }
        
        results.append(result)
    
    return results


def parse_releases(releases):
    """Parse release (album) search results"""
    results = []
    
    for release in releases:
        # Parse artist information
        artist_string, artist_list = parse_artist_credit(release.get('artist-credit', []))
        
        content_parts = []
        
        # Add artist
        content_parts.append(f"Artist: {artist_string}")
        
        # Add release date
        if 'date' in release:
            content_parts.append(f"Released: {release['date']}")
        
        # Add format
        if 'media' in release and release['media']:
            formats = []
            for medium in release['media']:
                format_str = medium.get('format', 'Unknown')
                if 'track-count' in medium:
                    format_str += f" ({medium['track-count']} tracks)"
                formats.append(format_str)
            content_parts.append(f"Format: {', '.join(formats)}")
        
        # Add label
        if 'label-info' in release and release['label-info']:
            labels = []
            for label_info in release['label-info']:
                if 'label' in label_info and label_info['label']:
                    labels.append(label_info['label']['name'])
            if labels:
                content_parts.append(f"Label: {', '.join(labels)}")
        
        # Add country
        if 'country' in release:
            content_parts.append(f"Country: {release['country']}")
        
        result = {
            'url': f"{web_url}/release/{release['id']}",
            'title': release.get('title', 'Unknown Release'),
            'content': ' • '.join(content_parts),
            'template': 'default.html',
            'metadata': {
                'mbid': release['id'],
                'artist': artist_string,
                'artists': artist_list,
                'date': release.get('date'),
                'country': release.get('country')
            }
        }
        
        results.append(result)
    
    return results


# Unit test
if __name__ == '__main__':
    # Test recording search
    test_params = {'pageno': 1}
    params = request('Bohemian Rhapsody Queen', test_params)
    print(f"URL: {params['url']}")
    
    # Test artist search
    params = request('artist:Radiohead', test_params)
    print(f"Artist URL: {params['url']}")
    
    # Test album search
    params = request('album:OK Computer', test_params)
    print(f"Album URL: {params['url']}")