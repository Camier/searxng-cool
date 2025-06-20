#!/usr/bin/env python3
"""Check status of all music engines in SearXNG"""
import requests
import json

SEARXNG_URL = 'http://localhost:8888'

# Get all engines from config
response = requests.get(f"{SEARXNG_URL}/config")
data = response.json()

print("Music Engines Status in SearXNG")
print("=" * 60)
print(f"{'Engine Name':<25} {'Shortcut':<10} {'Enabled':<10} {'Categories'}")
print("-" * 60)

music_engines = []
for engine in data.get('engines', []):
    if 'music' in engine.get('categories', []):
        enabled = not engine.get('disabled', False)
        name = engine.get('name', 'Unknown')
        shortcut = engine.get('shortcut', 'N/A')
        categories = ', '.join(engine.get('categories', []))
        
        print(f"{name:<25} {shortcut:<10} {'Yes' if enabled else 'No':<10} {categories}")
        
        if enabled:
            music_engines.append(name)

print(f"\nTotal music engines: {len(music_engines)}")
print(f"Enabled engines: {len([e for e in data.get('engines', []) if 'music' in e.get('categories', []) and not e.get('disabled', False)])}")

# List enabled engines
print("\nEnabled Music Engines:")
for i, engine in enumerate(sorted(music_engines), 1):
    print(f"{i}. {engine}")