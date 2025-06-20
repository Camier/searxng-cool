#!/usr/bin/env python3
"""Test all music engines"""
import requests
import json

SEARXNG_URL = 'http://localhost:8888'

# All music engines we've implemented
MUSIC_ENGINES = [
    ('lastfm', 'Last.fm'),
    ('deezer', 'Deezer'),
    ('free music archive', 'Free Music Archive'),
    ('beatport', 'Beatport'),
    ('musicbrainz', 'MusicBrainz'),
    ('radio paradise', 'Radio Paradise'),
    ('spotify web', 'Spotify Web'),
    ('apple music web', 'Apple Music Web'),
    ('tidal web', 'Tidal Web'),
    ('musixmatch', 'Musixmatch'),
    ('musictoscrape', 'MusicToScrape'),
    ('allmusic', 'AllMusic'),
    ('pitchfork', 'Pitchfork'),
]

# Also test existing engines
EXISTING_ENGINES = [
    ('bandcamp', 'Bandcamp'),
    ('soundcloud', 'SoundCloud'),
    ('mixcloud', 'MixCloud'),
    ('genius', 'Genius'),
    ('youtube', 'YouTube'),
]

def test_engine(engine_id, query='test'):
    """Test a single engine"""
    try:
        url = f"{SEARXNG_URL}/search"
        params = {
            'q': query,
            'engines': engine_id,
            'format': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        results = data.get('results', [])
        errors = data.get('unresponsive_engines', [])
        
        return len(results), errors
    except Exception as e:
        return 0, [[engine_id, str(e)]]

print("Testing Music Engines")
print("=" * 60)

# Test our implemented engines
print("\n🎵 Custom Music Engines:")
working = 0
for engine_id, name in MUSIC_ENGINES:
    count, errors = test_engine(engine_id)
    if count > 0:
        print(f"✅ {name:25} {count:3} results")
        working += 1
    elif errors:
        error_msg = errors[0][1] if errors else "No error"
        print(f"❌ {name:25}   0 results ({error_msg})")
    else:
        print(f"⚠️  {name:25}   0 results (no errors)")

# Test existing engines
print("\n🎵 Existing Music Engines:")
for engine_id, name in EXISTING_ENGINES:
    count, errors = test_engine(engine_id)
    if count > 0:
        print(f"✅ {name:25} {count:3} results")
        working += 1
    elif errors:
        error_msg = errors[0][1] if errors else "No error"
        print(f"❌ {name:25}   0 results ({error_msg})")
    else:
        print(f"⚠️  {name:25}   0 results (no errors)")

print(f"\n📊 Total Working Engines: {working}")