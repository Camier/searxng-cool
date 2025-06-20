# SearXNG Custom Engine Development: Comprehensive Research Findings

## Table of Contents
1. [Engine Architecture & Implementation](#engine-architecture--implementation)
2. [Result Type System & Typification](#result-type-system--typification)
3. [Engine Traits & Configuration](#engine-traits--configuration)
4. [Development Patterns & Best Practices](#development-patterns--best-practices)
5. [Testing & Quality Assurance](#testing--quality-assurance)
6. [Security & Anti-Bot Measures](#security--anti-bot-measures)
7. [Plugin System](#plugin-system)
8. [Internationalization (i18n)](#internationalization-i18n)
9. [Performance Optimization](#performance-optimization)
10. [Hidden Insights & Advanced Techniques](#hidden-insights--advanced-techniques)

## Engine Architecture & Implementation

### Basic Engine Structure
Every SearXNG engine follows a standard pattern with required functions:

```python
# Engine metadata
about = {
    "website": "https://example.com",
    "wikidata_id": "Q12345",
    "official_api_documentation": "https://example.com/api",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON"  # or "HTML"
}

# Engine configuration
categories = ['general']
paging = True
time_range_support = False

def request(query, params):
    """Build request parameters"""
    return params

def response(resp):
    """Parse response and return results"""
    return results
```

### Engine Files Found
Research discovered multiple engine implementations:
- `json_engine.py` - Generic JSON API engine
- `xpath.py` - Generic XPath-based HTML scraping engine
- `pypi.py`, `docker_hub.py`, `stackexchange.py` - API-based engines
- `bandcamp.py`, `soundcloud.py`, `mixcloud.py` - Music engines

## Result Type System & Typification

### Major Refactoring Initiative
SearXNG underwent significant typification refactoring:
- **PR #4424**: "[refactor] typification of SearXNG (MainResult) / result items (part 2)"
- **PR #4183**: "[refactor] typification of SearXNG (initial) / result items (part 1)"

### New Result Type Architecture
```python
from searx.result_types import EngineResults

def response(resp) -> EngineResults:
    res = EngineResults()
    
    # Different result types
    res.add(res.types.MainResult(...))
    res.add(res.types.KeyValue(...))
    res.add(res.types.Answer(...))
    res.add(res.types.Image(...))
    res.add(res.types.Video(...))
    
    return res
```

### Technology Choice
- Uses `msgspec.Struct` for fast serialization with type checking
- Enables future possibilities like distributed engine processing
- IDE support through proper typing

### Result Display Areas
1. **Main area** - Traditional search results
2. **Answer area** - Short answers/instant results
3. **Information area** - Wikipedia excerpts, maps
4. **Suggestions area** - Alternative search terms

## Engine Traits & Configuration

### fetch_traits Function
Used to fetch engine-specific traits from origin engines:

```python
def fetch_traits(engine_traits: EngineTraits):
    """Fetch languages & regions from origin engine"""
    # Fetch supported languages/regions
    # Map to SearXNG's internal representation
    # Update engine_traits object
```

### Configuration in settings.yml
```yaml
- name: example engine
  engine: example
  shortcut: ex
  categories: [general]
  timeout: 5.0
  api_key: 'YOUR_API_KEY'
  disabled: false
  tokens: ['private-token']  # For private engines
  weight: 1
  display_error_messages: true
```

### Private Engines
Engines can be made private using tokens:
```yaml
engines:
  - name: private search
    tokens: ['secret-token-123']
```

## Development Patterns & Best Practices

### Recent Engine Additions/Fixes
- **[feat] engines: add tavily (AI powered)** - PR #4221
- **[fix] engine: core.ac.uk implement API v3** - PR #4503
- **[mod] engine invidious: commented out** - No public API available

### XPath Engine Pattern
For HTML scraping engines:
```yaml
- name: custom scraper
  engine: xpath
  search_url: 'https://site.com/search?q={query}&page={pageno}'
  url_xpath: //a[@class="result-link"]/@href
  title_xpath: //h3[@class="result-title"]
  content_xpath: //p[@class="result-desc"]
```

### Utility Functions
- `eval_xpath()` - Evaluate XPath expressions
- `extract_text()` - Extract text from elements
- Rate limiting helpers
- Header management

## Testing & Quality Assurance

### Testing Challenges
- PR #3599: "Fix unit tests for engines"
- Issue #730: "write tests for token protected engines"
- Testing infrastructure uses pytest with GitHub Actions

### Mock Patterns
While specific test files weren't found, standard patterns include:
- Mocking HTTP responses
- Testing request parameter building
- Validating response parsing
- Edge case handling

## Security & Anti-Bot Measures

### Common Issues
1. **CAPTCHA Problems**
   - `SearxEngineCaptchaException` - 1 day suspension
   - Affects: Startpage, Archive.is, Qwant, Google
   - Issue #2844: "Built-in CAPTCHA solver" discussion

2. **Timeout Errors**
   - `SearxEngineAPIException`
   - `httpx.TimeoutException`
   - Configurable suspension times

### Cloudflare Bypass Techniques
1. **User-Agent Management**
   ```python
   headers = {
       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
   }
   ```

2. **Header Consistency**
   - Match headers with claimed browser
   - Include all expected headers
   - Maintain TLS/HTTP fingerprint consistency

3. **Advanced Techniques**
   - User-agent rotation
   - Proxy rotation
   - Session management
   - Browser automation fallback

### Solutions
- SSH tunnel method for manual CAPTCHA solving
- Cloudscraper Python module
- Header consistency checks
- Rate limiting implementation

## Plugin System

### Plugin Architecture
```python
from searx.plugin import SXNGPlugin

class CustomPlugin(SXNGPlugin):
    # Three main hooks:
    # - pre_search
    # - post_search  
    # - on_result
```

### Built-in Plugins
- Calculator
- Hash generator
- Self info
- Tracker URL remover
- Unit converter
- Ahmia filter
- Tor check

### Plugin Configuration
```yaml
plugins:
  - name: 'searx.plugins.calculator.SXNGPlugin'
    active: true
```

## Internationalization (i18n)

### Babel Integration
- Uses Python Babel for i18n/l10n
- gettext for message catalogs
- CLDR for locale data

### Translation Process
1. Extract strings to `.pot` files
2. Update `.po` files per language
3. Compile to `.mo` files
4. Babel handles locale detection

### Locale Support
- Multiple language support
- RTL language handling
- Date/time/currency formatting
- Dynamic locale switching

## Performance Optimization

### Asynchronous Possibilities
While SearXNG currently uses synchronous requests:
- AsyncIO/aiohttp could provide 70-90% performance improvement
- Cooperative multitasking for concurrent requests
- Connection pooling and keep-alive

### Caching Strategy
**Important**: SearXNG does NOT cache search results for privacy reasons

Current Redis usage:
- IP limiter plugin
- Token storage for some engines
- Future: Non-privacy-invasive caching

### Performance Considerations
- Upstream engine availability impacts performance
- Resource requirements for multiple engine integrations
- Socket connections recommended for public instances
- Load balancing with nginx for scaling

## Hidden Insights & Advanced Techniques

### Undocumented Features

1. **Result Score Manipulation**
   - Engines can provide relevance scores
   - Weight configuration affects result ranking
   - Cross-engine result merging algorithms

2. **Engine Categories Beyond Standard**
   - Custom categories can be defined
   - Category-specific result templates
   - Mixed-category searches

3. **Advanced Request Options**
   ```python
   params['method'] = 'POST'
   params['data'] = {'key': 'value'}
   params['cookies'] = {'session': 'id'}
   params['raise_for_httperror'] = False
   ```

4. **Time Range Mapping**
   ```python
   time_range_map = {
       'day': '24h',
       'week': '7d',
       'month': '30d',
       'year': '365d'
   }
   ```

5. **Safe Search Implementation**
   ```python
   safesearch_map = {0: 'off', 1: 'moderate', 2: 'strict'}
   ```

### Engine Development Tips

1. **Error Handling Patterns**
   ```python
   from searx.exceptions import SearxEngineAPIException
   
   if resp.status_code != 200:
       raise SearxEngineAPIException(f"API error: {resp.status_code}")
   ```

2. **Result Deduplication**
   - Use URL normalization
   - Implement fuzzy matching
   - Consider domain variations

3. **Performance Tricks**
   - Lazy loading for heavy operations
   - Streaming response parsing
   - Partial result returns

4. **Debugging Techniques**
   ```python
   from searx import logger
   engine_logger = logger.getChild('my_engine')
   engine_logger.debug(f"Response: {resp.text[:200]}")
   ```

### Future Directions

1. **Distributed Engine Processing**
   - Typification enables engine isolation
   - Potential for microservice architecture
   - Independent engine scaling

2. **AI Integration**
   - Tavily engine shows AI-powered search trend
   - Answer box enhancements
   - Query understanding improvements

3. **Advanced Scraping**
   - JavaScript rendering support discussions
   - Headless browser integration
   - Dynamic content handling

### Community Resources

1. **Matrix Chat**: #searxng:matrix.org
2. **Development Tracking**: GitHub issues/PRs
3. **Documentation**: docs.searxng.org
4. **Instance Lists**: searx.space

## Conclusion

This research uncovered both documented and undocumented aspects of SearXNG engine development. Key takeaways:

1. **Architecture Evolution**: Moving from dictionary-based to typed results
2. **Privacy First**: No result caching, careful data handling
3. **Extensibility**: Robust plugin system and engine traits
4. **Challenges**: Anti-bot measures, CAPTCHA handling, API changes
5. **Community**: Active development with regular updates

The combination of explicit documentation and hidden patterns provides a comprehensive foundation for advanced engine development in SearXNG.