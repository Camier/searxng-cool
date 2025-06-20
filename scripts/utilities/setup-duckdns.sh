#!/bin/bash
# setup-duckdns.sh - Automated DuckDNS setup for SearXNG-Cool
# This script configures DuckDNS dynamic DNS and SSL for public hosting

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Header
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🦆 DuckDNS Setup for SearXNG-Cool 🦆              ║"
echo "║                                                          ║"
echo "║  This script will configure:                             ║"
echo "║  • DuckDNS dynamic DNS                                   ║"
echo "║  • Automatic IP updates                                  ║"
echo "║  • SSL certificate with Let's Encrypt                   ║"
echo "║  • nginx HTTPS configuration                             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running in WSL2
if grep -q microsoft /proc/version; then
    print_status "Detected WSL2 environment"
    IS_WSL2=true
else
    IS_WSL2=false
fi

# Configuration prompts
echo ""
read -p "Enter your DuckDNS subdomain (without .duckdns.org): " DUCKDNS_DOMAIN
read -p "Enter your DuckDNS token: " DUCKDNS_TOKEN
read -p "Enter email for Let's Encrypt notifications: " LETSENCRYPT_EMAIL

# Validate inputs
if [[ -z "$DUCKDNS_DOMAIN" ]] || [[ -z "$DUCKDNS_TOKEN" ]] || [[ -z "$LETSENCRYPT_EMAIL" ]]; then
    print_error "All fields are required!"
    exit 1
fi

FULL_DOMAIN="${DUCKDNS_DOMAIN}.duckdns.org"

print_status "Configuration:"
echo "  Domain: $FULL_DOMAIN"
echo "  Email: $LETSENCRYPT_EMAIL"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Step 1: Create DuckDNS updater
print_status "Creating DuckDNS updater script..."

mkdir -p ~/duckdns
cat > ~/duckdns/duck.sh << EOF
#!/bin/bash
# DuckDNS updater for $FULL_DOMAIN
DUCKDNS_DOMAIN="$DUCKDNS_DOMAIN"
DUCKDNS_TOKEN="$DUCKDNS_TOKEN"

echo url="https://www.duckdns.org/update?domains=\$DUCKDNS_DOMAIN&token=\$DUCKDNS_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -

# Log the result with timestamp
echo "\$(date): \$(cat ~/duckdns/duck.log)" >> ~/duckdns/duck-history.log
EOF

chmod 700 ~/duckdns/duck.sh
print_success "DuckDNS updater created"

# Step 2: Test DuckDNS update
print_status "Testing DuckDNS update..."
~/duckdns/duck.sh

if grep -q "OK" ~/duckdns/duck.log; then
    print_success "DuckDNS update successful!"
else
    print_error "DuckDNS update failed! Check your token."
    cat ~/duckdns/duck.log
    exit 1
fi

# Step 3: Add to crontab
print_status "Adding DuckDNS updater to crontab..."
(crontab -l 2>/dev/null | grep -v "duck.sh"; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -
print_success "Crontab configured for 5-minute updates"

# Step 4: Install required packages
print_status "Installing required packages..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Step 5: Configure firewall
print_status "Configuring firewall rules..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
print_success "Firewall configured"

# Step 6: Stop nginx for certificate generation
print_status "Stopping nginx temporarily..."
sudo systemctl stop nginx || true

# Step 7: Get SSL certificate
print_status "Obtaining SSL certificate from Let's Encrypt..."
sudo certbot certonly --standalone \
    -d "$FULL_DOMAIN" \
    --email "$LETSENCRYPT_EMAIL" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring

if [ $? -eq 0 ]; then
    print_success "SSL certificate obtained successfully!"
else
    print_error "Failed to obtain SSL certificate"
    sudo systemctl start nginx
    exit 1
fi

# Step 8: Create nginx configuration
print_status "Creating nginx configuration..."

sudo tee /etc/nginx/sites-available/searxng-cool-duckdns > /dev/null << EOF
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name $FULL_DOMAIN;
    
    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    server_name $FULL_DOMAIN;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/$FULL_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$FULL_DOMAIN/privkey.pem;
    
    # Strong SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https:;" always;
    
    # Proxy to local SearXNG-Cool nginx
    location / {
        proxy_pass http://127.0.0.1:8095;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for Flask-SocketIO
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        
        # Timeouts for long-running searches
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Monitoring endpoint (restricted)
    location /server-status {
        stub_status on;
        allow 127.0.0.1;
        deny all;
    }
}
EOF

print_success "nginx configuration created"

# Step 9: Enable the new configuration
print_status "Enabling nginx configuration..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/searxng-cool-duckdns /etc/nginx/sites-enabled/

# Step 10: Test nginx configuration
print_status "Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    print_success "nginx configuration is valid"
else
    print_error "nginx configuration test failed"
    exit 1
fi

# Step 11: Start nginx
print_status "Starting nginx..."
sudo systemctl start nginx
sudo systemctl reload nginx
print_success "nginx started and configured"

# Step 12: Set up auto-renewal
print_status "Configuring SSL auto-renewal..."
sudo tee /etc/cron.d/certbot > /dev/null << EOF
# Renew Let's Encrypt certificates twice daily
0 */12 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
EOF
print_success "SSL auto-renewal configured"

# Step 13: Create test script
print_status "Creating test script..."
cat > ~/test-duckdns.sh << EOF
#!/bin/bash
echo "Testing DuckDNS setup for $FULL_DOMAIN"
echo ""
echo "1. Testing DNS resolution..."
nslookup $FULL_DOMAIN
echo ""
echo "2. Testing HTTP redirect..."
curl -I http://$FULL_DOMAIN
echo ""
echo "3. Testing HTTPS..."
curl -I https://$FULL_DOMAIN
echo ""
echo "4. Testing search functionality..."
curl -s "https://$FULL_DOMAIN/search?q=test" | grep -q "SearXNG" && echo "Search works!" || echo "Search failed!"
EOF

chmod +x ~/test-duckdns.sh
print_success "Test script created at ~/test-duckdns.sh"

# Step 14: WSL2 specific instructions
if [ "$IS_WSL2" = true ]; then
    print_warning "WSL2 Detected - Additional Steps Required:"
    echo ""
    echo "1. Configure port forwarding on your router:"
    echo "   - Forward external port 80 → WSL2 IP port 80"
    echo "   - Forward external port 443 → WSL2 IP port 443"
    echo ""
    echo "2. Your WSL2 IP address is:"
    ip addr show eth0 | grep inet | awk '{print "   " $2}' | cut -d/ -f1
    echo ""
    echo "3. In Windows PowerShell (Admin), allow through firewall:"
    echo "   New-NetFirewallRule -DisplayName \"WSL2 HTTPS\" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow"
    echo "   New-NetFirewallRule -DisplayName \"WSL2 HTTP\" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow"
fi

# Final summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ Setup Complete!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
print_success "DuckDNS configured for: $FULL_DOMAIN"
print_success "SSL certificate installed"
print_success "nginx configured with HTTPS"
print_success "Automatic IP updates every 5 minutes"
print_success "SSL auto-renewal configured"
echo ""
echo "🌐 Your SearXNG-Cool instance will be available at:"
echo "   https://$FULL_DOMAIN"
echo ""
echo "📝 Next steps:"
echo "1. Configure port forwarding on your router (80, 443)"
echo "2. Test with: ~/test-duckdns.sh"
echo "3. Monitor logs: tail -f /var/log/nginx/error.log"
echo ""
echo "🔒 Security note: Your instance is now publicly accessible."
echo "   Consider adding authentication if needed."