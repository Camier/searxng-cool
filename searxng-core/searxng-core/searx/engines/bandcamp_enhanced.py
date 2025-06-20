# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bandcamp Enhanced (Music)

Enhanced Bandcamp search with additional metadata extraction.
"""

import re
from urllib.parse import urlencode, urlparse
from lxml import html
from searx.utils import extract_text, eval_xpath
from datetime import datetime

# About
about = {
    "website": 'https://bandcamp.com',
    "wikidata_id": 'Q545966',
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True

# Base URLs
base_url = "https://bandcamp.com"
search_url = base_url + "/search"

# Search types
search_types = {
    'all': '',
    'artists_and_labels': 'b',
    'albums': 'a',
    'tracks': 't',
    'fans': 'f',
}

# XPath selectors for enhanced data extraction
result_xpath = '//li[@class="searchresult data-search"]'
title_xpath = './/div[@class="heading"]/a/text()'
url_xpath = './/div[@class="heading"]/a/@href'
content_xpath = './/div[@class="subhead"]/text()'
img_xpath = './/div[@class="art"]/img/@src'

# Additional metadata xpaths
artist_xpath = './/div[@class="subhead"]/text()[1]'
album_xpath = './/div[@class="subhead"]/text()[2]'
genre_xpath = './/div[@class="genre"]/text()'
tags_xpath = './/div[@class="tags"]//a/text()'
released_xpath = './/div[@class="released"]/text()'
length_xpath = './/div[@class="length"]/text()'
price_xpath = './/span[@class="price"]/text()'
format_xpath = './/div[@class="format"]/text()'
location_xpath = './/div[@class="location"]/text()'
itemtype_xpath = './/@data-search'


def request(query, params):
    """Build request for enhanced Bandcamp search"""
    
    # Default search type
    search_type = params.get('search_type', 'all')
    
    # Build search parameters
    search_params = {
        'q': query,
        'page': params.get('pageno', 1),
    }
    
    # Add item type filter
    if search_type in search_types and search_types[search_type]:
        search_params['item_type'] = search_types[search_type]
    
    params['url'] = f"{search_url}?{urlencode(search_params)}"
    
    return params


def response(resp):
    """Parse enhanced response from Bandcamp"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    # Parse HTML
    dom = html.fromstring(resp.text)
    
    # Extract search results
    for result in eval_xpath(dom, result_xpath):
        # Get item type
        item_type = extract_text(eval_xpath(result, itemtype_xpath))
        
        # Basic information
        title = extract_text(eval_xpath(result, title_xpath))
        url = extract_text(eval_xpath(result, url_xpath))
        
        if not url:
            continue
        
        # Make URL absolute
        if not url.startswith('http'):
            url = base_url + url
        
        # Get content/subhead info
        content_text = extract_text(eval_xpath(result, content_xpath))
        
        # Build enhanced content based on item type
        content_parts = []
        
        # Extract metadata based on result type
        if 'album' in str(item_type).lower():
            # Album result
            artist_info = extract_text(eval_xpath(result, './/div[@class="subhead"]/text()[1]'))
            if artist_info:
                content_parts.append(f"by {artist_info}")
            
            # Album metadata
            released = extract_text(eval_xpath(result, './/div[@class="released"]/text()'))
            if released:
                content_parts.append(f"Released: {released}")
            
            # Number of tracks
            track_count = extract_text(eval_xpath(result, './/div[@class="length"]/span[@class="num_tracks"]/text()'))
            if track_count:
                content_parts.append(f"{track_count}")
            
            # Total length
            total_length = extract_text(eval_xpath(result, './/div[@class="length"]/span[@class="time"]/text()'))
            if total_length:
                content_parts.append(f"Duration: {total_length}")
                
        elif 'track' in str(item_type).lower():
            # Track result
            # Extract artist and album
            subhead_parts = content_text.split(' by ')
            if len(subhead_parts) >= 2:
                track_info = subhead_parts[0].strip()
                artist_info = ' by '.join(subhead_parts[1:]).strip()
                
                # Check if track is from an album
                if ' from ' in track_info:
                    album_parts = track_info.split(' from ')
                    if len(album_parts) >= 2:
                        album_name = album_parts[-1].strip()
                        content_parts.append(f"from {album_name}")
                
                content_parts.append(f"by {artist_info}")
            
            # Track length
            track_length = extract_text(eval_xpath(result, './/div[@class="length"]/text()'))
            if track_length:
                content_parts.append(f"Duration: {track_length}")
                
        elif 'artist' in str(item_type).lower() or 'label' in str(item_type).lower():
            # Artist/Label result
            # Location
            location = extract_text(eval_xpath(result, './/div[@class="location"]/text()'))
            if location:
                content_parts.append(f"Location: {location}")
            
            # Genre
            genre = extract_text(eval_xpath(result, './/div[@class="genre"]/text()'))
            if genre:
                content_parts.append(f"Genre: {genre}")
                
        # Common metadata for all types
        # Tags
        tags = eval_xpath(result, './/div[@class="tags"]//a/text()')
        if tags:
            tag_list = [tag.strip() for tag in tags[:5]]  # Limit to 5 tags
            if tag_list:
                content_parts.append(f"Tags: {', '.join(tag_list)}")
        
        # Price information
        price = extract_text(eval_xpath(result, './/span[@class="price"]/text()'))
        if price and price.strip():
            # Clean up price
            price = price.strip()
            if price.lower() not in ['name your price', 'free download']:
                content_parts.append(f"Price: {price}")
            elif price.lower() == 'free download':
                content_parts.append("🆓 Free Download")
            elif price.lower() == 'name your price':
                content_parts.append("💰 Name Your Price")
        
        # Format (for albums)
        format_info = extract_text(eval_xpath(result, './/div[@class="format"]/text()'))
        if format_info:
            content_parts.append(f"Format: {format_info}")
        
        # Sold out indicator
        if 'sold out' in content_text.lower():
            content_parts.append("❌ Sold Out")
        
        # Limited edition indicator
        if 'limited' in content_text.lower():
            content_parts.append("⚡ Limited Edition")
        
        # Pre-order indicator
        if 'pre-order' in content_text.lower():
            content_parts.append("📅 Pre-order")
        
        # If we don't have specific content, use the original
        if not content_parts and content_text:
            content_parts.append(content_text)
        
        content = ' | '.join(content_parts)
        
        # Create result
        res = {
            'url': url,
            'title': title,
            'content': content,
        }
        
        # Thumbnail
        img_src = extract_text(eval_xpath(result, img_xpath))
        if img_src:
            # Bandcamp serves different image sizes
            # Replace _16 suffix with larger size
            img_src = re.sub(r'_\d+\.', '_7.', img_src)  # Use size 7 (larger)
            res['thumbnail'] = img_src
        
        # Try to extract embedded player URL for tracks
        if 'track' in str(item_type).lower() and '/track/' in url:
            # Extract track ID from URL
            track_match = re.search(r'/track/([^/?]+)', url)
            if track_match:
                track_slug = track_match.group(1)
                # Parse artist URL
                parsed_url = urlparse(url)
                if parsed_url.netloc:
                    # Bandcamp embed format
                    res['iframe_src'] = f"https://bandcamp.com/EmbeddedPlayer/track={track_slug}/size=small/bgcol=ffffff/linkcol=0687f5/transparent=true/"
        
        # For albums, we can also embed
        elif 'album' in str(item_type).lower() and '/album/' in url:
            album_match = re.search(r'/album/([^/?]+)', url)
            if album_match:
                album_slug = album_match.group(1)
                parsed_url = urlparse(url)
                if parsed_url.netloc:
                    res['iframe_src'] = f"https://bandcamp.com/EmbeddedPlayer/album={album_slug}/size=small/bgcol=ffffff/linkcol=0687f5/transparent=true/"
        
        # Try to parse release date
        if 'released' in ' '.join(content_parts).lower():
            date_match = re.search(r'Released:\s*(.+?)(?:\||$)', content)
            if date_match:
                date_str = date_match.group(1).strip()
                try:
                    # Try common date formats
                    for fmt in ['%B %d, %Y', '%B %Y', '%Y']:
                        try:
                            res['publishedDate'] = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                except:
                    pass
        
        results.append(res)
    
    return results