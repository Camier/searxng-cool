# SearXNG-Cool Music Engines

A collection of custom music search engines for SearXNG, providing comprehensive music discovery across multiple platforms.

## Overview

This repository contains 25+ custom music engines that extend SearXNG with specialized music search capabilities.

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

### Working Engines (15+)
- Last.fm - Music metadata and artist information
- MusicBrainz - Open music encyclopedia
- Discogs - Music database and marketplace
- Jamendo - Free music platform
- Bandcamp - Independent music platform
- SoundCloud - Audio distribution platform
- Genius - Song lyrics and annotations
- And more...

## Configuration

See `config/settings.yml.example` for engine configuration.

## Development

To add a new music engine:
1. Create new engine file in `engines/`
2. Inherit from `base_music.py`
3. Implement required methods
4. Add to settings.yml
5. Test with test suite
