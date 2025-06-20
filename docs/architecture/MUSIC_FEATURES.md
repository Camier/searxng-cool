# SearXNG Music Platform - Feature Specifications

## 🎯 Core Philosophy
**Do the basics exceptionally well.** No gimmicks, just reliable tools for serious music lovers.

## 📦 Core Features

### 1. Universal Playlist System

#### Multi-Source Integration
- **YouTube** - Full catalog access
- **SoundCloud** - Underground/indie focus
- **Bandcamp** - Direct artist support
- **Spotify** - Metadata and preview only
- **Mixcloud** - DJ sets and radio shows
- **Direct URLs** - MP3/WAV/FLAC links
- **User Uploads** - Personal collection

#### Unified Track Model
Every track, regardless of source, has:
- **Core Fields**: ID, source, title, artist, duration
- **Extended Metadata**: Album, year, genre, BPM, key
- **Playback Info**: Stream URL, preview, waveform
- **Social Data**: Play count, likes, comments
- **Technical Info**: Bitrate, file size, license

#### Playlist Features
- **Multi-source playlists** - Mix YouTube, SoundCloud, etc in one playlist
- **Smart deduplication** - No duplicate tracks across sources
- **Drag-and-drop reordering** - Intuitive playlist management
- **Batch operations** - Select multiple tracks for actions
- **Collaborative editing** - Real-time multi-user editing
- **Version history** - See who added what and when
- **Export to any format** - M3U, CSV, JSON, Spotify, DJ software

### 2. SOLID Digging Tools

#### Advanced Search
Natural language queries with smart parsing:
```
"jazz 120-130bpm key:Am year:1970-1980"
"label:'Blue Note' country:USA"
"genre:techno detroit -mainstream"
"similar:youtube_dQw4w9WgXcQ bpm:>120"
```

#### Search Filters
- **Musical Properties**
  - BPM range (e.g., 120-130)
  - Key (Am, C, F#m with Camelot notation)
  - Genre with sub-genre support
  - Year/era filtering
  
- **Technical Filters**
  - Duration (3-8 minutes)
  - Audio quality (320kbps, lossless)
  - License type (CC, commercial)
  
- **Discovery Options**
  - Similar tracks
  - Same label catalog
  - Played by specific DJs
  - Sample relationships

#### Digging Sessions
- **Stateful search progression** - Track your digging journey
- **Found/rejected tracking** - Mark tracks as gold, maybe, or no
- **Session notes** - Document what you're looking for
- **Fork sessions** - Start from someone else's dig
- **Export finds** - Convert session to playlist

#### Related Track Discovery
Find similar music using:
- **Audio similarity** - Actual sonic characteristics
- **Same catalog** - Label and artist exploration
- **User patterns** - What others played next
- **Metadata matching** - Genre, era, location

### 3. Social Features (Simple but Complete)

#### Comments
- **Threaded discussions** - Reply to specific comments
- **Track timestamps** - Comment on specific moments
- **Moderation tools** - Report/block/pin comments
- **Rich text** - Basic formatting support

#### Likes & Collections
- **One-click likes** - No complicated rating systems
- **Custom collections** - Organize beyond playlists
- **Saved searches** - Re-run complex queries
- **Dig later** - Bookmark for future exploration

#### Sharing
- **Public playlists** - Share with URL
- **Collaborative playlists** - Invite specific users
- **Embed player** - For blogs/websites
- **Social media integration** - Quick share buttons

### 4. Import/Export Excellence

#### Import From
- **Spotify playlists** - Via public URLs
- **YouTube playlists** - Full import with metadata
- **M3U/PLS files** - Standard playlist formats
- **CSV with columns** - For bulk operations
- **Last.fm history** - Import your scrobbles

#### Export To
- **M3U/M3U8** - Universal playlist format
- **CSV** - Full metadata spreadsheet
- **JSON** - For developers
- **Spotify URIs** - For re-import
- **YouTube URLs** - Share elsewhere
- **Rekordbox XML** - For DJs
- **Serato Crates** - DJ software
- **Traktor NML** - Native format

### 5. Audio Analysis

#### Automatic Detection
- **BPM** - Accurate tempo detection
- **Key** - Musical key and scale
- **Energy** - Track intensity 0-1
- **Waveform** - Visual representation

#### On-Demand Analysis
- **Detailed metrics** - Danceability, valence
- **Spectral analysis** - Frequency content
- **Dynamic range** - Loudness info
- **Section detection** - Intro/verse/chorus

### 6. Performance & Reliability

#### Smart Caching
- **Multi-tier cache** - Memory → Redis → Database
- **API limit handling** - Never hit rate limits
- **Offline mode** - Continue working without internet
- **Background updates** - Refresh data intelligently

#### Playback Reliability
- **Multiple sources** - Fallback if one fails
- **Preview fallback** - Always have something to play
- **Quality selection** - Choose bitrate based on connection
- **Buffering strategy** - Smooth playback

## 🎨 User Interface Principles

### Desktop First, Mobile Friendly
- **Information density** - See more without scrolling
- **Keyboard shortcuts** - Full control without mouse
- **Drag and drop** - Natural interactions
- **Responsive design** - Works on all screens

### Key Views

#### Search Results
- **Compact table view** - Maximum information
- **Inline preview** - Hover to hear
- **Quick actions** - Add to playlist, like, etc
- **Bulk selection** - Shift+click for multiple

#### Playlist Editor
- **Split view** - Search + playlist
- **Inline editing** - Click to edit any field
- **Keyboard navigation** - Arrow keys + shortcuts
- **Live collaboration** - See others' cursors

#### Track Inspector
- **All metadata** - Everything in one panel
- **Related tracks** - One-click discovery
- **Edit history** - Who changed what
- **Quick actions** - All options visible

#### Digging Mode
- **Focused interface** - Minimal distractions
- **Quick marking** - Keyboard shortcuts for gold/maybe/no
- **Session progress** - Visual journey map
- **Auto-expand** - Find more like the good ones

## 📊 Success Metrics

### Performance Targets
- **Search results** < 500ms
- **Track playback** < 1 second
- **Page load** < 2 seconds
- **API response** < 200ms

### Reliability Targets
- **99.9% uptime** - Rock solid
- **Zero data loss** - Everything backed up
- **Graceful degradation** - Works even if services fail
- **Clear error messages** - Know what went wrong

### Usability Targets
- **2 clicks maximum** - For any common action
- **Keyboard alternative** - For every mouse action
- **Undo everything** - Mistakes are okay
- **Batch operations** - Power user features

## 🔧 Technical Requirements

### Backend
- **Python 3.8+** - Modern async support
- **PostgreSQL** - Reliable data storage
- **Redis** - Fast caching
- **Elasticsearch** - Music search
- **Celery** - Background tasks

### Frontend
- **Fast loading** - Minimal JavaScript
- **Progressive enhancement** - Works without JS
- **Semantic HTML** - Accessible by default
- **CSS Grid/Flexbox** - Modern layouts

### APIs
- **RESTful design** - Standard HTTP verbs
- **JSON responses** - Simple and fast
- **Pagination** - Handle large results
- **Rate limiting** - Fair use for all

## 🚀 Future Considerations

### Planned Enhancements
- **Mobile apps** - Native iOS/Android
- **Desktop app** - Electron for offline
- **Browser extension** - Quick add from anywhere
- **API v2** - GraphQL option

### Community Features
- **User radio** - Broadcast your session
- **Group listening** - Sync playback
- **Discovery stats** - Gamification lite
- **Taste matching** - Find similar users

### Never Implement
- ❌ Blockchain/NFT/Crypto
- ❌ AI-generated playlists
- ❌ Mood detection from webcam
- ❌ Social credit scores
- ❌ Advertising/tracking

---

**Focus on reliability. Master the fundamentals. Everything else is secondary.**