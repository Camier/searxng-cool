#!/bin/bash

# JWT token
JWT_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MDI1NTE5MiwianRpIjoiYzczNzdhNTAtNzI0My00OTJkLTgxNmYtYWYxMDk1ZGNlZWYwIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImFkbWluIiwibmJmIjoxNzUwMjU1MTkyLCJjc3JmIjoiMzY5NmY2Y2YtMWM2MS00OTNiLTgwYTgtNzczYTczMGRiNGNkIiwiZXhwIjoxNzUwMjU4NzkyfQ.DlB1d0gmfrydm_mDJ0T5MPqv0wJnNt_0oTMyD483Bj0"

# Base URL
BASE_URL="http://localhost:8889/api/music/search"

# List of engines to test
ENGINES=(
    "discogs music"
    "jamendo music"
    "soundcloud"
    "bandcamp"
    "genius lyrics"
    "youtube music"
    "soundcloud enhanced"
    "bandcamp enhanced"
    "mixcloud"
    "mixcloud enhanced"
    "radio paradise"
)

# Test queries
QUERIES=("electronic" "jazz" "rock" "test")

# Create results directory
mkdir -p music_engine_results

echo "Testing Music Engines - $(date)" > music_engine_results/summary.txt
echo "=================================" >> music_engine_results/summary.txt

# Function to test an engine
test_engine() {
    local engine="$1"
    local query="$2"
    local filename=$(echo "$engine" | tr ' ' '_')_$(echo "$query" | tr ' ' '_').json
    
    echo "Testing: $engine with query: $query"
    
    # Make the API call
    curl -s -X POST "$BASE_URL" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"q\": \"$query\", \"engines\": [\"$engine\"], \"page\": 1}" \
        > "music_engine_results/$filename"
    
    # Check if we got results
    if [ -f "music_engine_results/$filename" ]; then
        # Parse the response to check for errors or results
        local error=$(jq -r '.error // empty' "music_engine_results/$filename" 2>/dev/null)
        local result_count=$(jq -r '.results | length // 0' "music_engine_results/$filename" 2>/dev/null)
        
        if [ -n "$error" ]; then
            echo "  ERROR: $error"
            echo "  - $engine ($query): ERROR - $error" >> music_engine_results/summary.txt
        elif [ "$result_count" -gt 0 ]; then
            echo "  SUCCESS: Found $result_count results"
            echo "  - $engine ($query): SUCCESS - $result_count results" >> music_engine_results/summary.txt
            
            # Sample first result
            local first_title=$(jq -r '.results[0].title // "No title"' "music_engine_results/$filename" 2>/dev/null)
            local first_artist=$(jq -r '.results[0].artist // "No artist"' "music_engine_results/$filename" 2>/dev/null)
            echo "    Sample: $first_artist - $first_title"
        else
            echo "  NO RESULTS"
            echo "  - $engine ($query): NO RESULTS" >> music_engine_results/summary.txt
        fi
    else
        echo "  FAILED to create output file"
        echo "  - $engine ($query): FAILED" >> music_engine_results/summary.txt
    fi
    
    echo ""
    sleep 1  # Small delay between requests
}

# Test each engine with each query
for engine in "${ENGINES[@]}"; do
    echo "" >> music_engine_results/summary.txt
    echo "Engine: $engine" >> music_engine_results/summary.txt
    echo "-------------------" >> music_engine_results/summary.txt
    
    for query in "${QUERIES[@]}"; do
        test_engine "$engine" "$query"
    done
done

echo "Testing complete! Results saved in music_engine_results/"
echo "Summary saved in music_engine_results/summary.txt"