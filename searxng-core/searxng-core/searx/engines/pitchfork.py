# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pitchfork - Music Reviews and Discovery

Search Pitchfork for album reviews, artist information, and music news.
Focuses on indie, alternative, and electronic music.
"""

from urllib.parse import quote, urlencode
import json
import re
from lxml import html
from searx.utils import extract_text, eval_xpath_list, eval_xpath_getindex
from searx.engines.base_music import MusicEngineBase

# About
about = {
    'website': 'https://pitchfork.com',
    'wikidata_id': 'Q1552283',
    'official_api_documentation': None,
    'use_official_api': False,
    'require_api_key': False,
    'results': 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True

# Allow redirects for regional/HTTPS redirects
max_redirects = 2

# Base URL
base_url = 'https://pitchfork.com'
search_url = base_url + '/search/?query={query}'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for Pitchfork search"""
    
    # URL encode the query
    encoded_query = quote(query)
    
    # Add page parameter if needed
    page = params.get('pageno', 1)
    page_param = f'&page={page}' if page > 1 else ''
    
    # Build URL
    params['url'] = search_url.format(query=encoded_query) + page_param
    
    # Add headers to appear as a regular browser
    params['headers'] = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': base_url,
    }
    
    return params

def response(resp):
    """Parse response from Pitchfork search"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    dom = html.fromstring(resp.text)
    
    # Pitchfork loads some content dynamically, but initial results are in HTML
    # Look for search result items
    result_selectors = [
        '//div[@class="result-item"]',
        '//article[contains(@class, "review")]',
        '//div[contains(@class, "search-result")]',
        '//div[@class="fts-result__list-item"]',
        '//div[contains(@class, "result__item")]'
    ]
    
    items = []
    for selector in result_selectors:
        items = eval_xpath_list(dom, selector)
        if items:
            break
    
    # If no specific result items, try to find review cards
    if not items:
        items = eval_xpath_list(dom, '//div[@class="review-card"] | //a[contains(@class, "review-link")]')
    
    for item in items[:15]:  # Limit results
        try:
            # Determine the type of result
            result_type = determine_result_type(item)
            
            if result_type == 'review':
                result = parse_review_result(item)
            elif result_type == 'artist':
                result = parse_artist_result(item)
            elif result_type == 'news':
                result = parse_news_result(item)
            else:
                result = parse_generic_result(item)
            
            if result:
                results.append(result)
                
        except Exception:
            continue
    
    # If still no results, try looking for JSON-LD data
    if not results:
        script_elements = eval_xpath_list(dom, '//script[@type="application/ld+json"]')
        
        for script in script_elements:
            try:
                data = json.loads(script.text_content())
                
                if isinstance(data, dict):
                    if data.get('@type') == 'Review' or data.get('@type') == 'MusicAlbum':
                        result = parse_jsonld_review(data)
                        if result:
                            results.append(result)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') in ['Review', 'MusicAlbum']:
                            result = parse_jsonld_review(item)
                            if result:
                                results.append(result)
                                
            except (json.JSONDecodeError, KeyError):
                continue
    
    return results

def determine_result_type(item):
    """Determine the type of Pitchfork result"""
    # Check for review indicators
    if eval_xpath_getindex(item, './/*[@class="score"] | .//*[contains(@class, "rating")]', 0) is not None:
        return 'review'
    
    # Check for artist page indicators
    if eval_xpath_getindex(item, './/*[contains(@class, "artist-")]', 0) is not None:
        return 'artist'
    
    # Check for news indicators
    if eval_xpath_getindex(item, './/*[contains(@class, "news-")] | .//*[@class="tag"]', 0) is not None:
        return 'news'
    
    return 'unknown'

def parse_review_result(item):
    """Parse an album/track review result"""
    # Title (Album name)
    title_elem = eval_xpath_getindex(item, './/h2 | .//h3 | .//*[@class="title"] | .//a[contains(@class, "album")]', 0)
    if title_elem is None:
        return None
    
    title = extract_text(title_elem)
    
    # URL
    url_elem = eval_xpath_getindex(item, './/a[@href][1]', 0)
    if url_elem is None:
        return None
    
    url = url_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Artist
    artist_elem = eval_xpath_getindex(item, './/*[@class="artist"] | .//*[contains(@class, "artist-name")] | .//h3 | .//h4', 0)
    artist = extract_text(artist_elem) if artist_elem is not None else 'Unknown Artist'
    
    # If artist and title are in the same element, try to split them
    if artist == title and ' - ' in title:
        parts = title.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
    
    # Score/Rating
    score = None
    score_elem = eval_xpath_getindex(item, './/*[@class="score"] | .//*[contains(@class, "rating")] | .//*[@class="score-circle"]', 0)
    if score_elem is not None:
        score_text = extract_text(score_elem)
        # Extract numeric score (e.g., "8.5" from "8.5 / 10")
        score_match = re.search(r'(\d+\.?\d*)', score_text)
        if score_match:
            score = score_match.group(1)
    
    # Best New Music badge
    bnm = eval_xpath_getindex(item, './/*[contains(@class, "bnm")] | .//*[contains(text(), "Best New")]', 0) is not None
    
    # Genre/Tags
    genre_elems = eval_xpath_list(item, './/*[@class="genre"] | .//*[@class="tag"] | .//*[contains(@class, "genre-list")]//a')
    genres = [extract_text(g) for g in genre_elems if extract_text(g)]
    
    # Review snippet
    snippet_elem = eval_xpath_getindex(item, './/*[@class="abstract"] | .//*[contains(@class, "excerpt")] | .//p[1]', 0)
    snippet = extract_text(snippet_elem) if snippet_elem is not None else ''
    
    # Build result
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artist,
        'album': title,
        'engine_data': {
            'source': 'pitchfork',
            'type': 'review',
            'score': score,
            'best_new_music': bnm,
            'genres': genres
        }
    })
    
    # Content description
    content_parts = []
    if score:
        content_parts.append(f"Score: {score}/10")
    if bnm:
        content_parts.append("🏆 Best New Music")
    if genres:
        content_parts.append(f"Genre: {', '.join(genres[:2])}")
    if snippet:
        content_parts.append(snippet[:100] + '...' if len(snippet) > 100 else snippet)
    
    result['content'] = ' | '.join(content_parts)
    
    # Album artwork
    img_elem = eval_xpath_getindex(item, './/img[@src and contains(@class, "artwork")] | .//img[@data-src] | .//img[@src]', 0)
    if img_elem is not None:
        img_src = img_elem.get('src') or img_elem.get('data-src', '')
        if img_src and not img_src.startswith('data:'):
            if not img_src.startswith('http'):
                img_src = base_url + img_src
            result['thumbnail'] = img_src
    
    return result

def parse_artist_result(item):
    """Parse an artist result"""
    # Artist name
    name_elem = eval_xpath_getindex(item, './/h2 | .//h3 | .//*[@class="artist-name"]', 0)
    if name_elem is None:
        return None
    
    name = extract_text(name_elem)
    
    # URL
    url_elem = eval_xpath_getindex(item, './/a[@href][1]', 0)
    if url_elem is None:
        return None
    
    url = url_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Build result
    result = {
        'url': url,
        'title': f"{name} (Artist)",
        'content': "Artist profile on Pitchfork",
        'template': 'music.html',
        'engine_data': {
            'source': 'pitchfork',
            'type': 'artist'
        }
    }
    
    return result

def parse_news_result(item):
    """Parse a news/article result"""
    # Title
    title_elem = eval_xpath_getindex(item, './/h2 | .//h3 | .//*[@class="title"]', 0)
    if title_elem is None:
        return None
    
    title = extract_text(title_elem)
    
    # URL
    url_elem = eval_xpath_getindex(item, './/a[@href][1]', 0)
    if url_elem is None:
        return None
    
    url = url_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Snippet
    snippet_elem = eval_xpath_getindex(item, './/*[@class="abstract"] | .//p[1]', 0)
    snippet = extract_text(snippet_elem) if snippet_elem is not None else ''
    
    # Build result
    result = {
        'url': url,
        'title': title,
        'content': snippet[:200] if snippet else "Music news article",
        'template': 'music.html',
        'engine_data': {
            'source': 'pitchfork',
            'type': 'news'
        }
    }
    
    return result

def parse_generic_result(item):
    """Parse a generic result when type is unclear"""
    # Find the main link
    link_elem = eval_xpath_getindex(item, './/a[@href and not(contains(@href, "#"))][1]', 0)
    if link_elem is None:
        return None
    
    title = extract_text(link_elem)
    if not title:
        # Try to find title in heading
        title_elem = eval_xpath_getindex(item, './/h2 | .//h3 | .//h4', 0)
        title = extract_text(title_elem) if title_elem is not None else None
    
    if not title:
        return None
    
    url = link_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Extract any available content
    content = extract_text(item)
    # Remove title from content
    content = content.replace(title, '').strip()
    
    result = {
        'url': url,
        'title': title,
        'content': content[:200] if content else '',
        'template': 'music.html',
        'engine_data': {
            'source': 'pitchfork',
            'type': 'unknown'
        }
    }
    
    return result

def parse_jsonld_review(data):
    """Parse review from JSON-LD structured data"""
    # For Review type
    if data.get('@type') == 'Review':
        item_reviewed = data.get('itemReviewed', {})
        if not isinstance(item_reviewed, dict):
            return None
        
        title = item_reviewed.get('name', '')
        artist = item_reviewed.get('byArtist', {}).get('name', 'Unknown Artist')
        
        # Rating
        rating = data.get('reviewRating', {})
        score = rating.get('ratingValue') if isinstance(rating, dict) else None
        
        # URL
        url = data.get('url', base_url)
        
    # For MusicAlbum type
    elif data.get('@type') == 'MusicAlbum':
        title = data.get('name', '')
        artist = data.get('byArtist', {}).get('name', 'Unknown Artist')
        url = data.get('url', base_url)
        score = None
    
    else:
        return None
    
    if not title:
        return None
    
    result = music_base.standardize_result({
        'url': url,
        'title': title,
        'artist': artist,
        'album': title,
        'engine_data': {
            'source': 'pitchfork',
            'type': 'review',
            'score': score
        }
    })
    
    if score:
        result['content'] = f"Score: {score}/10 | Album review"
    
    return result