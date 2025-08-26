#!/usr/bin/env python3
"""
レース結果取得のデバッグ
"""

import requests
import json

# テスト対象
venue_id = 2
race_number = 10
race_date = "2025-08-22"

print(f"検索対象: Venue {venue_id}, Race {race_number}, Date {race_date}")

# OpenAPIから今日の結果を取得
response = requests.get('https://boatraceopenapi.github.io/results/v2/today.json')
data = response.json()

# 指定されたレースを検索
target_race = None
for race in data.get('results', []):
    print(f"checking: venue={race.get('race_stadium_number')}, race={race.get('race_number')}, date={race.get('race_date')}")
    if (race.get('race_stadium_number') == venue_id and 
        race.get('race_number') == race_number and 
        race.get('race_date') == race_date):
        target_race = race
        print(f"  → MATCH FOUND!")
        break

if target_race:
    print("\n=== 見つかったレース ===")
    print(json.dumps(target_race, indent=2, ensure_ascii=False))
    
    # 着順を構築
    finish_order = [0] * 6
    boats = target_race.get('boats', [])
    
    print("\n=== 着順構築過程 ===")
    for boat in boats:
        boat_number = boat.get('racer_boat_number')
        place = boat.get('racer_place_number')
        
        print(f"  Boat {boat_number} → Place {place}")
        
        if boat_number and place and 1 <= place <= 6:
            finish_order[place - 1] = boat_number
            print(f"    finish_order[{place-1}] = {boat_number}")
    
    print(f"\nFinal finish_order: {finish_order}")
    print(f"Contains 0? {0 in finish_order}")
else:
    print(f"\n❌ レースが見つかりません")
    
    # 利用可能なレースを表示
    print("\n利用可能なレース:")
    for race in data.get('results', []):
        if race.get('race_stadium_number') == venue_id:
            print(f"  Race {race.get('race_number')} on {race.get('race_date')}")