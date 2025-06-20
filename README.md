# SearXNG-Cool: Advanced Music Search Aggregator

A sophisticated multi-tier music search aggregation system built on SearXNG, featuring 27+ specialized music search engines, high-performance architecture, and collaborative features.

## 🎵 Features

- **27 Custom Music Search Engines**: Comprehensive coverage across all major music platforms
- **High-Performance Architecture**: EventLet-based orchestrator supporting 10,000+ concurrent connections
- **Multi-Source Aggregation**: Unified search across Spotify, Apple Music, YouTube Music, SoundCloud, and more
- **PostgreSQL Integration**: Full-featured database for user libraries, playlists, and discovery
- **Intelligent Caching**: Redis-powered caching and rate limiting
- **Collaborative Features**: Shared playlists, voting, and music discovery sessions
- **Production-Ready**: nginx reverse proxy, load balancing, and deployment automation

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│    nginx    │────▶│ Orchestrator │────▶│  SearXNG    │
└─────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                           │                     │                     │
                           ▼                     ▼                     ▼
                    ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
                    │Load Balance │     │    Redis     │     │ 27 Engines  │
                    └─────────────┘     └──────────────┘     └─────────────┘
                                                 │
                                                 ▼
                                        ┌──────────────┐
                                        │  PostgreSQL  │
                                        └──────────────┘
```

## 🎸 Music Engines

### Streaming Platforms
- **Spotify** (API + Web scraping)
- **Apple Music Web**
- **YouTube Music**
- **Tidal Web**
- **Deezer**
- **SoundCloud** (Standard + Enhanced)
- **Yandex Music**

### Music Databases
- **MusicBrainz** - Open music encyclopedia
- **Last.fm** - Music discovery and stats
- **Discogs** - Music database and marketplace
- **AllMusic** - Music reviews and metadata

### Specialized Sources
- **Beatport** - Electronic music
- **Bandcamp** (Standard + Enhanced) - Independent artists
- **Mixcloud** (Standard + Enhanced) - DJ mixes and radio
- **Radio Paradise** - Curated radio stations
- **Genius** - Lyrics and annotations
- **Pitchfork** - Music journalism
- **Free Music Archive** - Open licensed music
- **Jamendo** - Creative Commons music
- **Musixmatch** - Lyrics database
- **Archive.org Audio** - Historical recordings

## 📋 Requirements

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- nginx
- 2GB+ RAM recommended

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/searxng-cool.git
cd searxng-cool
```

### 2. Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r orchestrator/requirements.txt
```

### 3. Configure Services
```bash
cp config/.env.example .env
# Edit .env with your API keys and settings
```

### 4. Set Up Database
```bash
# Ensure PostgreSQL is running
sudo systemctl start postgresql

# Run migrations
cd migrations
alembic upgrade head
```

### 5. Start Services
```bash
# Start Redis
sudo systemctl start redis

# Start SearXNG Core
cd searxng-core/searxng-core
python searx/webapp.py &

# Start Orchestrator
cd ../../orchestrator
python app_eventlet_optimized.py &
```

### 6. Configure nginx
```bash
sudo cp config/nginx-searxng-cool-advanced.conf /etc/nginx/sites-available/searxng-cool
sudo ln -s /etc/nginx/sites-available/searxng-cool /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 📁 Project Structure

```
searxng-cool/
├── orchestrator/          # Flask-SocketIO API server
│   ├── blueprints/       # API endpoints
│   ├── services/         # Business logic
│   └── models/           # Database models
├── searxng-core/         # Modified SearXNG instance
│   └── searx/engines/    # 27 custom music engines
├── music/                # Music-specific components
│   ├── cache/           # Caching implementation
│   └── rate_limiter/    # Rate limiting
├── config/              # Configuration files
├── scripts/             # Deployment automation
├── migrations/          # Database migrations
└── docs/               # Documentation
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:
```bash
# Database
DATABASE_URL=postgresql://searxng_user:searxng_music_2024@localhost/searxng_cool_music

# Redis
REDIS_URL=redis://localhost:6379

# API Keys (optional, for enhanced features)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
GENIUS_API_KEY=your_genius_api_key
```

### Music Engine Configuration
Engines can be configured in `searxng-core/searxng-core/searx/settings.yml`

## 🚢 Deployment

### Production Deployment
```bash
./scripts/deployment/sync_to_production.sh
```

### Docker Deployment (Coming Soon)
```bash
docker-compose up -d
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the AGPL-3.0 License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built on [SearXNG](https://github.com/searxng/searxng)
- Inspired by the need for unified music search
- Thanks to all music platform APIs and services

## 📞 Support

- Create an issue for bug reports
- Discussions for feature requests
- Wiki for documentation

---

**Note**: This project aggregates search results from various music platforms. Please respect the terms of service of each platform and use responsibly.