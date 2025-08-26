#!/usr/bin/env python3
"""
データベースの内容確認スクリプト
"""

import sqlite3
import json
from datetime import datetime

# データベース接続
db_path = "cache/accuracy_tracker.db"

try:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        print("=== データベース内容確認 ===")
        
        # 予想データ数
        cursor.execute("SELECT COUNT(*) FROM predictions")
        prediction_count = cursor.fetchone()[0]
        print(f"予想データ数: {prediction_count}件")
        
        # 結果データ数
        cursor.execute("SELECT COUNT(*) FROM race_results")
        result_count = cursor.fetchone()[0]
        print(f"結果データ数: {result_count}件")
        
        # 的中記録数
        cursor.execute("SELECT COUNT(*) FROM accuracy_records")
        accuracy_count = cursor.fetchone()[0]
        print(f"的中記録数: {accuracy_count}件")
        
        # 今日の予想データサンプル（最新5件）
        print("\n=== 今日の予想データ（最新5件） ===")
        cursor.execute("""
            SELECT venue_name, race_number, predicted_win, predicted_place, confidence, created_at
            FROM predictions 
            WHERE race_date = DATE('now') 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            venue_name, race_number, predicted_win, predicted_place, confidence, created_at = row
            try:
                place_data = json.loads(predicted_place) if predicted_place else []
            except:
                place_data = predicted_place
            print(f"{venue_name} {race_number}R: 1位={predicted_win}号艇, 複勝={place_data}, 信頼度={confidence:.2f}, 作成={created_at}")
        
        # 今日の結果データサンプル（最新5件）
        print("\n=== 今日の結果データ（最新5件） ===")
        cursor.execute("""
            SELECT venue_name, race_number, winning_boat, place_results, fetched_at
            FROM race_results 
            WHERE race_date = DATE('now') 
            ORDER BY fetched_at DESC 
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            venue_name, race_number, winning_boat, place_results, fetched_at = row
            try:
                place_data = json.loads(place_results) if place_results else []
            except:
                place_data = place_results
            print(f"{venue_name} {race_number}R: 1位={winning_boat}号艇, 着順={place_data}, 取得={fetched_at}")
        
        # 的中率統計
        print("\n=== 的中率統計 ===")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_win_hit = 1 THEN 1 ELSE 0 END) as win_hits,
                SUM(CASE WHEN is_place_hit = 1 THEN 1 ELSE 0 END) as place_hits
            FROM accuracy_records
            WHERE hit_status != 'pending'
        """)
        
        stats = cursor.fetchone()
        if stats and stats[0] > 0:
            total, win_hits, place_hits = stats
            win_rate = (win_hits / total * 100) if total > 0 else 0
            place_rate = (place_hits / total * 100) if total > 0 else 0
            print(f"総レース数: {total}件")
            print(f"単勝的中: {win_hits}件 ({win_rate:.1f}%)")
            print(f"複勝的中: {place_hits}件 ({place_rate:.1f}%)")
        else:
            print("的中率データがまだありません")

except Exception as e:
    print(f"データベース確認エラー: {e}")