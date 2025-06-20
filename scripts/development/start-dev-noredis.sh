#!/bin/bash

# SearXNG-Cool Development Startup Script (Modified - No Redis Check)

set -e

PROJECT_ROOT="/home/mik/SEARXNG/searxng-cool"
SEARXNG_CORE_DIR="/searxng-core/searxng-core"
ORCHESTRATOR_DIR="/orchestrator"
CONFIG_DIR="/config"

echo "🚀 Starting SearXNG-Cool Development Environment (Modified)"
echo "================================================"

# Skip Redis check for now
echo "⚠️  Skipping Redis check (known connectivity issue)"

# Check PostgreSQL connection
echo "🗄️  Checking PostgreSQL connection..."
if ! PGPASSWORD=secure_password_here psql -U searxng_cool -d searxng_cool_auth -h localhost -c "SELECT 1;" >/dev/null 2>&1; then
    echo "⚠️  PostgreSQL connection failed - continuing anyway"
    echo "Database might need to be created first"
fi

# Function to start SearXNG core
start_searxng() {
    echo "🔍 Starting SearXNG Core..."
    cd ""
    
    # Activate SearXNG virtual environment
    source searxng-venv/bin/activate
    
    # Set environment variables
    export SEARXNG_SETTINGS_PATH="/searxng-settings.yml"
    export SEARXNG_SECRET="35252cc1a9e34982a35fa65632c09f17"
    export SEARXNG_REDIS_URL="redis://localhost:6380/2"
    
    # Start SearXNG in background
    python searx/webapp.py --host 127.0.0.1 --port 8888 &
    SEARXNG_PID=
    echo "✅ SearXNG Core started (PID: )"
    
    # Wait for SearXNG to be ready
    echo "⏳ Waiting for SearXNG to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8888/ >/dev/null 2>&1; then
            echo "✅ SearXNG Core is ready"
            break
        fi
        if [  -eq 30 ]; then
            echo "❌ SearXNG Core failed to start"
            kill  2>/dev/null || true
            exit 1
        fi
        sleep 1
    done
}

# Function to start Orchestrator
start_orchestrator() {
    echo "🎭 Starting Flask Orchestrator..."
    cd ""
    
    # Activate main virtual environment
    source "/venv/bin/activate"
    
    # Start orchestrator
    python app.py &
    ORCHESTRATOR_PID=
    echo "✅ Orchestrator started (PID: )"
    
    # Wait for orchestrator to be ready
    echo "⏳ Waiting for Orchestrator to be ready..."
    for i in {1..20}; do
        if curl -s http://localhost:8095/health >/dev/null 2>&1; then
            echo "✅ Orchestrator is ready"
            break
        fi
        if [  -eq 20 ]; then
            echo "❌ Orchestrator failed to start"
            kill  2>/dev/null || true
            kill  2>/dev/null || true
            exit 1
        fi
        sleep 1
    done
}

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "" ]; then
        kill  2>/dev/null || true
        echo "✅ Orchestrator stopped"
    fi
    if [ ! -z "" ]; then
        kill  2>/dev/null || true
        echo "✅ SearXNG Core stopped"
    fi
    echo "👋 Development environment stopped"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Start services
start_searxng
start_orchestrator

echo ""
echo "🎉 SearXNG-Cool Development Environment is running!"
echo "================================================"
echo "🔍 SearXNG Core:     http://localhost:8888"
echo "🎭 Orchestrator:     http://localhost:8095"
echo "📊 Health Check:     http://localhost:8095/health"
echo "🔐 Auth Status:      http://localhost:8095/auth/status"
echo "📡 API Status:       http://localhost:8095/api/status"
echo "🌐 WebSocket Status: http://localhost:8095/ws/status"
echo ""
echo "⚠️  Note: Redis connectivity issue detected"
echo "    Some features may not work properly"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep script running
wait
EOF && chmod +x /home/mik/SEARXNG/searxng-cool/scripts/start-dev-noredis.sh
