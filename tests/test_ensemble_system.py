"""
アンサンブル学習システムのテストとデモンストレーション
高度なアンサンブル予測システムの動作確認
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# プロジェクトモジュール
from ml.advanced_ensemble_predictor import (
    AdvancedEnsemblePredictor, 
    EnsembleConfig,
    create_ensemble_predictor,
    create_optimized_config
)
# from ml.advanced_feature_engineering_v2 import AdvancedFeatureEngineer
from utils.performance_monitor import performance_monitor, measure_time
from data.simple_models import TeikokuRaceInfo, TeikokuRacerStats

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_training_data(n_races: int = 1000) -> tuple[pd.DataFrame, pd.Series]:
    """サンプル訓練データの生成"""
    logger.info(f"サンプル訓練データを生成中... ({n_races}レース)")
    
    np.random.seed(42)
    
    # 基本特徴量
    features = {}
    
    # 選手成績関連
    features['win_rate'] = np.random.beta(2, 8, n_races) * 0.3  # 勝率 0-30%
    features['place_rate'] = features['win_rate'] + np.random.beta(2, 5, n_races) * 0.3  # 連対率
    features['avg_start_time'] = np.random.normal(0.17, 0.05, n_races)  # 平均ST
    features['recent_performance'] = np.random.beta(3, 7, n_races)  # 最近の成績
    
    # モーター成績
    features['motor_win_rate'] = np.random.beta(2, 8, n_races) * 0.4
    features['motor_place_rate'] = features['motor_win_rate'] + np.random.beta(2, 5, n_races) * 0.3
    
    # ボート成績
    features['boat_win_rate'] = np.random.beta(2, 8, n_races) * 0.35
    features['boat_place_rate'] = features['boat_win_rate'] + np.random.beta(2, 5, n_races) * 0.25
    
    # レース条件
    features['lane_number'] = np.random.randint(1, 7, n_races)
    features['weather_score'] = np.random.normal(0.5, 0.2, n_races)
    features['wind_strength'] = np.random.exponential(2, n_races)
    features['wave_height'] = np.random.exponential(1, n_races)
    
    # 高度な特徴量
    features['skill_index'] = (
        features['win_rate'] * 0.4 + 
        features['place_rate'] * 0.3 + 
        (1 - features['avg_start_time']) * 0.3
    )
    
    features['equipment_score'] = (
        features['motor_win_rate'] * 0.5 + 
        features['boat_win_rate'] * 0.5
    )
    
    features['condition_factor'] = (
        features['weather_score'] * 0.4 + 
        (1 / (1 + features['wind_strength'])) * 0.3 +
        (1 / (1 + features['wave_height'])) * 0.3
    )
    
    # 相互作用特徴量
    features['skill_equipment_interaction'] = features['skill_index'] * features['equipment_score']
    features['lane_skill_interaction'] = features['skill_index'] * (7 - features['lane_number']) / 6
    features['condition_equipment_interaction'] = features['condition_factor'] * features['equipment_score']
    
    # DataFrameに変換
    X = pd.DataFrame(features)
    
    # ターゲット変数（勝利確率に基づく）
    win_probability = (
        features['skill_index'] * 0.35 +
        features['equipment_score'] * 0.25 +
        features['condition_factor'] * 0.15 +
        (7 - features['lane_number']) / 6 * 0.15 +
        np.random.normal(0, 0.1, n_races) * 0.1  # ノイズ
    )
    
    # 0-1範囲にクリップ
    win_probability = np.clip(win_probability, 0, 1)
    
    # バイナリターゲット（上位20%を勝利とする）
    threshold = np.percentile(win_probability, 80)
    y = (win_probability > threshold).astype(int)
    
    logger.info(f"データ生成完了: {X.shape}, 勝利率: {y.mean():.3f}")
    return X, pd.Series(y)


def test_ensemble_training():
    """アンサンブル訓練のテスト"""
    logger.info("=== アンサンブル訓練テスト開始 ===")
    
    try:
        # サンプルデータ生成
        X_train, y_train = generate_sample_training_data(800)
        X_test, y_test = generate_sample_training_data(200)
        
        # アンサンブル予測器作成
        config = create_optimized_config()
        predictor = create_ensemble_predictor(config)
        
        # 訓練実行
        with measure_time("アンサンブル訓練"):
            training_result = predictor.train(X_train, y_train, validation_data=(X_test, y_test))
        
        # 結果表示
        logger.info("=== 訓練結果 ===")
        logger.info(f"訓練完了: {training_result['models_trained']}モデル")
        logger.info(f"訓練時間: {training_result['training_duration']}")
        
        # 個別モデル結果
        if 'individual_results' in training_result:
            logger.info("\n=== 個別モデル性能 ===")
            for model_name, result in training_result['individual_results'].items():
                if 'error' not in result:
                    logger.info(f"{model_name}:")
                    logger.info(f"  CV平均スコア: {result['cv_mean_score']:.4f} ± {result['cv_std_score']:.4f}")
                    logger.info(f"  訓練精度: {result['train_accuracy']:.4f}")
                    logger.info(f"  訓練時間: {result['training_time']}")
                else:
                    logger.warning(f"{model_name}: エラー - {result['error']}")
        
        # アンサンブル結果
        if 'ensemble_results' in training_result:
            logger.info("\n=== アンサンブル性能 ===")
            ensemble_results = training_result['ensemble_results']
            
            if 'stacking' in ensemble_results and 'error' not in ensemble_results['stacking']:
                stacking = ensemble_results['stacking']
                logger.info(f"スタッキング: {stacking['cv_mean_score']:.4f} ± {stacking['cv_std_score']:.4f}")
            
            if 'voting' in ensemble_results and 'error' not in ensemble_results['voting']:
                voting = ensemble_results['voting']
                logger.info(f"投票: {voting['cv_mean_score']:.4f} ± {voting['cv_std_score']:.4f}")
        
        # 重み最適化結果
        if 'weight_optimization' in training_result:
            weight_opt = training_result['weight_optimization']
            if 'error' not in weight_opt:
                logger.info(f"\n=== 重み最適化 ===")
                logger.info(f"最適化スコア: {weight_opt.get('best_score', 'N/A'):.4f}")
                logger.info("最適化重み:")
                for model_name, weight in weight_opt.get('optimized_weights', {}).items():
                    logger.info(f"  {model_name}: {weight:.3f}")
        
        return predictor, training_result
        
    except Exception as e:
        logger.error(f"アンサンブル訓練テストエラー: {e}")
        raise


def test_ensemble_prediction(predictor: AdvancedEnsemblePredictor):
    """アンサンブル予測のテスト"""
    logger.info("=== アンサンブル予測テスト開始 ===")
    
    try:
        # テストデータ生成
        X_test, y_true = generate_sample_training_data(50)
        
        correct_predictions = 0
        prediction_times = []
        
        logger.info("\n=== 予測結果サンプル ===")
        
        for i in range(min(10, len(X_test))):  # 最初の10件をテスト
            # 単一レース予測
            race_data = X_test.iloc[i:i+1]
            
            with measure_time(f"予測_{i+1}"):
                prediction_result = predictor.predict(race_data)
            
            prediction_times.append(prediction_result.processing_time)
            
            # 予測評価
            predicted_class = 1 if prediction_result.ensemble_prediction > 0.5 else 0
            actual_class = y_true.iloc[i]
            is_correct = predicted_class == actual_class
            
            if is_correct:
                correct_predictions += 1
            
            # 結果表示
            logger.info(f"予測 {i+1}:")
            logger.info(f"  アンサンブル予測: {prediction_result.ensemble_prediction:.4f}")
            logger.info(f"  信頼度: {prediction_result.confidence_score:.4f}")
            logger.info(f"  処理時間: {prediction_result.processing_time:.4f}秒")
            logger.info(f"  予測クラス: {predicted_class}, 実際: {actual_class}, 正解: {is_correct}")
            
            # 個別モデル予測表示
            logger.info("  個別予測:")
            for model_name, pred_value in prediction_result.predictions.items():
                weight = prediction_result.model_weights.get(model_name, 1.0)
                logger.info(f"    {model_name}: {pred_value:.4f} (重み: {weight:.3f})")
            logger.info("")
        
        # 統計表示
        accuracy = correct_predictions / min(10, len(X_test))
        avg_time = np.mean(prediction_times)
        
        logger.info("=== 予測統計 ===")
        logger.info(f"予測精度: {accuracy:.3f} ({correct_predictions}/{min(10, len(X_test))})")
        logger.info(f"平均処理時間: {avg_time:.4f}秒")
        logger.info(f"最大処理時間: {max(prediction_times):.4f}秒")
        logger.info(f"最小処理時間: {min(prediction_times):.4f}秒")
        
        return {
            "accuracy": accuracy,
            "avg_processing_time": avg_time,
            "prediction_count": min(10, len(X_test))
        }
        
    except Exception as e:
        logger.error(f"アンサンブル予測テストエラー: {e}")
        raise


def test_performance_monitoring():
    """パフォーマンス監視のテスト"""
    logger.info("=== パフォーマンス監視テスト ===")
    
    try:
        # パフォーマンス監視開始
        performance_monitor.start_monitoring(interval=30.0)
        
        # システム情報表示
        system_info = performance_monitor.get_performance_summary()
        logger.info("システム状態:")
        logger.info(f"  メモリ使用量: {system_info['system_status']['memory_usage_mb']:.1f}MB")
        logger.info(f"  CPU使用率: {system_info['system_status']['cpu_usage_percent']:.1f}%")
        logger.info(f"  監視対象関数数: {system_info['function_statistics']['total_functions_monitored']}")
        logger.info(f"  総関数呼び出し数: {system_info['function_statistics']['total_function_calls']}")
        
        # 最も時間のかかる関数TOP3
        if system_info['top_slowest_functions']:
            logger.info("\n最も時間のかかる関数:")
            for i, func_info in enumerate(system_info['top_slowest_functions'][:3], 1):
                logger.info(f"  {i}. {func_info['name']}: {func_info['avg_time']:.4f}秒 (呼び出し: {func_info['call_count']}回)")
        
        return system_info
        
    except Exception as e:
        logger.error(f"パフォーマンス監視テストエラー: {e}")
        return {}


def test_model_saving_loading(predictor: AdvancedEnsemblePredictor):
    """モデル保存・読み込みのテスト"""
    logger.info("=== モデル保存・読み込みテスト ===")
    
    try:
        model_path = "ensemble_model_test.pkl"
        
        # モデル保存
        with measure_time("モデル保存"):
            predictor.save_model(model_path)
        logger.info(f"モデル保存完了: {model_path}")
        
        # 新しい予測器でモデル読み込み
        new_predictor = create_ensemble_predictor()
        
        with measure_time("モデル読み込み"):
            new_predictor.load_model(model_path)
        logger.info("モデル読み込み完了")
        
        # 読み込み後の状態確認
        performance_summary = new_predictor.get_performance_summary()
        logger.info("読み込み後の状態:")
        logger.info(f"  訓練済み: {performance_summary['training_info']['is_trained']}")
        logger.info(f"  モデル数: {performance_summary['models']['total_models']}")
        logger.info(f"  モデル名: {', '.join(performance_summary['models']['model_names'])}")
        
        # 簡単な予測テスト
        X_simple = pd.DataFrame({
            'win_rate': [0.25],
            'place_rate': [0.45],
            'avg_start_time': [0.16],
            'recent_performance': [0.7],
            'motor_win_rate': [0.3],
            'motor_place_rate': [0.5],
            'boat_win_rate': [0.28],
            'boat_place_rate': [0.48],
            'lane_number': [1],
            'weather_score': [0.6],
            'wind_strength': [1.5],
            'wave_height': [0.8],
            'skill_index': [0.5],
            'equipment_score': [0.4],
            'condition_factor': [0.55],
            'skill_equipment_interaction': [0.2],
            'lane_skill_interaction': [0.5],
            'condition_equipment_interaction': [0.22]
        })
        
        prediction = new_predictor.predict(X_simple)
        logger.info(f"読み込み後予測テスト: {prediction.ensemble_prediction:.4f}")
        
        # ファイル削除
        import os
        if os.path.exists(model_path):
            os.remove(model_path)
            logger.info("テスト用モデルファイルを削除しました")
        
        return True
        
    except Exception as e:
        logger.error(f"モデル保存・読み込みテストエラー: {e}")
        return False


def main():
    """メイン実行関数"""
    logger.info("競艇アンサンブル学習システム - 総合テスト開始")
    logger.info("=" * 60)
    
    try:
        # 1. アンサンブル訓練テスト
        predictor, training_result = test_ensemble_training()
        
        print("\n" + "=" * 60)
        
        # 2. アンサンブル予測テスト
        prediction_result = test_ensemble_prediction(predictor)
        
        print("\n" + "=" * 60)
        
        # 3. パフォーマンス監視テスト
        performance_result = test_performance_monitoring()
        
        print("\n" + "=" * 60)
        
        # 4. モデル保存・読み込みテスト
        save_load_result = test_model_saving_loading(predictor)
        
        print("\n" + "=" * 60)
        
        # 総合結果表示
        logger.info("=== 総合テスト結果 ===")
        logger.info(f"✓ アンサンブル訓練: 成功 ({training_result['models_trained']}モデル)")
        logger.info(f"✓ アンサンブル予測: 成功 (精度: {prediction_result['accuracy']:.3f})")
        logger.info(f"✓ パフォーマンス監視: {'成功' if performance_result else '部分的成功'}")
        logger.info(f"✓ モデル保存・読み込み: {'成功' if save_load_result else '失敗'}")
        
        # システム推奨事項
        logger.info("\n=== システム推奨事項 ===")
        if prediction_result['avg_processing_time'] > 1.0:
            logger.info("! 予測処理時間が1秒を超えています。高速化の検討が必要です。")
        else:
            logger.info("✓ 予測処理速度は良好です。")
        
        if prediction_result['accuracy'] < 0.6:
            logger.info("! 予測精度が60%を下回っています。モデル調整が必要です。")
        else:
            logger.info("✓ 予測精度は良好です。")
        
        logger.info("\nアンサンブル学習システムのテストが完了しました。")
        
    except Exception as e:
        logger.error(f"総合テスト中にエラーが発生: {e}")
        raise
    
    finally:
        # 監視停止
        try:
            performance_monitor.stop_monitoring_thread()
        except:
            pass


if __name__ == "__main__":
    main()