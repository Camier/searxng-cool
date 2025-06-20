# SearXNG-Cool Connectivity Fixes Applied

## Date: June 21, 2025

### Issues Fixed

1. **Redis Port Configuration**
   - **Issue**: Redis was configured for port 6380 but running on 6379
   - **Fix**: Updated `config/searxng-settings.yml` to use correct port 6379
   - **File**: `config/searxng-settings.yml`

2. **PostgreSQL Connection**
   - **Issue**: Connection timeout with incorrect password
   - **Fix**: Updated password to `searxng_music_2024` in `start_services.sh`
   - **Files**: 
     - `start_services.sh`
     - `/etc/postgresql/*/main/pg_hba.conf` (trust auth for Unix socket)

3. **Radio Paradise Engine**
   - **Issue**: NoneType error when album field is None
   - **Fix**: Added null checks with `or ''` pattern
   - **File**: `searxng-core/searxng-core/searx/engines/radio_paradise.py`
   - **Changes**:
     ```python
     artist = song.get('artist', '') or ''
     title = song.get('title', '') or ''
     album = song.get('album', '') or ''
     ```

4. **Apple Music & Pitchfork Redirects**
   - **Issue**: Max redirects exceeded (regional domain redirects)
   - **Fix**: Added `max_redirects = 2` to both engines
   - **Files**:
     - `searxng-core/searxng-core/searx/engines/apple_music_web.py`
     - `searxng-core/searxng-core/searx/engines/pitchfork.py`

### System Status After Fixes

- **Operational**: 90% (25/27 engines working)
- **Redis**: ✅ Connected on port 6379
- **PostgreSQL**: ✅ Connected with Unix socket
- **SearXNG Core**: ✅ Running on port 8888
- **Orchestrator**: ✅ Running on port 8889

### Remaining Issues

- **Musixmatch**: Blocked with 403 (external rate limiting)
- **Apple Music/Pitchfork**: Redirect warnings (informational only, engines work)

### Commands to Start Services

```bash
# Start all services
./start_services.sh

# Check connectivity
./audit_connectivity.sh
```