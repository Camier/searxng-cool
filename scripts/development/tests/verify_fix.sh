#!/bin/bash
# Quick verification that the fix worked

echo "🔍 Verifying SearXNG Music Engine Fix"
echo "===================================="

# Check if radio browser is disabled in config
echo -e "\n📄 Checking configuration..."
if grep -A5 "name: radio browser" /home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core/searx/settings.yml | grep -q "disabled: true"; then
    echo "✅ Radio browser is DISABLED in config"
else
    echo "❌ Radio browser is still ENABLED!"
fi

# Test search results
echo -e "\n🎵 Testing music search..."
RESULTS=$(curl -s "http://localhost:8888/search?q=electronic+music&format=json" 2>/dev/null)

if [ -z "$RESULTS" ]; then
    echo "❌ No response from SearXNG - needs restart"
else
    # Count results by engine
    RADIO_COUNT=$(echo "$RESULTS" | grep -o '"engine":"radio browser"' | wc -l)
    TOTAL_COUNT=$(echo "$RESULTS" | grep -o '"engine":' | wc -l)
    
    if [ "$RADIO_COUNT" -eq 0 ]; then
        echo "✅ SUCCESS: No radio browser results!"
        echo "   Total results: $TOTAL_COUNT"
        
        # Show engines that returned results
        echo -e "\n📊 Active engines:"
        echo "$RESULTS" | grep -o '"engine":"[^"]*"' | sort | uniq -c | sort -nr
    else
        echo "❌ FAIL: Still getting $RADIO_COUNT radio results out of $TOTAL_COUNT total"
        echo "   SearXNG needs to be restarted for changes to take effect"
    fi
fi

echo -e "\n💡 If still seeing radio results:"
echo "   1. sudo systemctl restart searxng"
echo "   2. Wait 10 seconds"  
echo "   3. Run this script again"
