# SearXNG Integration Guide for SearXNG-Cool

## Table of Contents
1. [SearXNG Configuration](#searxng-configuration)
2. [Theme Customization](#theme-customization)
3. [Search Engine Configuration](#search-engines)
4. [Plugin Development](#plugin-development)
5. [Performance Optimization](#performance-optimization)
6. [Privacy Settings](#privacy-settings)
7. [API Integration](#api-integration)
8. [Monitoring & Debugging](#monitoring-debugging)

## SearXNG Configuration {#searxng-configuration}

### Core Settings Configuration
```yaml
# settings.yml
general:
    debug: false
    instance_name: "SearXNG-Cool"
    privacypolicy_url: false
    contact_url: false
    enable_metrics: true

search:
    safe_search: 0
    autocomplete: "duckduckgo"
    autocomplete_min: 4
    default_lang: "en-US"
    ban_time_on_fail: 5
    max_ban_time_on_fail: 120
    suspended_times:
        SearxEngineAccessDenied: 86400
        SearxEngineCaptcha: 86400
        SearxEngineTooManyRequests: 3600
        cf_SearxEngineCaptcha: 1296000
        cf_SearxEngineAccessDenied: 86400
        recaptcha_SearxEngineCaptcha: 604800

server:
    port: 8888
    bind_address: "127.0.0.1"
    secret_key: "ultrasecretkey"  # Change this!
    base_url: "https://alfredisgone.duckdns.org/"
    image_proxy: true
    http_protocol_version: "1.1"
    method: "POST"
    default_http_headers:
        X-Content-Type-Options: "nosniff"
        X-XSS-Protection: "1; mode=block"
        X-Download-Options: "noopen"
        X-Robots-Tag: "noindex, nofollow"
        Referrer-Policy: "no-referrer"

redis:
    url: redis://localhost:6379/0
    
limiter:
    botdetection:
        ip_limit:
            link_token: false
            
ui:
    static_path: ""
    templates_path: ""
    default_theme: "simple"
    default_locale: "en"
    query_in_title: false
    infinite_scroll: true
    center_alignment: false
    cache_url: https://web.archive.org/web/
    
preferences:
    lock:
        - language
        - autocomplete
        - safesearch
```

### Advanced Engine Configuration
```yaml
# engines/settings.yml
engines:
  - name: google
    engine: google
    shortcut: g
    disabled: false
    timeout: 3.0
    weight: 1.0
    display_error_messages: true
    proxies:
      http: socks5://127.0.0.1:9050
      https: socks5://127.0.0.1:9050
    
  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
    timeout: 3.0
    disabled: false
    weight: 1.5  # Higher weight = higher priority
    
  - name: startpage
    engine: startpage
    shortcut: sp
    timeout: 6.0
    disabled: false
    language: en-US
    
  - name: custom_engine
    engine: json_engine
    search_url: https://api.example.com/search?q={query}&page={pageno}
    results_query: results
    url_query: url
    title_query: title
    content_query: description
    categories: general
    shortcut: cst
    timeout: 5.0
    disabled: false
    weight: 0.5
    paging: true
    page_size: 10
    first_page_num: 1
```

### Result Processors
```python
# searx/engines/custom_processor.py
from searx import logger
from searx.engines import Engine

class CustomResultProcessor:
    """Custom result processor for SearXNG"""
    
    def __init__(self):
        self.logger = logger.getChild('custom_processor')
    
    def pre_search(self, request_args, search_args):
        """Modify search parameters before search"""
        # Add custom headers
        if 'headers' not in request_args:
            request_args['headers'] = {}
        request_args['headers']['X-Custom-Search'] = 'true'
        
        # Modify query
        query = search_args['query']
        if 'site:' not in query:
            search_args['query'] = f"{query} -ads"
        
        return request_args, search_args
    
    def post_search(self, results):
        """Process results after search"""
        processed_results = []
        
        for result in results:
            # Filter out unwanted results
            if self.should_filter(result):
                continue
            
            # Enhance result
            result = self.enhance_result(result)
            
            processed_results.append(result)
        
        return processed_results
    
    def should_filter(self, result):
        """Determine if result should be filtered"""
        # Filter tracking domains
        tracking_domains = ['doubleclick.net', 'googleadservices.com']
        url = result.get('url', '')
        
        for domain in tracking_domains:
            if domain in url:
                return True
        
        # Filter by content
        content = result.get('content', '').lower()
        spam_keywords = ['viagra', 'casino', 'lottery']
        
        for keyword in spam_keywords:
            if keyword in content:
                return True
        
        return False
    
    def enhance_result(self, result):
        """Enhance result with additional data"""
        # Add favicon
        from urllib.parse import urlparse
        parsed = urlparse(result['url'])
        result['favicon'] = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        
        # Add reading time estimate
        content_length = len(result.get('content', ''))
        result['reading_time'] = max(1, content_length // 200)  # 200 chars/min
        
        # Add relevance score
        result['relevance_score'] = self.calculate_relevance(result)
        
        return result
    
    def calculate_relevance(self, result):
        """Calculate custom relevance score"""
        score = 0
        
        # Title match
        if 'query' in result.get('title', '').lower():
            score += 10
        
        # URL quality
        if result['url'].startswith('https://'):
            score += 5
        
        # Content length
        content_length = len(result.get('content', ''))
        if content_length > 100:
            score += 3
        
        return score
```

## Theme Customization {#theme-customization}

### Custom Theme Structure
```
searxng-cool/
└── searx/
    └── static/
        └── themes/
            └── nichijou/
                ├── css/
                │   ├── style.css
                │   └── searxng.min.css
                ├── js/
                │   └── searxng.min.js
                ├── img/
                │   ├── favicon.png
                │   └── logo.svg
                └── templates/
                    ├── base.html
                    ├── index.html
                    └── results.html
```

### Theme Configuration
```python
# searx/themes/nichijou/theme.py
from flask import Blueprint

theme = Blueprint('nichijou_theme', __name__, 
                  static_folder='static',
                  template_folder='templates')

# Theme configuration
THEME_CONFIG = {
    'name': 'nichijou',
    'version': '1.0.0',
    'author': 'SearXNG-Cool',
    'description': 'Clean and modern theme for SearXNG',
    'styles': [
        'css/style.css',
        'css/searxng.min.css'
    ],
    'scripts': [
        'js/searxng.min.js'
    ],
    'features': {
        'dark_mode': True,
        'infinite_scroll': True,
        'instant_answers': True,
        'keyboard_shortcuts': True
    }
}

# Theme-specific filters
@theme.app_template_filter('humanize')
def humanize_filter(value):
    """Humanize numbers and dates"""
    if isinstance(value, int):
        if value > 1000000:
            return f"{value/1000000:.1f}M"
        elif value > 1000:
            return f"{value/1000:.1f}K"
    return value
```

### Custom CSS
```css
/* themes/nichijou/css/style.css */
:root {
    --primary-color: #2E86AB;
    --secondary-color: #A23B72;
    --background-color: #F8F9FA;
    --text-color: #212529;
    --border-color: #DEE2E6;
    --shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Dark mode variables */
@media (prefers-color-scheme: dark) {
    :root {
        --background-color: #1a1a1a;
        --text-color: #e0e0e0;
        --border-color: #333;
    }
}

/* Custom search box */
.search-container {
    max-width: 600px;
    margin: 2rem auto;
    padding: 1rem;
}

.search-box {
    width: 100%;
    padding: 1rem 1.5rem;
    font-size: 1.1rem;
    border: 2px solid var(--border-color);
    border-radius: 50px;
    transition: all 0.3s ease;
    box-shadow: var(--shadow);
}

.search-box:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(46, 134, 171, 0.1);
}

/* Results styling */
.result {
    background: white;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-radius: 8px;
    box-shadow: var(--shadow);
    transition: transform 0.2s ease;
}

.result:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.result-title {
    color: var(--primary-color);
    font-size: 1.2rem;
    font-weight: 500;
    text-decoration: none;
}

.result-url {
    color: #6C757D;
    font-size: 0.9rem;
    margin: 0.25rem 0;
}

.result-content {
    color: var(--text-color);
    line-height: 1.6;
}

/* Instant answers */
.instant-answer {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
}

/* Loading animation */
.loading-results {
    display: flex;
    justify-content: center;
    padding: 3rem;
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border-color);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

## Search Engine Configuration {#search-engines}

### Custom Search Engine
```python
# searx/engines/custom_api.py
from urllib.parse import urlencode
from searx.utils import to_string
from datetime import datetime

# Engine metadata
about = {
    'website': 'https://api.example.com',
    'wikidata_id': None,
    'official_api_documentation': 'https://api.example.com/docs',
    'use_official_api': True,
    'require_api_key': True,
    'results': 'JSON',
}

categories = ['general', 'images']
paging = True
time_range_support = True
safesearch = True

# API configuration
base_url = 'https://api.example.com/v1/'
api_key = 'your-api-key'  # Should be in settings.yml

# Request parameters
def request(query, params):
    """Build the request parameters"""
    
    # Build API parameters
    api_params = {
        'q': query,
        'page': params['pageno'],
        'per_page': 10,
        'lang': params['language'],
        'safe_search': params['safesearch'],
        'api_key': api_key
    }
    
    # Time range mapping
    time_range_map = {
        'day': '1d',
        'week': '7d',
        'month': '30d',
        'year': '365d'
    }
    
    if params['time_range'] in time_range_map:
        api_params['time_range'] = time_range_map[params['time_range']]
    
    # Category-specific parameters
    if params['category'] == 'images':
        api_params['type'] = 'image'
        api_params['size'] = 'large'
    
    params['url'] = base_url + 'search?' + urlencode(api_params)
    params['headers'] = {
        'Accept': 'application/json',
        'User-Agent': 'SearXNG-Cool/1.0'
    }
    
    return params

# Response parsing
def response(resp):
    """Parse the API response"""
    results = []
    
    try:
        json_data = resp.json()
    except:
        return results
    
    # Check for API errors
    if 'error' in json_data:
        raise Exception(f"API Error: {json_data['error']}")
    
    # Parse results
    for item in json_data.get('results', []):
        result = {
            'url': item['url'],
            'title': item['title'],
            'content': item.get('description', ''),
            'publishedDate': parse_date(item.get('date')),
            'template': 'default.html'
        }
        
        # Add image-specific fields
        if item.get('type') == 'image':
            result.update({
                'img_src': item['image_url'],
                'thumbnail_src': item.get('thumbnail_url', item['image_url']),
                'resolution': f"{item.get('width', 0)}x{item.get('height', 0)}",
                'template': 'images.html'
            })
        
        # Add custom metadata
        if 'metadata' in item:
            result['metadata'] = item['metadata']
        
        results.append(result)
    
    return results

def parse_date(date_str):
    """Parse date string to datetime"""
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return None
```

### Engine Testing
```python
# tests/test_custom_engine.py
import pytest
from searx.engines import custom_api
from searx.testing import SearxTestCase

class TestCustomEngine(SearxTestCase):
    def test_request_params(self):
        params = {
            'pageno': 1,
            'language': 'en-US',
            'safesearch': 1,
            'time_range': 'week',
            'category': 'general'
        }
        
        query = 'test query'
        request_params = custom_api.request(query, params)
        
        assert 'url' in request_params
        assert 'q=test+query' in request_params['url']
        assert 'page=1' in request_params['url']
        assert 'time_range=7d' in request_params['url']
    
    def test_response_parsing(self):
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [
                {
                    'url': 'https://example.com',
                    'title': 'Test Result',
                    'description': 'Test description',
                    'date': '2024-01-01'
                }
            ]
        }
        
        results = custom_api.response(mock_response)
        
        assert len(results) == 1
        assert results[0]['url'] == 'https://example.com'
        assert results[0]['title'] == 'Test Result'
        assert results[0]['content'] == 'Test description'
```

## Plugin Development {#plugin-development}

### Plugin Structure
```python
# searx/plugins/content_filter.py
from flask_babel import gettext
from searx import settings
from searx.plugins import logger

name = gettext('Content Filter')
description = gettext('Filters unwanted content from search results')
default_on = True
preference_section = 'general'

# Plugin settings
plugin_settings = {
    'blocked_domains': [],
    'blocked_keywords': [],
    'content_filters': []
}

def pre_search(request, search):
    """Modify search before execution"""
    # Add negative keywords to query
    blocked_keywords = plugin_settings.get('blocked_keywords', [])
    if blocked_keywords:
        search.query = f"{search.query} -{' -'.join(blocked_keywords)}"
    
    return True

def post_search(request, search):
    """Filter results after search"""
    filtered_results = []
    blocked_domains = plugin_settings.get('blocked_domains', [])
    
    for result in search.result_container.get_ordered_results():
        # Check blocked domains
        if any(domain in result['url'] for domain in blocked_domains):
            logger.debug(f"Filtered result from blocked domain: {result['url']}")
            continue
        
        # Check content filters
        if not passes_content_filter(result):
            continue
        
        filtered_results.append(result)
    
    # Update results
    search.result_container._results = filtered_results
    return True

def passes_content_filter(result):
    """Check if result passes content filters"""
    filters = plugin_settings.get('content_filters', [])
    
    for filter_rule in filters:
        if filter_rule['type'] == 'regex':
            import re
            pattern = re.compile(filter_rule['pattern'], re.IGNORECASE)
            
            if pattern.search(result.get('content', '')):
                return False
            
            if pattern.search(result.get('title', '')):
                return False
    
    return True

def on_result(request, search, result):
    """Process individual result"""
    # Add custom scoring
    result['score'] = calculate_result_score(result)
    
    # Add badges
    if is_trusted_source(result['url']):
        result['badges'] = result.get('badges', [])
        result['badges'].append({
            'label': 'Trusted',
            'color': 'green'
        })
    
    return True

def calculate_result_score(result):
    """Calculate custom result score"""
    score = 0
    
    # HTTPS bonus
    if result['url'].startswith('https://'):
        score += 10
    
    # Domain reputation
    trusted_domains = ['wikipedia.org', 'github.com', 'stackoverflow.com']
    for domain in trusted_domains:
        if domain in result['url']:
            score += 20
            break
    
    return score

def is_trusted_source(url):
    """Check if URL is from trusted source"""
    trusted_sources = settings.get('plugins.content_filter.trusted_sources', [])
    return any(source in url for source in trusted_sources)
```

### Plugin Configuration
```yaml
# Plugin settings in settings.yml
enabled_plugins:
  - 'Hash plugin'
  - 'Self Informations'
  - 'Tracker URL remover'
  - 'Content Filter'  # Custom plugin

plugins:
  content_filter:
    blocked_domains:
      - spam-domain.com
      - malware-site.net
    blocked_keywords:
      - spam
      - adult
    content_filters:
      - type: regex
        pattern: 'casino|lottery|viagra'
    trusted_sources:
      - wikipedia.org
      - github.com
      - stackoverflow.com
      - arxiv.org
```

## Performance Optimization {#performance-optimization}

### Caching Configuration
```python
# searx/cache/redis_cache.py
import redis
import pickle
from datetime import timedelta
from searx import settings

class RedisCache:
    def __init__(self):
        self.client = redis.Redis.from_url(
            settings['redis']['url'],
            decode_responses=False
        )
        self.ttl = timedelta(minutes=10)
    
    def get_search_results(self, query, engines, **kwargs):
        """Get cached search results"""
        cache_key = self._generate_cache_key(query, engines, **kwargs)
        
        cached = self.client.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        return None
    
    def set_search_results(self, query, engines, results, **kwargs):
        """Cache search results"""
        cache_key = self._generate_cache_key(query, engines, **kwargs)
        
        self.client.setex(
            cache_key,
            self.ttl,
            pickle.dumps(results)
        )
    
    def _generate_cache_key(self, query, engines, **kwargs):
        """Generate cache key from search parameters"""
        key_parts = [
            'search',
            query.lower().strip(),
            ','.join(sorted(engines)),
            kwargs.get('language', 'all'),
            str(kwargs.get('pageno', 1)),
            kwargs.get('time_range', 'all'),
            str(kwargs.get('safesearch', 0))
        ]
        
        return ':'.join(key_parts)
    
    def invalidate_pattern(self, pattern):
        """Invalidate cache entries matching pattern"""
        for key in self.client.scan_iter(match=f"search:{pattern}*"):
            self.client.delete(key)
```

### Async Engine Requests
```python
# searx/search/processors/async_processor.py
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from searx.engines import engines

class AsyncSearchProcessor:
    def __init__(self, timeout=3.0):
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=20)
    
    async def search(self, query, engine_list):
        """Perform async search across multiple engines"""
        tasks = []
        
        async with aiohttp.ClientSession() as session:
            for engine_name in engine_list:
                engine = engines[engine_name]
                
                if hasattr(engine, 'request_async'):
                    # Async engine
                    task = self.search_async_engine(
                        session, query, engine
                    )
                else:
                    # Sync engine wrapped in executor
                    task = self.search_sync_engine(
                        query, engine
                    )
                
                tasks.append(task)
            
            # Wait for all results with timeout
            results = await asyncio.gather(
                *tasks,
                return_exceptions=True
            )
        
        return self.merge_results(results)
    
    async def search_async_engine(self, session, query, engine):
        """Search using async engine"""
        try:
            params = await engine.request_async(query)
            
            async with session.get(
                params['url'],
                headers=params.get('headers', {}),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                
                resp_text = await response.text()
                results = await engine.response_async(resp_text)
                
                return {
                    'engine': engine.name,
                    'results': results,
                    'response_time': response.headers.get('X-Response-Time')
                }
                
        except Exception as e:
            return {
                'engine': engine.name,
                'error': str(e),
                'results': []
            }
    
    async def search_sync_engine(self, query, engine):
        """Wrap sync engine in async"""
        loop = asyncio.get_event_loop()
        
        try:
            # Run sync engine in executor
            result = await loop.run_in_executor(
                self.executor,
                self.run_sync_search,
                query,
                engine
            )
            return result
            
        except Exception as e:
            return {
                'engine': engine.name,
                'error': str(e),
                'results': []
            }
    
    def run_sync_search(self, query, engine):
        """Run synchronous engine search"""
        # This runs in thread pool
        params = engine.request(query, {})
        # Make HTTP request
        response = make_request(params)
        results = engine.response(response)
        
        return {
            'engine': engine.name,
            'results': results
        }
    
    def merge_results(self, engine_results):
        """Merge and rank results from all engines"""
        all_results = []
        
        for engine_result in engine_results:
            if isinstance(engine_result, dict) and 'results' in engine_result:
                for result in engine_result['results']:
                    result['engine'] = engine_result['engine']
                    all_results.append(result)
        
        # Deduplicate and rank
        return self.rank_results(self.deduplicate(all_results))
```

## Privacy Settings {#privacy-settings}

### Privacy Configuration
```yaml
# Privacy-focused settings.yml
privacy:
    # Disable all tracking
    enable_metrics: false
    
    # Don't save queries
    query_log: false
    
    # Don't use autocomplete that sends data externally
    autocomplete: ""
    
    # Disable cookies
    cookies:
        enabled: false
    
    # Image proxy to prevent IP leaks
    image_proxy: true
    
    # Result proxy settings
    result_proxy:
        url: http://localhost:8889/proxy
        key: "your-proxy-key"
    
    # HTTP headers for privacy
    http_headers:
        DNT: "1"
        X-Forwarded-For: ""  # Don't forward real IP

# Engine-specific privacy settings
engines:
  - name: google
    tokens: []  # No tokens to prevent tracking
    cookies:
      disable: true
    headers:
      Cookie: ""
      
  - name: duckduckgo
    safe_search: 1
    no_redirect: true  # Prevent redirect tracking
```

### Privacy Proxy
```python
# searx/proxy/privacy_proxy.py
from flask import Blueprint, request, Response
import requests
from urllib.parse import urlparse

proxy_bp = Blueprint('proxy', __name__)

@proxy_bp.route('/proxy')
def proxy_request():
    """Proxy requests to hide user IP"""
    target_url = request.args.get('url')
    
    if not is_url_allowed(target_url):
        return "Forbidden", 403
    
    # Strip tracking parameters
    target_url = strip_tracking_params(target_url)
    
    # Make request with privacy headers
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': request.headers.get('Accept', '*/*'),
        'Accept-Language': 'en-US,en;q=0.9',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Remove identifying headers
    for header in ['Cookie', 'X-Forwarded-For', 'X-Real-IP']:
        headers.pop(header, None)
    
    try:
        resp = requests.get(
            target_url,
            headers=headers,
            timeout=10,
            allow_redirects=False,
            stream=True
        )
        
        # Stream response
        def generate():
            for chunk in resp.iter_content(chunk_size=4096):
                yield chunk
        
        # Build response
        excluded_headers = [
            'connection', 'content-encoding', 
            'content-length', 'transfer-encoding'
        ]
        
        headers = [
            (name, value) for name, value in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        
        return Response(
            generate(),
            resp.status_code,
            headers
        )
        
    except Exception as e:
        return f"Proxy error: {str(e)}", 500

def is_url_allowed(url):
    """Check if URL is allowed for proxying"""
    parsed = urlparse(url)
    
    # Block local URLs
    if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
        return False
    
    # Block private IPs
    import ipaddress
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private:
            return False
    except:
        pass
    
    return True

def strip_tracking_params(url):
    """Remove tracking parameters from URL"""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'mc_eid', '_ga'
    ]
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    # Remove tracking parameters
    for param in tracking_params:
        params.pop(param, None)
    
    # Rebuild URL
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def get_random_user_agent():
    """Get random user agent for privacy"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    ]
    
    import random
    return random.choice(user_agents)
```

## API Integration {#api-integration}

### RESTful API
```python
# searx/api/v1.py
from flask import Blueprint, jsonify, request
from searx.search import SearchQuery, Search
from searx.engines import engines

api_v1 = Blueprint('api_v1', __name__)

@api_v1.route('/search')
def search():
    """API endpoint for search"""
    # Get parameters
    query = request.args.get('q', '')
    engines_list = request.args.getlist('engines') or ['google', 'duckduckgo']
    language = request.args.get('language', 'en-US')
    pageno = int(request.args.get('page', 1))
    time_range = request.args.get('time_range', '')
    safesearch = int(request.args.get('safesearch', 0))
    
    # Validate
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    # Create search query
    search_query = SearchQuery(
        query=query,
        engines=engines_list,
        lang=language,
        pageno=pageno,
        time_range=time_range,
        safesearch=safesearch
    )
    
    # Perform search
    search = Search(search_query)
    results = search.search()
    
    # Format response
    return jsonify({
        'query': query,
        'results': format_results(results),
        'suggestions': results.suggestions,
        'infoboxes': results.infoboxes,
        'number_of_results': results.number_of_results,
        'search_time': results.search_time
    })

def format_results(results):
    """Format results for API response"""
    formatted = []
    
    for result in results:
        formatted.append({
            'title': result.get('title', ''),
            'url': result.get('url', ''),
            'content': result.get('content', ''),
            'engine': result.get('engine', ''),
            'score': result.get('score', 0),
            'publishedDate': result.get('publishedDate', ''),
            'thumbnail': result.get('img_src', ''),
            'metadata': result.get('metadata', {})
        })
    
    return formatted

@api_v1.route('/engines')
def list_engines():
    """List available engines"""
    engine_list = []
    
    for engine_name, engine in engines.items():
        engine_list.append({
            'name': engine_name,
            'categories': engine.categories,
            'shortcut': engine.shortcut,
            'timeout': engine.timeout,
            'disabled': engine.disabled,
            'language_support': engine.language_support,
            'paging': engine.paging,
            'safesearch': engine.safesearch,
            'time_range_support': engine.time_range_support
        })
    
    return jsonify({
        'engines': engine_list,
        'categories': list(categories)
    })

@api_v1.route('/suggestions')
def suggestions():
    """Get search suggestions"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'suggestions': []})
    
    # Get suggestions from engines
    suggestions = get_suggestions(query)
    
    return jsonify({
        'query': query,
        'suggestions': suggestions
    })
```

## Monitoring & Debugging {#monitoring-debugging}

### Performance Metrics
```python
# searx/metrics/collector.py
import time
from collections import defaultdict
from datetime import datetime, timedelta

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.engine_stats = defaultdict(lambda: {
            'requests': 0,
            'errors': 0,
            'total_time': 0,
            'timeouts': 0
        })
    
    def record_search(self, query, results_count, search_time):
        """Record search metrics"""
        self.metrics['searches'].append({
            'timestamp': datetime.utcnow(),
            'query_length': len(query),
            'results_count': results_count,
            'search_time': search_time
        })
        
        # Clean old metrics
        self.clean_old_metrics()
    
    def record_engine_response(self, engine_name, response_time, error=None):
        """Record engine response metrics"""
        stats = self.engine_stats[engine_name]
        stats['requests'] += 1
        
        if error:
            stats['errors'] += 1
            if 'timeout' in str(error).lower():
                stats['timeouts'] += 1
        else:
            stats['total_time'] += response_time
    
    def get_metrics_summary(self):
        """Get metrics summary"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        recent_searches = [
            s for s in self.metrics['searches']
            if s['timestamp'] > hour_ago
        ]
        
        if not recent_searches:
            return {
                'searches_per_hour': 0,
                'avg_search_time': 0,
                'avg_results_count': 0
            }
        
        return {
            'searches_per_hour': len(recent_searches),
            'avg_search_time': sum(s['search_time'] for s in recent_searches) / len(recent_searches),
            'avg_results_count': sum(s['results_count'] for s in recent_searches) / len(recent_searches),
            'engine_stats': dict(self.engine_stats)
        }
    
    def clean_old_metrics(self):
        """Remove metrics older than 24 hours"""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        for key in self.metrics:
            self.metrics[key] = [
                m for m in self.metrics[key]
                if m['timestamp'] > cutoff
            ]
```

### Debug Mode
```python
# searx/debug/debugger.py
from flask import g, request
import logging
import json

class SearchDebugger:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        if app.debug:
            app.before_request(self.before_request)
            app.after_request(self.after_request)
            
            # Configure debug logging
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def before_request(self):
        g.request_start_time = time.time()
        g.debug_info = {
            'request': {
                'method': request.method,
                'path': request.path,
                'args': dict(request.args),
                'headers': dict(request.headers)
            },
            'engines': []
        }
    
    def after_request(self, response):
        if hasattr(g, 'debug_info'):
            # Add response info
            g.debug_info['response'] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'duration': time.time() - g.request_start_time
            }
            
            # Log debug info
            logging.debug(json.dumps(g.debug_info, indent=2))
            
            # Add debug header
            response.headers['X-Debug-Info'] = json.dumps({
                'duration': g.debug_info['response']['duration'],
                'engines_used': len(g.debug_info['engines'])
            })
        
        return response
    
    @staticmethod
    def log_engine_request(engine_name, params):
        """Log engine request details"""
        if hasattr(g, 'debug_info'):
            g.debug_info['engines'].append({
                'name': engine_name,
                'params': params,
                'timestamp': time.time()
            })
    
    @staticmethod
    def log_engine_response(engine_name, response_time, results_count, error=None):
        """Log engine response details"""
        if hasattr(g, 'debug_info'):
            for engine in g.debug_info['engines']:
                if engine['name'] == engine_name:
                    engine['response_time'] = response_time
                    engine['results_count'] = results_count
                    engine['error'] = str(error) if error else None
                    break
```

This comprehensive guide covers all aspects of SearXNG integration, customization, and optimization for the SearXNG-Cool project.