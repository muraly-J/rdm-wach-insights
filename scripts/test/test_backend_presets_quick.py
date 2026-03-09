#!/usr/bin/env python3
"""Quick test of critical preset prompts."""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://127.0.0.1:8081/api/query"

TEST_CASES = [
    ('Power: top 20 all levels', 'Compare top 20 devices by power demand this week across all levels'),
    ('Energy: top 10 all time', 'Which 10 AHUs have the highest energy consumption all time?'),
    ('Efficiency: top 10 all levels', 'Which 10 AHUs have the worst power factor across all levels?'),
    ('Current: top 10 all time', 'Which 10 AHUs have the highest average current all time?'),
    ('Diagnostics: THD all levels', 'Current THD comparison across all building levels — identify issues'),
    ('Reactive: top 10 all time', 'Which 10 devices have the highest reactive energy import all time?'),
    ('Power: levels 7,8,9', 'Which 15 AHUs have the highest total power in levels 7, 8, and 9?'),
    ('Power: compare e0206 vs e0301', 'Compare e0206 vs e0301 power today'),
    ('Energy: compare e0206 vs e0401', 'Compare e0206 vs e0401 energy import last 30 days'),
]

passed = 0
failed = 0

for name, query in TEST_CASES:
    try:
        response = requests.post(BASE_URL, json={
            'user_query': query,
            'session_id': f'test-{name}'
        }, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            
            query_type = data.get('query_type')
            chart_data = data.get('chart', {}).get('data', [])
            
            if query_type == 'ranking':
                chart_devices = [item.get('device_id') for item in chart_data if item.get('device_id')]
                unique_devices = list(dict.fromkeys(chart_devices))
            else:
                if chart_data:
                    unique_devices = list(chart_data[0].keys())
                    unique_devices = [d for d in unique_devices if d != 'time']
                else:
                    unique_devices = []
            
            issues = []
            if 'top' in query.lower() or 'rank' in query.lower():
                if len(unique_devices) == 1 and 'e0101' in unique_devices:
                    issues.append('Only e0101!')
                elif len(unique_devices) == 0:
                    issues.append('No devices returned!')
            
            if 'levels' in query.lower():
                if len(unique_devices) > 0:
                    has_only_e01 = all(d and d.startswith('e01') for d in unique_devices)
                    if has_only_e01 and len(unique_devices) < 5:
                        issues.append(f'Only e01xx ({len(unique_devices)})!')
            
            if issues:
                print(f'[✗] {name}: {issues}')
                failed += 1
            else:
                print(f'[✓] {name}: {len(unique_devices)} devices')
                passed += 1
        else:
            print(f'[✗] {name}: HTTP {response.status_code}')
            failed += 1
    except Exception as e:
        print(f'[✗] {name}: {str(e)[:50]}')
        failed += 1

print()
print(f'Summary: {passed} passed, {failed} failed')
