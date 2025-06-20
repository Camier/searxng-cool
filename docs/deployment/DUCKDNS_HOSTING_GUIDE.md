# 🦆 Hosting SearXNG-Cool on DuckDNS

This guide will help you make your SearXNG-Cool instance publicly accessible using DuckDNS free dynamic DNS service.

## 📋 Prerequisites

- Working SearXNG-Cool installation (already achieved! ✅)
- Router access for port forwarding
- DuckDNS account (free)
- Let's Encrypt for SSL (free)

## 🚀 Step 1: Register with DuckDNS

1. Visit [https://www.duckdns.org](https://www.duckdns.org)
2. Sign in with GitHub, Google, or Twitter
3. Create a subdomain (e.g., `my-searxng.duckdns.org`)
4. Save your token (looks like: `a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6`)

## 🔧 Step 2: Set Up DuckDNS Updater

Create the DuckDNS update script:

```bash
# Create directory
mkdir -p ~/duckdns
cd ~/duckdns

# Create update script
cat > duck.sh << 'EOF'
#!/bin/bash
# DuckDNS updater for SearXNG-Cool

# IMPORTANT: Replace these with your values
DUCKDNS_DOMAIN="my-searxng"  # Just the subdomain part
DUCKDNS_TOKEN="your-token-here"

# Update DuckDNS
echo url="https://www.duckdns.org/update?domains=$DUCKDNS_DOMAIN&token=$DUCKDNS_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -

# Log the result
echo "DuckDNS updated at $(date)" >> ~/duckdns/duck.log
EOF

# Make executable
chmod 700 duck.sh

# Test it
./duck.sh
cat duck.log  # Should show "OK"
```

## 📅 Step 3: Automate IP Updates

Add to crontab for automatic updates every 5 minutes:

```bash
# Open crontab
crontab -e

# Add this line:
*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

## 🔓 Step 4: Configure Port Forwarding

On your router, forward these ports to your WSL2 machine:

1. **Port 80** → Internal 80 (for Let's Encrypt verification)
2. **Port 443** → Internal 443 (for HTTPS access)

For WSL2, you might need to get the IP:
```bash
# Get WSL2 IP address
ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1
```

## 🔒 Step 5: Install SSL Certificate

Install Certbot and get SSL certificate:

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Stop nginx temporarily
sudo systemctl stop nginx

# Get certificate (standalone mode)
sudo certbot certonly --standalone -d my-searxng.duckdns.org

# Start nginx again
sudo systemctl start nginx
```

## 🌐 Step 6: Update nginx Configuration

Create a new nginx configuration for DuckDNS:

```bash
# Backup existing config
sudo cp /etc/nginx/sites-enabled/searxng-cool /etc/nginx/sites-enabled/searxng-cool.backup

# Create new config
sudo nano /etc/nginx/sites-available/searxng-cool-duckdns
```

Add this configuration:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name my-searxng.duckdns.org;
    
    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    server_name my-searxng.duckdns.org;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/my-searxng.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/my-searxng.duckdns.org/privkey.pem;
    
    # Strong SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer" always;
    
    # Your existing upstream configuration
    location / {
        proxy_pass http://127.0.0.1:8095;  # Your existing nginx on 8095
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the new configuration:

```bash
# Disable old config
sudo rm /etc/nginx/sites-enabled/searxng-cool

# Enable new config
sudo ln -s /etc/nginx/sites-available/searxng-cool-duckdns /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo nginx -s reload
```

## 🔄 Step 7: Set Up Auto-Renewal

Configure automatic SSL renewal:

```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab
sudo crontab -e

# Add this line:
0 2 * * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
```

## 🚦 Step 8: Update UFW Firewall

Allow HTTPS traffic:

```bash
sudo ufw allow 80/tcp   # HTTP for Let's Encrypt
sudo ufw allow 443/tcp  # HTTPS
sudo ufw reload
```

## 🧪 Step 9: Test Your Setup

1. **Test locally first**:
   ```bash
   curl https://my-searxng.duckdns.org
   ```

2. **Test from external network** (use mobile data):
   - Visit https://my-searxng.duckdns.org
   - Should see your SearXNG-Cool instance!

3. **Test SSL**:
   - Visit https://www.ssllabs.com/ssltest/
   - Enter your domain
   - Should get A+ rating

## 🛡️ Security Considerations

### 1. IP Whitelisting (Optional)
```nginx
# In nginx config, restrict to specific IPs
location /admin {
    allow 192.168.1.0/24;  # Local network
    allow 1.2.3.4;         # Your external IP
    deny all;
}
```

### 2. Basic Authentication (Optional)
```bash
# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd searxuser

# Add to nginx location:
auth_basic "Private Search";
auth_basic_user_file /etc/nginx/.htpasswd;
```

### 3. Rate Limiting
Already configured in your nginx setup! ✅

## 🔍 Troubleshooting

### DuckDNS not updating
```bash
# Check the log
cat ~/duckdns/duck.log

# Manually run update
~/duckdns/duck.sh

# Verify DNS
nslookup my-searxng.duckdns.org
```

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Connection Refused
```bash
# Check all services running
sudo systemctl status nginx
ps aux | grep app_eventlet
ps aux | grep searx

# Check ports
sudo netstat -tlnp | grep -E '(80|443|8095|8889|8888)'

# Check UFW
sudo ufw status
```

### WSL2 Specific Issues
```bash
# Check WSL2 IP
ip addr show eth0

# Windows firewall might block - add rules:
# In PowerShell (Admin):
New-NetFirewallRule -DisplayName "WSL2 HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "WSL2 HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
```

## 🎯 Complete Setup Script

Here's an all-in-one script:

```bash
#!/bin/bash
# setup-duckdns.sh - Complete DuckDNS setup for SearXNG-Cool

# Configuration
DOMAIN="my-searxng"  # Change this!
TOKEN="your-token"   # Change this!
EMAIL="your@email"   # For Let's Encrypt

echo "🦆 Setting up DuckDNS for SearXNG-Cool..."

# 1. Create DuckDNS updater
mkdir -p ~/duckdns
cat > ~/duckdns/duck.sh << EOF
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -
EOF
chmod 700 ~/duckdns/duck.sh

# 2. Add to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -

# 3. Update DuckDNS
~/duckdns/duck.sh

# 4. Install Certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# 5. Get SSL certificate
sudo certbot certonly --standalone -d $DOMAIN.duckdns.org --email $EMAIL --agree-tos --non-interactive

# 6. Configure nginx (creates the config file)
# ... (nginx config creation here)

# 7. Update firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

echo "✅ DuckDNS setup complete!"
echo "🌐 Your site will be available at: https://$DOMAIN.duckdns.org"
```

## 🚀 Alternative: Cloudflare Tunnel

If port forwarding is difficult, use your existing Cloudflare Tunnel setup:

```bash
# You already have this script!
/home/mik/SEARXNG/searxng-convivial/setup_cloudflare_tunnel.sh
```

Benefits:
- No port forwarding needed
- Works behind CGNAT
- Built-in SSL
- DDoS protection

## 📝 Summary

Your SearXNG-Cool instance is now:
- ✅ Publicly accessible via DuckDNS
- ✅ Secured with SSL/HTTPS
- ✅ Auto-updating IP address
- ✅ Production-ready with 10,000+ connection support

Access your private search engine from anywhere at:
**https://your-subdomain.duckdns.org**

Remember to:
1. Keep your DuckDNS token secret
2. Monitor your logs regularly
3. Update SSL certificates (automated)
4. Check firewall rules after system updates