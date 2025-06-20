# SearXNG-Cool Music Engines Implementation Plan

## Executive Summary
This plan outlines the implementation of 15+ new music engines for SearXNG-Cool, transforming it into a comprehensive music search platform with rich metadata, cross-platform search, and intelligent result aggregation.

## Current State
- **Working Engines**: bandcamp, soundcloud, mixcloud, discogs, jamendo, genius, piped.music, archive.org, youtube
- **Disabled**: Enhanced versions (non-functional), radio browser, youtube music
- **Issues**: Limited platform coverage, basic metadata, no cross-referencing

## Implementation Phases

### Phase 1: Foundation & Quick Wins (Week 1)

#### 1. Base Music Engine Class
Create `/searx/engines/base_music.py`:
```python
class MusicEngineBase:
    def parse_duration(self, duration_str) -> int:
        """Convert various duration formats to milliseconds"""
        
    def normalize_artist(self, artist_str) -> str:
        """Normalize artist names (feat., ft., &, etc.)"""
        
    def extract_year(self, date_str) -> int:
        """Extract year from various date formats"""
        
    def build_thumbnail_url(self, image_id, size='medium') -> str:
        """Build thumbnail URL with size options"""
        
    def rate_limit_wait(self):
        """Implement rate limiting"""
        
    def cache_result(self, key, data, ttl=3600):
        """Cache results with TTL"""
```

#### 2. MusicBrainz Engine
- **API**: https://musicbrainz.org/ws/2/
- **Features**: MBID lookup, artist credits, release info, ISRCs
- **Rate Limit**: 1 req/sec
- **Priority**: CRITICAL (metadata backbone)

#### 3. Last.fm Engine
- **API**: https://ws.audioscrobbler.com/2.0/
- **Features**: Play counts, tags, similar artists, top tracks
- **Auth**: Optional API key
- **Priority**: HIGH (discovery & stats)

#### 4. Deezer Engine
- **API**: https://api.deezer.com/
- **Features**: 30-sec previews, full metadata, charts
- **Rate Limit**: 50 req/5 sec
- **Priority**: HIGH (preview URLs)

### Phase 2: Core Engines (Week 2)

#### 5. Free Music Archive
- **API**: https://freemusicarchive.org/api/v2/
- **Features**: CC-licensed music, download URLs
- **Priority**: MEDIUM (free music)

#### 6. Internet Archive Music
- **Enhancement**: Beyond basic audio search
- **Features**: Live recordings, historical content
- **Priority**: MEDIUM (unique content)

#### 7. Beatport Engine
- **Method**: Web scraping
- **Features**: BPM, key, genre (electronic focus)
- **Priority**: MEDIUM (DJ tools)

#### 8. Boomkat Engine
- **Method**: Web scraping
- **Features**: Independent/experimental music
- **Priority**: LOW (niche content)

### Phase 3: Advanced Integration (Week 3)

#### 9. Spotify Web Search
- **Method**: Public web interface scraping
- **Features**: Popular tracks, artist info
- **Note**: No API key required
- **Priority**: HIGH (popularity data)

#### 10. Apple Music Web
- **Method**: Web scraping
- **Features**: iTunes metadata, preview URLs
- **Priority**: MEDIUM (iOS users)

#### 11. Tidal Web
- **Method**: Web interface parsing
- **Features**: Hi-fi focus, exclusive content
- **Priority**: LOW (audiophile niche)

#### 12. Musixmatch Engine
- **API**: Developer API (free tier)
- **Features**: Lyrics, synchronized lyrics
- **Priority**: MEDIUM (lyrics)

### Phase 4: Specialized Engines (Week 4)

#### 13. Songkick Engine
- **API**: https://api.songkick.com/
- **Features**: Concert dates, tour info
- **Priority**: MEDIUM (live music)

#### 14. Qobuz Engine
- **Method**: Web scraping
- **Features**: Hi-res audio info
- **Priority**: LOW (audiophile)

#### 15. Bandsintown Engine
- **API**: Public API
- **Features**: Concert listings, artist events
- **Priority**: MEDIUM (live events)

## Technical Architecture

### Result Standardization
All engines must return results with this structure:
```python
{
    'url': str,              # Link to track/album
    'title': str,            # Track/album name
    'artist': str,           # Primary artist (normalized)
    'artists': List[str],    # All artists
    'album': str,            # Album name
    'duration_ms': int,      # Duration in milliseconds
    'preview_url': str,      # 30-second preview
    'thumbnail': str,        # Album/artist image
    'release_date': str,     # ISO format date
    'genres': List[str],     # Genres/tags
    'isrc': str,            # International recording code
    'mbid': str,            # MusicBrainz ID
    'engine_data': dict     # Engine-specific metadata
}
```

### Metadata Enrichment Pipeline

```
1. Initial Search → 2. Identifier Collection → 3. Cross-Reference → 4. Enrichment → 5. Aggregation
```

1. **Initial Search**: Query multiple engines in parallel
2. **Identifier Collection**: Gather MBIDs, ISRCs, artist IDs
3. **Cross-Reference**: Match tracks across platforms
4. **Enrichment**: Add metadata from specialized sources
5. **Aggregation**: Merge and rank results

### Caching Strategy
- Artist metadata: 7 days
- Album metadata: 30 days
- Search results: 1 hour
- Enrichment data: 24 hours

## Implementation Guidelines

### Engine Template
```python
# searx/engines/newmusic_engine.py
from searx.engines.base_music import MusicEngineBase
from json import loads
from urllib.parse import quote

about = {
    "website": "https://example-music.com",
    "wikidata_id": "Q12345",
    "official_api_documentation": "https://example-music.com/api",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON"
}

categories = ['music']
paging = True
time_range_support = False

base_url = "https://api.example-music.com/v1"

class NewMusicEngine(MusicEngineBase):
    def request(self, query, params):
        params['url'] = f"{base_url}/search?q={quote(query)}&page={params['pageno']}"
        params['headers'] = {'Accept': 'application/json'}
        return params
    
    def response(self, resp):
        results = []
        data = loads(resp.text)
        
        for item in data.get('tracks', []):
            result = {
                'url': item['url'],
                'title': item['title'],
                'artist': self.normalize_artist(item['artist']),
                'duration_ms': self.parse_duration(item['duration']),
                'preview_url': item.get('preview'),
                'thumbnail': item.get('artwork', {}).get('url'),
                'template': 'music.html'
            }
            results.append(result)
        
        return results

# Instantiate for SearXNG
engine = NewMusicEngine()
request = engine.request
response = engine.response
```

### Testing Requirements
1. Unit tests for request/response functions
2. Mock API responses
3. Integration tests with rate limiting
4. Metadata completeness validation

### Quality Metrics
- Preview URL availability: >80%
- Album artwork coverage: >90%
- MBID match rate: >60%
- Average response time: <2s
- Deduplication accuracy: >95%

## Orchestrator Integration

### Enhanced Music Search Service
```python
class EnhancedMusicSearchService:
    def __init__(self):
        self.metadata_enricher = MetadataEnricher()
        self.result_aggregator = ResultAggregator()
        self.cache = MusicCache()
    
    def search(self, query: str, engines: List[str] = None):
        # 1. Parallel search across engines
        raw_results = self._parallel_search(query, engines)
        
        # 2. Enrich with metadata
        enriched_results = self.metadata_enricher.enrich(raw_results)
        
        # 3. Aggregate and deduplicate
        final_results = self.result_aggregator.aggregate(enriched_results)
        
        # 4. Cache results
        self.cache.store(query, final_results)
        
        return final_results
```

## Success Criteria
- [ ] 15+ working music engines
- [ ] <2 second average search response
- [ ] 90%+ metadata completeness score
- [ ] Robust deduplication system
- [ ] Cross-platform track matching
- [ ] Rich interconnected music data
- [ ] Comprehensive error handling
- [ ] Performance monitoring dashboard

## Timeline
- **Week 1**: Foundation + 3 engines (MusicBrainz, Last.fm, Deezer)
- **Week 2**: 4 more engines + enrichment pipeline
- **Week 3**: 5 more engines + aggregation system
- **Week 4**: Final engines + polish + monitoring

## Next Steps
1. Create base_music.py
2. Implement MusicBrainz engine
3. Set up testing framework
4. Begin enrichment pipeline
5. Document API requirements