# SearXNG-Cool Music Engines

A focused collection of 27 custom music search engines for SearXNG, providing comprehensive music discovery across multiple platforms.

## Overview

This repository contains custom music engines that extend SearXNG with specialized music search capabilities. Originally part of a larger 12,000+ file project, this has been consolidated to just the essential custom engines for easier maintenance and deployment.

## Structure

```
├── engines/          # Custom music search engines
├── scripts/          # Deployment and utility scripts
├── tests/            # Engine test suite
├── config/           # Configuration examples
└── docs/             # Documentation
```

## Deployment

```bash
# Sync engines to production SearXNG instance
./scripts/deploy/sync_to_production.sh

# Test all engines
python tests/test_all_music_engines.py
```

## Music Engines

### All 27 Music Engines

**Metadata & Information:**
- Last.fm - Music metadata and artist information
- MusicBrainz - Open music encyclopedia  
- AllMusic - Music reviews and metadata
- Discogs - Music database and marketplace
- Genius - Song lyrics and annotations

**Streaming & Discovery:**
- Spotify Web - Music metadata (no playback)
- Deezer - Music streaming service data
- SoundCloud - Audio distribution platform
- YouTube Music - Music videos and tracks
- Apple Music Web - Music catalog data
- Tidal Web - High-fidelity music data

**Independent & Free Music:**
- Bandcamp - Independent music platform
- Jamendo - Free music platform
- Free Music Archive - Open music library

**Specialized Engines:**
- Beatport - Electronic music
- Mixcloud - DJ mixes and radio shows
- Pitchfork - Music reviews
- Radio Paradise - Curated radio
- Musixmatch - Lyrics database

**Enhanced Versions:**
- Bandcamp Enhanced
- SoundCloud Enhanced  
- Mixcloud Enhanced
- Genius Lyrics (focused version)

## Configuration

See `config/settings.yml.example` for engine configuration.

## Development

To add a new music engine:
1. Create new engine file in `engines/`
2. Inherit from `base_music.py`
3. Implement required methods
4. Add to settings.yml
5. Test with test suite
