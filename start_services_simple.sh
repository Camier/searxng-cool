#!/bin/bash
# Simplified launcher for testing

cd /home/mik/SEARXNG/searxng-cool-restored
source venv/bin/activate

# Basic environment
export DATABASE_URL="postgresql://searxng_user:DO2ZkP0lUc8G6di3@localhost/searxng_cool_music"
export JWT_SECRET_KEY=cc19cb632dc41bbfb4ec0b547dac81db75b84603c6f43cc8c73a860c96f166f9
export REDIS_URL=redis://localhost:6379/0

# Kill existing
pkill -f "python searx/webapp.py" 2>/dev/null
pkill -f "python app_eventlet_optimized.py" 2>/dev/null
sleep 2

# Start SearXNG
echo "Starting SearXNG on port 8888..."
cd searxng-core/searxng-core
export PYTHONPATH=/home/mik/SEARXNG/searxng-cool-restored/searxng-core/searxng-core:$PYTHONPATH
python searx/webapp.py &
cd ../..

echo -e "\n✅ SearXNG-Cool is running!"
echo "- Web UI: http://localhost:8888"
echo -e "\nTo search for music:"
echo "- Direct search: http://localhost:8888/search?q=pink+floyd&categories=music"
echo "- Use music engines: !spotify queen, !lastfm beatles, !genius lyrics"