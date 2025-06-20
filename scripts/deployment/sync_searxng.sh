#!/bin/bash
# SearXNG Sync Script - Syncs development to production

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directories
DEV_DIR="/home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core"
PROD_DIR="/usr/local/searxng/searxng-src"
BACKUP_DIR="/home/mik/SEARXNG/searxng-cool/backups/$(date +%Y%m%d_%H%M%S)"

echo -e "${YELLOW}SearXNG Sync Script${NC}"
echo "==================="

# 1. Create backup
echo -e "\n${YELLOW}1. Creating backup...${NC}"
mkdir -p "$BACKUP_DIR"
sudo cp -r "$PROD_DIR/searx/engines/"*.py "$BACKUP_DIR/" 2>/dev/null || true
sudo cp "$PROD_DIR/searx/settings.yml" "$BACKUP_DIR/settings.yml.bak" 2>/dev/null || true
echo -e "${GREEN}✓ Backup created in $BACKUP_DIR${NC}"

# 2. Sync music engines
echo -e "\n${YELLOW}2. Syncing music engines...${NC}"
MUSIC_ENGINES=(
    "base_music.py"
    "lastfm.py"
    "beatport.py"
    "free_music_archive.py"
    "musicbrainz.py"
    "spotify_web.py"
    "apple_music_web.py"
    "tidal_web.py"
    "musixmatch.py"
    "pitchfork.py"
    "radio_paradise.py"
    "allmusic.py"
    "musictoscrape.py"
)

for engine in "${MUSIC_ENGINES[@]}"; do
    if [ -f "$DEV_DIR/searx/engines/$engine" ]; then
        sudo cp "$DEV_DIR/searx/engines/$engine" "$PROD_DIR/searx/engines/"
        echo -e "${GREEN}✓ Copied $engine${NC}"
    else
        echo -e "${RED}✗ Not found: $engine${NC}"
    fi
done

# 3. Sync settings.yml if requested
if [[ "$1" == "--settings" ]]; then
    echo -e "\n${YELLOW}3. Syncing settings.yml...${NC}"
    sudo cp "$DEV_DIR/searx/settings.yml" "$PROD_DIR/searx/settings.yml"
    echo -e "${GREEN}✓ Settings synced${NC}"
fi

# 4. Fix permissions
echo -e "\n${YELLOW}4. Fixing permissions...${NC}"
sudo chown -R searxng:searxng "$PROD_DIR"
if ls "$PROD_DIR/searx/engines/"*.py 1> /dev/null 2>&1; then
    sudo chmod 644 "$PROD_DIR/searx/engines/"*.py
fi
sudo chmod 644 "$PROD_DIR/searx/settings.yml"
echo -e "${GREEN}✓ Permissions fixed${NC}"

# 5. Restart SearXNG
echo -e "\n${YELLOW}5. Restarting SearXNG...${NC}"
sudo systemctl restart searxng
sleep 3

# Check status
if sudo systemctl is-active --quiet searxng; then
    echo -e "${GREEN}✓ SearXNG is running${NC}"
else
    echo -e "${RED}✗ SearXNG failed to start!${NC}"
    echo "Check logs with: sudo journalctl -u searxng -n 50"
    exit 1
fi

# 6. Test engines
echo -e "\n${YELLOW}6. Testing engines...${NC}"
echo "Testing Last.fm..."
RESULT=$(curl -s "http://localhost:8888/search?q=test&engines=lastfm&format=json" | jq -r '.results | length' 2>/dev/null || echo "0")
if [ "$RESULT" -gt 0 ]; then
    echo -e "${GREEN}✓ Last.fm: $RESULT results${NC}"
else
    echo -e "${RED}✗ Last.fm: No results${NC}"
fi

echo -e "\n${GREEN}Sync complete!${NC}"
echo -e "\nTo test all engines, run: ${YELLOW}python3 test_all_music_engines.py${NC}"
echo -e "To view logs, run: ${YELLOW}sudo journalctl -u searxng -f${NC}"