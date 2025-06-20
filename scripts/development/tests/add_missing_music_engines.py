#!/usr/bin/env python3
"""Add missing music engines to settings.yml"""

# Music engines to add (that we implemented but are missing from settings)
MISSING_ENGINES = """
- name: lastfm
  engine: lastfm
  shortcut: lfm
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: beatport
  engine: beatport
  shortcut: bp
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: spotify web
  engine: spotify_web
  shortcut: spw
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: tidal web
  engine: tidal_web
  shortcut: tdw
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: musixmatch
  engine: musixmatch
  shortcut: mxm
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: radio paradise
  engine: radio_paradise
  shortcut: rp
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: pitchfork
  engine: pitchfork
  shortcut: pf
  categories:
  - music
  timeout: 15.0
  max_redirects: 2
  disabled: false
- name: soundcloud
  engine: soundcloud
  shortcut: sc
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: mixcloud
  engine: mixcloud
  shortcut: mc
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: genius
  engine: genius
  shortcut: gen
  categories:
  - music
  timeout: 5.0
  disabled: false
- name: deezer
  engine: deezer
  shortcut: dz
  categories:
  - music
  timeout: 5.0
  disabled: false
"""

print("Add these engines to /usr/local/searxng/searxng-src/searx/settings.yml")
print("Insert them in the engines: section")
print("=" * 60)
print(MISSING_ENGINES)