#!/usr/bin/env python3
"""Test if SearXNG can import music engines"""
import sys
import os

# Add SearXNG to path
searxng_path = os.path.join(os.path.dirname(__file__), 'searxng-core', 'searxng-core')
sys.path.insert(0, searxng_path)

# Test basic SearXNG import
try:
    import searx
    print("✓ SearXNG core importable")
except ImportError as e:
    print(f"✗ Cannot import SearXNG core: {e}")
    sys.exit(1)

# Test engine imports
engines_to_test = [
    'base_music',
    'allmusic', 
    'apple_music_web',
    'beatport',
    'lastfm',
    'musicbrainz',
    'pitchfork',
    'radio_paradise',
    'spotify_web',
    'tidal_web'
]

success = 0
failed = []

for engine in engines_to_test:
    try:
        module = __import__(f'searx.engines.{engine}', fromlist=[''])
        print(f"✓ {engine}: imported successfully")
        success += 1
    except Exception as e:
        print(f"✗ {engine}: {type(e).__name__}: {str(e)[:60]}")
        failed.append(engine)

print(f"\nSummary: {success}/{len(engines_to_test)} engines imported successfully")
if failed:
    print(f"Failed engines: {', '.join(failed)}")