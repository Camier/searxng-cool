# 🚀 nginx Advanced Configuration Master Guide for SearXNG-Cool

## Table of Contents
1. [Core nginx Concepts & Architecture](#core-concepts)
2. [Advanced Reverse Proxy Patterns](#reverse-proxy-patterns)
3. [Security Hardening & Headers](#security-hardening)
4. [Performance Optimization Extreme](#performance-optimization)
5. [Rate Limiting & DDoS Protection](#rate-limiting)
6. [SSL/TLS Advanced Configuration](#ssl-tls-configuration)
7. [WebSocket & Real-time Features](#websocket-configuration)
8. [Load Balancing & High Availability](#load-balancing)
9. [Caching Strategies](#caching-strategies)
10. [Error Handling & Fallback Patterns](#error-handling)
11. [Monitoring & Debugging](#monitoring-debugging)
12. [SearXNG-Cool Specific Patterns](#searxng-specific)

---

## Core Concepts & Architecture {#core-concepts}

### nginx Request Processing Phases
Understanding nginx's request processing phases is crucial for advanced configurations:

```nginx
# nginx processes requests through these phases:
# 1. NGX_HTTP_POST_READ_PHASE - Reading request headers
# 2. NGX_HTTP_SERVER_REWRITE_PHASE - Server-level rewrite
# 3. NGX_HTTP_FIND_CONFIG_PHASE - Finding location configuration
# 4. NGX_HTTP_REWRITE_PHASE - Location-level rewrite
# 5. NGX_HTTP_POST_REWRITE_PHASE - Post-rewrite processing
# 6. NGX_HTTP_PREACCESS_PHASE - Pre-access checks (limit_req, limit_conn)
# 7. NGX_HTTP_ACCESS_PHASE - Access control (allow/deny, auth_basic)
# 8. NGX_HTTP_POST_ACCESS_PHASE - Post-access processing
# 9. NGX_HTTP_PRECONTENT_PHASE - try_files processing
# 10. NGX_HTTP_CONTENT_PHASE - Content generation
# 11. NGX_HTTP_LOG_PHASE - Access logging
```

### Variable Evaluation & Performance
```nginx
# Variables are evaluated at runtime - understand the performance impact
set $backend_protocol "http";
set $backend_host "flask_orchestrator";

# BAD: Variable in proxy_pass causes re-resolution on each request
proxy_pass $backend_protocol://$backend_host;

# GOOD: Static upstream reference
proxy_pass http://flask_orchestrator;

# Advanced: Using map for conditional logic without if
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

# Complex variable mapping for routing decisions
map $request_uri $backend_pool {
    ~^/api/     flask_orchestrator;
    ~^/search   searxng_core;
    default     flask_orchestrator;
}
```

## Advanced Reverse Proxy Patterns {#reverse-proxy-patterns}

### Multi-Tier Proxy Architecture
```nginx
# Advanced proxy configuration for SearXNG-Cool
upstream flask_orchestrator {
    # Connection pooling and keepalive
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;
    
    # Health check parameters
    server 127.0.0.1:8889 max_fails=3 fail_timeout=30s weight=5;
    
    # Backup server for high availability
    # server 127.0.0.1:8890 backup;
    
    # Load balancing algorithm
    least_conn;  # or ip_hash for session persistence
}

upstream searxng_core {
    keepalive 16;
    server 127.0.0.1:8888 max_fails=2 fail_timeout=15s;
}

# Advanced proxy headers for proper forwarding
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $server_name;
proxy_set_header X-Forwarded-Port $server_port;
proxy_set_header X-Original-URI $request_uri;
proxy_set_header X-Request-ID $request_id;  # For request tracing

# Connection optimization
proxy_http_version 1.1;
proxy_set_header Connection "";  # Clear connection header for keepalive

# Timeouts optimization for different scenarios
proxy_connect_timeout 5s;       # Quick fail for dead backends
proxy_send_timeout 60s;         # Time to send request to backend
proxy_read_timeout 60s;         # Time to receive response from backend

# Buffer optimization for performance
proxy_buffering on;
proxy_buffer_size 4k;           # First part of response
proxy_buffers 8 4k;             # Number and size of buffers
proxy_busy_buffers_size 8k;     # Size of busy buffers
proxy_temp_file_write_size 8k;  # Temp file write size
proxy_max_temp_file_size 1024m; # Max temp file size

# Request/Response modification
proxy_request_buffering on;     # Buffer entire request before sending
proxy_ignore_headers X-Accel-Expires Expires Cache-Control Set-Cookie;
```

### Conditional Proxy Routing
```nginx
# Advanced routing based on multiple conditions
map $http_user_agent $is_bot {
    default 0;
    ~*bot   1;
    ~*crawl 1;
    ~*spider 1;
}

map $request_method $is_post {
    default 0;
    POST    1;
}

# Composite routing decision
map $is_bot:$is_post $route_backend {
    "1:0"   searxng_core;      # Bots doing GET
    "1:1"   flask_orchestrator; # Bots doing POST (block?)
    default flask_orchestrator;
}

server {
    location / {
        proxy_pass http://$route_backend;
    }
}
```

### Request Coalescing & Caching
```nginx
# Prevent thundering herd with proxy_cache_lock
proxy_cache_path /var/cache/nginx/searxng 
    levels=1:2 
    keys_zone=searxng_cache:10m 
    max_size=1g 
    inactive=60m 
    use_temp_path=off;

location /search {
    proxy_cache searxng_cache;
    proxy_cache_key "$scheme$request_method$host$request_uri$arg_q";
    proxy_cache_valid 200 10m;
    proxy_cache_valid 404 1m;
    proxy_cache_valid any 30s;
    
    # Request coalescing - only one request goes to backend
    proxy_cache_lock on;
    proxy_cache_lock_timeout 5s;
    proxy_cache_lock_age 10s;
    
    # Serve stale content while updating
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    proxy_cache_background_update on;
    
    # Cache bypass conditions
    proxy_cache_bypass $http_pragma $http_authorization;
    
    # Add cache status header
    add_header X-Cache-Status $upstream_cache_status always;
    
    proxy_pass http://searxng_core;
}
```

## Security Hardening & Headers {#security-hardening}

### Comprehensive Security Headers
```nginx
# Security headers map for easy management
map $sent_http_content_type $content_security_policy {
    default "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";
    ~*text/html "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' 'nonce-$request_id'; style-src 'self' 'unsafe-inline' 'nonce-$request_id'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests";
}

# Apply security headers
add_header Content-Security-Policy $content_security_policy always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;

# Remove sensitive headers
proxy_hide_header X-Powered-By;
proxy_hide_header Server;
proxy_hide_header X-AspNet-Version;
proxy_hide_header X-AspNetMvc-Version;

# CORS configuration for API endpoints
map $http_origin $cors_header {
    default "";
    "~^https://alfredisgone\.duckdns\.org$" "$http_origin";
    "~^https://localhost(:[0-9]+)?$" "$http_origin";
}

location /api/ {
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' $cors_header always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        add_header 'Access-Control-Max-Age' 1728000 always;
        add_header 'Content-Type' 'text/plain; charset=utf-8' always;
        add_header 'Content-Length' 0 always;
        return 204;
    }
    
    add_header 'Access-Control-Allow-Origin' $cors_header always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
    
    proxy_pass http://flask_orchestrator;
}
```

### Request Filtering & Validation
```nginx
# Block common attack patterns
location ~ \.(asp|aspx|jsp|cgi|php|phtml|php3|php4|php5|php6|php7)$ {
    return 444;  # Close connection without response
}

# Block access to hidden files
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# SQL injection protection
if ($args ~* "(union.*select|select.*from|insert.*into|delete.*from|drop.*table|script.*>|<.*script|;.*shutdown|;.*drop)") {
    return 403;
}

# File injection protection
if ($request_uri ~* "(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f|%2e%2e%5c)") {
    return 403;
}

# User agent filtering
map $http_user_agent $blocked_agent {
    default 0;
    ~*malicious 1;
    ~*scanner   1;
    ~*exploit   1;
}

if ($blocked_agent) {
    return 403;
}
```

## Performance Optimization Extreme {#performance-optimization}

### Worker Process & Connection Tuning
```nginx
# nginx.conf global settings
user www-data;
worker_processes auto;  # One per CPU core
worker_cpu_affinity auto;
worker_rlimit_nofile 65535;  # Max file descriptors

events {
    worker_connections 10240;  # Max connections per worker
    multi_accept on;          # Accept multiple connections
    use epoll;                # Efficient connection method for Linux
    epoll_events 512;         # Number of events to process at once
}

http {
    # File handling optimization
    sendfile on;              # Zero-copy file transmission
    tcp_nopush on;           # Send headers in one packet
    tcp_nodelay on;          # Don't buffer data-sends
    
    # Keepalive optimization
    keepalive_timeout 65;
    keepalive_requests 100;
    reset_timedout_connection on;
    
    # Client optimization
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;
    
    # Buffer sizes
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    
    # Output buffers
    postpone_output 1460;     # Optimize for TCP packet size
    
    # File cache
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
```

### Gzip Compression Optimization
```nginx
# Compression settings
gzip on;
gzip_vary on;           # Vary: Accept-Encoding header
gzip_proxied any;       # Compress proxied requests
gzip_comp_level 6;      # Balance between CPU and compression
gzip_types 
    text/plain
    text/css
    text/xml
    text/javascript
    application/javascript
    application/xml+rss
    application/json
    application/x-font-ttf
    application/vnd.ms-fontobject
    font/opentype
    image/svg+xml
    image/x-icon;
gzip_min_length 1024;   # Don't compress small files
gzip_disable "msie6";   # Disable for old IE

# Pre-compressed static files
location ~* \.(js|css|html)$ {
    gzip_static on;     # Serve .gz files if they exist
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Static File Serving Optimization
```nginx
location /static/ {
    alias /var/www/searxng-cool/static/;
    
    # Aggressive caching
    expires 1y;
    add_header Cache-Control "public, immutable";
    
    # Disable access logging for static files
    access_log off;
    
    # Enable sendfile for zero-copy
    sendfile on;
    sendfile_max_chunk 1m;
    
    # TCP optimization
    tcp_nopush on;
    tcp_nodelay off;
    
    # Open file cache
    open_file_cache max=1000 inactive=60s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors off;
    
    # Serve pre-compressed files
    gzip_static on;
    
    # ETag handling
    etag on;
    
    # Conditional requests
    if_modified_since exact;
}
```

## Rate Limiting & DDoS Protection {#rate-limiting}

### Advanced Rate Limiting Configuration
```nginx
# Define multiple rate limit zones
# Binary IP storage is more efficient than string IP
limit_req_zone $binary_remote_addr zone=global:10m rate=100r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=search:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=auth:5m rate=2r/s;

# Compound key for more granular limiting
limit_req_zone "$binary_remote_addr$request_uri" zone=specific:10m rate=1r/s;

# User-agent based limiting
map $http_user_agent $limit_bot {
    default "";
    ~*bot "bot";
}
limit_req_zone $limit_bot zone=bots:5m rate=1r/m;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn_zone $server_name zone=servers:10m;

# Apply rate limits with burst handling
location /api/ {
    # Allow burst of 20 requests, process immediately (nodelay)
    limit_req zone=api burst=20 nodelay;
    limit_req zone=global burst=50;
    
    # Connection limits
    limit_conn addr 10;         # 10 concurrent connections per IP
    limit_conn servers 1000;    # 1000 total connections to server
    
    # Custom error page for rate limit
    limit_req_status 429;
    error_page 429 /429.html;
    
    proxy_pass http://flask_orchestrator;
}

location /search {
    # Allow burst but delay processing
    limit_req zone=search burst=10;
    
    # Different limits for bots
    limit_req zone=bots burst=2;
    
    proxy_pass http://searxng_core;
}

location /auth/login {
    # Strict limits for authentication endpoints
    limit_req zone=auth burst=5 nodelay;
    limit_req_log_level warn;
    
    proxy_pass http://flask_orchestrator;
}

# Rate limit bypass for whitelisted IPs
geo $whitelist {
    default 0;
    127.0.0.1 1;
    192.168.1.0/24 1;
}

map $whitelist $limit_key {
    0 $binary_remote_addr;
    1 "";
}

limit_req_zone $limit_key zone=conditional:10m rate=10r/s;
```

### DDoS Protection Patterns
```nginx
# Slowloris attack protection
client_body_timeout 10s;
client_header_timeout 10s;
keepalive_timeout 5s 5s;
send_timeout 10s;

# Large request protection
client_max_body_size 1m;
client_body_buffer_size 16k;
client_header_buffer_size 1k;
large_client_header_buffers 2 1k;

# Connection flood protection
limit_conn_zone $binary_remote_addr zone=perip:10m;
limit_conn_zone $server_name zone=perserver:10m;

server {
    limit_conn perip 10;
    limit_conn perserver 100;
    
    # Aggressive timeouts for suspicious requests
    location ~ \.php$ {
        return 444;  # Close connection immediately
    }
    
    # Challenge suspicious patterns
    location / {
        # Simple JavaScript challenge for bots
        if ($http_user_agent ~* "^$|bot|crawl|spider") {
            return 200 '<html><script>window.location.href="/?challenge=" + Date.now();</script></html>';
        }
        
        proxy_pass http://flask_orchestrator;
    }
}
```

## SSL/TLS Advanced Configuration {#ssl-tls-configuration}

### Production SSL/TLS Settings
```nginx
# Modern SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;

# SSL session optimization
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/letsencrypt/live/alfredisgone.duckdns.org/chain.pem;
resolver 8.8.8.8 8.8.4.4 1.1.1.1 valid=300s;
resolver_timeout 5s;

# DH parameters for perfect forward secrecy
ssl_dhparam /etc/nginx/dhparam.pem;

# Early data (0-RTT) for TLS 1.3 - use with caution
ssl_early_data on;
proxy_set_header Early-Data $ssl_early_data;

# Certificate transparency
add_header Expect-CT "enforce, max-age=30, report-uri=\"https://alfredisgone.duckdns.org/ct-report\"" always;
```

### Let's Encrypt Automation
```nginx
# ACME challenge location
location ^~ /.well-known/acme-challenge/ {
    default_type "text/plain";
    root /var/www/letsencrypt;
    try_files $uri =404;
}

# Redirect all HTTP to HTTPS except ACME
server {
    listen 80;
    server_name alfredisgone.duckdns.org;
    
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}
```

## WebSocket & Real-time Features {#websocket-configuration}

### Advanced WebSocket Configuration
```nginx
# WebSocket connection upgrade
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

# WebSocket endpoint with specific handling
location /ws/ {
    # WebSocket headers
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket specific timeouts (longer than HTTP)
    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;
    
    # Disable buffering for real-time
    proxy_buffering off;
    
    # Frame size limits
    proxy_max_temp_file_size 0;
    
    # Handle connection breaks
    proxy_next_upstream off;
    
    proxy_pass http://flask_orchestrator;
}

# Socket.IO specific configuration
location /socket.io/ {
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
    # Socket.IO sticky sessions with ip_hash
    proxy_pass http://flask_orchestrator;
}
```

## Load Balancing & High Availability {#load-balancing}

### Advanced Upstream Configuration
```nginx
# Load balancing with health checks
upstream flask_orchestrator {
    # Load balancing algorithm
    least_conn;  # Or: ip_hash, random, hash
    
    # Server definitions with parameters
    server 127.0.0.1:8889 weight=5 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8890 weight=3 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8891 weight=2 max_fails=3 fail_timeout=30s backup;
    
    # Connection pooling
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;
    
    # Queue requests when all servers are busy
    queue 100 timeout=30s;
}

# Consistent hashing for cache-friendly distribution
upstream cache_backend {
    hash $request_uri consistent;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

# Active health checks (nginx Plus feature, but can be simulated)
location /health-check {
    access_log off;
    proxy_pass http://flask_orchestrator/health;
    proxy_set_header Host $host;
    
    # Custom health check logic
    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 3;
    proxy_next_upstream_timeout 10s;
}
```

### Circuit Breaker Pattern
```nginx
# Implement circuit breaker with error tracking
map $upstream_response_time $backend_slow {
    default 0;
    "~^[0-9]+\.[5-9]" 1;  # Mark as slow if > 0.5s
}

map $upstream_status $backend_error {
    default 0;
    ~^[5] 1;  # 5xx errors
}

# Track errors in shared memory
limit_req_zone $backend_error zone=circuit:1m rate=1000r/s;

location / {
    # Check circuit status
    limit_req zone=circuit burst=10 nodelay;
    
    # If too many errors, return cached or default response
    error_page 503 = @circuit_open;
    
    proxy_pass http://flask_orchestrator;
    
    # Track response time
    add_header X-Backend-Response-Time $upstream_response_time always;
}

location @circuit_open {
    # Serve from cache or static response
    try_files /maintenance.html @serve_from_cache;
}
```

## Caching Strategies {#caching-strategies}

### Multi-Layer Caching
```nginx
# FastCGI cache for dynamic content
fastcgi_cache_path /var/cache/nginx/fastcgi
    levels=1:2
    keys_zone=FASTCGI:100m
    max_size=10g
    inactive=60m
    use_temp_path=off;

# Proxy cache for backend responses
proxy_cache_path /var/cache/nginx/proxy
    levels=1:2
    keys_zone=PROXY:100m
    max_size=10g
    inactive=60m
    use_temp_path=off;

# Micro-caching for high traffic
proxy_cache_path /var/cache/nginx/micro
    levels=1:2
    keys_zone=MICRO:10m
    max_size=1g
    inactive=1m
    use_temp_path=off;

# Cache configuration
location /api/search {
    # Use different cache for different content
    proxy_cache PROXY;
    
    # Complex cache key
    proxy_cache_key "$scheme$request_method$host$uri$is_args$args$http_authorization";
    
    # Varied cache times
    proxy_cache_valid 200 10m;
    proxy_cache_valid 301 302 5m;
    proxy_cache_valid 404 1m;
    proxy_cache_valid any 30s;
    
    # Conditional caching
    proxy_no_cache $http_pragma $http_authorization;
    proxy_cache_bypass $cookie_nocache $arg_nocache;
    
    # Cache locking to prevent thundering herd
    proxy_cache_lock on;
    proxy_cache_lock_timeout 5s;
    proxy_cache_lock_age 10s;
    
    # Background updates
    proxy_cache_background_update on;
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    
    # Add cache headers
    add_header X-Cache-Status $upstream_cache_status;
    add_header X-Cache-Key $proxy_cache_key;
    
    # Purge configuration
    proxy_cache_purge PURGE from 127.0.0.1;
    
    proxy_pass http://searxng_core;
}

# Micro-caching for home page
location = / {
    proxy_cache MICRO;
    proxy_cache_key "$scheme$request_method$host$uri";
    proxy_cache_valid 200 1s;  # Cache for 1 second
    proxy_cache_lock on;
    proxy_cache_use_stale updating;
    
    proxy_pass http://flask_orchestrator;
}
```

### Cache Purging & Warming
```nginx
# Cache purge endpoint
location ~ /purge(/.*) {
    allow 127.0.0.1;
    deny all;
    proxy_cache_purge PROXY "$scheme$request_method$host$1$is_args$args";
}

# Cache warming configuration
location /cache-warm {
    allow 127.0.0.1;
    deny all;
    
    # Warm specific URLs
    rewrite ^/cache-warm/(.*)$ /$1 break;
    proxy_pass http://flask_orchestrator;
    
    # Force cache update
    proxy_cache PROXY;
    proxy_cache_bypass 1;
}
```

## Error Handling & Fallback Patterns {#error-handling}

### Sophisticated Error Handling
```nginx
# Error page definitions
error_page 404 /404.html;
error_page 500 502 503 504 /50x.html;

# Custom error responses
location = /404.html {
    root /var/www/errors;
    internal;
    
    # Add cache headers for error pages
    expires 1h;
    add_header Cache-Control "public";
}

# Dynamic error pages
location @error_page {
    proxy_pass http://flask_orchestrator/error?code=$status&uri=$uri;
    proxy_set_header X-Original-Status $status;
    proxy_set_header X-Original-URI $request_uri;
    proxy_intercept_errors off;
}

# Fallback chain for SearXNG-Cool
location / {
    # Try Flask first
    proxy_pass http://flask_orchestrator;
    proxy_intercept_errors on;
    
    # On Flask error, try SearXNG
    error_page 502 503 504 = @try_searxng;
}

location @try_searxng {
    proxy_pass http://searxng_core;
    proxy_intercept_errors on;
    
    # On SearXNG error, serve static
    error_page 502 503 504 = @serve_static;
}

location @serve_static {
    root /var/www/searxng-cool/static;
    try_files /fallback.html =503;
}

# Recursive error handling with limits
error_page 500 502 503 504 @error_handler;
location @error_handler {
    # Prevent infinite recursion
    recursive_error_pages off;
    
    # Try to serve cached version
    proxy_cache_use_stale error timeout http_500 http_502 http_503 http_504;
    proxy_pass http://flask_orchestrator;
    
    # Final fallback
    error_page 500 502 503 504 /static/error.html;
}
```

### Graceful Degradation
```nginx
# Service degradation based on load
map $connections_active $server_busy {
    default 0;
    "~^[0-9]{4,}$" 1;  # 1000+ connections
}

location /search {
    # Serve simplified results when busy
    if ($server_busy) {
        rewrite ^ /search/simple last;
    }
    
    proxy_pass http://searxng_core;
}

location /search/simple {
    # Aggressive caching for degraded mode
    proxy_cache PROXY;
    proxy_cache_valid 200 5m;
    proxy_cache_lock on;
    
    # Reduced features endpoint
    proxy_pass http://searxng_core/search?simple=1;
}
```

## Monitoring & Debugging {#monitoring-debugging}

### Advanced Logging Configuration
```nginx
# Custom log format with timing information
log_format detailed '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $body_bytes_sent '
                   '"$http_referer" "$http_user_agent" '
                   'rt=$request_time uct=$upstream_connect_time '
                   'uht=$upstream_header_time urt=$upstream_response_time '
                   'cs=$upstream_cache_status';

# Conditional logging
map $status $loggable {
    ~^[23] 0;  # Don't log 2xx and 3xx
    default 1;
}

access_log /var/log/nginx/searxng_access.log detailed if=$loggable;
error_log /var/log/nginx/searxng_error.log warn;

# Debug logging for specific IPs
events {
    debug_connection 192.168.1.100;
    debug_connection 127.0.0.1;
}

# Request tracing
location /api/ {
    # Add request ID for tracing
    set $request_id $request_time-$pid-$msec;
    proxy_set_header X-Request-ID $request_id;
    
    # Log to separate file for API debugging
    access_log /var/log/nginx/api_debug.log detailed;
    
    proxy_pass http://flask_orchestrator;
}
```

### Performance Monitoring
```nginx
# Status endpoint
location /nginx-status {
    stub_status on;
    access_log off;
    
    allow 127.0.0.1;
    allow 192.168.1.0/24;
    deny all;
}

# Extended status with metrics
location /metrics {
    # Prometheus format metrics
    content_by_lua_block {
        local status = ngx.var.connections_active
        ngx.say("nginx_connections_active ", status)
        ngx.say("nginx_connections_reading ", ngx.var.connections_reading)
        ngx.say("nginx_connections_writing ", ngx.var.connections_writing)
        ngx.say("nginx_connections_waiting ", ngx.var.connections_waiting)
    }
    
    allow 127.0.0.1;
    deny all;
}

# Performance timing headers
location / {
    proxy_pass http://flask_orchestrator;
    
    # Add timing headers
    add_header X-Proxy-Cache $upstream_cache_status;
    add_header X-Response-Time $request_time;
    add_header X-Upstream-Response-Time $upstream_response_time;
    add_header X-Upstream-Connect-Time $upstream_connect_time;
    add_header X-Upstream-Header-Time $upstream_header_time;
}
```

## SearXNG-Cool Specific Patterns {#searxng-specific}

### Complete SearXNG-Cool nginx Configuration
```nginx
# Complete optimized configuration for SearXNG-Cool
user www-data;
worker_processes auto;
worker_cpu_affinity auto;
worker_rlimit_nofile 65535;
pid /run/nginx.pid;

events {
    worker_connections 10240;
    multi_accept on;
    use epoll;
}

http {
    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging
    log_format searxng '$remote_addr - $remote_user [$time_local] '
                      '"$request" $status $body_bytes_sent '
                      '"$http_referer" "$http_user_agent" '
                      'rt=$request_time uct=$upstream_connect_time '
                      'uht=$upstream_header_time urt=$upstream_response_time '
                      'cs=$upstream_cache_status rid=$request_id';
    
    access_log /var/log/nginx/access.log searxng;
    error_log /var/log/nginx/error.log warn;
    
    # Gzip Settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/javascript application/json application/xml+rss;
    
    # Rate Limiting Zones
    limit_req_zone $binary_remote_addr zone=global:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=search:10m rate=5r/s;
    limit_req_zone $binary_remote_addr zone=auth:5m rate=2r/s;
    
    # Connection Zones
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    
    # Cache Paths
    proxy_cache_path /var/cache/nginx/searxng levels=1:2 
                    keys_zone=searxng_cache:10m max_size=1g 
                    inactive=60m use_temp_path=off;
    
    # Upstreams with optimizations
    upstream flask_orchestrator {
        least_conn;
        server 127.0.0.1:8889 max_fails=3 fail_timeout=30s;
        keepalive 32;
        keepalive_requests 100;
        keepalive_timeout 60s;
    }
    
    upstream searxng_core {
        server 127.0.0.1:8888 max_fails=2 fail_timeout=15s;
        keepalive 16;
    }
    
    # Security Headers Map
    map $sent_http_content_type $content_security_policy {
        default "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";
    }
    
    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name alfredisgone.duckdns.org;
        
        location /.well-known/acme-challenge/ {
            root /var/www/letsencrypt;
        }
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }
    
    # Main HTTPS server
    server {
        listen 443 ssl http2;
        server_name alfredisgone.duckdns.org;
        
        # SSL Configuration
        ssl_certificate /etc/letsencrypt/live/alfredisgone.duckdns.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/alfredisgone.duckdns.org/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;
        ssl_session_tickets off;
        
        # Security Headers
        add_header Content-Security-Policy $content_security_policy always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        
        # Request ID for tracing
        set $request_id $request_time-$pid-$msec;
        add_header X-Request-ID $request_id always;
        
        # Root location with fallback chain
        location / {
            limit_req zone=global burst=50;
            
            proxy_pass http://flask_orchestrator;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
            
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
            
            proxy_intercept_errors on;
            error_page 502 503 504 = @fallback_to_searxng;
        }
        
        # Fallback to SearXNG
        location @fallback_to_searxng {
            proxy_pass http://searxng_core;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_intercept_errors on;
            error_page 502 503 504 /static/maintenance.html;
        }
        
        # API endpoints with stricter rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_conn addr 10;
            
            proxy_pass http://flask_orchestrator;
            include /etc/nginx/proxy_params;
            
            # CORS for API
            add_header Access-Control-Allow-Origin "https://alfredisgone.duckdns.org" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
            
            if ($request_method = OPTIONS) {
                return 204;
            }
        }
        
        # Search endpoint with caching
        location /search {
            limit_req zone=search burst=10;
            
            # Cache configuration
            proxy_cache searxng_cache;
            proxy_cache_key "$scheme$request_method$host$uri$is_args$args";
            proxy_cache_valid 200 10m;
            proxy_cache_valid 404 1m;
            proxy_cache_lock on;
            proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
            
            add_header X-Cache-Status $upstream_cache_status always;
            
            proxy_pass http://searxng_core;
            include /etc/nginx/proxy_params;
        }
        
        # WebSocket support
        location /ws/ {
            proxy_pass http://flask_orchestrator;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            
            proxy_connect_timeout 7d;
            proxy_send_timeout 7d;
            proxy_read_timeout 7d;
            proxy_buffering off;
        }
        
        # Static files with aggressive caching
        location /static/ {
            alias /var/www/searxng-cool/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
            
            gzip_static on;
            
            open_file_cache max=1000 inactive=60s;
            open_file_cache_valid 60s;
            open_file_cache_min_uses 2;
        }
        
        # Health check endpoint
        location /health {
            access_log off;
            proxy_pass http://flask_orchestrator;
            proxy_set_header Host $host;
            
            # Short timeouts for health checks
            proxy_connect_timeout 2s;
            proxy_send_timeout 2s;
            proxy_read_timeout 2s;
        }
        
        # Monitoring endpoints
        location /nginx-status {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            deny all;
        }
        
        # Error pages
        error_page 404 /404.html;
        error_page 500 502 503 504 /50x.html;
        
        location = /404.html {
            root /var/www/errors;
            internal;
        }
        
        location = /50x.html {
            root /var/www/errors;
            internal;
        }
    }
}
```

## Quick Reference & Commands

### Essential nginx Commands
```bash
# Configuration management
nginx -t                                    # Test configuration
nginx -T | less                            # View full configuration
nginx -V                                   # Show version and compile options

# Process control
nginx -s reload                            # Graceful reload
nginx -s quit                             # Graceful shutdown
nginx -s stop                             # Fast shutdown
nginx -s reopen                           # Reopen log files

# Debugging
nginx -g "daemon off; error_log stderr debug;"  # Debug mode
strace -p $(pgrep -f "nginx: worker") -s 1024  # Trace system calls
tcpdump -i any -w nginx.pcap port 443          # Capture HTTPS traffic

# Cache management
find /var/cache/nginx -type f -delete          # Clear all cache
curl -X PURGE https://localhost/path           # Purge specific URL

# Log analysis
tail -f /var/log/nginx/error.log              # Watch error log
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -20  # Top IPs
awk '{print $7}' access.log | sort | uniq -c | sort -rn | head -20  # Top URLs

# Performance testing
ab -n 10000 -c 100 https://localhost/         # Apache bench
wrk -t12 -c400 -d30s https://localhost/       # Modern load testing
siege -c 100 -t 60s https://localhost/        # Siege testing

# SSL/TLS testing
openssl s_client -connect localhost:443 -servername alfredisgone.duckdns.org
testssl.sh https://alfredisgone.duckdns.org
```

### Configuration Snippets Library

#### Proxy Parameters Include File
Create `/etc/nginx/proxy_params`:
```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $server_name;
proxy_set_header X-Request-ID $request_id;

proxy_http_version 1.1;
proxy_set_header Connection "";

proxy_connect_timeout 5s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;

proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
```

#### Security Headers Include File
Create `/etc/nginx/security_headers`:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;
```

#### Cache Configuration Include
Create `/etc/nginx/cache_settings`:
```nginx
proxy_cache_valid 200 301 302 10m;
proxy_cache_valid 404 1m;
proxy_cache_valid any 30s;
proxy_cache_key "$scheme$request_method$host$uri$is_args$args";
proxy_cache_lock on;
proxy_cache_lock_timeout 5s;
proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
proxy_cache_background_update on;
add_header X-Cache-Status $upstream_cache_status always;
```

## Testing & Validation Tools

### nginx Configuration Testing
```bash
# Syntax validation
nginx -t

# Full configuration dump
nginx -T > nginx_config_dump.txt

# Security analysis with gixy
pip install gixy
gixy /etc/nginx/nginx.conf

# Configuration formatting
npm install -g nginx-config-formatter
nginx-config-formatter -i /etc/nginx/nginx.conf

# Parse configuration with crossplane
pip install crossplane
crossplane parse /etc/nginx/nginx.conf
```

### Performance Testing Suite
```bash
# HTTP/1.1 load testing
ab -n 10000 -c 100 -H "Accept-Encoding: gzip" https://alfredisgone.duckdns.org/

# HTTP/2 load testing
h2load -n 10000 -c 100 -m 10 https://alfredisgone.duckdns.org/

# WebSocket testing
npm install -g wscat
wscat -c wss://alfredisgone.duckdns.org/ws/

# Complex scenario testing
cat > load_test.lua << 'EOF'
wrk.method = "POST"
wrk.body   = '{"query": "test search"}'
wrk.headers["Content-Type"] = "application/json"
EOF
wrk -t12 -c400 -d30s -s load_test.lua https://alfredisgone.duckdns.org/api/search

# Cache hit ratio testing
for i in {1..100}; do
    curl -s -I https://alfredisgone.duckdns.org/static/test.jpg | grep X-Cache-Status
done | sort | uniq -c
```

### SSL/TLS Validation
```bash
# Comprehensive SSL test
testssl.sh --html https://alfredisgone.duckdns.org

# Quick SSL check
openssl s_client -connect alfredisgone.duckdns.org:443 -servername alfredisgone.duckdns.org < /dev/null

# Certificate details
openssl s_client -connect alfredisgone.duckdns.org:443 -servername alfredisgone.duckdns.org < /dev/null | openssl x509 -noout -text

# Cipher suite testing
nmap --script ssl-enum-ciphers -p 443 alfredisgone.duckdns.org
```

## Troubleshooting Patterns

### Common Issues & Solutions

#### 1. 502 Bad Gateway
```nginx
# Check upstream connectivity
curl -I http://127.0.0.1:8889/health
curl -I http://127.0.0.1:8888/

# Verify nginx can reach upstreams
sudo -u www-data curl http://127.0.0.1:8889/health

# Check SELinux/AppArmor
sestatus  # For SELinux
aa-status # For AppArmor

# Review error logs
tail -f /var/log/nginx/error.log
```

#### 2. 504 Gateway Timeout
```nginx
# Increase timeouts
proxy_connect_timeout 10s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;

# Check upstream response time
curl -w "@curl-format.txt" -o /dev/null -s http://127.0.0.1:8889/
```

#### 3. High Memory Usage
```nginx
# Reduce buffer sizes
proxy_buffer_size 2k;
proxy_buffers 4 2k;

# Limit connections
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 5;

# Monitor memory
ps aux | grep nginx
cat /proc/$(pgrep -f "nginx: master")/status | grep VmRSS
```

#### 4. Cache Not Working
```nginx
# Debug cache decisions
add_header X-Cache-Status $upstream_cache_status always;
add_header X-Cache-Key $proxy_cache_key always;

# Check cache directory permissions
ls -la /var/cache/nginx/

# Verify cache key
curl -I https://localhost/test | grep X-Cache

# Monitor cache hit ratio
awk '$upstream_cache_status ~ /HIT|MISS|EXPIRED|STALE|UPDATING|REVALIDATED/ {print $upstream_cache_status}' /var/log/nginx/access.log | sort | uniq -c
```

## Best Practices Summary

1. **Always test configuration**: `nginx -t` before reload
2. **Use includes**: Modularize configuration
3. **Monitor performance**: Set up proper logging and metrics
4. **Security first**: Apply security headers and rate limiting
5. **Cache wisely**: Understand cache keys and invalidation
6. **Plan for failure**: Implement fallback mechanisms
7. **Optimize buffers**: Based on actual traffic patterns
8. **Document changes**: Comment complex configurations
9. **Version control**: Track nginx configuration in git
10. **Regular updates**: Keep nginx and modules updated

---

This guide represents advanced nginx configuration patterns specifically optimized for the SearXNG-Cool architecture. Regular review and updates based on traffic patterns and security requirements are recommended.