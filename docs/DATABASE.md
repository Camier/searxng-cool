# SearXNG-Cool Database Architecture

## Overview

SearXNG-Cool uses a production-grade PostgreSQL database with comprehensive optimization for music platform operations. The database implements zero technical debt patterns with proper migration management, performance indexing, and monitoring capabilities.

## Architecture Decisions

### Database Engine
- **PostgreSQL 14+**: Chosen for JSONB support, full-text search, and advanced indexing
- **Connection**: Unix socket for optimal performance
- **Encoding**: UTF-8 for international character support
- **Timezone**: UTC for consistency across deployments

### Schema Design Principles
1. **Normalized Structure**: Separate entities for artists, albums, tracks, and users
2. **Flexible Metadata**: JSONB fields for evolving data requirements
3. **Performance First**: Comprehensive indexing strategy
4. **Data Integrity**: Foreign key constraints and check constraints
5. **Audit Trail**: Timestamp tracking with automatic updates

## Core Tables

### Music Content Tables

#### `artists`
Primary artist information with metadata support.
```sql
- id: SERIAL PRIMARY KEY
- name: VARCHAR(255) NOT NULL
- musicbrainz_id: VARCHAR(36) UNIQUE
- genres: JSONB              -- Flexible genre classification
- aliases: JSONB             -- Alternative names
- social_links: JSONB        -- Social media and websites
- popularity: FLOAT          -- Calculated popularity score
- country: VARCHAR(2)        -- ISO country code
- search_vector: TEXT        -- Full-text search optimization
- created_at, updated_at: TIMESTAMP
```

#### `albums`
Album information with rich metadata.
```sql
- id: SERIAL PRIMARY KEY
- title: VARCHAR(255) NOT NULL
- artist_id: INTEGER REFERENCES artists(id)
- musicbrainz_id: VARCHAR(36) UNIQUE
- album_type: VARCHAR(50)    -- album, single, compilation, etc.
- release_date: DATE
- total_tracks: INTEGER
- genres: JSONB
- credits: JSONB             -- Producer, engineer, etc.
- cover_url variants: TEXT   -- Multiple resolution covers
- search_vector: TEXT
- created_at, updated_at: TIMESTAMP
```

#### `tracks`
Individual track information with audio features.
```sql
- id: SERIAL PRIMARY KEY
- title: VARCHAR(255) NOT NULL
- artist_id: INTEGER REFERENCES artists(id)
- album_id: INTEGER REFERENCES albums(id)
- track_number: INTEGER
- duration_ms: INTEGER
- audio_features: JSONB      -- Energy, danceability, valence, etc.
- lyrics: TEXT
- isrc: VARCHAR(12)          -- International Standard Recording Code
- popularity: FLOAT
- search_vector: TEXT
- created_at, updated_at: TIMESTAMP
```

### User & Interaction Tables

#### `users`
User account and profile information.
```sql
- id: SERIAL PRIMARY KEY
- username: VARCHAR(50) UNIQUE NOT NULL
- email: VARCHAR(255) UNIQUE NOT NULL
- password_hash: VARCHAR(255) NOT NULL
- is_active: BOOLEAN DEFAULT true
- preferences: JSONB         -- User preferences and settings
- created_at, updated_at: TIMESTAMP
```

#### `user_interactions`
Comprehensive user-track interaction tracking.
```sql
- id: SERIAL PRIMARY KEY
- user_id: INTEGER REFERENCES users(id)
- track_id: INTEGER REFERENCES tracks(id)
- interaction_type: VARCHAR(20) -- play, like, skip, share, etc.
- play_duration_ms: INTEGER  -- Actual listening duration
- context: JSONB             -- Playlist, discovery session, etc.
- created_at: TIMESTAMP
```

#### `user_music_profiles`
AI-driven user music preference profiles.
```sql
- id: SERIAL PRIMARY KEY
- user_id: INTEGER REFERENCES users(id) UNIQUE
- audio_preferences: JSONB   -- Preferred audio features
- genre_preferences: JSONB   -- Genre weights and preferences
- discovery_settings: JSONB  -- Discovery algorithm parameters
- last_updated: TIMESTAMP
```

### Playlist System

#### `playlists`
User-created and system playlists.
```sql
- id: SERIAL PRIMARY KEY
- name: VARCHAR(255) NOT NULL
- description: TEXT
- owner_id: INTEGER REFERENCES users(id)
- is_public: BOOLEAN DEFAULT false
- is_collaborative: BOOLEAN DEFAULT false
- tags: JSONB                -- User-defined tags
- dynamic_rules: JSONB       -- Rules for smart playlists
- total_duration_ms: INTEGER -- Calculated field
- created_at, updated_at: TIMESTAMP
```

#### `playlist_tracks`
Many-to-many relationship with ordering.
```sql
- id: SERIAL PRIMARY KEY
- playlist_id: INTEGER REFERENCES playlists(id)
- track_id: INTEGER REFERENCES tracks(id)
- position: INTEGER NOT NULL -- Track order in playlist
- added_by: INTEGER REFERENCES users(id)
- added_at: TIMESTAMP
```

### Discovery System

#### `discovery_sessions`
AI-powered music discovery sessions.
```sql
- id: SERIAL PRIMARY KEY
- user_id: INTEGER REFERENCES users(id)
- session_type: VARCHAR(50)  -- mood, genre, similarity, etc.
- parameters: JSONB          -- Session configuration
- started_at: TIMESTAMP
- ended_at: TIMESTAMP
- feedback_score: INTEGER    -- User satisfaction rating
```

#### `discovery_session_tracks`
Tracks presented during discovery.
```sql
- id: SERIAL PRIMARY KEY
- session_id: INTEGER REFERENCES discovery_sessions(id)
- track_id: INTEGER REFERENCES tracks(id)
- position: INTEGER          -- Order of presentation
- user_action: VARCHAR(20)   -- liked, skipped, saved, etc.
- presented_at: TIMESTAMP
```

### Source Integration

#### `track_sources`, `artist_sources`, `album_sources`
External service integration tracking.
```sql
- id: SERIAL PRIMARY KEY
- {entity}_id: INTEGER REFERENCES {entity}(id)
- source_type: VARCHAR(50)   -- spotify, youtube, soundcloud, etc.
- source_id: VARCHAR(255)    -- External ID
- source_uri: VARCHAR(500)   -- Playable URI
- is_available: BOOLEAN      -- Current availability
- last_synced: TIMESTAMP
```

## Performance Optimization

### Indexing Strategy

#### Foreign Key Indexes
All foreign key columns have dedicated indexes for optimal JOIN performance:
```sql
CREATE INDEX idx_tracks_artist_id ON tracks(artist_id);
CREATE INDEX idx_tracks_album_id ON tracks(album_id);
CREATE INDEX idx_user_interactions_user_id ON user_interactions(user_id);
-- ... and 20+ more FK indexes
```

#### Composite Indexes
Multi-column indexes for common query patterns:
```sql
CREATE INDEX idx_tracks_artist_album ON tracks(artist_id, album_id);
CREATE INDEX idx_user_interactions_composite ON user_interactions(user_id, track_id, interaction_type);
CREATE INDEX idx_playlist_tracks_position ON playlist_tracks(playlist_id, position);
```

#### JSONB GIN Indexes
Efficient querying of JSON data:
```sql
CREATE INDEX idx_tracks_audio_features ON tracks USING GIN (audio_features);
CREATE INDEX idx_artists_genres ON artists USING GIN (genres);
CREATE INDEX idx_playlists_tags ON playlists USING GIN (tags);
```

#### Full-Text Search Indexes
Optimized text search across content:
```sql
CREATE INDEX idx_tracks_search ON tracks USING GIN (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(search_vector, ''))
);
CREATE INDEX idx_artists_search ON artists USING GIN (
    to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(search_vector, ''))
);
```

#### Time-Based Indexes
Optimized for recent activity queries:
```sql
CREATE INDEX idx_user_interactions_created ON user_interactions(created_at DESC);
CREATE INDEX idx_discovery_sessions_started ON discovery_sessions(started_at DESC);
```

### Materialized Views

#### Track Popularity View
Pre-calculated popularity metrics for performance:
```sql
CREATE MATERIALIZED VIEW mv_track_popularity AS
SELECT 
    t.id,
    t.title,
    t.artist_id,
    COUNT(DISTINCT ui.user_id) as unique_listeners,
    COUNT(ui.id) FILTER (WHERE ui.interaction_type = 'play') as total_plays,
    COUNT(ui.id) FILTER (WHERE ui.interaction_type = 'like') as total_likes,
    AVG(ui.play_duration_ms) FILTER (WHERE ui.interaction_type = 'play') as avg_play_duration
FROM tracks t
LEFT JOIN user_interactions ui ON t.id = ui.track_id
GROUP BY t.id, t.title, t.artist_id;
```

### Database Triggers

#### Automatic Timestamp Updates
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Applied to: tracks, artists, albums, playlists, users, etc.
```

## Data Integrity

### Foreign Key Constraints
- All relationships enforced with proper FK constraints
- Appropriate CASCADE and RESTRICT behaviors
- Orphaned record prevention

### Check Constraints
```sql
ALTER TABLE tracks ADD CONSTRAINT check_duration CHECK (duration_ms >= 0);
ALTER TABLE user_interactions ADD CONSTRAINT check_play_duration CHECK (play_duration_ms >= 0);
ALTER TABLE albums ADD CONSTRAINT check_total_tracks CHECK (total_tracks >= 0);
```

### Unique Constraints
```sql
-- Prevent duplicate source mappings
CREATE UNIQUE INDEX idx_track_sources_unique ON track_sources(track_id, source_type, source_id);
-- Prevent duplicate playlist positions
CREATE UNIQUE INDEX idx_playlist_position ON playlist_tracks(playlist_id, position);
```

## Migration Management

### Migration System
- **Framework**: Alembic with Flask-Migrate
- **Versioning**: Timestamp-based revision IDs
- **Safety**: Automatic backups before major changes
- **Validation**: Post-migration integrity checks

### Migration Workflow
```bash
# Create new migration
python scripts/utilities/database/db_cli.py migrate -m "Description"

# Apply migrations
python scripts/utilities/database/db_cli.py upgrade

# Rollback if needed
python scripts/utilities/database/db_cli.py downgrade <revision>
```

### Migration Best Practices
1. **Always backup** before schema changes
2. **Test migrations** on development data first
3. **Include both** upgrade and downgrade logic
4. **Validate results** with test suite
5. **Document complex** migrations thoroughly

## Performance Monitoring

### Query Analysis
Enable `pg_stat_statements` for query performance tracking:
```sql
CREATE EXTENSION pg_stat_statements;
```

### Health Monitoring
Regular health checks via database management CLI:
```bash
python scripts/utilities/database/db_cli.py status
```

### Key Metrics to Monitor
- **Connection count**: Should stay below pool limits
- **Index usage**: Should be >90% for active tables
- **Slow queries**: Identify queries >100ms
- **Table bloat**: Vacuum when dead tuples >20%
- **Disk space**: Monitor growth trends

## Configuration

### Database Configuration
Located in `config/orchestrator.yml`:
```yaml
DATABASE:
  SQLALCHEMY_DATABASE_URI: ${DATABASE_URL:-postgresql://searxng_user:searxng_music_2024@/searxng_cool_music}
  SQLALCHEMY_TRACK_MODIFICATIONS: false
```

### Connection Pool Settings
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 0,
    'connect_args': {
        'connect_timeout': 30,
        'application_name': 'searxng_cool'
    }
}
```

## Management Tools

### Database CLI
Comprehensive management interface:
```bash
# Initialize database
python scripts/utilities/database/db_cli.py init

# Check status
python scripts/utilities/database/db_cli.py status

# Create migration
python scripts/utilities/database/db_cli.py migrate -m "Description"

# Apply migrations
python scripts/utilities/database/db_cli.py upgrade

# Create backup
python scripts/utilities/database/db_cli.py backup backup.sql

# Optimize performance
python scripts/utilities/database/db_cli.py optimize
```

### Validation Suite
Comprehensive database validation:
```bash
python scripts/utilities/database/db_validator.py
```

Tests:
- Schema integrity
- Relationship consistency
- Index effectiveness
- Performance benchmarks
- Data consistency
- Migration history

## Development Workflow

### Quick Setup
```bash
# One-command development setup
./scripts/development/init_database.sh
```

### Daily Development
```bash
# Load shortcuts
source db_shortcuts.sh

# Check status
db-status

# Create backup before changes
db-quick-backup

# Apply new migrations
db-upgrade

# Validate everything works
db-validate
```

### Testing
```bash
# Run database tests
pytest tests/database/ -v

# Run specific test suites
pytest tests/database/test_migrations.py -v
pytest tests/database/test_models.py -v
```

## Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
python -c "from scripts.utilities.database.db_manager import DatabaseManager; print(DatabaseManager().test_connection())"

# Check configuration
python -c "from orchestrator.config_loader import load_config; print(load_config()['DATABASE'])"
```

#### Migration Issues
```bash
# Check current revision
python scripts/utilities/database/db_cli.py status

# View migration history
FLASK_APP=migrations/migration_app.py flask db history

# Force migration state (dangerous)
FLASK_APP=migrations/migration_app.py flask db stamp <revision>
```

#### Performance Issues
```bash
# Run optimization
python scripts/utilities/database/db_cli.py optimize

# Check for slow queries
python scripts/utilities/database/db_cli.py status

# Analyze specific table
VACUUM ANALYZE table_name;
```

### Error Recovery

#### Corrupted Migration State
1. Create backup: `db-quick-backup`
2. Check history: `flask db history`
3. Reset to known good state: `flask db stamp <revision>`
4. Apply missing migrations: `db-upgrade`
5. Validate: `db-validate`

#### Performance Degradation
1. Check health: `db-status`
2. Run optimization: `db-optimize`
3. Refresh materialized views
4. Consider manual VACUUM FULL for heavily bloated tables

## Security Considerations

### Access Control
- Database user has minimal required privileges
- No superuser access for application
- Connection pooling limits concurrent access
- Application-level authentication for all operations

### Data Protection
- Passwords stored as secure hashes only
- Sensitive data identified and protected
- Audit trail for all user interactions
- Regular backup and disaster recovery procedures

### Configuration Security
- Environment variable configuration
- No hardcoded credentials in code
- Secure credential storage and rotation
- Configuration validation on startup

## Future Enhancements

### Planned Optimizations
1. **Table Partitioning**: For `user_interactions` as data grows
2. **Read Replicas**: For scaling read operations
3. **Query Caching**: Redis integration for static data
4. **Automated Monitoring**: Grafana dashboard integration
5. **Machine Learning Integration**: Real-time recommendation scoring

### Scalability Considerations
- Horizontal scaling via read replicas
- Vertical scaling with connection pooling
- Data archiving strategies for historical data
- CDN integration for audio features and metadata

---

## Quick Reference

### Essential Commands
```bash
# Setup
./scripts/development/init_database.sh

# Status
python scripts/utilities/database/db_cli.py status

# Migrate
python scripts/utilities/database/db_cli.py migrate -m "Description"
python scripts/utilities/database/db_cli.py upgrade

# Backup & Optimize
python scripts/utilities/database/db_cli.py backup backup.sql
python scripts/utilities/database/db_cli.py optimize

# Validate
python scripts/utilities/database/db_validator.py

# Test
pytest tests/database/ -v
```

### Configuration Files
- **Main Config**: `config/orchestrator.yml`
- **Migration App**: `migrations/migration_app.py`
- **Management CLI**: `scripts/utilities/database/db_cli.py`

### Documentation
- **Architecture**: `docs/DATABASE.md` (this file)
- **Migration Guide**: `docs/database_migration_guide.md`
- **API Documentation**: Generated from model docstrings