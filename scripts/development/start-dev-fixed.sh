#!/bin/bash

# SearXNG-Cool Development Startup Script - FIXED VERSION

set -e

PROJECT_ROOT="/home/mik/SEARXNG/searxng-cool"
SEARXNG_CORE_DIR="/searxng-core"  # Fixed path
ORCHESTRATOR_DIR="/orchestrator"
CONFIG_DIR="/config"

echo "🚀 Starting SearXNG-Cool Development Environment (FIXED)"
echo "================================================"

# Skip Redis check for now - it seems to have connectivity issues
echo "📡 Skipping Redis check (known issue)..."

# Skip PostgreSQL check for now
echo "🗄️  Skipping PostgreSQL check (will create tables on first run)..."

# Function to start SearXNG core
start_searxng() {
    echo "🔍 Starting SearXNG Core..."
    
    # Check the actual structure
    echo "DEBUG: Checking SearXNG directory structure..."
    echo "SEARXNG_CORE_DIR: "
    ls -la ""
    
    # Go to the actual searxng code directory
    cd "/searxng-core"
    
    # Activate SearXNG virtual environment (it's one level up)
    echo "DEBUG: Activating virtual environment..."
    source ../searxng-venv/bin/activate
    
    # Set environment variables
    export SEARXNG_SETTINGS_PATH="/searxng-settings.yml"
    export SEARXNG_SECRET="35252cc1a9e34982a35fa65632c09f17"
    export SEARXNG_REDIS_URL="redis://localhost:6380/2"
    
    echo "DEBUG: SEARXNG_SETTINGS_PATH="
    echo "DEBUG: Checking if settings file exists..."
    ls -la "" || echo "Settings file not found!"
    
    # Check if searx module exists
    echo "DEBUG: Checking for searx module..."
    ls -la searx/webapp.py || echo "searx/webapp.py not found!"
    
    # Start SearXNG in background
    echo "DEBUG: Starting SearXNG webapp..."
    python -m searx.webapp --host 127.0.0.1 --port 8888 &
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
            # Check logs
            echo "DEBUG: Last 20 lines of output:"
            tail -20 /tmp/searxng-output.log 2>/dev/null || echo "No log file"
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
    
    # Activate main virtual environment
    source "/venv/bin/activate"
    
    echo "DEBUG: Checking orchestrator files..."
    ls -la app.py || ls -la app_minimal.py || echo "No app files found!"
    
    # Check which app file to use
    if [ -f "app.py" ]; then
        APP_FILE="app.py"
    elif [ -f "app_minimal.py" ]; then
        APP_FILE="app_minimal.py"
    else
        echo "❌ No Flask app file found!"
        return 1
    fi
    
    # Start orchestrator with error output
    echo "DEBUG: Starting Flask app with ..."
    python  2>&1 &
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
echo "Starting SearXNG first..."
if start_searxng; then
    echo "Starting Orchestrator..."
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
        echo "🔧 Debugging Tips:"
        echo "- Check processes: ps aux | grep -E 'searx|flask'"
        echo "- Check ports: netstat -tlnp | grep -E '8888|8095'"
        echo "- SearXNG logs: Check console output above"
        echo "- Orchestrator logs: Check console output above"
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
