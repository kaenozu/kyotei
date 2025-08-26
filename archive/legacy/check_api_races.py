#!/usr/bin/env python3
"""
OpenAPIで利用可能なレース結果を確認
"""

import requests
import json

# OpenAPIから今日の結果を取得
response = requests.get('https://boatraceopenapi.github.io/results/v2/today.json')
data = response.json()

print(f'Total races: {len(data["results"])}')

# 会場ごとのレース番号を整理
venues = {}
for race in data['results']:
    venue = race['race_stadium_number']
    race_num = race['race_number']
    if venue not in venues:
        venues[venue] = []
    venues[venue].append(race_num)

# 結果表示
for venue in sorted(venues.keys()):
    print(f'Venue {venue}: Races {sorted(venues[venue])}')

# サンプルレースデータも表示
print("\n--- サンプルレース詳細 ---")
sample_race = data['results'][0]
print(f"Date: {sample_race['race_date']}")
print(f"Venue: {sample_race['race_stadium_number']}")
print(f"Race: {sample_race['race_number']}")
print("Boats:")
for boat in sample_race['boats']:
    print(f"  Boat {boat['racer_boat_number']}: Place {boat['racer_place_number']}")