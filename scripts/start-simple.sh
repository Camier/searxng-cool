#!/bin/bash

# Simple startup script for SearXNG-Cool

echo "🚀 Starting SearXNG-Cool Services..."

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "searx.webapp" 2>/dev/null
pkill -f "app.py" 2>/dev/null
pkill -f "app_minimal.py" 2>/dev/null
sleep 2

# Start SearXNG
echo "Starting SearXNG Core on port 8888..."
cd /home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core
source ../searxng-venv/bin/activate
export SEARXNG_SETTINGS_PATH="/home/mik/SEARXNG/searxng-cool/config/searxng-settings.yml"
python -m searx.webapp --host 127.0.0.1 --port 8888 &
SEARXNG_PID=
echo "SearXNG started with PID: "

# Wait a bit
sleep 5

# Start Orchestrator
echo "Starting Flask Orchestrator on port 8095..."
cd /home/mik/SEARXNG/searxng-cool/orchestrator
source /home/mik/SEARXNG/searxng-cool/venv/bin/activate

# Check which app file exists
if [ -f "app.py" ]; then
    python app.py &
    ORCHESTRATOR_PID=
    echo "Orchestrator (app.py) started with PID: "
elif [ -f "app_minimal.py" ]; then
    python app_minimal.py &
    ORCHESTRATOR_PID=
    echo "Orchestrator (app_minimal.py) started with PID: "
else
    echo "ERROR: No app file found!"
    kill 
    exit 1
fi

# Wait a bit for services to start
sleep 5

# Test the services
echo ""
echo "Testing services..."
echo -n "SearXNG Core (8888): "
curl -s http://localhost:8888/ >/dev/null && echo "✅ OK" || echo "❌ FAILED"

echo -n "Orchestrator (8095): "
curl -s http://localhost:8095/health >/dev/null && echo "✅ OK" || echo "❌ FAILED"

echo ""
echo "Services should be running at:"
echo "- SearXNG Core: http://localhost:8888"
echo "- Orchestrator: http://localhost:8095"
echo ""
echo "To stop: kill  "
echo "Or press Ctrl+C"

# Keep running
trap "kill   2>/dev/null; echo 'Services stopped'" EXIT
wait
