#!/usr/bin/env python3
"""
予想データのデバッグスクリプト
"""

import sqlite3
import json
from datetime import datetime

def debug_predictions():
    db_path = "cache/accuracy_tracker.db"
    race_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"DEBUG: {race_date} の予想データを確認")
    print("=" * 50)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 予想データを確認
            print("予想データ:")
            cursor.execute("""
                SELECT venue_id, venue_name, race_number, predicted_win, predicted_place, confidence, created_at
                FROM predictions 
                WHERE race_date = ?
                ORDER BY venue_id, race_number
            """, (race_date,))
            
            predictions = cursor.fetchall()
            
            if predictions:
                for row in predictions:
                    venue_id, venue_name, race_number, predicted_win, predicted_place_json, confidence, created_at = row
                    try:
                        predicted_place = json.loads(predicted_place_json) if predicted_place_json else []
                    except:
                        predicted_place = []
                    
                    print(f"  {venue_name}({venue_id}) {race_number}R: {predicted_win}号艇 (複勝: {predicted_place}) 信頼度: {confidence:.1%} - {created_at}")
            else:
                print("  予想データがありません")
            
            # 結果データを確認
            print("\n結果データ:")
            cursor.execute("""
                SELECT venue_id, venue_name, race_number, winning_boat, place_results, fetched_at
                FROM race_results 
                WHERE race_date = ?
                ORDER BY venue_id, race_number
            """, (race_date,))
            
            results = cursor.fetchall()
            
            if results:
                for row in results:
                    venue_id, venue_name, race_number, winning_boat, place_results_json, fetched_at = row
                    try:
                        place_results = json.loads(place_results_json) if place_results_json else []
                    except:
                        place_results = []
                    
                    print(f"  {venue_name}({venue_id}) {race_number}R: {winning_boat}号艇 (着順: {place_results}) - {fetched_at}")
            else:
                print("  結果データがありません")
            
            # 全件数確認
            cursor.execute("SELECT COUNT(*) FROM predictions")
            pred_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM race_results")
            result_count = cursor.fetchone()[0]
            
            print(f"\n統計:")
            print(f"  総予想件数: {pred_count}")
            print(f"  総結果件数: {result_count}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    debug_predictions()