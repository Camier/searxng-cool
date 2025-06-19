# SPDX-License-Identifier: AGPL-3.0-or-later
"""AllMusic - Comprehensive Music Database

Search AllMusic for albums, artists, songs, and detailed metadata.
AllMusic is one of the most comprehensive music databases available.
"""

from urllib.parse import quote, urlencode
import json
from lxml import html
from searx.utils import extract_text, eval_xpath_list, eval_xpath_getindex
from searx.engines.base_music import MusicEngineBase
import re

# About
about = {
    'website': 'https://www.allmusic.com',
    'wikidata_id': 'Q31307',
    'official_api_documentation': None,
    'use_official_api': False,
    'require_api_key': False,
    'results': 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = False  # AllMusic search doesn't have clear pagination

# Base URL
base_url = 'https://www.allmusic.com'
search_url = base_url + '/search/all/{query}'

# Create base class instance
music_base = MusicEngineBase()

def request(query, params):
    """Build request for AllMusic search"""
    
    # URL encode the query
    encoded_query = quote(query)
    
    # Build URL
    params['url'] = search_url.format(query=encoded_query)
    
    # Add headers to appear as a regular browser
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
    """Parse response from AllMusic search"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    dom = html.fromstring(resp.text)
    
    # AllMusic has different sections for different result types
    # Songs/Tracks section
    song_results = eval_xpath_list(dom, '//section[@class="songs"]//li[contains(@class, "song")]')
    
    for item in song_results[:5]:  # Limit songs
        try:
            result = parse_song_result(item)
            if result:
                results.append(result)
        except Exception:
            continue
    
    # Albums section
    album_results = eval_xpath_list(dom, '//section[@class="albums"]//li[contains(@class, "album")]')
    
    for item in album_results[:5]:  # Limit albums
        try:
            result = parse_album_result(item)
            if result:
                results.append(result)
        except Exception:
            continue
    
    # Artists section
    artist_results = eval_xpath_list(dom, '//section[@class="artists"]//li[contains(@class, "artist")]')
    
    for item in artist_results[:3]:  # Limit artists
        try:
            result = parse_artist_result(item)
            if result:
                results.append(result)
        except Exception:
            continue
    
    # If no results in sections, try generic search results
    if not results:
        generic_results = eval_xpath_list(dom, '//li[@class="result"]')
        
        for item in generic_results[:10]:
            try:
                # Determine result type
                type_elem = eval_xpath_getindex(item, './/div[@class="type"]', 0)
                result_type = extract_text(type_elem).lower() if type_elem is not None else 'unknown'
                
                if 'song' in result_type or 'track' in result_type:
                    result = parse_song_result(item)
                elif 'album' in result_type:
                    result = parse_album_result(item)
                elif 'artist' in result_type:
                    result = parse_artist_result(item)
                else:
                    result = parse_generic_result(item)
                
                if result:
                    results.append(result)
                    
            except Exception:
                continue
    
    return results

def parse_song_result(item):
    """Parse a song/track result"""
    # Title and URL
    title_elem = eval_xpath_getindex(item, './/h4[@class="title"]/a | .//a[@class="title"] | .//a[contains(@class, "song-link")]', 0)
    if title_elem is None:
        return None
    
    title = extract_text(title_elem)
    url = title_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Artist
    artist_elem = eval_xpath_getindex(item, './/h5[@class="artist"]/a | .//a[@class="artist"] | .//span[@class="artist"]', 0)
    artist = extract_text(artist_elem) if artist_elem is not None else 'Unknown Artist'
    
    # Album
    album_elem = eval_xpath_getindex(item, './/h5[@class="album"]/a | .//a[@class="album"] | .//span[@class="album"]', 0)
    album = extract_text(album_elem) if album_elem is not None else None
    
    # Year
    year = None
    year_elem = eval_xpath_getindex(item, './/span[@class="year"] | .//div[@class="year"]', 0)
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
        'release_date': year,
        'engine_data': {
            'source': 'allmusic',
            'type': 'song'
        }
    })
    
    # Content description
    content_parts = []
    if album:
        content_parts.append(f"Album: {album}")
    if year:
        content_parts.append(f"Year: {year}")
    
    if content_parts:
        result['content'] = ' | '.join(content_parts)
    
    return result

def parse_album_result(item):
    """Parse an album result"""
    # Title and URL
    title_elem = eval_xpath_getindex(item, './/h4[@class="title"]/a | .//a[@class="title"] | .//a[contains(@class, "album-link")]', 0)
    if title_elem is None:
        return None
    
    title = extract_text(title_elem)
    url = title_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Artist
    artist_elem = eval_xpath_getindex(item, './/h5[@class="artist"]/a | .//a[@class="artist"] | .//span[@class="artist"]', 0)
    artist = extract_text(artist_elem) if artist_elem is not None else 'Unknown Artist'
    
    # Year
    year = None
    year_elem = eval_xpath_getindex(item, './/span[@class="year"] | .//div[@class="year"]', 0)
    if year_elem is not None:
        year_text = extract_text(year_elem)
        year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
        if year_match:
            year = year_match.group()
    
    # Rating
    rating = None
    rating_elem = eval_xpath_getindex(item, './/div[@class="allmusic-rating"] | .//span[@class="rating"]', 0)
    if rating_elem is not None:
        # AllMusic uses star ratings, count the filled stars
        filled_stars = len(eval_xpath_list(rating_elem, './/i[contains(@class, "filled")] | .//span[@class="star-filled"]'))
        if filled_stars > 0:
            rating = f"{filled_stars}/5"
    
    # Build result
    result = music_base.standardize_result({
        'url': url,
        'title': f"{title} (Album)",
        'artist': artist,
        'album': title,
        'release_date': year,
        'engine_data': {
            'source': 'allmusic',
            'type': 'album',
            'rating': rating
        }
    })
    
    # Content description
    content_parts = [f"by {artist}"]
    if year:
        content_parts.append(f"Year: {year}")
    if rating:
        content_parts.append(f"Rating: {rating}")
    
    result['content'] = ' | '.join(content_parts)
    
    # Album cover
    img_elem = eval_xpath_getindex(item, './/img[@src and contains(@class, "cover")] | .//img[@data-src]', 0)
    if img_elem is not None:
        img_src = img_elem.get('src') or img_elem.get('data-src', '')
        if img_src and not img_src.startswith('data:'):
            if not img_src.startswith('http'):
                img_src = base_url + img_src
            result['thumbnail'] = img_src
    
    return result

def parse_artist_result(item):
    """Parse an artist result"""
    # Name and URL
    name_elem = eval_xpath_getindex(item, './/h4[@class="name"]/a | .//a[@class="name"] | .//a[contains(@class, "artist-link")]', 0)
    if name_elem is None:
        return None
    
    name = extract_text(name_elem)
    url = name_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Genre
    genre_elem = eval_xpath_getindex(item, './/div[@class="genre"] | .//span[@class="genre"]', 0)
    genre = extract_text(genre_elem) if genre_elem is not None else None
    
    # Active years
    years_elem = eval_xpath_getindex(item, './/div[@class="active-dates"] | .//span[@class="years"]', 0)
    years = extract_text(years_elem) if years_elem is not None else None
    
    # Build result
    result = {
        'url': url,
        'title': f"{name} (Artist)",
        'template': 'music.html',
        'engine_data': {
            'source': 'allmusic',
            'type': 'artist'
        }
    }
    
    # Content description
    content_parts = []
    if genre:
        content_parts.append(f"Genre: {genre}")
    if years:
        content_parts.append(f"Active: {years}")
    
    result['content'] = ' | '.join(content_parts) if content_parts else "Music Artist"
    
    # Artist image
    img_elem = eval_xpath_getindex(item, './/img[@src and contains(@class, "photo")] | .//img[@data-src]', 0)
    if img_elem is not None:
        img_src = img_elem.get('src') or img_elem.get('data-src', '')
        if img_src and not img_src.startswith('data:'):
            if not img_src.startswith('http'):
                img_src = base_url + img_src
            result['thumbnail'] = img_src
    
    return result

def parse_generic_result(item):
    """Parse a generic result when type is unknown"""
    # Try to extract basic information
    link_elem = eval_xpath_getindex(item, './/a[@href][1]', 0)
    if link_elem is None:
        return None
    
    title = extract_text(link_elem)
    if not title:
        return None
    
    url = link_elem.get('href', '')
    if not url.startswith('http'):
        url = base_url + url
    
    # Try to get any additional context
    content = extract_text(item)
    # Remove the title from content
    content = content.replace(title, '').strip()
    
    result = {
        'url': url,
        'title': title,
        'content': content[:200] if content else '',
        'template': 'music.html',
        'engine_data': {
            'source': 'allmusic',
            'type': 'unknown'
        }
    }
    
    return result