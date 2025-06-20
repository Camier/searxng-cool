#!/bin/bash
set -e

# Quick script to stop current SearXNG and restart with 0.0.0.0 binding

echo "🛑 Stopping current SearXNG instances..."
pkill -f "python.*searx.webapp" || true
sleep 2

echo "🚀 Starting SearXNG with WSL2 external access..."
cd /home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core

# Get WSL2 IP
WSL_IP=

# Activate venv if available
if [ -f "searxng-venv/bin/activate" ]; then
    source searxng-venv/bin/activate
fi

# Set env vars
export SEARXNG_SETTINGS_PATH="/home/mik/SEARXNG/searxng-cool/config/searxng-settings.yml"
export SEARXNG_SECRET="35252cc1a9e34982a35fa65632c09f17"
export SEARXNG_REDIS_URL="redis://localhost:6380/2"

# Start with 0.0.0.0 binding
python -m searx.webapp --host 0.0.0.0 --port 8888 &
PID=

echo "✅ SearXNG started with PID: "
echo ""
echo "🌐 Access URLs:"
echo "   Local:    http://localhost:8888"
echo "   Windows:  http://:8888"
echo ""
echo "Press Ctrl+C to stop"

wait 
