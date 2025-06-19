# Deployment Guide

## Production Setup

1. SearXNG is installed at `/usr/local/searxng/searxng-src/`
2. Custom engines go in `/usr/local/searxng/searxng-src/searx/engines/`
3. Configuration at `/usr/local/searxng/searxng-src/searx/settings.yml`

## Sync Process

```bash
./scripts/deploy/sync_to_production.sh
```

This script:
- Backs up current production engines
- Copies new engines to production
- Updates settings.yml if needed
- Restarts SearXNG service

## Testing

Always test changes locally first:
```bash
python tests/test_all_music_engines.py
```
