# SearXNG-Cool Installation Guide

## Prerequisites

### System Requirements
- Ubuntu 20.04+ or Debian 11+ (WSL2 supported)
- Python 3.10 or higher
- 2GB+ RAM
- 10GB disk space

### Required Services
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    git build-essential \
    libpq-dev libxml2-dev libxslt-dev \
    libffi-dev libssl-dev
```

## Step-by-Step Installation

### 1. Clone Repository
```bash
cd ~
git clone https://github.com/yourusername/searxng-cool.git
cd searxng-cool
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt
pip install -r orchestrator/requirements.txt
pip install -r searxng-core/searxng-core/requirements.txt
```

### 3. PostgreSQL Setup
```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE USER searxng_user WITH PASSWORD 'searxng_music_2024';
CREATE DATABASE searxng_cool_music OWNER searxng_user;
GRANT ALL PRIVILEGES ON DATABASE searxng_cool_music TO searxng_user;
EOF

# Run migrations
cd migrations
alembic upgrade head
cd ..
```

### 4. Redis Setup
```bash
# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
# Should return: PONG
```

### 5. Configuration
```bash
# Copy example config
cp config/.env.example .env

# Edit configuration
nano .env
```

Add your configuration:
```env
# Database
DATABASE_URL=postgresql://searxng_user:searxng_music_2024@localhost/searxng_cool_music

# Redis
REDIS_URL=redis://localhost:6379

# Orchestrator
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=7775

# SearXNG
SEARXNG_HOST=127.0.0.1
SEARXNG_PORT=8888

# Optional API Keys
SPOTIFY_CLIENT_ID=your_spotify_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
GENIUS_API_KEY=your_genius_key
```

### 6. nginx Configuration
```bash
# Copy nginx config
sudo cp config/nginx-searxng-cool-advanced.conf /etc/nginx/sites-available/searxng-cool

# Enable site
sudo ln -s /etc/nginx/sites-available/searxng-cool /etc/nginx/sites-enabled/

# Remove default site if needed
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 7. Start Services

#### Option A: Manual Start (Development)
```bash
# Terminal 1: Start SearXNG
cd searxng-core/searxng-core
python searx/webapp.py

# Terminal 2: Start Orchestrator
cd orchestrator
python app_eventlet_optimized.py

# Terminal 3: Monitor logs
tail -f orchestrator/logs/*.log
```

#### Option B: Systemd Services (Production)
Create service files:

```bash
# SearXNG service
sudo nano /etc/systemd/system/searxng.service
```

Add:
```ini
[Unit]
Description=SearXNG
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/searxng-cool/searxng-core/searxng-core
Environment="PATH=/home/your_username/searxng-cool/venv/bin"
ExecStart=/home/your_username/searxng-cool/venv/bin/python searx/webapp.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Orchestrator service
sudo nano /etc/systemd/system/searxng-orchestrator.service
```

Add:
```ini
[Unit]
Description=SearXNG Orchestrator
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/searxng-cool/orchestrator
Environment="PATH=/home/your_username/searxng-cool/venv/bin"
ExecStart=/home/your_username/searxng-cool/venv/bin/python app_eventlet_optimized.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable searxng searxng-orchestrator
sudo systemctl start searxng searxng-orchestrator
```

### 8. Verify Installation
```bash
# Check services
sudo systemctl status searxng
sudo systemctl status searxng-orchestrator
sudo systemctl status nginx
sudo systemctl status redis
sudo systemctl status postgresql

# Test endpoints
curl http://localhost:8888  # SearXNG
curl http://localhost:7775  # Orchestrator
```

### 9. Access Application
Open browser and navigate to:
- http://localhost (via nginx)
- http://localhost:7775 (direct orchestrator)
- http://localhost:8888 (direct SearXNG)

## Troubleshooting

### Common Issues

1. **Module not found errors**
   ```bash
   pip install missing_module
   ```

2. **Database connection errors**
   - Check PostgreSQL is running
   - Verify credentials in .env
   - Check pg_hba.conf allows local connections

3. **Redis connection errors**
   ```bash
   sudo systemctl restart redis-server
   ```

4. **Permission errors**
   - Ensure user owns all files
   - Check nginx user can access socket files

### Logs Location
- Orchestrator: `orchestrator/logs/`
- SearXNG: `searxng-core/logs/`
- nginx: `/var/log/nginx/`

## Next Steps
1. Configure API keys for enhanced features
2. Set up SSL with Let's Encrypt
3. Configure firewall rules
4. Set up monitoring (Prometheus/Grafana)
5. Configure backup strategies

## Support
- GitHub Issues: [Report bugs](https://github.com/yourusername/searxng-cool/issues)
- Documentation: See `/docs` directory
- Logs: Check application logs for detailed errors