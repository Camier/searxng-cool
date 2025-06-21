#!/bin/bash
# SearXNG-Cool Service Launcher - Secure Version

# Change to project directory
cd /home/mik/SEARXNG/searxng-cool-restored

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables from .env file
set -a  # automatically export all variables
source .env
set +a  # turn off automatic export

# Additional environment variables not in .env
export JWT_ACCESS_TOKEN_EXPIRES=3600
export JWT_REFRESH_TOKEN_EXPIRES=86400
export SOCKETIO_REDIS_URL=redis://localhost:6379/1
export SEARXNG_CORE_URL=http://localhost:8888
export SEARXNG_SETTINGS_PATH=/home/mik/SEARXNG/searxng-cool-restored/config/searxng-settings.yml
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8889
export DEBUG=false
export CORS_ORIGINS="http://localhost:3000,http://localhost:8095"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Error: Virtual environment not found!"
    echo "Please create it with: python3 -m venv venv"
    exit 1
fi

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

# Verify Redis is on correct port
redis-cli -p 6379 ping > /dev/null 2>&1
if [ 0 -ne 0 ]; then
    echo "❌ Error: Redis not responding on port 6379"
    exit 1
fi

# Kill any existing services
echo "Stopping any existing services..."
pkill -f "python searx/webapp.py" 2>/dev/null
pkill -f "python app_eventlet_optimized.py" 2>/dev/null
sleep 2

# Start SearXNG Core
echo "Starting SearXNG Core on port 8888..."
cd searxng-core/searxng-core
export PYTHONPATH=/home/mik/SEARXNG/searxng-cool-restored/searxng-core/searxng-core:
python searx/webapp.py > /tmp/searxng-core.log 2>&1 &
SEARXNG_PID=
echo "SearXNG Core PID: "

# Wait for SearXNG to start
echo "Waiting for SearXNG Core to start..."
for i in {1..10}; do
    if curl -s http://localhost:8888 > /dev/null; then
        echo "✅ SearXNG Core is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Start Orchestrator
echo "Starting Orchestrator on port 8889..."
cd ../../orchestrator
export PYTHONPATH=/home/mik/SEARXNG/searxng-cool-restored:
python app_eventlet_optimized.py > /tmp/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=
echo "Orchestrator PID: "

# Wait for services to initialize
sleep 3

# Check if services are running
echo -e "\n✅ Services Status:"
echo "==================="
if ps -p  > /dev/null 2>&1; then
    echo "✓ SearXNG Core is running on http://localhost:8888"
else
    echo "✗ SearXNG Core failed to start. Check /tmp/searxng-core.log"
fi

if ps -p  > /dev/null 2>&1; then
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

echo -e "\n🔒 Security Note:"
echo "=================="
echo "All credentials are now loaded from .env file"
echo "Never commit .env to version control!"
