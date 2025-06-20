# Changelog

All notable changes to SearXNG-Cool will be documented in this file.

## [2.0.0] - 2025-06-20

### 🎉 Major Restoration Release

This release represents a complete restoration of the SearXNG-Cool architecture after an incorrect consolidation that broke the system.

### Added
- ✅ Restored full multi-tier architecture (nginx → Orchestrator → SearXNG → Engines)
- ✅ Restored Flask-SocketIO orchestrator with WebSocket support
- ✅ Restored Redis message queue integration
- ✅ Restored PostgreSQL database with 21 music-related tables
- ✅ Added comprehensive documentation (README, Installation Guide, Architecture)
- ✅ Added test suites for all components
- ✅ Added deployment automation scripts

### Fixed
- 🔧 Fixed `base_music.py` missing 'key' field error
- 🔧 Fixed Radio Paradise NoneType errors
- 🔧 Fixed Apple Music Web KeyError issues
- 🔧 Fixed Pitchfork timeout issues (increased to 15s)
- 🔧 Fixed missing doi_resolvers configuration
- 🔧 Restored proper directory hierarchy (searxng-core/searxng-core/searx/engines/)

### Changed
- 📝 Updated all 27 music engines with latest fixes
- 📝 Improved error handling in music engines
- 📝 Enhanced caching and rate limiting systems
- 📝 Optimized EventLet configuration for 10,000+ concurrent connections

### Music Engines Status (27 Total)
#### Working Engines (20+)
- ✅ AllMusic
- ✅ Apple Music Web
- ✅ Beatport
- ✅ Deezer
- ✅ Discogs Music
- ✅ Free Music Archive
- ✅ Jamendo
- ✅ Last.fm
- ✅ MusicBrainz
- ✅ Pitchfork
- ✅ Radio Paradise
- ✅ SoundCloud
- ✅ Spotify Web
- ✅ Tidal Web
- ✅ And more...

#### Enhanced Engines
- 🔄 Bandcamp Enhanced
- 🔄 Mixcloud Enhanced
- 🔄 SoundCloud Enhanced

## [1.5.0] - 2025-06-19

### Changed
- Wrongful consolidation that reduced 12,431 files to 44 files (broken state)

## [1.0.0] - 2025-06-18

### Initial Release
- 27 custom music search engines
- Multi-tier architecture with nginx, Flask, and Redis
- PostgreSQL integration for user features
- Collaborative playlist system
- Music discovery features

---

## Version History Summary

- **2.0.0** - Full restoration with all features working
- **1.5.0** - Broken consolidation (avoid this version)
- **1.0.0** - Initial working release