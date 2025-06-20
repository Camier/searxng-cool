#!/bin/bash
# Sync music engines to production SearXNG

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PROD_DIR="/usr/local/searxng/searxng-src"

echo "Syncing music engines to production..."

# Backup production engines
sudo cp -r "$PROD_DIR/searx/engines" "$PROD_DIR/searx/engines.backup.$(date +%Y%m%d)"

# Sync custom engines
for engine in "$PROJECT_ROOT/engines/"*.py; do
    if [ -f "$engine" ]; then
        echo "Copying $(basename "$engine")..."
        sudo cp "$engine" "$PROD_DIR/searx/engines/"
    fi
done

echo "Sync complete!"
echo "Remember to restart SearXNG: sudo systemctl restart searxng"
