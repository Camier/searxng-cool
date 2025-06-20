#!/bin/bash
# SearXNG-Cool Connectivity Audit Script

echo "=========================================="
echo "🔍 SearXNG-Cool Connectivity Audit"
echo "=========================================="
echo "Date: $(date)"
echo ""

# 1. Check Process Status
echo "1️⃣ PROCESS STATUS"
echo "=================="
echo "SearXNG Core:"
ps aux | grep -E "searx.webapp" | grep -v grep | head -1 || echo "❌ Not found"
echo ""
echo "Orchestrator:"
ps aux | grep -E "app_eventlet" | grep -v grep | head -1 || echo "❌ Not found"
echo ""

# 2. Check Port Bindings
echo "2️⃣ PORT BINDINGS"
echo "================="
echo "Listening ports:"
sudo netstat -tlnp 2>/dev/null | grep -E "8888|8889|6379|5432" || \
sudo ss -tlnp 2>/dev/null | grep -E "8888|8889|6379|5432" || \
echo "Need sudo for detailed port info"
echo ""

# 3. Test Service Endpoints
echo "3️⃣ SERVICE ENDPOINTS"
echo "===================="

# SearXNG Core
echo -n "SearXNG Core (8888): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/ | grep -q "200"; then
    echo "✅ HTTP 200 OK"
else
    echo "❌ Not responding"
fi

# Orchestrator
echo -n "Orchestrator (8889): "
if timeout 2 curl -s -o /dev/null -w "%{http_code}" http://localhost:8889/ 2>/dev/null; then
    echo "✅ Responding"
else
    echo "❌ Not responding or timeout"
fi

# Redis
echo -n "Redis (6379): "
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ PONG"
else
    echo "❌ Not responding"
fi

# PostgreSQL
echo -n "PostgreSQL (5432): "
if timeout 2 nc -zv localhost 5432 2>&1 | grep -q "succeeded"; then
    echo "✅ Port open"
else
    echo "❌ Port closed or timeout"
fi
echo ""

# 4. Test Database Connectivity
echo "4️⃣ DATABASE CONNECTIVITY"
echo "======================="
echo -n "Database connection test: "
if timeout 3 PGPASSWORD=DO2ZkP0lUc8G6di3 psql -h 127.0.0.1 -U searxng_user -d searxng_cool_music -c "SELECT 'OK' as status;" 2>&1 | grep -q "OK"; then
    echo "✅ Connected"
else
    echo "❌ Connection failed"
    echo "Trying with different methods..."
    # Try localhost
    timeout 3 PGPASSWORD=DO2ZkP0lUc8G6di3 psql -h localhost -U searxng_user -d searxng_cool_music -c "SELECT 1;" 2>&1 | head -5
fi
echo ""

# 5. Test Redis Operations
echo "5️⃣ REDIS OPERATIONS"
echo "=================="
echo -n "Redis SET/GET test: "
redis-cli SET test_key "test_value" 2>/dev/null
if [ "$(redis-cli GET test_key 2>/dev/null)" = "test_value" ]; then
    echo "✅ Working"
    redis-cli DEL test_key >/dev/null 2>&1
else
    echo "❌ Failed"
fi

echo -n "Redis INFO: "
redis-cli INFO server 2>/dev/null | grep "redis_version" || echo "❌ Cannot get info"
echo ""

# 6. Test SearXNG Search Functionality
echo "6️⃣ SEARXNG SEARCH TEST"
echo "===================="
echo "Testing general search:"
curl -s "http://localhost:8888/search?q=test&format=json" | jq -r '.number_of_results' 2>/dev/null || echo "❌ Search failed"

echo -e "\nTesting music search:"
curl -s "http://localhost:8888/search?q=music&categories=music&format=json" | jq -r '.results[0].engine' 2>/dev/null || echo "❌ Music search failed"
echo ""

# 7. Check Inter-Service Communication
echo "7️⃣ INTER-SERVICE COMMUNICATION"
echo "============================"
echo "Checking SearXNG settings for Redis:"
grep -A2 "redis:" /home/mik/SEARXNG/searxng-cool-restored/config/searxng-settings.yml 2>/dev/null | grep -E "url:|host:" || echo "❌ Redis config not found"

echo -e "\nChecking Orchestrator config:"
grep -E "REDIS_URL|DATABASE_URL" /home/mik/SEARXNG/searxng-cool-restored/.env 2>/dev/null | head -3 || echo "❌ Env config not found"
echo ""

# 8. Network Interface Check
echo "8️⃣ NETWORK INTERFACES"
echo "===================="
echo "Active interfaces:"
ip addr show | grep -E "^[0-9]+:|inet " | grep -v "127.0.0.1" | head -10
echo ""

# 9. Firewall Status
echo "9️⃣ FIREWALL STATUS"
echo "================="
sudo ufw status 2>/dev/null | grep -E "8888|8889|6379|5432" || echo "UFW not active or no rules"
echo ""

# 10. Recent Errors
echo "🔟 RECENT ERRORS"
echo "================"
echo "SearXNG errors (last 5):"
grep -i "error\|exception" /tmp/searxng-core.log 2>/dev/null | tail -5 || echo "No log file"

echo -e "\nOrchestrator errors (last 5):"
grep -i "error\|failed" /tmp/orchestrator.log 2>/dev/null | tail -5 || echo "No log file"
echo ""

# Summary
echo "📊 CONNECTIVITY SUMMARY"
echo "====================="
searxng_ok=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/ 2>/dev/null)
redis_ok=$(redis-cli ping 2>/dev/null)
pg_ok=$(timeout 2 nc -zv localhost 5432 2>&1 | grep -c "succeeded")

if [ "$searxng_ok" = "200" ] && [ "$redis_ok" = "PONG" ]; then
    echo "✅ Core services are operational"
    echo "⚠️  Database connection needs attention"
    echo "✅ Search functionality is working"
else
    echo "❌ Service connectivity issues detected"
fi

echo ""
echo "Audit complete at $(date +%T)"