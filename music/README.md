# Music Platform Components

This directory contains all music-specific components for SearXNG Cool.

## Directory Structure

```
music/
├── README.md                 # This file
├── engines/                  # SearXNG search engine plugins
│   ├── __init__.py
│   ├── music_meta.py        # Multi-source aggregator
│   ├── bandcamp.py          # Bandcamp search
│   ├── soundcloud.py        # SoundCloud search
│   └── youtube_music.py     # YouTube Music search
├── services/                 # Core music services
│   ├── __init__.py
│   ├── audio_analyzer.py    # BPM, key detection
│   ├── playlist_manager.py  # Playlist CRUD operations
│   ├── recommendation.py    # Music recommendation engine
│   └── cache_service.py     # Multi-tier caching
├── models/                   # Database models
│   ├── __init__.py
│   ├── track.py             # Universal track model
│   ├── playlist.py          # Playlist model
│   └── user_library.py      # User collections
├── api/                      # API endpoints
│   ├── __init__.py
│   ├── search.py            # Search endpoints
│   ├── playlists.py         # Playlist management
│   └── discovery.py         # Discovery tools
├── websocket/               # Real-time features
│   ├── __init__.py
│   ├── collaborative.py     # Collaborative editing
│   └── music_room.py        # Shared listening
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── deduplication.py    # Track deduplication
│   ├── export.py           # Export utilities
│   └── import.py           # Import utilities
└── tests/                   # Test suite
    ├── __init__.py
    ├── test_search.py
    ├── test_playlist.py
    └── test_discovery.py
```

## Quick Start

1. Install music-specific dependencies:
```bash
pip install -r music/requirements.txt
```

2. Run database migrations:
```bash
python manage.py db upgrade
```

3. Start music services:
```bash
python manage.py start_music_services
```

## Development

### Adding a New Music Source

1. Create a new engine in `engines/`
2. Implement the `BaseEngine` interface
3. Register in `engines/__init__.py`
4. Add tests in `tests/`

### Working with Playlists

```python
from music.services import PlaylistManager

pm = PlaylistManager()
playlist = pm.create_playlist("My Dig", user_id)
pm.add_track(playlist.id, track_id)
```

### Audio Analysis

```python
from music.services import AudioAnalyzer

analyzer = AudioAnalyzer()
features = await analyzer.analyze_track(track_url)
print(f"BPM: {features.bpm}, Key: {features.key}")
```

## Testing

Run the music test suite:
```bash
pytest music/tests/
```

## Architecture Notes

- All music operations are async-first
- Heavy operations (audio analysis) use Celery
- Search results are cached aggressively
- Playlists use CRDT for conflict-free collaboration
- Audio fingerprinting prevents duplicates across sources