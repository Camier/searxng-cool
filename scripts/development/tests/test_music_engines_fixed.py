#!/usr/bin/env python3
"""
Test music engines after fixes
"""
import requests
import json
import sys
import time

# Configuration
SEARXNG_BASE_URL = 'http://localhost:8888'

# Engines that had errors
PROBLEM_ENGINES = [
    ('radio paradise', 'rp', 'Radio Paradise'),
    ('apple music web', 'amw', 'Apple Music Web'),
    ('pitchfork', 'pf', 'Pitchfork'),
    ('musixmatch', 'mxm', 'Musixmatch'),
]

def test_engine(engine_id, query='radiohead'):
    """Test a single engine"""
    url = f"{SEARXNG_BASE_URL}/search"
    params = {
        'q': query,
        'engines': engine_id,
        'format': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        errors = data.get('unresponsive_engines', [])
        
        return {
            'success': True,
            'result_count': len(results),
            'results': results[:3],  # First 3 results
            'errors': errors,
            'status_code': response.status_code
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': str(e),
            'result_count': 0,
            'results': [],
            'errors': []
        }

def print_engine_result(engine_name, shortcut, result):
    """Print test result for an engine"""
    print(f"\n{'='*60}")
    print(f"Engine: {engine_name} ({shortcut})")
    print(f"{'='*60}")
    
    if result['success']:
        if result['result_count'] > 0:
            print(f"✅ SUCCESS: {result['result_count']} results found")
            print("\nFirst result:")
            first = result['results'][0]
            print(f"  Title: {first.get('title', 'N/A')}")
            print(f"  URL: {first.get('url', 'N/A')[:80]}...")
            if 'content' in first:
                print(f"  Content: {first['content'][:100]}...")
            if 'key' in first:
                print(f"  Key: {first['key']} (✓ key field present)")
            else:
                print("  ⚠️  WARNING: 'key' field missing")
        else:
            print(f"⚠️  NO RESULTS (but no errors)")
            
        if result['errors']:
            print(f"\n❌ Engine errors reported:")
            for error in result['errors']:
                print(f"  - {error}")
    else:
        print(f"❌ FAILED: {result['error']}")

def check_logs():
    """Check recent logs for errors"""
    print("\n📋 Checking recent logs...")
    try:
        import subprocess
        # Get last 50 lines of log
        result = subprocess.run(
            ['tail', '-50', '/home/mik/SEARXNG/searxng-cool/logs/searxng.log'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            errors = [line for line in lines if 'ERROR' in line or 'KeyError' in line]
            
            if errors:
                print("\nRecent errors in log:")
                for error in errors[-5:]:  # Last 5 errors
                    print(f"  {error[:120]}...")
            else:
                print("✅ No recent errors in log")
    except Exception as e:
        print(f"Could not check logs: {e}")

def main():
    """Run tests for problem engines"""
    print("🧪 Testing SearXNG Music Engines After Fixes")
    print("=" * 60)
    
    # Check if SearXNG is running
    try:
        response = requests.get(f"{SEARXNG_BASE_URL}/config", timeout=5)
        if response.status_code != 200:
            print("❌ ERROR: SearXNG is not responding properly")
            return 1
    except requests.exceptions.RequestException:
        print(f"❌ ERROR: Cannot connect to SearXNG at {SEARXNG_BASE_URL}")
        print("Please ensure SearXNG is running")
        return 1
    
    print("✅ SearXNG is running\n")
    
    # Test each problem engine
    results_summary = []
    
    for engine_id, shortcut, engine_name in PROBLEM_ENGINES:
        print(f"\n🔍 Testing {engine_name}...")
        result = test_engine(engine_id)
        print_engine_result(engine_name, shortcut, result)
        
        # Summary
        if result['success'] and result['result_count'] > 0:
            status = "✅ FIXED"
        elif result['success'] and result['result_count'] == 0:
            status = "⚠️  NO RESULTS"
        else:
            status = "❌ FAILED"
        
        results_summary.append((engine_name, status))
        time.sleep(1)  # Be nice to the server
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for engine, status in results_summary:
        print(f"{status} {engine}")
    
    # Check logs
    check_logs()
    
    # Recommendations
    print("\n📝 Recommendations:")
    print("1. If Apple Music Web still shows KeyError, run: sudo python3 fix_music_engines.py")
    print("2. For Pitchfork timeouts, manually update settings.yml with the timeout config")
    print("3. Musixmatch may remain blocked due to CloudFlare - consider disabling it")
    print("4. Radio Paradise should work now (it already had the fix)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())