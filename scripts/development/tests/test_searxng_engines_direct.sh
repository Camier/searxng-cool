#!/bin/bash

echo "Testing SearXNG Music Engines Directly on Port 8888"
echo "=================================================="
echo

# Test each engine individually
engines=("bandcamp" "discogs" "jamendo" "soundcloud" "genius" "mixcloud")

for engine in "${engines[@]}"; do
    echo "Testing $engine..."
    
    # Make request
    response=$(curl -s "http://localhost:8888/search?q=music&format=json&engines=$engine" 2>/dev/null)
    
    # Check response
    if [ -n "$response" ]; then
        # Get result count
        count=$(echo "$response" | jq '.results | length' 2>/dev/null || echo "0")
        
        # Check for errors
        unresponsive=$(echo "$response" | jq -r '.unresponsive_engines[]?[0]' 2>/dev/null | grep -c "$engine")
        
        if [ "$unresponsive" -gt 0 ]; then
            error=$(echo "$response" | jq -r ".unresponsive_engines[] | select(.[0] == \"$engine\") | .[1]" 2>/dev/null)
            echo "  ❌ Engine unresponsive: $error"
        elif [ "$count" -gt 0 ]; then
            echo "  ✅ Results found: $count"
            # Show first result
            title=$(echo "$response" | jq -r '.results[0].title // "No title"' 2>/dev/null)
            url=$(echo "$response" | jq -r '.results[0].url // "No URL"' 2>/dev/null)
            echo "     First result: $title"
            echo "     URL: $url"
        else
            echo "  ⚠️  No results returned"
        fi
    else
        echo "  ❌ No response from server"
    fi
    
    echo
done

# Test if general search works
echo "Testing general search (DuckDuckGo)..."
response=$(curl -s "http://localhost:8888/search?q=test&format=json&engines=duckduckgo" 2>/dev/null)
if [ -n "$response" ]; then
    count=$(echo "$response" | jq '.results | length' 2>/dev/null || echo "0")
    if [ "$count" -gt 0 ]; then
        echo "  ✅ General search working: $count results"
    else
        echo "  ⚠️  General search returned no results"
    fi
else
    echo "  ❌ No response from server"
fi