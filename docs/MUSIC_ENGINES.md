# SearXNG-Cool Music Engines Documentation

## Overview
SearXNG-Cool includes 27 specialized music search engines that aggregate results from various music platforms, databases, and services.

## Engine Categories

### 🎵 Streaming Platforms

#### Spotify (2 engines)
- **spotify.py** - Uses Spotify Web API (requires API credentials)
- **spotify_web.py** - Web scraping fallback (no API needed)
- Features: Albums, artists, tracks, playlists

#### Apple Music Web
- **apple_music_web.py** - Scrapes Apple Music website
- Features: Albums, artists, songs
- Note: Uses base_music.py for result standardization

#### YouTube Music
- **youtube_music.py** - YouTube Music search
- Features: Songs, albums, artists, playlists
- Status: Disabled by default

#### Tidal Web
- **tidal_web.py** - Tidal streaming service
- Features: High-quality audio results
- Region: Best results in US/EU

#### Deezer
- **deezer.py** - Deezer music streaming
- Features: Tracks, albums, artists
- API: Public search API

#### Yandex Music
- **yandex_music.py** - Russian music service
- Features: Cyrillic search support
- Status: Disabled by default

### 🎸 Music Databases

#### MusicBrainz
- **musicbrainz.py** - Open music encyclopedia
- Features: Detailed metadata, relationships
- API: Public, no key required

#### Last.fm
- **lastfm.py** - Music discovery and stats
- Features: Similar artists, tags, charts
- Timeout: 10 seconds

#### Discogs
- **discogs_music.py** - Music database and marketplace
- Features: Releases, artists, labels
- Uses: BaseMusicEngine class

#### AllMusic
- **allmusic.py** - Music reviews and metadata
- Features: Reviews, ratings, biographies
- Scraping: BeautifulSoup based

### 🎤 Independent & DJ Platforms

#### Bandcamp (2 engines)
- **bandcamp.py** - Standard search
- **bandcamp_enhanced.py** - Extended features
- Features: Independent artists, direct support

#### SoundCloud (2 engines)
- **soundcloud.py** - Standard search
- **soundcloud_enhanced.py** - Advanced features
- Features: Remixes, DJ sets, podcasts

#### Mixcloud (2 engines)
- **mixcloud.py** - Standard search
- **mixcloud_enhanced.py** - Enhanced results
- Features: DJ mixes, radio shows

### 🎼 Specialized Sources

#### Beatport
- **beatport.py** - Electronic music focus
- Features: BPM, key, genre classification
- Timeout: 15 seconds

#### Genius (2 engines)
- **genius.py** - General search
- **genius_lyrics.py** - Lyrics focus
- Features: Annotations, meanings

#### Pitchfork
- **pitchfork.py** - Music journalism
- Features: Reviews, news, features
- Timeout: 15 seconds (increased from 5s)

#### Radio Paradise
- **radio_paradise.py** - Curated radio
- Features: Now playing, history
- Fixed: NoneType errors in album search

### 🎵 Free & Open Music

#### Free Music Archive
- **free_music_archive.py** - CC licensed music
- Features: Legal downloads, various licenses

#### Jamendo
- **jamendo_music.py** - Creative Commons music
- Features: Free streaming, licensing options

#### Archive.org Audio
- **archive_audio.py** - Historical recordings
- Features: Public domain, live concerts

#### Musixmatch
- **musixmatch.py** - Lyrics database
- Features: Synchronized lyrics, translations

### 🎧 Utility Engines

#### Base Music Engine
- **base_music.py** - Base class for standardization
- Features: 
  - Automatic 'key' field generation
  - Result validation
  - Error handling
  - Common methods for all music engines

## Configuration

### Enable/Disable Engines
In `settings.yml`:
```yaml
- name: spotify web
  engine: spotify_web
  categories: music
  disabled: false  # Set to true to disable
```

### Timeout Settings
Adjust timeouts for slow engines:
```yaml
- name: pitchfork
  timeout: 15.0  # Increased for reliability
```

### API Keys
Some engines work better with API keys:
```yaml
# In .env or settings
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret
GENIUS_API_KEY=your_key
```

## Usage Examples

### Search All Music Engines
```
!music queen bohemian rhapsody
```

### Search Specific Engine
```
!spotify bohemian rhapsody
!musicbrainz pink floyd
!beatport techno 130bpm
```

### Advanced Queries
```
!genius "lyrics:stairway to heaven"
!bandcamp "tag:synthwave"
!soundcloud "remix calvin harris"
```

## Engine Status

### ✅ Fully Working (20+)
Most engines work out of the box without configuration

### ⚠️ Requires Configuration (3-4)
- Spotify API (needs credentials)
- Some regional engines (Yandex)

### 🔧 Enhanced Versions
Enhanced engines provide additional features but may be slower

## Troubleshooting

### Common Issues
1. **Timeout errors**: Increase timeout in settings.yml
2. **No results**: Check if engine is disabled
3. **API errors**: Verify API keys are set
4. **Scraping fails**: Site may have changed layout

### Debug Mode
Enable debug logging:
```python
# In settings.yml
general:
  debug: true
```

## Contributing New Engines

### Using BaseMusicEngine
```python
from searx.engines.base_music import BaseMusicEngine

class MyMusicEngine(BaseMusicEngine):
    def parse_results(self, response):
        # Your parsing logic
        return results
```

### Standard Result Format
```python
{
    'url': 'https://...',
    'title': 'Song Title',
    'content': 'Artist - Album',
    'thumbnail': 'https://...',
    'key': 'unique_id',  # Auto-generated if missing
    'publishedDate': datetime,
    'metadata': {
        'artist': 'Artist Name',
        'album': 'Album Name',
        'duration': '3:45'
    }
}
```