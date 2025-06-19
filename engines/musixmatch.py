# SPDX-License-Identifier: AGPL-3.0-or-later
"""Musixmatch Lyrics Search

Search Musixmatch for song lyrics and translations.
This engine focuses on lyrical content and song metadata.
"""

from urllib.parse import quote
import json
import re
from lxml import html
from searx.utils import extract_text, eval_xpath_list, eval_xpath_getindex
from searx.engines.base_music import MusicEngineBase

# About
about = {
    'website': 'https://www.musixmatch.com',
    'wikidata_id': 'Q19801692',
    'official_api_documentation': 'https://developer.musixmatch.com',
    'use_official_api': False,
    'require_api_key': False,
    'results': 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music', 'lyrics']
paging = True

# Base URL
base_url = 'https://www.musixmatch.com'
search_url = base_url + '/search/{query}'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for Musixmatch search"""
    
    # Handle special query types
    clean_query = query
    if query.startswith('lyrics:'):
        clean_query = query[7:].strip()
    
    # Encode query
    encoded_query = quote(clean_query)
    
    # Add page number if paging
    page_suffix = ''
    if params.get('pageno', 1) > 1:
        page_suffix = f'/{params["pageno"]}'
    
    # Build URL
    params['url'] = search_url.format(query=encoded_query) + page_suffix
    
    # Add headers to avoid bot detection
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    return params

def response(resp):
    """Parse response from Musixmatch search"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    dom = html.fromstring(resp.text)
    
    # Look for structured data first
    script_elements = eval_xpath_list(dom, '//script[@type="application/ld+json"]')
    
    for script in script_elements:
        try:
            data = json.loads(script.text_content())
            
            # Check for ItemList schema
            if isinstance(data, dict) and data.get('@type') == 'ItemList':
                items = data.get('itemListElement', [])
                for item in items:
                    if 'item' in item:
                        result = parse_schema_track(item['item'])
                        if result:
                            results.append(result)
            
            # Check for MusicRecording
            elif isinstance(data, dict) and data.get('@type') == 'MusicRecording':
                result = parse_schema_track(data)
                if result:
                    results.append(result)
                    
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    # Fallback to HTML scraping
    if not results:
        # Search for track list items
        track_selectors = [
            '//div[@class="media-card-body"]',
            '//div[contains(@class, "track-list__item")]',
            '//li[contains(@class, "serp-item")]',
            '//div[@class="box-content"]//div[@class="track-snippet"]'
        ]
        
        for selector in track_selectors:
            elements = eval_xpath_list(dom, selector)
            if elements:
                for element in elements[:15]:  # Limit results
                    result = parse_html_track(element)
                    if result:
                        results.append(result)
                break
    
    return results

def parse_schema_track(track_data):
    """Parse track from schema.org data"""
    if not isinstance(track_data, dict):
        return None
    
    title = track_data.get('name', '')
    url = track_data.get('url', '')
    
    if not title or not url:
        return None
    
    # Get artist info
    artists = []
    performer = track_data.get('byArtist') or track_data.get('performer')
    if isinstance(performer, dict):
        artists.append(performer.get('name', 'Unknown Artist'))
    elif isinstance(performer, list):
        for artist in performer:
            if isinstance(artist, dict):
                artists.append(artist.get('name', 'Unknown Artist'))
    
    # Get lyrics info
    lyrics_data = track_data.get('recordingOf', {})
    has_lyrics = False
    lyrics_languages = []
    
    if isinstance(lyrics_data, dict):
        # Check for lyrics
        if 'lyrics' in lyrics_data:
            has_lyrics = True
            lyrics = lyrics_data['lyrics']
            if isinstance(lyrics, dict) and 'inLanguage' in lyrics:
                lang = lyrics['inLanguage']
                if isinstance(lang, str):
                    lyrics_languages.append(lang)
    
    # Build result
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artists[0] if artists else 'Unknown Artist',
        'artists': artists,
        'engine_data': {
            'source': 'musixmatch',
            'has_lyrics': has_lyrics,
            'lyrics_languages': lyrics_languages
        }
    })
    
    # Add lyrics availability to content
    content_parts = []
    if has_lyrics:
        content_parts.append("Lyrics available")
    if lyrics_languages:
        content_parts.append(f"Languages: {', '.join(lyrics_languages)}")
    
    if content_parts:
        result['content'] = ' | '.join(content_parts)
    
    return result

def parse_html_track(element):
    """Parse track from HTML element"""
    try:
        # Find the main link
        link_elem = eval_xpath_getindex(element, './/a[@href and contains(@href, "/lyrics/")]', 0)
        if link_elem is None:
            # Try alternative selectors
            link_elem = eval_xpath_getindex(element, './/h2/a[@href] | .//h3/a[@href]', 0)
        
        if link_elem is None:
            return None
        
        url = link_elem.get('href', '')
        if not url.startswith('http'):
            url = base_url + url
        
        # Extract title and artist from link or nearby elements
        link_text = extract_text(link_elem)
        
        # Musixmatch often formats as "Artist - Song Title"
        title = 'Unknown Track'
        artist = 'Unknown Artist'
        
        if ' - ' in link_text:
            parts = link_text.split(' - ', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            # Try to find title and artist separately
            title_elem = eval_xpath_getindex(element, './/span[@class="title"] | .//div[@class="title"]', 0)
            if title_elem is not None:
                title = extract_text(title_elem)
            else:
                title = link_text
            
            artist_elem = eval_xpath_getindex(element, './/span[@class="artist"] | .//a[contains(@href, "/artist/")]', 0)
            if artist_elem is not None:
                artist = extract_text(artist_elem)
        
        # Look for additional metadata
        content_parts = []
        
        # Check for lyrics availability
        lyrics_elem = eval_xpath_getindex(element, './/*[contains(@class, "lyrics-available")] | .//*[contains(text(), "Lyrics")]', 0)
        if lyrics_elem is not None:
            content_parts.append("Lyrics available")
        
        # Check for translations
        translation_elem = eval_xpath_getindex(element, './/*[contains(@class, "translation")] | .//*[contains(text(), "translation")]', 0)
        if translation_elem is not None:
            translation_text = extract_text(translation_elem)
            if translation_text:
                content_parts.append(translation_text)
        
        # Check for snippet
        snippet_elem = eval_xpath_getindex(element, './/p[@class="snippet"] | .//div[@class="lyrics-snippet"]', 0)
        if snippet_elem is not None:
            snippet = extract_text(snippet_elem)
            if snippet:
                # Clean and truncate snippet
                snippet = snippet.strip()
                if len(snippet) > 100:
                    snippet = snippet[:97] + '...'
                content_parts.append(f'"{snippet}"')
        
        # Build result
        result = music_base.standardize_result({
            'url': url,
            'title': title,
            'artist': artist,
            'engine_data': {
                'source': 'musixmatch',
                'scraped': True
            }
        })
        
        if content_parts:
            result['content'] = ' | '.join(content_parts)
        
        # Try to find album art
        img_elem = eval_xpath_getindex(element, './/img[@src and @alt]', 0)
        if img_elem is not None:
            img_src = img_elem.get('src', '')
            if img_src and not img_src.startswith('data:'):
                if not img_src.startswith('http'):
                    img_src = base_url + img_src
                result['thumbnail'] = img_src
        
        return result
        
    except Exception:
        return None

def get_lyrics_snippet(url):
    """Attempt to extract a lyrics snippet from the page"""
    # This would require an additional request, so we'll skip it for now
    # In a real implementation, you might cache these or fetch them asynchronously
    return None