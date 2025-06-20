# Security Configuration Guide

This guide describes the security configuration setup for SearXNG-Cool.

## Quick Start

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Generate secure keys:
   ```bash
   # Generate JWT secret
   openssl rand -hex 32
   
   # Generate Flask secret key
   openssl rand -hex 32
   ```

3. Update `.env` with your secure values and API keys

4. Ensure `.env` is never committed to version control

## Configuration Files

### `.env.example`
Template file with all available configuration options. This file is safe to commit and serves as documentation.

### `.env`
Your actual configuration file with sensitive data. This file is gitignored and should never be committed.

### `config/orchestrator.yml`
Main orchestrator configuration that references environment variables. Uses the pattern:
- `${VAR}` - Simple substitution
- `${VAR:-default}` - With default value
- `${VAR:?error}` - Required variable

### `config/security.py`
Centralized security configuration module that:
- Loads environment variables securely
- Provides default values for non-critical settings
- Validates API key formats
- Manages security headers
- Handles password hashing

## Environment Variables

### Required Variables
These must be set or the application will fail to start:

- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Secret key for JWT tokens (generate with `openssl rand -hex 32`)

### Security Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access token lifetime (seconds) | 3600 |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh token lifetime (seconds) | 86400 |
| `SECRET_KEY` | Flask session key | Generated |
| `SESSION_COOKIE_SECURE` | HTTPS-only cookies | true |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Full PostgreSQL URL | Required |
| `DATABASE_POOL_SIZE` | Connection pool size | 10 |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | 20 |
| `DATABASE_POOL_TIMEOUT` | Pool timeout (seconds) | 30 |

### Redis Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Main Redis URL | redis://localhost:6379/0 |
| `SOCKETIO_REDIS_URL` | WebSocket Redis URL | redis://localhost:6379/1 |
| `RATE_LIMIT_STORAGE_URL` | Rate limiting Redis URL | redis://localhost:6379/2 |

### API Keys

All API keys are optional but required for their respective features:

- `LASTFM_API_KEY`, `LASTFM_API_SECRET`
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- `DISCOGS_TOKEN`
- `MUSICBRAINZ_USER_AGENT`

## Security Features

### Password Hashing
The security module uses bcrypt for password hashing with automatic fallback to PBKDF2:

```python
from config import security_config

# Hash a password
hashed = security_config.hash_password("user_password")

# Verify a password
is_valid = security_config.verify_password("user_password", hashed)
```

### API Key Validation
API keys are validated against expected patterns:

```python
from config import require_api_key

@require_api_key('spotify')
def fetch_spotify_data():
    # This will only run if SPOTIFY_CLIENT_ID is set and valid
    pass
```

### Security Headers
Automatic security headers for all responses:

```python
from config import apply_security_headers

@app.after_request
def add_security_headers(response):
    return apply_security_headers(response)
```

Headers included:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
- Content-Security-Policy

### CORS Configuration
CORS origins are configurable via `CORS_ORIGINS` environment variable:

```
CORS_ORIGINS=http://localhost:3000,http://localhost:8095,https://yourdomain.com
```

## Production Deployment

1. **Generate Production Keys**:
   ```bash
   # Generate strong keys for production
   openssl rand -hex 64  # For extra security
   ```

2. **Set Environment**:
   ```bash
   export FLASK_ENV=production
   export DEBUG=false
   ```

3. **Configure Logging**:
   ```bash
   export LOG_LEVEL=WARNING
   export LOG_FILE=/var/log/searxng-cool/orchestrator.log
   ```

4. **Enable HTTPS**:
   ```bash
   export SESSION_COOKIE_SECURE=true
   ```

5. **Database Security**:
   - Use strong passwords
   - Enable SSL for database connections
   - Restrict database access by IP

## Security Best Practices

1. **Key Rotation**: Rotate JWT secrets periodically
2. **API Key Management**: Use a key management service in production
3. **Environment Isolation**: Use separate configurations for dev/staging/prod
4. **Audit Logging**: Monitor authentication and authorization events
5. **Rate Limiting**: Configure appropriate limits for your use case
6. **HTTPS**: Always use HTTPS in production
7. **Database Security**: Use SSL connections and strong passwords

## Troubleshooting

### Missing Environment Variables
If you see errors about missing variables:
1. Check your `.env` file exists
2. Ensure the variable is set
3. Check for typos in variable names

### Invalid Configuration
Run the configuration validator:
```bash
python orchestrator/config_loader.py
```

### Permission Issues
Ensure log directories exist and are writable:
```bash
sudo mkdir -p /var/log/searxng-cool
sudo chown $USER:$USER /var/log/searxng-cool
```