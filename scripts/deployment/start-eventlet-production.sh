#!/bin/bash
# SearXNG-Cool Eventlet Production Deployment
# High-performance WebSocket-ready deployment with eventlet optimizations

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║         SearXNG-Cool Eventlet Production Deployment           ║${NC}"
echo -e "${PURPLE}║    🚀 10,000+ Concurrent WebSockets • 4KB/Connection          ║${NC}"
echo -e "${PURPLE}║    ⚡ Async I/O • Redis Message Queue • Background Tasks     ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"

cd /home/mik/SEARXNG/searxng-cool

# Set production environment for eventlet
export FLASK_ENV=production
export PYTHONUNBUFFERED=1
export EVENTLET_THREADPOOL_SIZE=100

# Linux optimization (WSL2)
if [[ "$(uname)" == "Linux" ]]; then
    # Use poll instead of epoll for WSL2 compatibility
    export EVENTLET_HUB=poll
    echo -e "${GREEN}✅ Linux poll optimization enabled (WSL2 compatible)${NC}"
fi

# Clean up any existing processes
echo -e "\n${CYAN}🧹 Cleaning up existing processes...${NC}"
pkill -f "app_.*\.py" || true
sleep 2

# Dependency check
echo -e "\n${CYAN}📦 Eventlet Dependencies Check...${NC}"

# Virtual environment
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Virtual Environment${NC} - Found"
    source venv/bin/activate
else
    echo -e "${RED}❌ Virtual Environment${NC} - Not found"
    exit 1
fi

# Install eventlet with proper dependencies
echo -e "\n${BLUE}Installing Eventlet Production Stack...${NC}"
pip install -q eventlet==0.33.3
pip install -q dnspython==2.4.2
pip install -q flask-socketio[eventlet]==5.5.1

# Verify eventlet installation
if python -c "import eventlet; print('Eventlet version:', eventlet.__version__)" 2>/dev/null; then
    echo -e "${GREEN}✅ eventlet${NC} - Production async server ready"
else
    echo -e "${RED}❌ eventlet${NC} - Installation failed"
    exit 1
fi

# Verify dnspython for async DNS
if python -c "import dns.resolver" 2>/dev/null; then
    echo -e "${GREEN}✅ dnspython${NC} - Async DNS ready"
else
    echo -e "${RED}❌ dnspython${NC} - Required for eventlet DNS resolution"
    exit 1
fi

# Service dependency checks
echo -e "\n${CYAN}🔧 Service Dependencies...${NC}"

# Redis check
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis${NC} - Message queue ready"
    
    # Redis info
    REDIS_MEMORY=$(redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    REDIS_CLIENTS=$(redis-cli info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
    echo -e "${CYAN}   Memory: $REDIS_MEMORY, Clients: $REDIS_CLIENTS${NC}"
else
    echo -e "${YELLOW}⚠️  Redis not running. Starting...${NC}"
    redis-server --daemonize yes
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis${NC} - Started successfully"
    else
        echo -e "${RED}❌ Redis${NC} - Failed to start"
        exit 1
    fi
fi

# SearXNG check
if curl -s http://localhost:8888 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SearXNG Core${NC} - Search engine ready"
else
    echo -e "${YELLOW}⚠️  SearXNG Core${NC} - Not running (degraded mode)"
fi

# nginx check
if systemctl is-active nginx > /dev/null 2>&1; then
    echo -e "${GREEN}✅ nginx${NC} - Reverse proxy ready"
    
    # Check for sticky sessions
    if grep -q "ip_hash" /etc/nginx/sites-enabled/searxng-cool 2>/dev/null; then
        echo -e "${GREEN}✅ Sticky Sessions${NC} - WebSocket load balancing ready"
    else
        echo -e "${YELLOW}⚠️  Sticky Sessions${NC} - Add 'ip_hash;' to nginx upstream"
    fi
else
    echo -e "${YELLOW}⚠️  nginx${NC} - Not active"
fi

# Port management
echo -e "\n${CYAN}🔌 Port Management...${NC}"
TARGET_PORT=8889

if netstat -tln | grep ":$TARGET_PORT " > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $TARGET_PORT in use${NC}"
    if pgrep -f ".*$TARGET_PORT" > /dev/null; then
        echo -e "${CYAN}ℹ️  Killing existing process...${NC}"
        pkill -f ".*$TARGET_PORT" || true
        sleep 2
    fi
fi

# Configuration validation
echo -e "\n${CYAN}⚙️  Configuration Validation...${NC}"
if [ -f "config/orchestrator.yml" ]; then
    echo -e "${GREEN}✅ orchestrator.yml${NC} - Configuration found"
    
    if grep -q "redis://localhost:6379" config/orchestrator.yml; then
        echo -e "${GREEN}✅ Redis Message Queue${NC} - Configured for eventlet"
    fi
else
    echo -e "${YELLOW}⚠️  Configuration${NC} - Using defaults"
fi

# Eventlet optimizations info
echo -e "\n${PURPLE}⚡ Eventlet Production Features:${NC}"
echo -e "  • ${GREEN}Async I/O${NC}: Non-blocking socket operations"
echo -e "  • ${GREEN}Greenlets${NC}: Lightweight coroutines (~4KB each)"
echo -e "  • ${GREEN}WebSocket Native${NC}: Built-in WebSocket support"
echo -e "  • ${GREEN}Connection Scaling${NC}: 10,000+ concurrent connections"
echo -e "  • ${GREEN}Memory Efficient${NC}: Minimal memory per connection"
echo -e "  • ${GREEN}Redis Message Queue${NC}: Multi-process WebSocket scaling"
echo -e "  • ${GREEN}Background Tasks${NC}: Non-blocking background processing"

echo -e "\n${CYAN}🎯 Performance Expectations:${NC}"
echo -e "  • ${CYAN}Concurrent WebSockets${NC}: 10,000+ connections"
echo -e "  • ${CYAN}Memory per Connection${NC}: ~4KB (vs 8MB threads)"
echo -e "  • ${CYAN}Response Time${NC}: Sub-millisecond message routing"
echo -e "  • ${CYAN}CPU Usage${NC}: Single-threaded event loop efficiency"

echo -e "\n${CYAN}🔗 Access URLs:${NC}"
echo -e "  • ${GREEN}nginx Entry Point${NC}: http://localhost:8095"
echo -e "  • ${GREEN}Eventlet Orchestrator${NC}: http://localhost:8889"
echo -e "  • ${GREEN}Health Check${NC}: http://localhost:8889/health"
echo -e "  • ${GREEN}Eventlet Stats${NC}: http://localhost:8889/eventlet-stats"
echo -e "  • ${GREEN}WebSocket Test${NC}: ws://localhost:8889/socket.io/"

echo -e "\n${BLUE}🚀 Starting Eventlet Production Server...${NC}"

# Check for eventlet optimized app
if [ -f "orchestrator/app_eventlet_optimized.py" ]; then
    echo -e "${GREEN}✅ Eventlet Optimized App${NC} - Using production version"
    python orchestrator/app_eventlet_optimized.py
else
    echo -e "${YELLOW}⚠️  Using standard production app${NC}"
    python orchestrator/app_production.py
fi