#!/bin/bash
# Start SearXNG-Cool Orchestrator with WSL2 Fixes

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "╔════════════════════════════════════════════╗"
echo -e "║    SearXNG-Cool Flask Orchestrator         ║"
echo -e "║    WSL2 Networking Fix Applied ✓           ║"
echo -e "╚════════════════════════════════════════════╝"

cd /home/mik/SEARXNG/searxng-cool

# Check Redis
echo -e "\nChecking Redis..."
if redis-cli -p 6379 ping > /dev/null 2>&1; then
    echo -e "✅ Redis is running on port 6379"
else
    echo -e "❌ Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

# Check SearXNG core
echo -e "\nChecking SearXNG Core..."
if curl -s http://localhost:8888 > /dev/null; then
    echo -e "✅ SearXNG Core is running on port 8888"
else
    echo -e "⚠️  SearXNG Core is not running"
fi

# Update config
sed -i 's/PORT: [0-9]*/PORT: 8889/' config/orchestrator.yml

# Kill existing processes
PIDS=
if [ ! -z "" ]; then
    echo -e "Killing existing processes on port 8095"
    kill -9  2>/dev/null || true
    sleep 1
fi

# Activate venv
source venv/bin/activate

echo -e "\nStarting with Flask (WSL2 fixes applied)..."
echo -e "Fixes: threaded=True, use_reloader=False"
echo -e "\nAccess URLs:"
echo -e "  - http://localhost:8095 (nginx main entry)"
echo -e "  - http://localhost:8889/health (direct orchestrator)"

cd orchestrator
python app_wsl2_fixed.py
