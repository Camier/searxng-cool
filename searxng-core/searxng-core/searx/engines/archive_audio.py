# SPDX-License-Identifier: AGPL-3.0-or-later
"""Archive.org Audio (Music/Podcasts)

Search audio content from the Internet Archive's vast collection.
No API key required.
"""

from urllib.parse import urlencode, quote
from datetime import datetime
import re

# About
about = {
    'website': 'https://archive.org',
    'wikidata_id': 'Q461',
    'official_api_documentation': 'https://archive.org/developers/advanced_search.html',
    'use_official_api': True,
    'require_api_key': False,
    'results': 'JSON',
}

# Engine configuration
engine_type = 'online'
categories = ['music']
paging = True
time_range_support = True

# API configuration
base_url = 'https://archive.org'
search_url = base_url + '/advancedsearch.php'

# Time range mapping
time_range_map = {
    'day': '[NOW-1DAY TO NOW]',
    'week': '[NOW-7DAY TO NOW]',
    'month': '[NOW-1MONTH TO NOW]',
    'year': '[NOW-1YEAR TO NOW]',
}


def request(query, params):
    """Build request parameters for Archive.org API"""
    
    # Build search query - always search audio media type
    search_query = f'mediatype:audio AND {query}'
    
    # Add time range if specified
    if params.get('time_range') in time_range_map:
        search_query += f' AND addeddate:{time_range_map[params["time_range"]]}'
    
    # Calculate rows and start for pagination
    rows = 20
    start = (params.get('pageno', 1) - 1) * rows
    
    # Build request parameters
    request_params = {
        'q': search_query,
        'output': 'json',
        'rows': rows,
        'start': start,
        'fl': 'identifier,title,creator,date,description,downloads,format,collection,avg_rating,num_reviews',
        'sort': 'downloads desc'  # Sort by popularity
    }
    
    params['url'] = f"{search_url}?{urlencode(request_params)}"
    
    return params


def response(resp):
    """Parse response from Archive.org API"""
    results = []
    
    if resp.status_code != 200:
        return []
    
    try:
        json_data = resp.json()
    except ValueError:
        return []
    
    # Check if we have results
    if 'response' not in json_data or 'docs' not in json_data['response']:
        return []
    
    for item in json_data['response']['docs']:
        # Skip if no identifier
        identifier = item.get('identifier')
        if not identifier:
            continue
            
        # Build item URL
        url = f"{base_url}/details/{identifier}"
        
        # Title and creator
        title = item.get('title', 'Unknown Title')
        creator = item.get('creator')
        if isinstance(creator, list):
            creator = ', '.join(creator)
        elif not creator:
            creator = 'Unknown Artist'
            
        # Format title
        display_title = f"{creator} - {title}" if creator != 'Unknown Artist' else title
        
        # Build content description
        content_parts = []
        
        # Add description (truncate if too long)
        description = item.get('description', '')
        if isinstance(description, list):
            description = ' '.join(description)
        if description:
            # Clean HTML tags
            description = re.sub('<[^<]+?>', '', description)
            if len(description) > 200:
                description = description[:197] + '...'
            content_parts.append(description)
        
        # Add metadata
        metadata = []
        
        # Format info
        formats = item.get('format', [])
        if isinstance(formats, str):
            formats = [formats]
        if formats:
            # Filter audio formats
            audio_formats = [f for f in formats if any(x in f.lower() for x in ['mp3', 'ogg', 'flac', 'wav', 'm4a'])]
            if audio_formats:
                metadata.append(f"Formats: {', '.join(audio_formats[:3])}")
        
        # Collection
        collection = item.get('collection', [])
        if isinstance(collection, str):
            collection = [collection]
        if collection:
            metadata.append(f"Collection: {collection[0]}")
        
        # Downloads
        downloads = item.get('downloads', 0)
        if downloads:
            if downloads > 1000000:
                metadata.append(f"Downloads: {downloads/1000000:.1f}M")
            elif downloads > 1000:
                metadata.append(f"Downloads: {downloads/1000:.1f}K")
            else:
                metadata.append(f"Downloads: {downloads}")
        
        # Rating
        avg_rating = item.get('avg_rating', 0)
        if avg_rating:
            metadata.append(f"Rating: {avg_rating:.1f}/5")
        
        # Combine content
        if metadata:
            if content_parts:
                content = content_parts[0] + ' | ' + ' | '.join(metadata)
            else:
                content = ' | '.join(metadata)
        else:
            content = content_parts[0] if content_parts else ''
        
        # Create result
        result = {
            'url': url,
            'title': display_title,
            'content': content,
        }
        
        # Add thumbnail - Archive.org provides thumbnails at predictable URLs
        result['thumbnail'] = f"https://archive.org/services/img/{identifier}"
        
        # Add audio player iframe
        # Archive.org provides embeddable player
        result['iframe_src'] = f"https://archive.org/embed/{identifier}"
        
        # Add published date if available
        date = item.get('date')
        if date:
            try:
                # Archive.org dates can be in various formats
                if len(date) == 4:  # Just year
                    result['publishedDate'] = datetime(int(date), 1, 1)
                elif len(date) == 7:  # YYYY-MM
                    year, month = date.split('-')
                    result['publishedDate'] = datetime(int(year), int(month), 1)
                elif len(date) >= 10:  # Full date
                    result['publishedDate'] = datetime.strptime(date[:10], '%Y-%m-%d')
            except (ValueError, TypeError):
                pass
        
        results.append(result)
    
    return results