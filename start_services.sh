#!/bin/bash
# SearXNG-Cool Service Launcher

# Change to project directory
cd /home/mik/SEARXNG/searxng-cool-restored

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export SECRET_KEY=8c63818f43844ceb06312ca096326b8af4c3640fd6c0c678eb2ea32ad9aeda99
export JWT_SECRET_KEY=cc19cb632dc41bbfb4ec0b547dac81db75b84603c6f43cc8c73a860c96f166f9
export DB_PASSWORD=searxng_music_2024
export DATABASE_URL="postgresql://searxng_user:searxng_music_2024@localhost/searxng_cool_music"
export JWT_ACCESS_TOKEN_EXPIRES=3600
export JWT_REFRESH_TOKEN_EXPIRES=86400
export REDIS_URL=redis://localhost:6379/0
export SOCKETIO_REDIS_URL=redis://localhost:6379/1
export SEARXNG_CORE_URL=http://localhost:8888
export SEARXNG_SETTINGS_PATH=/home/mik/SEARXNG/searxng-cool-restored/config/searxng-settings.yml
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8889
export DEBUG=false
export CORS_ORIGINS="http://localhost:3000,http://localhost:8095"

# Check PostgreSQL
echo "Checking PostgreSQL..."
if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL is not running. Please start it with: sudo systemctl start postgresql"
    exit 1
fi

# Check Redis
echo "Checking Redis..."
if ! systemctl is-active --quiet redis-server; then
    echo "Starting Redis..."
    sudo service redis-server start
fi

# Kill any existing services
echo "Stopping any existing services..."
pkill -f "python searx/webapp.py" 2>/dev/null
pkill -f "python app_eventlet_optimized.py" 2>/dev/null
sleep 2

# Start SearXNG Core
echo "Starting SearXNG Core on port 8888..."
cd searxng-core/searxng-core
export PYTHONPATH=/home/mik/SEARXNG/searxng-cool-restored/searxng-core/searxng-core:$PYTHONPATH
python searx/webapp.py > /tmp/searxng-core.log 2>&1 &
SEARXNG_PID=$!
echo "SearXNG Core PID: $SEARXNG_PID"

# Wait for SearXNG to start
echo "Waiting for SearXNG Core to start..."
sleep 5

# Start Orchestrator
echo "Starting Orchestrator on port 8889..."
cd ../../orchestrator
export PYTHONPATH=/home/mik/SEARXNG/searxng-cool-restored:$PYTHONPATH
python app_eventlet_optimized.py > /tmp/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
echo "Orchestrator PID: $ORCHESTRATOR_PID"

# Wait for services to initialize
sleep 3

# Check if services are running
echo -e "\n✅ Services Status:"
echo "==================="
if ps -p $SEARXNG_PID > /dev/null 2>&1; then
    echo "✓ SearXNG Core is running on http://localhost:8888"
else
    echo "✗ SearXNG Core failed to start. Check /tmp/searxng-core.log"
fi

if ps -p $ORCHESTRATOR_PID > /dev/null 2>&1; then
    echo "✓ Orchestrator is running on http://localhost:8889"
else
    echo "✗ Orchestrator failed to start. Check /tmp/orchestrator.log"
fi

echo -e "\n📌 Access Points:"
echo "================="
echo "- SearXNG Web UI: http://localhost:8888"
echo "- Orchestrator API: http://localhost:8889"
echo "- WebSocket: ws://localhost:8889/socket.io/"

echo -e "\n📝 Logs:"
echo "========"
echo "- SearXNG Core: /tmp/searxng-core.log"
echo "- Orchestrator: /tmp/orchestrator.log"

echo -e "\n🛑 To stop services:"
echo "===================="
echo "pkill -f 'python searx/webapp.py'"
echo "pkill -f 'python app_eventlet_optimized.py'"