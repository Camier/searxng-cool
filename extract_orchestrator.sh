#!/bin/bash
# Optional: Extract orchestrator (Flask API) components

echo "Extracting orchestrator components..."

# Create orchestrator structure
mkdir -p orchestrator/{models/music,blueprints/api,services}

# Copy from archive
ARCHIVE_DIR="/home/mik/SEARXNG/searxng-cool-archive-20250619_140512"

if [ -d "$ARCHIVE_DIR/orchestrator" ]; then
    # Copy models
    cp -r "$ARCHIVE_DIR/orchestrator/models/music/"*.py orchestrator/models/music/
    cp "$ARCHIVE_DIR/orchestrator/models/__init__.py" orchestrator/models/
    
    # Copy essential API blueprints
    cp -r "$ARCHIVE_DIR/orchestrator/blueprints/api/"*.py orchestrator/blueprints/api/ 2>/dev/null || true
    
    # Copy main app
    cp "$ARCHIVE_DIR/orchestrator/app.py" orchestrator/
    
    # Copy services
    cp "$ARCHIVE_DIR/orchestrator/services/music_"*.py orchestrator/services/ 2>/dev/null || true
    
    echo "✓ Orchestrator components extracted"
    echo ""
    echo "Note: This adds Flask API functionality with:"
    echo "- Database models for tracks, albums, artists, playlists"
    echo "- API endpoints for music platform features"
    echo "- WebSocket support for real-time features"
else
    echo "Archive not found. Please update path in script."
fi