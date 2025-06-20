# Database Migration Guide

## Overview

This guide documents the production-grade database consolidation performed on the SearXNG-Cool music platform database. The consolidation includes proper migration management, performance optimizations, and monitoring capabilities.

## Migration History

### Initial State
- Database was manually created with `manual_creation_20250617`
- 21 tables existed without proper migration files
- No performance indexes or optimizations

### Consolidation Migrations

1. **`20250618_075008_initial_schema`** - Captures existing database state
   - Documents all 21 tables
   - Establishes baseline for future migrations
   - No actual changes (tables already exist)

2. **`20250618_075149_add_performance_indexes`** - Adds comprehensive optimizations
   - 35+ performance indexes
   - JSONB GIN indexes
   - Full-text search configuration
   - Materialized views
   - Check constraints
   - Update triggers

## Running Migrations

### Prerequisites
```bash
cd /home/mik/SEARXNG/searxng-cool
source venv/bin/activate
```

### Apply Migrations
```bash
# Set the Flask app
export FLASK_APP=migrations/migration_app.py

# Check current migration status
flask db current

# Apply all pending migrations
flask db upgrade

# Or apply a specific migration
flask db upgrade <revision>
```

### Rollback Migrations
```bash
# Rollback one migration
flask db downgrade -1

# Rollback to specific revision
flask db downgrade <revision>

# Rollback all migrations (DANGER!)
flask db downgrade base
```

## Creating New Migrations

### Auto-generate Migration
```bash
# After modifying models
flask db migrate -m "Description of changes"

# Review the generated migration
# Edit if necessary in migrations/versions/

# Apply the migration
flask db upgrade
```

### Manual Migration
```bash
# Create empty migration
flask db revision -m "Description of changes"

# Edit the generated file to add upgrade/downgrade logic
```

## Performance Optimizations

### Indexes Added

#### Foreign Key Indexes
- All foreign key columns now have indexes
- Dramatically improves JOIN performance
- Examples: `idx_tracks_artist_id`, `idx_playlist_tracks_track_id`

#### Composite Indexes
- Multi-column indexes for common query patterns
- Examples: `idx_tracks_artist_album`, `idx_user_interactions_composite`

#### JSONB Indexes
- GIN indexes on all JSONB columns
- Enables efficient queries on nested data
- Examples: `idx_tracks_audio_features`, `idx_artists_genres`

#### Full-Text Search
- GIN indexes with `to_tsvector` for text search
- Configured for English language
- Examples: `idx_tracks_search`, `idx_artists_search`

### Materialized Views

#### `mv_track_popularity`
- Pre-calculated track statistics
- Refreshed periodically for performance
- Includes: unique listeners, play counts, average duration

Refresh command:
```bash
python scripts/db_manager.py refresh-view mv_track_popularity
```

### Database Triggers

#### `update_<table>_updated_at`
- Automatically updates `updated_at` timestamp
- Applied to all tables with this column
- Ensures accurate modification tracking

## Database Management

### Using the Database Manager

The `scripts/db_manager.py` tool provides comprehensive database management:

```bash
# Make executable
chmod +x scripts/db_manager.py

# View all commands
python scripts/db_manager.py --help

# Analyze index usage
python scripts/db_manager.py analyze-indexes

# Check for slow queries
python scripts/db_manager.py analyze-queries

# View table statistics
python scripts/db_manager.py table-stats

# Find missing indexes
python scripts/db_manager.py missing-indexes

# Run health check
python scripts/db_manager.py health-check

# Vacuum a table
python scripts/db_manager.py vacuum-table tracks

# View connection statistics
python scripts/db_manager.py connection-stats
```

### Regular Maintenance Tasks

#### Daily
- Monitor slow queries
- Check connection statistics
- Review error logs

#### Weekly
- Refresh materialized views
- Analyze index usage
- Check table bloat

#### Monthly
- Full VACUUM ANALYZE
- Review and drop unused indexes
- Performance testing

## Performance Testing

### Running Performance Tests
```bash
# Install test dependencies
pip install pytest tabulate

# Run all performance tests
pytest tests/test_database_performance.py -v

# Run specific test category
pytest tests/test_database_performance.py::TestIndexPerformance -v

# Generate performance report
pytest tests/test_database_performance.py::test_query_performance_summary -s
```

### Performance Benchmarks

Expected query performance after optimizations:
- Simple lookups: < 10ms
- Complex joins: < 50ms
- Aggregations: < 200ms
- Full-text search: < 100ms

## Monitoring Setup

### Enable Query Statistics
```sql
-- As postgres superuser
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- In postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
```

### Connection Pooling Configuration

In your application configuration:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 0
}
```

## Troubleshooting

### Common Issues

#### Migration Import Errors
```bash
# Fix: Ensure correct Python path
cd /home/mik/SEARXNG/searxng-cool
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

#### Permission Errors
```bash
# Ensure correct database permissions
sudo -u postgres psql -d searxng_cool_music
GRANT ALL ON SCHEMA public TO searxng_user;
```

#### Slow Queries After Migration
```bash
# Analyze and vacuum all tables
python scripts/db_manager.py vacuum-table <table_name>

# Or for all tables
sudo -u postgres vacuumdb -d searxng_cool_music -z
```

## Best Practices

### Development Workflow
1. Always create migrations for schema changes
2. Review auto-generated migrations carefully
3. Test migrations on development database first
4. Include both upgrade and downgrade logic
5. Document complex migrations

### Query Optimization
1. Use EXPLAIN ANALYZE for slow queries
2. Ensure queries use appropriate indexes
3. Avoid N+1 query patterns
4. Use eager loading for relationships
5. Consider caching for static data

### Index Management
1. Monitor index usage regularly
2. Drop unused indexes (waste space)
3. Add indexes for frequent query patterns
4. Use partial indexes for specific conditions
5. Consider index maintenance overhead

## Future Improvements

### Planned Optimizations
1. Table partitioning for large tables
2. Read replicas for scaling
3. Query result caching
4. Automatic index recommendations
5. Performance dashboard

### Monitoring Enhancements
1. Grafana dashboard setup
2. Alert configuration
3. Automated performance reports
4. Query pattern analysis
5. Capacity planning tools

## References

- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [SQLAlchemy Performance Guide](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)