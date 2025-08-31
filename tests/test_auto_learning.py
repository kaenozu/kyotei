#!/usr/bin/env python3
"""
自動学習システムのテスト
実際のレース結果を使って予想検証をテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.accuracy_tracker import AccuracyTracker
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_auto_learning():
    """自動学習システムテスト"""
    
    print("=== 自動学習システムテスト ===")
    
    # 実際のレース結果でテスト
    test_cases = [
        {
            "venue_id": 2,
            "race_number": 1,
            "race_date": "2025-08-22",
            "predicted_order": [1, 2, 3, 4, 5, 6],  # 仮の予想（1-2-3順）
            "predicted_scores": [88.5, 7.2, 2.1, 1.2, 0.8, 0.2],  # 仮の予想確率
            "confidence_level": 0.75
        },
        {
            "venue_id": 3,
            "race_number": 1,
            "race_date": "2025-08-22",
            "predicted_order": [1, 2, 3, 4, 5, 6],  # 仮の予想（1-2-3順）
            "predicted_scores": [85.0, 8.0, 3.5, 2.0, 1.0, 0.5],  # 仮の予想確率
            "confidence_level": 0.80
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i} ---")
        print(f"会場: {test_case['venue_id']}")
        print(f"レース: {test_case['race_number']}R")
        print(f"予想: {test_case['predicted_order']}")
        print(f"予想確率: {test_case['predicted_scores']}")
        
        try:
            # 予想データを準備
            prediction_data = {
                'racers': [
                    {
                        'boat_number': i,
                        'prediction_percentage': test_case['predicted_scores'][i-1],
                        'predicted_rank': test_case['predicted_order'][i-1]
                    }
                    for i in range(1, 7)
                ],
                'race_date': test_case['race_date'],
                'confidence_level': test_case['confidence_level']
            }
            
            # 予想を登録
            prediction_id = accuracy_validator.record_prediction(
                venue_id=test_case['venue_id'],
                race_number=test_case['race_number'],
                prediction_data=prediction_data
            )
            
            print(f"[OK] 予想登録完了 (ID: {prediction_id})")
            
            # 即座に検証実行（通常は30分後）
            print("[INFO] 検証実行中...")
            verified_count = accuracy_validator.verify_predictions()
            print(f"[OK] 検証完了: {verified_count}件処理")
                
        except Exception as e:
            print(f"[ERR] エラー: {e}")
    
    # 学習統計を表示
    print("\n=== システム完了 ===")
    print("自動学習システムのテストが完了しました")

if __name__ == "__main__":
    test_auto_learning()