#!/bin/bash
# Start all SearXNG-Cool services with production configuration

echo "🚀 Starting SearXNG-Cool Production Stack"
echo "======================================="

# Check if running in WSL2
if grep -qi microsoft /proc/version; then
    echo "✅ WSL2 environment detected"
    export EVENTLET_HUB=poll
fi

# Function to check if port is open
check_port() {
    nc -z localhost $1 2>/dev/null
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Redis if not running
echo "🔄 Starting Redis..."
if ! check_port 6379; then
    redis-server --port 6379 --maxclients 10000 --daemonize yes
    echo "✅ Redis started on port 6379"
else
    echo "✅ Redis already running on port 6379"
fi

# Start SearXNG Core
echo "🔄 Starting SearXNG Core..."
if ! check_port 8888; then
    cd searxng-core/searxng-core
    source ../searxng-venv/bin/activate
    nohup python -m searx.webapp --host 127.0.0.1 --port 8888 > ../../logs/searxng.log 2>&1 &
    echo "✅ SearXNG Core started on port 8888"
    cd ../..
else
    echo "✅ SearXNG Core already running on port 8888"
fi

# Start Flask Orchestrator
echo "🔄 Starting Flask Orchestrator with Eventlet..."
if ! check_port 8889; then
    source venv/bin/activate
    nohup python orchestrator/app_production.py > logs/flask.log 2>&1 &
    echo "✅ Flask Orchestrator started on port 8889"
else
    echo "✅ Flask Orchestrator already running on port 8889"
fi

# Reload nginx
echo "🔄 Reloading nginx configuration..."
sudo nginx -s reload
echo "✅ nginx reloaded"

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 3

# Check health
echo ""
echo "🏥 Checking service health..."
if curl -s http://localhost:8889/health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    echo "✅ Flask Orchestrator is healthy"
else
    echo "⚠️  Flask Orchestrator health check failed"
fi

if curl -s http://localhost:8888 > /dev/null 2>&1; then
    echo "✅ SearXNG Core is responding"
else
    echo "⚠️  SearXNG Core not responding"
fi

echo ""
echo "🎉 SearXNG-Cool is ready!"
echo "=================================="
echo "🌐 Main Entry: https://alfredisgone.duckdns.org"
echo "🌐 Local Entry: http://localhost:8095"
echo "📊 Health Check: http://localhost:8889/health"
echo "📊 Eventlet Stats: http://localhost:8889/eventlet-stats"
echo ""
echo "📋 Logs:"
echo "   - Flask: logs/flask.log"
echo "   - SearXNG: logs/searxng.log"
echo "   - nginx: /var/log/nginx/searxng_*.log"