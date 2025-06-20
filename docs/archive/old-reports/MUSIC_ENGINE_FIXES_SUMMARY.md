# Music Engine Fixes Summary

## Quick Fix Commands

```bash
# 1. Apply automated fixes
sudo python3 fix_music_engines.py

# 2. Restart SearXNG
sudo systemctl restart searxng

# 3. Test engines
python3 test_music_engines_fixed.py
```

## Manual Settings Update

Edit `/home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core/searx/settings.yml` and add:

```yaml
engines:
  - name: pitchfork
    engine: pitchfork
    shortcut: pf
    timeout: 15.0  # Increase from default 5s
    max_redirects: 2  # Allow redirects
```

## Issues & Fixes

| Engine | Error | Fix | Status |
|--------|-------|-----|--------|
| Radio Paradise | 'list' object has no attribute 'get' | Already fixed in code | ✅ Should work |
| Apple Music Web | KeyError: 'key' | Add 'key' field in base_music.py | 🔧 Run fix script |
| Pitchfork | Timeout (5s) | Increase timeout in settings.yml | 📝 Manual config |
| Musixmatch | HTTP 403 CloudFlare | May need to disable | ⚠️ Likely blocked |

## After Fixes

Working engines should increase from 11 to 13+ (Radio Paradise and Apple Music Web fixed).

## Troubleshooting

If issues persist:
1. Check logs: `tail -f /home/mik/SEARXNG/searxng-cool/logs/searxng.log`
2. Verify engines loaded: `curl http://localhost:8888/config | jq .engines`
3. Test individually: `curl "http://localhost:8888/search?q=test&engines=engine_name&format=json"`