#!/bin/bash

# Test using the SearXNG direct search endpoint
BASE_URL="http://localhost:8889"

echo "Testing SearXNG directly (not through music API)..."
echo

# Test a few engines directly
ENGINES=("discogs" "jamendo" "soundcloud" "bandcamp" "genius")

for engine in "${ENGINES[@]}"; do
    echo "Testing engine: $engine"
    
    # Make direct SearXNG search request
    curl -s -X GET "$BASE_URL/search" \
        -G \
        --data-urlencode "q=electronic music" \
        --data-urlencode "engines=$engine" \
        --data-urlencode "format=json" \
        > "direct_$engine.json"
    
    # Check results
    if [ -f "direct_$engine.json" ]; then
        result_count=$(jq -r '.results | length // 0' "direct_$engine.json" 2>/dev/null)
        echo "  Results: $result_count"
        
        if [ "$result_count" -gt 0 ]; then
            # Show first result
            title=$(jq -r '.results[0].title // "No title"' "direct_$engine.json" 2>/dev/null)
            url=$(jq -r '.results[0].url // "No URL"' "direct_$engine.json" 2>/dev/null)
            echo "  First result: $title"
            echo "  URL: $url"
        fi
    fi
    
    echo
    sleep 1
done

# Also test if music category works
echo "Testing music category search..."
curl -s -X GET "$BASE_URL/search" \
    -G \
    --data-urlencode "q=electronic" \
    --data-urlencode "categories=music" \
    --data-urlencode "format=json" \
    > "direct_music_category.json"

result_count=$(jq -r '.results | length // 0' "direct_music_category.json" 2>/dev/null)
echo "Music category results: $result_count"

# Check which engines were actually used
engines_used=$(jq -r '.results[].engine | unique' "direct_music_category.json" 2>/dev/null | sort | uniq)
echo "Engines that returned results:"
echo "$engines_used"