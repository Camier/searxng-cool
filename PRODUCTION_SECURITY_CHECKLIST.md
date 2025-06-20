# Production Security Checklist for SearXNG-Cool

## Pre-Deployment Security Audit

### ✅ Credentials & Secrets
- [ ] All hardcoded credentials removed from code
- [ ] `.env` file created with strong secrets
- [ ] JWT secret key is 32+ characters (generated with `openssl rand -hex 32`)
- [ ] Database password is strong and unique
- [ ] Neo4j password updated from default
- [ ] API keys stored in environment variables only
- [ ] No secrets in git history (`git log -p | grep -i password`)

### ✅ Environment Configuration
- [ ] `.env` file has restrictive permissions (`chmod 600 .env`)
- [ ] Environment validated with `python scripts/utilities/validate_config.py`
- [ ] Production uses `FLASK_ENV=production`
- [ ] Debug mode disabled (`FLASK_DEBUG=False`)
- [ ] All required environment variables set

### ✅ Database Security
- [ ] PostgreSQL password rotated
- [ ] Database connections use SSL (`sslmode=require`)
- [ ] Connection pooling configured with limits
- [ ] Database user has minimal required privileges
- [ ] Regular backups configured
- [ ] pg_hba.conf restricts connections appropriately

### ✅ Application Security
- [ ] Security headers configured (HSTS, CSP, X-Frame-Options)
- [ ] Session cookies set to secure & httponly
- [ ] CORS origins explicitly defined (no wildcards)
- [ ] Rate limiting enabled on all endpoints
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (using ORM/prepared statements)

### ✅ JWT & Authentication
- [ ] Access tokens expire in 15 minutes or less
- [ ] Refresh tokens properly implemented
- [ ] Token revocation mechanism in place (Redis blocklist)
- [ ] CSRF protection enabled for cookie-based auth
- [ ] Password hashing uses bcrypt or PBKDF2

### ✅ Network Security
- [ ] HTTPS enforced (SSL/TLS certificates installed)
- [ ] nginx configured with secure headers
- [ ] Firewall rules restrict unnecessary ports
- [ ] SSH access limited to specific IPs
- [ ] DDoS protection configured (rate limiting)

### ✅ File System Security
- [ ] Application runs as non-root user
- [ ] File permissions properly set (644 for configs, 755 for scripts)
- [ ] Temporary files cleaned up automatically
- [ ] Upload directories outside web root
- [ ] No directory listing enabled

### ✅ Logging & Monitoring
- [ ] Security events logged (failed logins, auth errors)
- [ ] Logs don't contain sensitive information
- [ ] Log rotation configured
- [ ] Monitoring alerts for suspicious activity
- [ ] Regular security audit logs reviewed

### ✅ Dependencies & Updates
- [ ] All dependencies up to date (`pip list --outdated`)
- [ ] Security vulnerabilities checked (`pip audit`)
- [ ] Operating system patches applied
- [ ] Automated security updates configured
- [ ] Dependency pinning in requirements.txt

### ✅ Backup & Recovery
- [ ] Database backups automated and tested
- [ ] Backup encryption enabled
- [ ] Offsite backup storage configured
- [ ] Recovery procedures documented
- [ ] Recovery time tested

## Deployment Commands

### 1. Final Security Check
```bash
# Check for exposed secrets
grep -r "password\|secret\|key" --include="*.py" --include="*.yml" .

# Verify permissions
find . -type f -name "*.py" -exec ls -la {} \; | grep -v "rw-r--r--"

# Test configuration
python scripts/utilities/validate_config.py
```

### 2. Generate Production Secrets
```bash
# Generate secure secrets
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env
echo "SECURITY_PASSWORD_SALT=$(openssl rand -hex 16)" >> .env
```

### 3. Set File Permissions
```bash
# Secure the .env file
chmod 600 .env

# Set proper permissions
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type f -name "*.sh" -exec chmod 755 {} \;
chmod 600 config/*.yml
```

### 4. Database Security
```bash
# Update PostgreSQL password
sudo -u postgres psql -c "ALTER USER searxng_user WITH PASSWORD 'new_secure_password';"

# Enable SSL
echo "ssl = on" | sudo tee -a /etc/postgresql/14/main/postgresql.conf
```

### 5. Start Services Securely
```bash
# Create systemd service files with security options
sudo systemctl edit searxng.service
# Add:
# [Service]
# User=searxng
# Group=searxng
# PrivateTmp=yes
# NoNewPrivileges=yes
# ReadOnlyPaths=/etc
# ReadWritePaths=/var/log/searxng

# Start services
sudo systemctl start searxng searxng-orchestrator
```

## Post-Deployment Verification

### Security Tests
```bash
# Test security headers
curl -I https://your-domain.com | grep -E "Strict-Transport|X-Frame|X-Content"

# Test rate limiting
for i in {1..100}; do curl https://your-domain.com/api/test; done

# Check SSL configuration
nmap --script ssl-enum-ciphers -p 443 your-domain.com
```

### Monitoring Setup
```bash
# Set up fail2ban for brute force protection
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban

# Configure log monitoring
sudo tail -f /var/log/nginx/access.log | grep -E "401|403|404"
```

## Emergency Procedures

### If Credentials Are Exposed
1. Immediately rotate all affected credentials
2. Check logs for unauthorized access
3. Revoke all active sessions
4. Update .env and restart services
5. Audit recent database changes

### Security Incident Response
1. Isolate affected systems
2. Preserve logs for analysis
3. Identify attack vector
4. Apply patches/fixes
5. Document incident and response

## Regular Maintenance

### Weekly
- [ ] Review security logs
- [ ] Check for failed login attempts
- [ ] Verify backup completion
- [ ] Monitor resource usage

### Monthly
- [ ] Update dependencies
- [ ] Rotate API keys
- [ ] Security vulnerability scan
- [ ] Review user permissions

### Quarterly
- [ ] Full security audit
- [ ] Penetration testing
- [ ] Update security policies
- [ ] Disaster recovery drill

---

**Remember**: Security is an ongoing process, not a one-time setup. Stay vigilant and keep your systems updated!