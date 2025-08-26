#!/usr/bin/env python3
"""
予想処理エラーデバッグ用テスト
'predictions'キーエラーの原因特定
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_prediction_systems():
    """予想システムのエラーテスト"""
    print("=== 予想システムエラーデバッグテスト ===")
    
    # テスト用レースデータ
    test_race_data = {
        'race_stadium_number': 2,
        'race_number': 11,
        'race_distance': 1800,
        'weather': {
            'wind_speed': 4.5,
            'wave_height': 2.3,
            'temperature': 29,
            'humidity': 70,
            'pressure': 1010
        },
        'racers': [
            {
                'boat_number': 1,
                'racer_name': 'テストA',
                'win_rate': 35.8,
                'place_rate': 62.1,
                'avg_st': 0.15,
                'motor_2rate': 45.2,
                'boat_2rate': 41.7
            },
            {
                'boat_number': 2,
                'racer_name': 'テストB',
                'win_rate': 31.2,
                'place_rate': 57.8,
                'avg_st': 0.17,
                'motor_2rate': 42.1,
                'boat_2rate': 38.4
            },
            {
                'boat_number': 3,
                'racer_name': 'テストC',
                'win_rate': 27.6,
                'place_rate': 53.2,
                'avg_st': 0.18,
                'motor_2rate': 39.5,
                'boat_2rate': 35.8
            },
            {
                'boat_number': 4,
                'racer_name': 'テストD',
                'win_rate': 23.9,
                'place_rate': 48.7,
                'avg_st': 0.20,
                'motor_2rate': 36.8,
                'boat_2rate': 32.5
            },
            {
                'boat_number': 5,
                'racer_name': 'テストE',
                'win_rate': 20.3,
                'place_rate': 44.1,
                'avg_st': 0.22,
                'motor_2rate': 34.2,
                'boat_2rate': 29.3
            },
            {
                'boat_number': 6,
                'racer_name': 'テストF',
                'win_rate': 16.8,
                'place_rate': 39.6,
                'avg_st': 0.24,
                'motor_2rate': 31.5,
                'boat_2rate': 26.2
            }
        ]
    }
    
    print("\n[1] 超高精度システム単体テスト")
    try:
        from ultra_accuracy_enhancer import ultra_enhancer
        ultra_result = ultra_enhancer.predict_ultra(test_race_data)
        
        print(f"Ultra結果タイプ: {type(ultra_result)}")
        print(f"Ultra結果キー: {list(ultra_result.keys()) if isinstance(ultra_result, dict) else 'Not dict'}")
        
        if 'predictions' in ultra_result:
            print(f"Predictions存在: {ultra_result['predictions']}")
        else:
            print("[ERROR] 'predictions'キーが存在しません！")
            print(f"実際の内容: {ultra_result}")
        
    except Exception as e:
        print(f"[ERROR] 超高精度システムエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[2] アンサンブル予測システムテスト")
    try:
        from ensemble_predictor import ensemble_predictor
        ensemble_result = ensemble_predictor.calculate_ensemble_prediction(test_race_data)
        
        print(f"Ensemble結果タイプ: {type(ensemble_result)}")
        print(f"Ensemble結果キー: {list(ensemble_result.keys()) if isinstance(ensemble_result, dict) else 'Not dict'}")
        
        if 'predictions' in ensemble_result:
            print(f"Predictions存在: {ensemble_result['predictions']}")
        elif 'racers' in ensemble_result:
            print(f"Racers形式で結果あり: {len(ensemble_result['racers'])}艇")
        else:
            print("[ERROR] 'predictions'も'racers'も見つからない！")
            print(f"実際の内容: {ensemble_result}")
        
    except Exception as e:
        print(f"[ERROR] アンサンブルシステムエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[3] 超高精度ML単体メソッドテスト")
    try:
        from ensemble_predictor import ensemble_predictor
        ultra_ml_result = ensemble_predictor._ultra_ml_prediction(test_race_data)
        
        print(f"Ultra ML結果タイプ: {type(ultra_ml_result)}")
        print(f"Ultra ML結果キー: {list(ultra_ml_result.keys()) if isinstance(ultra_ml_result, dict) else 'Not dict'}")
        
        if 'predictions' in ultra_ml_result:
            print(f"Predictions存在: {ultra_ml_result['predictions']}")
        elif 'racers' in ultra_ml_result:
            print(f"Racers形式で結果あり: {len(ultra_ml_result['racers'])}艇")
        else:
            print("[ERROR] 予想結果形式が不明！")
            print(f"実際の内容: {ultra_ml_result}")
        
    except Exception as e:
        print(f"[ERROR] Ultra MLメソッドエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[4] フォールバック予測テスト")
    try:
        from advanced_ml_predictor import advanced_ml_predictor
        fallback_result = advanced_ml_predictor._fallback_prediction(test_race_data)
        
        print(f"Fallback結果タイプ: {type(fallback_result)}")
        print(f"Fallback結果キー: {list(fallback_result.keys()) if isinstance(fallback_result, dict) else 'Not dict'}")
        
        if 'predictions' in fallback_result:
            print(f"Predictions存在: {fallback_result['predictions']}")
        else:
            print("[ERROR] フォールバック予測でも'predictions'キーなし！")
            print(f"実際の内容: {fallback_result}")
        
    except Exception as e:
        print(f"[ERROR] フォールバック予測エラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン実行"""
    print("予想処理'predictions'エラーデバッグ")
    print("=" * 50)
    test_prediction_systems()
    print("\n" + "=" * 50)
    print("デバッグ完了")

if __name__ == "__main__":
    main()