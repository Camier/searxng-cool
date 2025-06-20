"""
Last.fm search engine

Search for music tracks, artists, and albums on Last.fm
Requires API key for full functionality
"""

import urllib.parse
from datetime import datetime
from searx.utils import extract_text, eval_xpath

# Engine metadata
about = {
    "website": "https://www.last.fm",
    "wikidata_id": "Q183718",
    "official_api_documentation": "https://www.last.fm/api",
    "use_official_api": True,
    "require_api_key": True,
    "results": "JSON"
}

# Engine configuration
categories = ['music']
paging = True
time_range_support = False

# API configuration
api_key = "5792f7d603168a9ab61972f58d9e7b7e"
base_url = "https://ws.audioscrobbler.com/2.0/"
page_size = 30


def request(query, params):
    """Build API request for Last.fm"""
    
    # Determine search method based on query format
    method = "track.search"
    search_params = {"track": query}
    
    # Check for artist search
    if query.startswith("artist:"):
        method = "artist.search"
        search_params = {"artist": query[7:].strip()}
    # Check for album search
    elif query.startswith("album:"):
        method = "album.search"
        search_params = {"album": query[6:].strip()}
    # Check for tag search
    elif query.startswith("tag:"):
        method = "tag.gettoptracks"
        search_params = {"tag": query[4:].strip()}
    
    # Build API parameters
    api_params = {
        "method": method,
        "api_key": api_key,
        "format": "json",
        "page": params.get('pageno', 1),
        "limit": page_size
    }
    api_params.update(search_params)
    
    params['url'] = f"{base_url}?{urllib.parse.urlencode(api_params)}"
    
    return params


def response(resp):
    """Parse Last.fm API response"""
    results = []
    
    try:
        json_data = resp.json()
        
        # Handle different response formats based on search method
        if "results" in json_data:
            # Track/Artist/Album search response
            results_data = json_data["results"]
            
            # Extract tracks
            if "trackmatches" in results_data:
                tracks = results_data["trackmatches"].get("track", [])
                for track in tracks:
                    result = parse_track(track)
                    if result:
                        results.append(result)
            
            # Extract artists
            elif "artistmatches" in results_data:
                artists = results_data["artistmatches"].get("artist", [])
                for artist in artists:
                    result = parse_artist(artist)
                    if result:
                        results.append(result)
            
            # Extract albums
            elif "albummatches" in results_data:
                albums = results_data["albummatches"].get("album", [])
                for album in albums:
                    result = parse_album(album)
                    if result:
                        results.append(result)
        
        # Handle tag.gettoptracks response
        elif "tracks" in json_data:
            tracks_data = json_data["tracks"]
            if "track" in tracks_data:
                tracks = tracks_data["track"]
                for track in tracks:
                    result = parse_track(track)
                    if result:
                        results.append(result)
    
    except Exception as e:
        # Log error but don't crash
        pass
    
    return results


def parse_track(track_data):
    """Parse track data into result format"""
    try:
        title = track_data.get("name", "")
        artist = track_data.get("artist")
        
        # Handle different artist formats
        if isinstance(artist, dict):
            artist_name = artist.get("name", "Unknown Artist")
        elif isinstance(artist, str):
            artist_name = artist
        else:
            artist_name = "Unknown Artist"
        
        # Build URL
        url = track_data.get("url", "")
        if not url and title and artist_name:
            # Construct URL if not provided
            url_artist = urllib.parse.quote(artist_name.replace(" ", "+"))
            url_track = urllib.parse.quote(title.replace(" ", "+"))
            url = f"https://www.last.fm/music/{url_artist}/_/{url_track}"
        
        # Get additional metadata
        listeners = track_data.get("listeners", "")
        playcount = track_data.get("playcount", "")
        
        # Build content/description
        content_parts = []
        if listeners:
            content_parts.append(f"{int(listeners):,} listeners")
        if playcount:
            content_parts.append(f"{int(playcount):,} plays")
        
        content = " • ".join(content_parts) if content_parts else ""
        
        # Get image
        images = track_data.get("image", [])
        thumbnail = ""
        for img in images:
            if img.get("size") == "large":
                thumbnail = img.get("#text", "")
                break
        
        return {
            "title": f"{artist_name} - {title}",
            "url": url,
            "content": content,
            "thumbnail": thumbnail,
            "metadata": {
                "artist": artist_name,
                "track": title,
                "listeners": listeners,
                "playcount": playcount
            }
        }
    
    except Exception:
        return None


def parse_artist(artist_data):
    """Parse artist data into result format"""
    try:
        name = artist_data.get("name", "")
        url = artist_data.get("url", "")
        
        if not url and name:
            url_name = urllib.parse.quote(name.replace(" ", "+"))
            url = f"https://www.last.fm/music/{url_name}"
        
        listeners = artist_data.get("listeners", "")
        
        content = f"{int(listeners):,} listeners" if listeners else ""
        
        # Get image
        images = artist_data.get("image", [])
        thumbnail = ""
        for img in images:
            if img.get("size") == "large":
                thumbnail = img.get("#text", "")
                break
        
        return {
            "title": name,
            "url": url,
            "content": content,
            "thumbnail": thumbnail,
            "metadata": {
                "type": "artist",
                "listeners": listeners
            }
        }
    
    except Exception:
        return None


def parse_album(album_data):
    """Parse album data into result format"""
    try:
        name = album_data.get("name", "")
        artist = album_data.get("artist", "Unknown Artist")
        url = album_data.get("url", "")
        
        if not url and name and artist:
            url_artist = urllib.parse.quote(artist.replace(" ", "+"))
            url_album = urllib.parse.quote(name.replace(" ", "+"))
            url = f"https://www.last.fm/music/{url_artist}/{url_album}"
        
        # Get image
        images = album_data.get("image", [])
        thumbnail = ""
        for img in images:
            if img.get("size") == "large":
                thumbnail = img.get("#text", "")
                break
        
        return {
            "title": f"{artist} - {name}",
            "url": url,
            "content": "Album",
            "thumbnail": thumbnail,
            "metadata": {
                "type": "album",
                "artist": artist,
                "album": name
            }
        }
    
    except Exception:
        return None