# SPDX-License-Identifier: AGPL-3.0-or-later
"""MusicToScrape - Practice Music Scraping Site

A safe environment for testing music scraping techniques.
This site is specifically designed for web scraping practice.
"""

from urllib.parse import quote, urlencode
from lxml import html
from searx.utils import extract_text, eval_xpath_list, eval_xpath_getindex
from searx.engines.base_music import MusicEngineBase
import re

# About
about = {
    'website': 'https://music-to-scrape.org',
    'wikidata_id': None,
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
base_url = 'https://music-to-scrape.org'
search_url = base_url + '/search'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for MusicToScrape search"""
    
    # Build search parameters
    args = {
        'q': query,
        'page': params.get('pageno', 1)
    }
    
    params['url'] = f"{search_url}?{urlencode(args)}"
    
    # Simple headers since this is a practice site
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (compatible; SearXNG)',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    return params

def response(resp):
    """Parse response from MusicToScrape"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    dom = html.fromstring(resp.text)
    
    # Try to find track/album elements
    # Common patterns for music sites
    selectors = [
        '//div[@class="track-item"]',
        '//div[@class="album-item"]',
        '//article[@class="music-item"]',
        '//div[contains(@class, "result")]',
        '//div[@class="song"]',
        '//li[@class="track"]',
        '//div[@class="music-card"]',
        '//div[@class="item"]'
    ]
    
    items = []
    for selector in selectors:
        items = eval_xpath_list(dom, selector)
        if items:
            break
    
    # If no items found with class selectors, try generic approach
    if not items:
        # Look for any repeating structure that might contain music data
        items = eval_xpath_list(dom, '//div[@id="results"]//div[@class]')
        if not items:
            items = eval_xpath_list(dom, '//main//article | //main//div[@class]')
    
    for item in items[:20]:  # Limit to 20 results per page
        try:
            # Extract title (try multiple patterns)
            title = None
            title_selectors = [
                './/h2 | .//h3 | .//h4',
                './/*[@class="title"] | .//*[@class="track-title"] | .//*[@class="song-title"]',
                './/a[contains(@class, "title")]',
                './/span[@class="title"]'
            ]
            
            for selector in title_selectors:
                title_elem = eval_xpath_getindex(item, selector, 0)
                if title_elem is not None:
                    title = extract_text(title_elem)
                    if title:
                        break
            
            if not title:
                continue
            
            # Extract artist
            artist = None
            artist_selectors = [
                './/*[@class="artist"] | .//*[@class="artist-name"]',
                './/span[contains(@class, "artist")]',
                './/a[contains(@class, "artist")]',
                './/div[@class="by"] | .//span[@class="by"]'
            ]
            
            for selector in artist_selectors:
                artist_elem = eval_xpath_getindex(item, selector, 0)
                if artist_elem is not None:
                    artist = extract_text(artist_elem)
                    if artist:
                        break
            
            if not artist:
                artist = 'Unknown Artist'
            
            # Extract URL
            url = None
            link_elem = eval_xpath_getindex(item, './/a[@href]', 0)
            if link_elem is not None:
                url = link_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = base_url + url
            
            if not url:
                # Generate a URL based on title
                url = f"{base_url}/track/{quote(title.lower().replace(' ', '-'))}"
            
            # Extract additional metadata
            album = None
            album_elem = eval_xpath_getindex(item, './/*[@class="album"] | .//span[contains(@class, "album")]', 0)
            if album_elem is not None:
                album = extract_text(album_elem)
            
            # Duration
            duration = None
            duration_elem = eval_xpath_getindex(item, './/*[@class="duration"] | .//time | .//span[contains(@class, "time")]', 0)
            if duration_elem is not None:
                duration_str = extract_text(duration_elem)
                duration = music_base.parse_duration(duration_str)
            
            # Genre
            genre = None
            genre_elem = eval_xpath_getindex(item, './/*[@class="genre"] | .//span[contains(@class, "genre")]', 0)
            if genre_elem is not None:
                genre = extract_text(genre_elem)
            
            # Year
            year = None
            year_elem = eval_xpath_getindex(item, './/*[@class="year"] | .//span[contains(@class, "year")] | .//time[@datetime]', 0)
            if year_elem is not None:
                year_text = extract_text(year_elem)
                year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                if year_match:
                    year = year_match.group()
            
            # Build result
            result = music_base.standardize_result({
                'url': url,
                'title': title,
                'artist': artist,
                'album': album,
                'duration_ms': duration,
                'engine_data': {
                    'source': 'musictoscrape',
                    'practice_site': True
                }
            })
            
            # Add content description
            content_parts = []
            if album:
                content_parts.append(f"Album: {album}")
            if genre:
                content_parts.append(f"Genre: {genre}")
            if year:
                content_parts.append(f"Year: {year}")
            if duration:
                content_parts.append(f"Duration: {duration // 60000}:{(duration % 60000) // 1000:02d}")
            
            if content_parts:
                result['content'] = ' | '.join(content_parts)
            
            # Try to find thumbnail
            img_elem = eval_xpath_getindex(item, './/img[@src]', 0)
            if img_elem is not None:
                img_src = img_elem.get('src', '')
                if img_src:
                    if not img_src.startswith('http'):
                        img_src = base_url + img_src
                    result['thumbnail'] = img_src
            
            results.append(result)
            
        except Exception as e:
            # Continue on error for individual items
            continue
    
    # If no results found, try to check if the site structure is different
    if not results and len(items) > 0:
        # Try a more generic extraction
        all_links = eval_xpath_list(dom, '//a[@href and contains(@href, "/track/") or contains(@href, "/album/") or contains(@href, "/song/")]')
        
        for link in all_links[:10]:
            try:
                title = extract_text(link)
                if not title:
                    continue
                
                url = link.get('href', '')
                if not url.startswith('http'):
                    url = base_url + url
                
                # Try to find artist from context
                parent = link.getparent()
                artist_text = extract_text(parent)
                
                # Simple pattern matching for "by Artist" or "- Artist"
                artist_match = re.search(r'(?:by|[-–—])\s*([^-–—]+?)(?:\s*[-–—]|$)', artist_text)
                artist = artist_match.group(1).strip() if artist_match else 'Unknown Artist'
                
                result = music_base.standardize_result({
                    'url': url,
                    'title': title,
                    'artist': artist,
                    'engine_data': {
                        'source': 'musictoscrape',
                        'practice_site': True,
                        'generic_extraction': True
                    }
                })
                
                results.append(result)
                
            except Exception:
                continue
    
    return results