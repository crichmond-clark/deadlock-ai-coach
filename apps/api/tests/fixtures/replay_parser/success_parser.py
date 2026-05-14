#!/usr/bin/env python3
import json
import sys

path = sys.argv[sys.argv.index('--input') + 1]
print(json.dumps({
  'schema_version':'deadlock-replay-parse-v1',
  'parser': {'name':'fake','version':'test','app_parser_version':'0.1.0'},
  'source': {'filename': path.split('/')[-1], 'size_bytes': 1, 'sha256': None},
  'match': {'match_id': None, 'duration_seconds': 120, 'tick_count': 1000, 'winning_team': None},
  'players': [{'slot':0,'account_id':None,'display_name':'Player','hero':None,'team':None}],
  'timeline': [{'time_seconds':1.0,'tick':10,'type':'test','description':'event','data':{}}],
  'capabilities': {'overview_available': True, 'players_available': True, 'combat_log_available': False, 'entities_sampled': False},
  'warnings': ['test warning'],
  'stats': {'parse_duration_ms': 5, 'timeline_events_emitted': 1, 'timeline_events_dropped': 0}
}))
