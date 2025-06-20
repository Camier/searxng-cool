"""
Beatport music search engine

Electronic music store with BPM, key, and genre information
Web scraping approach
"""

from lxml import html
from searx.utils import extract_text, eval_xpath_list
from searx import logger
from searx.engines.base_music import MusicEngineBase
import re

logger = logger.getChild('beatport')

# Engine metadata
about = {
    "website": "https://www.beatport.com",
    "wikidata_id": "Q4877354",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML"
}

# Engine configuration
categories = ['music']
paging = True
time_range_support = False

# Base configuration
base_url = "https://www.beatport.com"
search_url = base_url + "/search?q={query}&page={page}"

# Create engine instance
engine = MusicEngineBase()


def request(query, params):
    """Build search request for Beatport"""
    
    # Page number
    page = params.get('pageno', 1)
    
    # Encode query and build URL
    import urllib.parse
    query_encoded = urllib.parse.quote_plus(query)
    params['url'] = search_url.format(query=query_encoded, page=page)
    
    # Add headers to avoid bot detection
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    return params


def response(resp):
    """Parse Beatport response"""
    results = []
    
    try:
        # Parse HTML
        dom = html.fromstring(resp.text)
        
        # Find track containers - adjust selector based on actual HTML structure
        track_selector = '//div[contains(@class, "track-") or contains(@class, "TrackItem") or contains(@data-track-id, "")]'
        track_elements = eval_xpath_list(dom, track_selector)
        
        logger.debug(f"Found {len(track_elements)} potential tracks on Beatport")
        
        # If no tracks found with first selector, try alternatives
        if not track_elements:
            # Try alternative selectors
            track_selector = '//li[contains(@class, "track")]|//div[contains(@class, "result")]|//article[contains(@class, "track")]'
            track_elements = eval_xpath_list(dom, track_selector)
            logger.debug(f"Alternative selector found {len(track_elements)} tracks")
        
        for track in track_elements:
            try:
                # Extract track information with multiple possible selectors
                title_elem = eval_xpath_list(track, './/a[contains(@class, "track-title")]|.//span[contains(@class, "title")]|.//h3/a')
                artist_elem = eval_xpath_list(track, './/a[contains(@class, "artist")]|.//span[contains(@class, "artist")]|.//p[contains(@class, "artist")]/a')
                
                if not title_elem:
                    continue
                
                # Basic info
                title = extract_text(title_elem[0])
                url = title_elem[0].get('href', '')
                if url and not url.startswith('http'):
                    url = base_url + url
                
                # Artist
                artist = ""
                if artist_elem:
                    artist_parts = []
                    for elem in artist_elem:
                        text = extract_text(elem)
                        if text:
                            artist_parts.append(text)
                    artist = ", ".join(artist_parts)
                
                if not artist:
                    artist = "Unknown Artist"
                
                # BPM
                bpm = ""
                bpm_elem = eval_xpath_list(track, './/*[contains(text(), "BPM") or contains(@class, "bpm")]/text()')
                if bpm_elem:
                    for text in bpm_elem:
                        bpm_match = re.search(r'(\d+)\s*BPM', text)
                        if bpm_match:
                            bpm = bpm_match.group(1)
                            break
                
                # Key
                key = ""
                key_elem = eval_xpath_list(track, './/*[contains(@class, "key") or contains(text(), "Key:")]/text()')
                if key_elem:
                    for text in key_elem:
                        # Look for key patterns like "Am", "C#", "Fmaj"
                        key_match = re.search(r'([A-G][#b]?(?:m|maj|min)?)', text)
                        if key_match:
                            key = key_match.group(1)
                            break
                
                # Genre
                genre = ""
                genre_elem = eval_xpath_list(track, './/a[contains(@class, "genre")]|.//span[contains(@class, "genre")]')
                if genre_elem:
                    genre = extract_text(genre_elem[0])
                
                # Label
                label = ""
                label_elem = eval_xpath_list(track, './/a[contains(@class, "label")]|.//span[contains(@class, "label")]')
                if label_elem:
                    label = extract_text(label_elem[0])
                
                # Price
                price = ""
                price_elem = eval_xpath_list(track, './/*[contains(@class, "price")]/text()|.//*[contains(text(), "€")]')
                if price_elem:
                    for text in price_elem:
                        price_match = re.search(r'[€$£]?\s*(\d+[.,]\d{2})', text)
                        if price_match:
                            price = price_match.group(0)
                            break
                
                # Build content
                content_parts = []
                if bpm:
                    content_parts.append(f"{bpm} BPM")
                if key:
                    content_parts.append(f"Key: {key}")
                if genre:
                    content_parts.append(genre)
                if label:
                    content_parts.append(label)
                if price:
                    content_parts.append(price)
                
                content = " • ".join(content_parts)
                
                # Build result
                result = {
                    "title": f"{artist} - {title}",
                    "url": url,
                    "content": content,
                    "metadata": {
                        "artist": artist,
                        "track": title,
                        "bpm": bpm,
                        "key": key,
                        "genre": genre,
                        "label": label,
                        "price": price
                    }
                }
                
                results.append(result)
                
            except Exception as e:
                logger.debug(f"Error processing Beatport track: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error parsing Beatport response: {e}")
    
    logger.info(f"Beatport returned {len(results)} results")
    return results