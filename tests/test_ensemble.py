#!/usr/bin/env python3
"""
アンサンブル予想システムテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ensemble_predictor import ensemble_predictor
import json

def test_ensemble_prediction():
    """アンサンブル予想テスト"""
    
    # テスト用レースデータ
    test_race_data = {
        'venue_info': {
            'name': '戸田',
            'id': 2
        },
        'race_info': {
            'race_number': 10,
            'distance': 1800
        },
        'weather': {
            'wind_speed': 3.2,
            'wave_height': 1.5,
            'temperature': 25
        },
        'racers': [
            {
                'boat_number': 1,
                'racer_name': '選手A',
                'win_rate': 0.35,
                'place_rate': 0.65,
                'avg_st': 0.18,
                'motor_2rate': 0.45,
                'boat_2rate': 0.38
            },
            {
                'boat_number': 2,
                'racer_name': '選手B',
                'win_rate': 0.28,
                'place_rate': 0.58,
                'avg_st': 0.16,
                'motor_2rate': 0.42,
                'boat_2rate': 0.35
            },
            {
                'boat_number': 3,
                'racer_name': '選手C',
                'win_rate': 0.22,
                'place_rate': 0.52,
                'avg_st': 0.19,
                'motor_2rate': 0.38,
                'boat_2rate': 0.32
            },
            {
                'boat_number': 4,
                'racer_name': '選手D',
                'win_rate': 0.18,
                'place_rate': 0.45,
                'avg_st': 0.21,
                'motor_2rate': 0.35,
                'boat_2rate': 0.29
            },
            {
                'boat_number': 5,
                'racer_name': '選手E',
                'win_rate': 0.15,
                'place_rate': 0.40,
                'avg_st': 0.22,
                'motor_2rate': 0.32,
                'boat_2rate': 0.26
            },
            {
                'boat_number': 6,
                'racer_name': '選手F',
                'win_rate': 0.12,
                'place_rate': 0.35,
                'avg_st': 0.24,
                'motor_2rate': 0.28,
                'boat_2rate': 0.23
            }
        ]
    }
    
    print("=== アンサンブル予想システムテスト ===")
    print(f"テスト会場: {test_race_data['venue_info']['name']}")
    print(f"レース: {test_race_data['race_info']['race_number']}R")
    
    try:
        # アンサンブル予想実行
        result = ensemble_predictor.calculate_ensemble_prediction(test_race_data)
        
        print(f"\n[OK] アンサンブル予想成功!")
        print(f"信頼度: {result['confidence']:.3f}")
        print(f"使用モデル数: {result['models_used']}")
        print(f"戦略: {result.get('strategy', 'unknown')}")
        print(f"予想のばらつき: {result.get('ensemble_variance', 0):.3f}")
        
        print("\n--- 予想結果 ---")
        for i, racer in enumerate(result['racers'][:3], 1):
            print(f"{i}位予想: {racer['boat_number']}号艇 - {racer['prediction_percentage']:.1f}%")
        
        print("\n--- モデル詳細 ---")
        model_details = result.get('model_details', {})
        for model_name, details in model_details.items():
            print(f"{model_name}: 重み {details['weight']:.3f}, 本命 {details['top_boat']}号艇")
        
    except Exception as e:
        print(f"[ERR] アンサンブル予想エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_prediction()