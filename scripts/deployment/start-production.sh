#!/bin/bash
# SearXNG-Cool Production Deployment Script
# Flask-SocketIO + eventlet + Redis message queue

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║            SearXNG-Cool Production Orchestrator             ║${NC}"
echo -e "${PURPLE}║    Flask-SocketIO • eventlet • Redis Message Queue         ║${NC}"
echo -e "${PURPLE}║         Multi-Process Ready • Production Deployment         ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"

cd /home/mik/SEARXNG/searxng-cool

# Production dependency check
echo -e "\n${CYAN}📦 Production Dependencies Check...${NC}"

# Check Redis
echo -e "\n${BLUE}Redis Status:${NC}"
if redis-cli -p 6379 ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis${NC} - Running and ready for message queue"
    
    # Test Redis info
    REDIS_CLIENTS=$(redis-cli info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
    REDIS_MEMORY=$(redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    echo -e "${CYAN}   Connected clients: $REDIS_CLIENTS${NC}"
    echo -e "${CYAN}   Memory usage: $REDIS_MEMORY${NC}"
else
    echo -e "${YELLOW}⚠️  Redis not running. Starting Redis...${NC}"
    redis-server --daemonize yes
    sleep 3
    if redis-cli -p 6379 ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis${NC} - Started successfully"
    else
        echo -e "${RED}❌ Redis${NC} - Failed to start (required for production)"
        exit 1
    fi
fi

# Check SearXNG Core
echo -e "\n${BLUE}SearXNG Core Status:${NC}"
if curl -s http://localhost:8888 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SearXNG Core${NC} - Running on port 8888"
else
    echo -e "${YELLOW}⚠️  SearXNG Core not running${NC}"
    echo -e "${CYAN}ℹ️  Start with: cd searxng-core/searxng-core && source ../searxng-venv/bin/activate && python -m searx.webapp --host 0.0.0.0 --port 8888${NC}"
    echo -e "${CYAN}ℹ️  Production will continue with degraded functionality${NC}"
fi

# Virtual environment and production packages
echo -e "\n${CYAN}🐍 Production Environment Setup...${NC}"
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Virtual Environment${NC} - Found"
    source venv/bin/activate
    
    # Check for production orchestrator
    if [ -f "orchestrator/app_production.py" ]; then
        echo -e "${GREEN}✅ Production Orchestrator${NC} - Available"
    else
        echo -e "${RED}❌ Production Orchestrator${NC} - app_production.py not found"
        exit 1
    fi
    
    # Install production dependencies
    echo -e "\n${CYAN}📦 Installing Production Dependencies...${NC}"
    pip install -q eventlet gunicorn
    
    # Verify eventlet installation
    if python -c "import eventlet" 2>/dev/null; then
        echo -e "${GREEN}✅ eventlet${NC} - Production async server ready"
    else
        echo -e "${RED}❌ eventlet${NC} - Installation failed"
        exit 1
    fi
    
else
    echo -e "${RED}❌ Virtual Environment${NC} - Not found"
    echo -e "${CYAN}ℹ️  Run: python3 -m venv venv && source venv/bin/activate && pip install -r orchestrator/requirements.txt${NC}"
    exit 1
fi

# Configuration validation
echo -e "\n${CYAN}🔧 Production Configuration...${NC}"
if [ -f "config/orchestrator.yml" ]; then
    echo -e "${GREEN}✅ orchestrator.yml${NC} - Configuration file found"
    
    # Verify Redis URL in config
    if grep -q "redis://localhost:6379" config/orchestrator.yml; then
        echo -e "${GREEN}✅ Redis Message Queue${NC} - Configured"
    else
        echo -e "${YELLOW}⚠️  Redis URL${NC} - May need verification"
    fi
else
    echo -e "${YELLOW}⚠️  orchestrator.yml not found${NC}"
    if [ -f "config/orchestrator.yml.example" ]; then
        cp config/orchestrator.yml.example config/orchestrator.yml
        echo -e "${CYAN}ℹ️  Please edit config/orchestrator.yml for production${NC}"
    fi
fi

# nginx production check
echo -e "\n${BLUE}nginx Production Status:${NC}"
if systemctl is-active nginx > /dev/null 2>&1; then
    echo -e "${GREEN}✅ nginx${NC} - Service active"
    
    if [ -f "/etc/nginx/sites-enabled/searxng-cool" ]; then
        echo -e "${GREEN}✅ SearXNG-Cool Config${NC} - Enabled"
        
        # Check for sticky sessions (production WebSocket requirement)
        if grep -q "ip_hash" /etc/nginx/sites-enabled/searxng-cool 2>/dev/null; then
            echo -e "${GREEN}✅ Sticky Sessions${NC} - Configured for WebSocket"
        else
            echo -e "${YELLOW}⚠️  Sticky Sessions${NC} - Not configured (recommended for WebSocket)"
            echo -e "${CYAN}ℹ️  Add 'ip_hash;' to upstream flask_orchestrator block${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  SearXNG-Cool Config${NC} - Not enabled"
    fi
else
    echo -e "${RED}❌ nginx${NC} - Service not active"
fi

# Port conflict resolution
echo -e "\n${CYAN}🔌 Production Port Management...${NC}"
PRODUCTION_PORT=8889

if netstat -tln | grep ":$PRODUCTION_PORT " > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $PRODUCTION_PORT in use${NC}"
    
    # Kill any existing Flask processes
    if pgrep -f "app.*$PRODUCTION_PORT" > /dev/null; then
        echo -e "${CYAN}ℹ️  Stopping existing Flask processes...${NC}"
        pkill -f "app.*$PRODUCTION_PORT" || true
        sleep 3
    fi
fi

# Production deployment options
echo -e "\n${PURPLE}🚀 Production Deployment Options:${NC}"
echo -e "${CYAN}Choose deployment method:${NC}"
echo -e "  1) ${GREEN}Flask-SocketIO + eventlet${NC} (Recommended for WebSocket)"
echo -e "  2) ${BLUE}Gunicorn + eventlet workers${NC} (Alternative production setup)"
echo -e "  3) ${YELLOW}Development mode${NC} (Testing only)"

read -p "Enter choice (1-3, default: 1): " DEPLOY_CHOICE
DEPLOY_CHOICE=${DEPLOY_CHOICE:-1}

case $DEPLOY_CHOICE in
    1)
        echo -e "\n${GREEN}🎯 Starting Flask-SocketIO Production Server${NC}"
        echo -e "${CYAN}Features:${NC}"
        echo -e "  • ${GREEN}Redis Message Queue${NC} - Multi-process WebSocket support"
        echo -e "  • ${GREEN}eventlet Async Server${NC} - High-performance async I/O"
        echo -e "  • ${GREEN}Connection Pooling${NC} - Redis (50 conn) + Database (30 conn)"
        echo -e "  • ${GREEN}Production Logging${NC} - Structured JSON logs"
        echo -e "  • ${GREEN}Health Monitoring${NC} - /health, /metrics endpoints"
        
        echo -e "\n${CYAN}Access URLs:${NC}"
        echo -e "  • ${GREEN}nginx Reverse Proxy${NC}: http://localhost:8095"
        echo -e "  • ${GREEN}Production Orchestrator${NC}: http://localhost:8889"
        echo -e "  • ${GREEN}Health Check${NC}: http://localhost:8889/health"
        echo -e "  • ${GREEN}Metrics${NC}: http://localhost:8889/metrics"
        
        echo -e "\n${BLUE}Starting Production Orchestrator...${NC}"
        cd orchestrator
        python app_production.py
        ;;
        
    2)
        echo -e "\n${BLUE}🎯 Starting Gunicorn Production Server${NC}"
        echo -e "${CYAN}Configuration: 4 eventlet workers, production settings${NC}"
        
        cd orchestrator
        gunicorn --worker-class eventlet \
                 --workers 4 \
                 --bind 0.0.0.0:8889 \
                 --timeout 60 \
                 --keepalive 5 \
                 --max-requests 1000 \
                 --max-requests-jitter 100 \
                 --preload \
                 --access-logfile - \
                 --error-logfile - \
                 app_production:app
        ;;
        
    3)
        echo -e "\n${YELLOW}🎯 Starting Development Mode${NC}"
        echo -e "${CYAN}⚠️  Not recommended for production use${NC}"
        
        cd orchestrator
        python app_production.py
        ;;
        
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac