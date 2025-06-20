# 🎵 Music Engines Implementation Guide

## Overview

This document describes the implementation of 11 specialized music search engines for SearXNG-Cool. The engines provide comprehensive music discovery across various platforms with features like streaming URLs, metadata extraction, and intelligent caching.

## Architecture

### Component Structure

```
searxng-cool/
├── searxng-core/searxng-core/searx/engines/music/
│   ├── __init__.py          # Package initialization
│   ├── base.py             # Base music engine class
│   ├── discogs.py          # Discogs API integration
│   ├── jamendo.py          # Jamendo free music
│   ├── soundcloud.py       # SoundCloud scraping
│   ├── bandcamp.py         # Bandcamp scraping
│   ├── archive_audio.py    # Internet Archive audio
│   ├── mixcloud.py         # MixCloud integration
│   ├── fma.py              # Free Music Archive
│   ├── deezer.py           # Deezer search
│   ├── genius.py           # Genius lyrics
│   ├── radioparadise.py    # Radio Paradise
│   └── youtube_music.py    # YouTube Music
├── music/
│   ├── cache/              # Redis caching layer
│   ├── rate_limiter/       # Rate limiting implementation
│   └── tests/              # Comprehensive test suite
└── config/
    └── music_engines.yml   # Centralized configuration
```

## Core Features

### 1. Base Music Engine (`base.py`)

The `BaseMusicEngine` class provides:

- **Standardized Interface**: All engines inherit common functionality
- **Automatic Caching**: Redis-based result caching with configurable TTL
- **Rate Limiting**: Token bucket algorithm prevents API abuse
- **Result Normalization**: Consistent output format across all engines
- **Error Handling**: Retry logic with exponential backoff
- **Performance Monitoring**: Request timing and success rate tracking

```python
class BaseMusicEngine(ABC):
    def search(self, query: str, params: Dict) -> List[Dict]:
        # Check cache
        # Apply rate limiting
        # Make request with retry
        # Normalize results
        # Cache results
        return normalized_results
```

### 2. Result Format

All engines return results in this standardized format:

```python
{
    "url": "https://example.com/track",
    "title": "Track Name",
    "artist": "Artist Name",
    "content": "Year: 2023 | Format: MP3 | Duration: 3:45",
    "thumbnail": "https://example.com/cover.jpg",
    "duration": 225,  # seconds
    "year": 2023,
    "format": "MP3",
    "source": "jamendo",
    "quality": 0.95,  # 0-1 score
    "playable_url": "https://example.com/stream.mp3",
    "metadata": {
        "genre": ["Electronic", "Ambient"],
        "label": "Record Label",
        "catalog_no": "CAT-001",
        "country": "UK",
        "license": "CC BY-SA 4.0",
        "bpm": 120,
        "key": "A minor"
    }
}
```

## Engine Implementations

### 1. Discogs Engine

**Features:**
- Comprehensive vinyl/CD database
- Marketplace data (want/have ratios)
- Advanced filtering (year, format, country, label)
- Master vs release distinction

**Rate Limit:** 60 requests/minute (authenticated)

**Example Usage:**
```python
engine = DiscogsEngine(config)
results = engine.search("aphex twin", {
    "year": 1992,
    "format": "Vinyl",
    "country": "UK"
})
```

### 2. Jamendo Engine

**Features:**
- Free and legal music streaming
- Creative Commons licensing
- Direct download URLs
- Tag-based filtering
- Multiple audio formats (MP3, OGG, FLAC)

**Rate Limit:** 100 requests/minute

**Special Filters:**
- `vocalinstrumental`: vocal, instrumental, or both
- `acousticelectric`: acoustic, electric, or both  
- `speed`: verylow, low, medium, high, veryhigh
- `durationbetween`: "min_max" in seconds

### 3. SoundCloud Engine

**Features:**
- Web scraping (no API key required)
- Stream URL extraction
- Play count and like statistics
- User profiles and playlists
- Waveform visualization data

**Rate Limit:** 30 requests/minute (self-imposed)

### 4. Bandcamp Engine

**Features:**
- Independent artist focus
- Digital and physical format parsing
- Price extraction
- Label catalog browsing
- Geographic artist data

### 5. Internet Archive Audio

**Features:**
- Massive collection of free audio
- Live concert recordings
- 78 RPM records
- Netlabel releases
- Advanced metadata filtering

**Collections:**
- Live Music Archive
- 78 RPMs and Cylinder Recordings
- Netlabels
- Community Audio

## Caching Strategy

### Redis Cache Implementation

```python
cache_keys = {
    "search": "music:search:{engine}:{query_hash}:{page}",
    "artist": "music:artist:{engine}:{artist_id}",
    "release": "music:release:{engine}:{release_id}",
    "metadata": "music:meta:{engine}:{item_id}"
}

ttl_config = {
    "search_results": 3600,      # 1 hour
    "artist_data": 86400,        # 24 hours  
    "release_data": 604800,      # 1 week
    "static_metadata": 2592000   # 30 days
}
```

### Cache Warming

Popular searches are pre-cached during off-peak hours:

```python
POPULAR_SEARCHES = [
    "electronic", "rock", "jazz", "classical", 
    "hip hop", "techno", "house", "ambient"
]
```

## Rate Limiting

### Token Bucket Algorithm

Each engine has configurable rate limits:

```python
rate_limits = {
    "discogs": {"requests": 60, "period": 60},
    "jamendo": {"requests": 100, "period": 60},
    "soundcloud": {"requests": 30, "period": 60},
    "bandcamp": {"requests": 20, "period": 60}
}
```

### Distributed Rate Limiting

Uses Redis for coordination across multiple workers:

```python
class RateLimiter:
    def acquire(self, engine: str, limit: int, period: int) -> bool:
        # Uses Redis sorted sets for sliding window
        # Returns True if request allowed
```

## Search Enhancement

### Natural Language Processing

Queries are enhanced before searching:

```python
"jazz vinyl from 1960s" → {
    "query": "jazz",
    "format": "vinyl",
    "year_range": "1960-1969"
}
```

### Multi-Engine Aggregation

Parallel searches with deduplication:

```python
async def multi_search(query, engines):
    tasks = [engine.search(query) for engine in engines]
    results = await asyncio.gather(*tasks)
    return deduplicate(merge(results))
```

## Security Considerations

### API Key Management

- Keys stored in environment variables
- Never logged or exposed in errors
- Automatic masking in debug output
- Regular rotation schedule

```python
# Secure loading
api_key = os.environ.get('JAMENDO_API_KEY')
if not api_key:
    logger.warning("API key not configured")
    engine.enabled = False
```

### Input Sanitization

All user queries are sanitized:

```python
def sanitize_query(query: str) -> str:
    # Remove special characters
    # Limit length
    # Escape for APIs
    return clean_query
```

## Performance Optimizations

### 1. Connection Pooling

```python
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10
)
```

### 2. Async Operations

```python
async def parallel_search(engines, query):
    return await asyncio.gather(*[
        engine.search_async(query) 
        for engine in engines
    ])
```

### 3. Result Streaming

Large result sets are streamed:

```python
def stream_results(query):
    for page in range(1, max_pages):
        results = search(query, page)
        yield from results
```

## Testing

### Unit Tests

Comprehensive test coverage for each engine:

```bash
pytest music/tests/ -v --cov=searxng-core/searxng-core/searx/engines/music
```

### Integration Tests

Live API testing with rate limit awareness:

```python
@pytest.mark.integration
def test_live_search():
    engine = DiscogsEngine(live_config)
    results = engine.search("test")
    assert len(results) > 0
```

### Load Testing

Concurrent request handling:

```python
def test_concurrent_searches():
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(search, f"query{i}") 
                  for i in range(100)]
```

## Deployment

### Prerequisites

1. Redis server running
2. API keys configured in `.env`
3. Python dependencies installed

### Deployment Steps

```bash
# Install dependencies
pip install -r requirements_music.txt

# Run tests
pytest music/tests/

# Deploy engines
./deploy_music_engines.sh

# Verify deployment
./verify_music_engines.sh
```

### Configuration

Update `searxng-core/searxng-core/searx/settings.yml`:

```yaml
engines:
  - name: discogs
    engine: music.discogs
    shortcut: disc
    categories: music
    timeout: 10.0
    
  - name: jamendo
    engine: music.jamendo
    shortcut: jam
    categories: music
    timeout: 5.0
```

## Monitoring

### Health Checks

Each engine provides health status:

```python
GET /api/engines/music/status

{
    "discogs": {
        "enabled": true,
        "requests": 1234,
        "success_rate": 0.98,
        "avg_response_time": 0.234,
        "rate_limit_remaining": 45
    }
}
```

### Metrics

- Request count per engine
- Cache hit/miss rates
- Error rates by type
- Response time percentiles

## Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   - Check `X-RateLimit-Remaining` headers
   - Implement exponential backoff
   - Use cache more aggressively

2. **API Key Invalid**
   - Verify environment variables
   - Check key permissions
   - Rotate if compromised

3. **Parsing Errors**
   - Update scraping selectors
   - Handle API version changes
   - Add error recovery

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger('searx.engines.music').setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Audio Fingerprinting**: Deduplicate by audio content
2. **Recommendation Engine**: ML-based similar track suggestions
3. **Playlist Generation**: Auto-create playlists from search results
4. **Social Features**: Share and collaborate on music discovery
5. **Analytics Dashboard**: Track popular searches and trends

## Contributing

To add a new music engine:

1. Create `engine_name.py` in `searx/engines/music/`
2. Inherit from `BaseMusicEngine`
3. Implement `_search()` and `_parse_response()`
4. Add configuration to `music_engines.yml`
5. Write tests in `music/tests/test_engine_name.py`
6. Update documentation

## License

The music engines are released under the same AGPL-3.0 license as SearXNG-Cool.