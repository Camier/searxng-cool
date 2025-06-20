# Production Security Checklist

This checklist ensures your SearXNG-Cool deployment is secure for production use.

## Pre-Deployment

### 1. Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Generate new JWT secret: `openssl rand -hex 32`
- [ ] Generate new Flask secret: `openssl rand -hex 32`
- [ ] Set `FLASK_ENV=production`
- [ ] Set `DEBUG=false`
- [ ] Configure strong database password
- [ ] Set appropriate CORS origins (no wildcards)

### 2. Validate Configuration
```bash
# Run configuration validator
python scripts/utilities/validate_config.py

# Check for any errors or warnings
```

### 3. Database Security
- [ ] Use SSL for database connections
- [ ] Create dedicated database user with minimal privileges
- [ ] Restrict database access by IP/network
- [ ] Enable query logging for audit trail
- [ ] Regular backups configured

### 4. Redis Security
- [ ] Set Redis password (requirepass)
- [ ] Bind to localhost only or use firewall rules
- [ ] Disable dangerous commands (FLUSHDB, CONFIG, etc.)
- [ ] Use separate databases for different purposes

### 5. API Keys
- [ ] Remove default/example API keys
- [ ] Store API keys securely (consider key vault)
- [ ] Rotate API keys periodically
- [ ] Monitor API key usage

## Deployment

### 6. Web Server Configuration
- [ ] Enable HTTPS with valid certificate
- [ ] Configure security headers in nginx/apache
- [ ] Disable server version disclosure
- [ ] Enable rate limiting at web server level
- [ ] Configure appropriate timeouts

### 7. Application Security
- [ ] Verify security headers are applied:
  ```bash
  curl -I https://yourdomain.com | grep -E "X-Content-Type|X-Frame|Strict-Transport"
  ```
- [ ] Test CORS configuration
- [ ] Verify JWT tokens expire appropriately
- [ ] Check session security settings

### 8. File Permissions
- [ ] Set restrictive permissions on `.env`: `chmod 600 .env`
- [ ] Ensure log directory is writable but secure
- [ ] Application files owned by non-root user
- [ ] No world-writable directories

### 9. Logging & Monitoring
- [ ] Configure log rotation
- [ ] Set appropriate log levels (not DEBUG)
- [ ] Monitor for authentication failures
- [ ] Set up alerts for security events
- [ ] Regular log review process

## Post-Deployment

### 10. Security Testing
- [ ] Run security scanner (e.g., OWASP ZAP)
- [ ] Test authentication endpoints
- [ ] Verify rate limiting works
- [ ] Check for information disclosure
- [ ] Test error handling (no stack traces)

### 11. Operational Security
- [ ] Document security procedures
- [ ] Plan for security updates
- [ ] Incident response plan
- [ ] Regular security audits
- [ ] Monitor dependencies for vulnerabilities

### 12. Backup & Recovery
- [ ] Test backup restoration
- [ ] Secure backup storage
- [ ] Document recovery procedures
- [ ] Regular backup verification

## Quick Security Commands

```bash
# Generate secure secrets
python scripts/utilities/generate_secrets.py --all

# Validate configuration
python scripts/utilities/validate_config.py

# Check current security headers
curl -s -I http://localhost:8889/health | grep -E "^X-|^Strict"

# Test rate limiting
for i in {1..100}; do curl -s http://localhost:8889/api/test > /dev/null; done

# Check for exposed secrets in code
grep -r "password\|secret\|key" --include="*.py" . | grep -v ".env"
```

## Security Contacts

- Security issues: security@yourdomain.com
- Responsible disclosure policy: [link]
- Security updates: [link to changelog]

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Guide](https://flask.palletsprojects.com/en/2.0.x/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [Redis Security](https://redis.io/topics/security)

Remember: Security is an ongoing process, not a one-time setup!