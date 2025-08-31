#!/usr/bin/env python3
"""
強化予測システムのテストとトレーニング
"""

import json
from enhanced_predictor import EnhancedPredictor
from datetime import datetime
import random

def load_training_data():
    """既存のキャッシュからトレーニングデータを読み込み"""
    try:
        with open('cache/boatrace_openapi_cache.json', 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        training_data = []
        target_results = []
        
        # キャッシュデータからレース情報を抽出
        for key, data in cache_data.items():
            if 'programs' in data:
                programs = data['programs']
                for program in programs[:10]:  # 最初の10レース分
                    if 'boats' in program and len(program['boats']) >= 6:
                        training_data.append(program)
                        # ダミーの結果データ（1号艇勝利確率を基準に）
                        boat1_rate = float(program['boats'][0].get('racer_rate', 5.0))
                        # 勝率が高い場合は1号艇勝利とする確率を上げる
                        if boat1_rate > 6.0:
                            target_results.append(1)
                        else:
                            target_results.append(random.randint(1, 6))
                            
        return training_data, target_results
        
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        return [], []

def create_dummy_training_data():
    """ダミートレーニングデータ作成"""
    training_data = []
    target_results = []
    
    for i in range(50):
        race_data = {
            'race_number': random.randint(1, 12),
            'race_distance': random.choice([1800, 1200, 1400]),
            'boats': []
        }
        
        # 1号艇を強くする（テストのため）
        for boat_num in range(6):
            if boat_num == 0:  # 1号艇
                base_rate = 6.5 + random.uniform(-1.0, 1.0)
            else:
                base_rate = 5.0 + random.uniform(-1.5, 1.5)
                
            boat_data = {
                'racer_name': f'選手{boat_num+1}',
                'racer_rate': max(2.0, min(9.0, base_rate)),
                'racer_age': random.randint(22, 50),
                'motor_rate': base_rate + random.uniform(-0.5, 0.5),
                'boat_rate': base_rate + random.uniform(-0.5, 0.5)
            }
            race_data['boats'].append(boat_data)
        
        training_data.append(race_data)
        
        # 1号艇の勝率が高い場合は1号艇勝利、そうでなければランダム
        if race_data['boats'][0]['racer_rate'] > 6.0:
            target_results.append(1 if random.random() > 0.3 else random.randint(2, 6))
        else:
            target_results.append(random.randint(1, 6))
    
    return training_data, target_results

def main():
    print("強化予測システム - Phase 1 テスト開始")
    print("=" * 50)
    
    # システム初期化
    enhanced_system = EnhancedPredictor()
    
    # トレーニングデータ読み込み
    print("トレーニングデータ読み込み中...")
    training_data, target_results = load_training_data()
    
    if not training_data:
        print("既存データなし - ダミーデータで代替")
        training_data, target_results = create_dummy_training_data()
    
    print(f"トレーニングデータ: {len(training_data)}件")
    print(f"結果データ: {len(target_results)}件")
    
    if len(training_data) < 10:
        print("データ不足のため、ダミーデータを追加...")
        dummy_data, dummy_results = create_dummy_training_data()
        training_data.extend(dummy_data)
        target_results.extend(dummy_results)
    
    # データクリーニング実行
    print("\nデータクリーニング実行中...")
    cleaned_training_data = []
    for data in training_data:
        cleaned = enhanced_system.data_cleaner.clean_race_data(data)
        cleaned_training_data.append(cleaned)
    
    print("データクリーニング完了")
    
    # モデル訓練
    print("\nモデル訓練開始...")
    training_results = enhanced_system.ensemble_predictor.train_models(
        cleaned_training_data, target_results
    )
    
    if training_results:
        print("\nトレーニング結果:")
        for model_name, accuracy in training_results.items():
            print(f"  {model_name}: {accuracy:.3f}")
    else:
        print("トレーニング失敗")
        return
    
    # テスト予測
    print("\n" + "=" * 50)
    print("テスト予測実行")
    
    test_data = {
        'race_number': 1,
        'race_distance': 1800,
        'boats': [
            {'racer_name': 'エース', 'racer_rate': 7.2, 'racer_age': 28, 'motor_rate': 6.8, 'boat_rate': 6.5},
            {'racer_name': '実力者', 'racer_rate': 5.8, 'racer_age': 35, 'motor_rate': 5.9, 'boat_rate': 5.5},
            {'racer_name': '中堅', 'racer_rate': 4.9, 'racer_age': 42, 'motor_rate': 5.1, 'boat_rate': 4.8},
            {'racer_name': 'ベテラン', 'racer_rate': 5.2, 'racer_age': 38, 'motor_rate': 5.0, 'boat_rate': 5.2},
            {'racer_name': '新人', 'racer_rate': 4.1, 'racer_age': 25, 'motor_rate': 4.8, 'boat_rate': 4.9},
            {'racer_name': '若手', 'racer_rate': 3.8, 'racer_age': 29, 'motor_rate': 4.2, 'boat_rate': 4.1}
        ]
    }
    
    result = enhanced_system.predict_race(test_data)
    
    print("\n予測結果:")
    print(f"勝利予想: {result.get('predicted_winner', '不明')}号艇")
    print(f"信頼度: {result.get('confidence', 0):.1%}")
    print(f"データ品質: {result.get('data_quality', 0):.1%}")
    print(f"期待精度: {result.get('expected_accuracy', 0):.1%}")
    
    if 'metrics' in result:
        print(f"モデル合意度: {result['metrics'].get('model_agreement', 0):.1%}")
        print(f"システム信頼度: {result['metrics'].get('system_confidence', 0):.1%}")
    
    if 'model_predictions' in result:
        print("\n各モデルの予測:")
        for model, pred in result['model_predictions'].items():
            print(f"  {model}: {pred}号艇")
    
    print(f"\nシステム: {result.get('system_version', '不明')}")
    print(f"改善方法: {result.get('data_cleaning', '不明')}")
    
    if 'error' not in result:
        print("\n🎯 Phase 1 実装成功!")
        print("目標: 41% -> 55% 精度向上への第一歩完了")
        
        # 追加テスト
        print("\n追加テスト実行...")
        for i in range(3):
            print(f"\nテスト{i+1}:")
            # ランダムなテストデータ
            test_boats = []
            for j in range(6):
                test_boats.append({
                    'racer_name': f'テスト選手{j+1}',
                    'racer_rate': random.uniform(3.0, 8.0),
                    'racer_age': random.randint(22, 50),
                    'motor_rate': random.uniform(3.0, 8.0),
                    'boat_rate': random.uniform(3.0, 8.0)
                })
            
            test_data_rand = {
                'race_number': i+1,
                'race_distance': 1800,
                'boats': test_boats
            }
            
            result = enhanced_system.predict_race(test_data_rand)
            print(f"  予想: {result.get('predicted_winner', '?')}号艇")
            print(f"  信頼度: {result.get('confidence', 0):.1%}")
            print(f"  期待精度: {result.get('expected_accuracy', 0):.1%}")
    else:
        print(f"\nエラー: {result['error']}")

if __name__ == "__main__":
    main()
