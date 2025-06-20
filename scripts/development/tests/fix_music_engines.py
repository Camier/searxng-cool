#!/usr/bin/env python3
"""
Fix music engine issues in SearXNG
"""
import os
import sys
import re
import shutil
from datetime import datetime

def fix_base_music_py():
    """Add 'key' field to standardize_result method"""
    file_path = '/home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core/searx/engines/base_music.py'
    
    print(f"Fixing {file_path}...")
    
    # Backup first
    backup_path = f"{file_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if "result['key']" in content:
        print("✅ base_music.py already has 'key' field handling")
        return
    
    # Find the return statement in standardize_result
    pattern = r'(        result\[\'metadata\'\] = \{[^}]+\}\s*\n\s*)(return result)'
    
    replacement = r'''\1
        # Add the 'key' field that SearXNG expects
        if 'key' not in result:
            # Generate a unique key from title and URL
            import hashlib
            key_string = f"{result.get('title', '')}{result.get('url', '')}"
            result['key'] = hashlib.md5(key_string.encode()).hexdigest()[:16]
        
        \2'''
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content == content:
        print("❌ Failed to find the right place to add 'key' field")
        print("Trying alternative approach...")
        
        # Alternative: Add before return result
        pattern2 = r'(\n)(        return result)'
        replacement2 = r'''\1
        # Add the 'key' field that SearXNG expects
        if 'key' not in result:
            # Generate a unique key from title and URL
            import hashlib
            key_string = f"{result.get('title', '')}{result.get('url', '')}"
            result['key'] = hashlib.md5(key_string.encode()).hexdigest()[:16]
        
\2'''
        new_content = re.sub(pattern2, replacement2, content)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed base_music.py - added 'key' field generation")

def create_limiter_config():
    """Create limiter configuration to fix SQLite warnings"""
    config_path = '/etc/searxng/limiter.toml'
    
    config_content = '''[botdetection.ip_limit]
# Enable IP-based rate limiting
enable = true
# Number of requests per time window
limit = 100
# Time window in seconds
window = 300

[botdetection.link_token]
# Enable link token checks
enable = false

[real_ip]
# X-Forwarded-For header depth
x_forwarded_for = 1
'''
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write config (requires sudo)
        print(f"\nCreating {config_path}...")
        print("This requires sudo permissions...")
        
        # Write to temp file first
        temp_path = '/tmp/limiter.toml'
        with open(temp_path, 'w') as f:
            f.write(config_content)
        
        # Use sudo to copy
        os.system(f'sudo cp {temp_path} {config_path}')
        os.system(f'sudo chmod 644 {config_path}')
        os.remove(temp_path)
        
        print("✅ Created limiter configuration")
    except Exception as e:
        print(f"❌ Failed to create limiter config: {e}")
        print("\nPlease create /etc/searxng/limiter.toml manually with:")
        print(config_content)

def update_settings_yml():
    """Update settings.yml for Pitchfork timeout"""
    settings_path = '/home/mik/SEARXNG/searxng-cool/searxng-core/searxng-core/searx/settings.yml'
    
    print(f"\n📝 To fix Pitchfork timeouts, add this to {settings_path}:")
    print("""
engines:
  - name: pitchfork
    engine: pitchfork
    shortcut: pf
    timeout: 15.0  # Increase from default 5s
    max_redirects: 2  # Allow redirects
""")

def main():
    """Run all fixes"""
    print("🔧 Fixing SearXNG Music Engine Issues")
    print("=" * 50)
    
    # 1. Fix base_music.py
    fix_base_music_py()
    
    # 2. Create limiter config
    create_limiter_config()
    
    # 3. Show settings.yml update instructions
    update_settings_yml()
    
    print("\n✅ Fixes applied!")
    print("\n🔄 Please restart SearXNG:")
    print("   sudo systemctl restart searxng")
    print("\n🧪 Then test with:")
    print("   python3 test_music_engines_fixed.py")

if __name__ == '__main__':
    main()