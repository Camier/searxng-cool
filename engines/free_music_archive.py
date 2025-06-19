"""
Free Music Archive search engine

Search for Creative Commons licensed music
No API key required
"""

import json
import urllib.parse
from lxml import html
from searx.utils import extract_text, eval_xpath_list
from searx import logger

logger = logger.getChild('free_music_archive')

# Engine metadata
about = {
    "website": "https://freemusicarchive.org",
    "wikidata_id": "Q5499899",
    "official_api_documentation": None,  # API no longer available
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML"
}

# Engine configuration
categories = ['music']
paging = True
time_range_support = False

# Search configuration
base_url = "https://freemusicarchive.org"
search_url = base_url + "/search?quicksearch={query}&page={page}"


def request(query, params):
    """Build search request for Free Music Archive"""
    
    # Page number
    page = params.get('pageno', 1)
    
    # Encode query
    query_encoded = urllib.parse.quote_plus(query)
    
    params['url'] = search_url.format(query=query_encoded, page=page)
    
    return params


def response(resp):
    """Parse Free Music Archive response"""
    results = []
    
    try:
        # Parse HTML response
        dom = html.fromstring(resp.text)
        
        # Extract track elements with data-track-info JSON
        track_selector = '//div[contains(@class, "play-item")][@data-track-info]'
        track_elements = eval_xpath_list(dom, track_selector)
        
        logger.debug(f"Found {len(track_elements)} tracks on FMA")
        
        for track in track_elements:
            try:
                # Get the JSON data from data-track-info attribute
                track_info_json = track.get('data-track-info')
                if not track_info_json:
                    continue
                
                # Parse JSON data
                track_info = json.loads(track_info_json)
                
                # Extract data from JSON
                title = track_info.get('title', '')
                artist = track_info.get('artistName', 'Unknown Artist')
                url = track_info.get('url', '')
                preview_url = track_info.get('playbackUrl', '')
                download_url = track_info.get('downloadUrl', '')
                
                if not title or not url:
                    continue
                
                # Try to get additional metadata from HTML
                album = ""
                duration = ""
                genres = []
                
                # Look for album info
                album_elem = eval_xpath_list(track, './/span[@class="ptxt-album"]/a')
                if album_elem:
                    album = extract_text(album_elem[0])
                
                # Look for duration
                duration_elem = eval_xpath_list(track, './/span[contains(@class, "duration")]')
                if duration_elem:
                    duration = extract_text(duration_elem[0])
                
                # Look for genres
                genre_elems = eval_xpath_list(track, './/a[contains(@class, "genre")]')
                for genre_elem in genre_elems:
                    genre = extract_text(genre_elem)
                    if genre:
                        genres.append(genre)
                
                # Build content
                content_parts = []
                if album:
                    content_parts.append(f"Album: {album}")
                if genres:
                    content_parts.append(f"Genres: {', '.join(genres)}")
                if duration:
                    content_parts.append(duration)
                content_parts.append("Free/CC License")
                
                content = " • ".join(content_parts)
                
                result = {
                    "title": f"{artist} - {title}",
                    "url": url,
                    "content": content,
                    "metadata": {
                        "artist": artist,
                        "track": title,
                        "album": album,
                        "genres": genres,
                        "duration": duration,
                        "license": "Creative Commons",
                        "download_url": download_url,
                        "preview_url": preview_url
                    }
                }
                
                # Add download link if available
                if download_url:
                    result["download_url"] = download_url
                
                results.append(result)
                
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse track JSON: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error processing track: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error parsing FMA response: {e}")
    
    logger.info(f"FMA returned {len(results)} results")
    return results