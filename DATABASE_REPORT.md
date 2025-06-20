# SearXNG-Cool Database Report

## Database: searxng_cool_music

### Overview
- **Database**: searxng_cool_music
- **Owner**: searxng_user
- **Connection**: postgresql://searxng_user:searxng_music_2024@localhost/searxng_cool_music
- **Status**: Active and accessible

### Tables Structure (21 tables)

#### Core Music Tables
1. **artists** - Artist information
   - Fields: id, name, musicbrainz_id, spotify_id, bio, genres, social_links, etc.
   - Sample data: 5 artists (Lofi Girl, EDM mixes, etc.)

2. **albums** - Album records
   - Linked to artists
   - Contains metadata and sources

3. **tracks** - Individual tracks
   - Current count: 9 tracks
   - Linked to albums and artists

#### Source Integration Tables
4. **artist_sources** - Links artists to various platforms
5. **album_sources** - Links albums to various platforms  
6. **track_sources** - Links tracks to various platforms

#### User Interaction Tables
7. **users** - User accounts
8. **user_library** - Personal music libraries
9. **user_album_collections** - User's album collections
10. **user_artist_follows** - Followed artists
11. **user_music_profiles** - User preferences
12. **user_interactions** - Activity tracking

#### Playlist System Tables
13. **playlists** - User-created playlists
14. **playlist_tracks** - Tracks in playlists
15. **playlist_collaborators** - Shared playlist access
16. **playlist_follows** - Playlist subscriptions
17. **playlist_track_votes** - Community voting
18. **playlist_activities** - Playlist history

#### Discovery Features
19. **discovery_sessions** - Music discovery sessions
20. **discovery_session_tracks** - Tracks in discovery

#### System
21. **alembic_version** - Database migration tracking

### Key Features Supported
- Multi-source music aggregation (Spotify, MusicBrainz, etc.)
- User libraries and collections
- Collaborative playlists with voting
- Music discovery sessions
- Social features (follows, sharing)
- Rich metadata with JSONB fields

### Integration with SearXNG
The database is designed to:
1. Store aggregated results from 27 music engines
2. Build user profiles and recommendations
3. Enable collaborative music discovery
4. Track cross-platform music sources

### Current Data
- 5 artists loaded (test data)
- 9 tracks in database
- Ready for production use

### Connection Details for Orchestrator
```python
DATABASE_URL = "postgresql://searxng_user:searxng_music_2024@localhost/searxng_cool_music"
```

The database structure fully supports the music search aggregation and social features of SearXNG-Cool!