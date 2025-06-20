#!/bin/bash

# SearXNG-Cool Development Startup Script - DEBUG VERSION

set -e

PROJECT_ROOT="/home/mik/SEARXNG/searxng-cool"
SEARXNG_CORE_DIR="/searxng-core/searxng-core"
ORCHESTRATOR_DIR="/orchestrator"
CONFIG_DIR="/config"

echo "🚀 Starting SearXNG-Cool Development Environment (DEBUG MODE)"
echo "================================================"

# Check if Redis is running on port 6380
echo "📡 Checking Redis connection..."
echo "DEBUG: Testing Redis with timeout..."
if timeout 2 redis-cli -p 6380 ping 2>&1; then
    echo "✅ Redis is running"
else
    echo "⚠️  Redis check failed, but continuing anyway..."
    echo "DEBUG: Redis might be running but not responding to ping"
fi

# Check PostgreSQL connection
echo "🗄️  Checking PostgreSQL connection..."
if PGPASSWORD=secure_password_here psql -U searxng_cool -d searxng_cool_auth -h localhost -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "⚠️  PostgreSQL connection failed"
    echo "DEBUG: Trying to create database if it doesn't exist..."
    # Continue anyway for debugging
fi

# Function to start SearXNG core
start_searxng() {
    echo "🔍 Starting SearXNG Core..."
    cd ""
    
    # Check if virtualenv exists
    if [ ! -d "searxng-venv" ]; then
        echo "❌ SearXNG virtual environment not found at /searxng-venv"
        echo "DEBUG: Contents of searxng-core directory:"
        ls -la
        return 1
    fi
    
    # Activate SearXNG virtual environment
    source searxng-venv/bin/activate
    
    # Set environment variables
    export SEARXNG_SETTINGS_PATH="/searxng-settings.yml"
    export SEARXNG_SECRET="35252cc1a9e34982a35fa65632c09f17"
    export SEARXNG_REDIS_URL="redis://localhost:6380/2"
    
    echo "DEBUG: SEARXNG_SETTINGS_PATH="
    echo "DEBUG: Checking if settings file exists..."
    ls -la "" || echo "Settings file not found!"
    
    # Start SearXNG in background
    echo "DEBUG: Starting SearXNG webapp..."
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
            echo "DEBUG: Checking if process is still running..."
            ps -p  || echo "Process died"
            kill  2>/dev/null || true
            return 1
        fi
        echo -n "."
        sleep 1
    done
    echo ""
}

# Function to start Orchestrator
start_orchestrator() {
    echo "🎭 Starting Flask Orchestrator..."
    cd ""
    
    # Check if virtualenv exists
    if [ ! -d "/venv" ]; then
        echo "❌ Main virtual environment not found at /venv"
        return 1
    fi
    
    # Activate main virtual environment
    source "/venv/bin/activate"
    
    echo "DEBUG: Checking if app.py exists..."
    ls -la app.py || echo "app.py not found!"
    
    # Start orchestrator
    echo "DEBUG: Starting Flask app..."
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
            echo "DEBUG: Checking if process is still running..."
            ps -p  || echo "Process died"
            kill  2>/dev/null || true
            kill  2>/dev/null || true
            return 1
        fi
        echo -n "."
        sleep 1
    done
    echo ""
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
if start_searxng; then
    if start_orchestrator; then
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
        echo "Press Ctrl+C to stop all services"
        
        # Keep script running
        wait
    else
        echo "❌ Failed to start Orchestrator"
        exit 1
    fi
else
    echo "❌ Failed to start SearXNG Core"
    exit 1
fi
EOF && chmod +x /home/mik/SEARXNG/searxng-cool/scripts/start-dev-debug.sh
