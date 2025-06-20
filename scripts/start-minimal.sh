#!/bin/bash

# Minimal SearXNG-Cool Startup (No Checks)

PROJECT_ROOT="/home/mik/SEARXNG/searxng-cool"

echo "🚀 Starting SearXNG-Cool (Minimal Mode)"
echo "======================================"

# Start SearXNG Core
echo "🔍 Starting SearXNG Core..."
cd "/searxng-core/searxng-core"
source searxng-venv/bin/activate
export SEARXNG_SETTINGS_PATH="/config/searxng-settings.yml"
export SEARXNG_SECRET="35252cc1a9e34982a35fa65632c09f17"
python searx/webapp.py --host 127.0.0.1 --port 8888 &
SEARXNG_PID=
echo "✅ SearXNG Core started (PID: )"

# Start Orchestrator
echo "🎭 Starting Flask Orchestrator..."
cd "/orchestrator"
source "/venv/bin/activate"
python app.py &
ORCHESTRATOR_PID=
echo "✅ Orchestrator started (PID: )"

# Cleanup on exit
cleanup() {
    echo -e "\n🛑 Stopping services..."
    kill   2>/dev/null
    echo "✅ Services stopped"
}
trap cleanup EXIT INT TERM

echo -e "\n🎉 Services started!"
echo "🔍 SearXNG Core: http://localhost:8888"
echo "🎭 Orchestrator: http://localhost:8095"
echo -e "\nPress Ctrl+C to stop\n"

# Wait
wait
EOF && chmod +x /home/mik/SEARXNG/searxng-cool/scripts/start-minimal.sh
