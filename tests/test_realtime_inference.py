"""
リアルタイム推論最適化システムのテスト
高速レース予測システムの性能評価
"""

import logging
import asyncio
import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import threading
import warnings
warnings.filterwarnings('ignore')

# プロジェクトモジュール
from ml.advanced_ensemble_predictor import create_ensemble_predictor, create_optimized_config
from ml.realtime_inference_optimizer import (
    RealtimeInferenceOptimizer,
    InferenceConfig,
    create_realtime_optimizer,
    create_high_performance_config,
    create_low_latency_config
)
from utils.performance_monitor import performance_monitor, measure_time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_race_data(n_samples: int = 100) -> List[pd.DataFrame]:
    """テスト用レースデータ生成"""
    race_data_list = []
    
    for i in range(n_samples):
        # ランダムな特徴量生成
        data = {
            'win_rate': np.random.beta(2, 8),
            'place_rate': np.random.beta(3, 6),
            'avg_start_time': np.random.normal(0.17, 0.05),
            'recent_performance': np.random.beta(3, 7),
            'motor_win_rate': np.random.beta(2, 8),
            'motor_place_rate': np.random.beta(3, 6),
            'boat_win_rate': np.random.beta(2, 8),
            'boat_place_rate': np.random.beta(3, 6),
            'lane_number': np.random.randint(1, 7),
            'weather_score': np.random.normal(0.5, 0.2),
            'wind_strength': np.random.exponential(2),
            'wave_height': np.random.exponential(1),
            'skill_index': np.random.beta(4, 6),
            'equipment_score': np.random.beta(3, 7),
            'condition_factor': np.random.beta(4, 6),
            'skill_equipment_interaction': np.random.beta(3, 7),
            'lane_skill_interaction': np.random.beta(4, 6),
            'condition_equipment_interaction': np.random.beta(3, 7)
        }
        
        race_data_list.append(pd.DataFrame([data]))
    
    return race_data_list


def test_basic_realtime_prediction(optimizer: RealtimeInferenceOptimizer):
    """基本的なリアルタイム予測テスト"""
    logger.info("=== 基本リアルタイム予測テスト ===")
    
    try:
        # テストデータ生成
        test_data = generate_test_race_data(10)
        
        results = []
        total_time = 0
        
        for i, race_data in enumerate(test_data):
            start_time = time.time()
            
            response = optimizer.predict_realtime(
                race_data=race_data,
                request_id=f"test_{i}",
                priority=1
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            total_time += processing_time
            
            results.append({
                'request_id': response.request_id,
                'success': response.error is None,
                'processing_time': response.processing_time,
                'total_time': processing_time,
                'cache_hit': response.cache_hit,
                'prediction': response.prediction_result.ensemble_prediction if response.prediction_result else None
            })
            
            logger.info(f"予測 {i+1}: {processing_time:.4f}秒, キャッシュ: {response.cache_hit}, 成功: {response.error is None}")
        
        # 統計計算
        successful_count = sum(1 for r in results if r['success'])
        avg_processing_time = total_time / len(results)
        cache_hit_count = sum(1 for r in results if r['cache_hit'])
        
        logger.info(f"成功率: {successful_count}/{len(results)} ({successful_count/len(results):.2%})")
        logger.info(f"平均処理時間: {avg_processing_time:.4f}秒")
        logger.info(f"キャッシュヒット: {cache_hit_count}/{len(results)} ({cache_hit_count/len(results):.2%})")
        
        return {
            'success_rate': successful_count / len(results),
            'avg_processing_time': avg_processing_time,
            'cache_hit_rate': cache_hit_count / len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"基本リアルタイム予測テストエラー: {e}")
        return {'error': str(e)}


async def test_async_prediction(optimizer: RealtimeInferenceOptimizer):
    """非同期予測テスト"""
    logger.info("=== 非同期予測テスト ===")
    
    try:
        # テストデータ生成
        test_data = generate_test_race_data(5)
        
        # 非同期リクエスト送信
        request_ids = []
        for i, race_data in enumerate(test_data):
            request_id = await optimizer.predict_async(
                race_data=race_data,
                request_id=f"async_test_{i}",
                priority=1
            )
            request_ids.append(request_id)
            logger.info(f"非同期リクエスト送信: {request_id}")
        
        # 結果取得
        results = []
        for request_id in request_ids:
            response = await optimizer.get_async_result(request_id, timeout=10.0)
            if response:
                results.append({
                    'request_id': response.request_id,
                    'success': response.error is None,
                    'processing_time': response.processing_time,
                    'cache_hit': response.cache_hit
                })
                logger.info(f"非同期結果取得: {request_id}, 成功: {response.error is None}")
            else:
                results.append({
                    'request_id': request_id,
                    'success': False,
                    'processing_time': 0,
                    'cache_hit': False
                })
                logger.warning(f"非同期結果取得失敗: {request_id}")
        
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"非同期予測成功率: {success_count}/{len(results)} ({success_count/len(results):.2%})")
        
        return {
            'success_rate': success_count / len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"非同期予測テストエラー: {e}")
        return {'error': str(e)}


def test_batch_prediction(optimizer: RealtimeInferenceOptimizer):
    """バッチ予測テスト"""
    logger.info("=== バッチ予測テスト ===")
    
    try:
        # テストデータ生成
        test_data = generate_test_race_data(20)
        
        with measure_time("バッチ予測"):
            responses = optimizer.batch_predict(test_data)
        
        # 結果分析
        successful_count = sum(1 for r in responses if r.error is None)
        total_processing_time = sum(r.processing_time for r in responses)
        cache_hits = sum(1 for r in responses if r.cache_hit)
        
        logger.info(f"バッチ予測結果:")
        logger.info(f"  成功: {successful_count}/{len(responses)} ({successful_count/len(responses):.2%})")
        logger.info(f"  総処理時間: {total_processing_time:.4f}秒")
        logger.info(f"  平均処理時間: {total_processing_time/len(responses):.4f}秒")
        logger.info(f"  キャッシュヒット: {cache_hits}/{len(responses)} ({cache_hits/len(responses):.2%})")
        
        return {
            'success_rate': successful_count / len(responses),
            'avg_processing_time': total_processing_time / len(responses),
            'cache_hit_rate': cache_hits / len(responses),
            'total_predictions': len(responses)
        }
        
    except Exception as e:
        logger.error(f"バッチ予測テストエラー: {e}")
        return {'error': str(e)}


def test_concurrent_predictions(optimizer: RealtimeInferenceOptimizer):
    """並行予測テスト"""
    logger.info("=== 並行予測テスト ===")
    
    def worker_function(worker_id: int, num_predictions: int) -> Dict[str, Any]:
        """ワーカー関数"""
        results = []
        test_data = generate_test_race_data(num_predictions)
        
        for i, race_data in enumerate(test_data):
            try:
                start_time = time.time()
                response = optimizer.predict_realtime(
                    race_data=race_data,
                    request_id=f"worker_{worker_id}_pred_{i}",
                    priority=2
                )
                end_time = time.time()
                
                results.append({
                    'success': response.error is None,
                    'processing_time': end_time - start_time,
                    'cache_hit': response.cache_hit
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'processing_time': 0,
                    'cache_hit': False,
                    'error': str(e)
                })
        
        return {
            'worker_id': worker_id,
            'results': results,
            'success_count': sum(1 for r in results if r['success']),
            'avg_time': np.mean([r['processing_time'] for r in results if r['success']])
        }
    
    try:
        # 複数スレッドで並行実行
        num_workers = 4
        predictions_per_worker = 5
        
        threads = []
        worker_results = {}
        
        start_time = time.time()
        
        # スレッド開始
        for worker_id in range(num_workers):
            thread = threading.Thread(
                target=lambda wid=worker_id: worker_results.update({wid: worker_function(wid, predictions_per_worker)}),
                name=f"TestWorker-{worker_id}"
            )
            thread.start()
            threads.append(thread)
        
        # スレッド終了待機
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 結果集計
        total_predictions = num_workers * predictions_per_worker
        total_successful = sum(result['success_count'] for result in worker_results.values())
        all_times = []
        
        for result in worker_results.values():
            for r in result['results']:
                if r['success']:
                    all_times.append(r['processing_time'])
        
        logger.info(f"並行予測結果:")
        logger.info(f"  ワーカー数: {num_workers}")
        logger.info(f"  総予測数: {total_predictions}")
        logger.info(f"  成功数: {total_successful} ({total_successful/total_predictions:.2%})")
        logger.info(f"  総実行時間: {total_time:.4f}秒")
        logger.info(f"  平均処理時間: {np.mean(all_times):.4f}秒")
        logger.info(f"  最大処理時間: {max(all_times):.4f}秒")
        logger.info(f"  最小処理時間: {min(all_times):.4f}秒")
        
        return {
            'num_workers': num_workers,
            'total_predictions': total_predictions,
            'success_rate': total_successful / total_predictions,
            'total_time': total_time,
            'avg_processing_time': np.mean(all_times),
            'max_processing_time': max(all_times),
            'min_processing_time': min(all_times),
            'worker_results': worker_results
        }
        
    except Exception as e:
        logger.error(f"並行予測テストエラー: {e}")
        return {'error': str(e)}


def test_performance_optimization(optimizer: RealtimeInferenceOptimizer):
    """パフォーマンス最適化テスト"""
    logger.info("=== パフォーマンス最適化テスト ===")
    
    try:
        # 初期メトリクス
        initial_metrics = optimizer.get_performance_metrics()
        logger.info("初期パフォーマンスメトリクス:")
        logger.info(f"  処理済みリクエスト: {initial_metrics['requests']['total']}")
        logger.info(f"  平均処理時間: {initial_metrics['performance']['avg_processing_time']:.4f}秒")
        logger.info(f"  キャッシュヒット率: {initial_metrics['performance']['cache_hit_rate']:.2%}")
        
        # いくつかの予測を実行してメトリクスを更新
        test_data = generate_test_race_data(10)
        for i, race_data in enumerate(test_data):
            optimizer.predict_realtime(race_data, f"metrics_test_{i}")
        
        # 更新されたメトリクス
        updated_metrics = optimizer.get_performance_metrics()
        
        # 最適化分析
        optimization_analysis = optimizer.optimize_configuration(target_latency_ms=50)
        
        logger.info("更新されたパフォーマンスメトリクス:")
        logger.info(f"  処理済みリクエスト: {updated_metrics['requests']['total']}")
        logger.info(f"  平均処理時間: {updated_metrics['performance']['avg_processing_time']:.4f}秒")
        logger.info(f"  キャッシュヒット率: {updated_metrics['performance']['cache_hit_rate']:.2%}")
        logger.info(f"  成功率: {updated_metrics['requests']['success_rate']:.2%}")
        
        logger.info("最適化分析結果:")
        logger.info(f"  現在のレイテンシー: {optimization_analysis['current_latency_ms']:.2f}ms")
        logger.info(f"  目標レイテンシー: {optimization_analysis['target_latency_ms']}ms")
        logger.info(f"  最適化が必要: {optimization_analysis['optimization_needed']}")
        
        if optimization_analysis['recommendations']:
            logger.info("推奨事項:")
            for rec in optimization_analysis['recommendations']:
                logger.info(f"  - {rec}")
        
        return {
            'initial_metrics': initial_metrics,
            'updated_metrics': updated_metrics,
            'optimization_analysis': optimization_analysis
        }
        
    except Exception as e:
        logger.error(f"パフォーマンス最適化テストエラー: {e}")
        return {'error': str(e)}


async def main():
    """メイン実行関数"""
    logger.info("リアルタイム推論最適化システム - 総合テスト開始")
    logger.info("=" * 60)
    
    try:
        # 1. アンサンブルモデル準備
        logger.info("アンサンブルモデルを準備中...")
        ensemble_config = create_optimized_config()
        predictor = create_ensemble_predictor(ensemble_config)
        
        # 訓練データ生成（テストデータと同じ特徴量名を使用）
        X_train = pd.DataFrame({
            'win_rate': np.random.beta(2, 8, 100),
            'place_rate': np.random.beta(3, 6, 100),
            'avg_start_time': np.random.normal(0.17, 0.05, 100),
            'recent_performance': np.random.beta(3, 7, 100),
            'motor_win_rate': np.random.beta(2, 8, 100),
            'motor_place_rate': np.random.beta(3, 6, 100),
            'boat_win_rate': np.random.beta(2, 8, 100),
            'boat_place_rate': np.random.beta(3, 6, 100),
            'lane_number': np.random.randint(1, 7, 100),
            'weather_score': np.random.normal(0.5, 0.2, 100),
            'wind_strength': np.random.exponential(2, 100),
            'wave_height': np.random.exponential(1, 100),
            'skill_index': np.random.beta(4, 6, 100),
            'equipment_score': np.random.beta(3, 7, 100),
            'condition_factor': np.random.beta(4, 6, 100),
            'skill_equipment_interaction': np.random.beta(3, 7, 100),
            'lane_skill_interaction': np.random.beta(4, 6, 100),
            'condition_equipment_interaction': np.random.beta(3, 7, 100)
        })
        y_train = pd.Series(np.random.randint(0, 2, 100))
        
        with measure_time("モデル訓練"):
            predictor.train(X_train, y_train)
        
        # 2. リアルタイム推論最適化システム初期化
        logger.info("リアルタイム推論最適化システムを初期化中...")
        
        # 高性能設定でテスト
        high_perf_config = create_high_performance_config()
        
        with create_realtime_optimizer(predictor, high_perf_config) as optimizer:
            
            print("\n" + "=" * 60)
            
            # 3. 基本リアルタイム予測テスト
            basic_results = test_basic_realtime_prediction(optimizer)
            
            print("\n" + "=" * 60)
            
            # 4. 非同期予測テスト
            async_results = await test_async_prediction(optimizer)
            
            print("\n" + "=" * 60)
            
            # 5. バッチ予測テスト
            batch_results = test_batch_prediction(optimizer)
            
            print("\n" + "=" * 60)
            
            # 6. 並行予測テスト
            concurrent_results = test_concurrent_predictions(optimizer)
            
            print("\n" + "=" * 60)
            
            # 7. パフォーマンス最適化テスト
            perf_results = test_performance_optimization(optimizer)
            
            print("\n" + "=" * 60)
            
            # 総合結果表示
            logger.info("=== 総合テスト結果 ===")
            
            if 'error' not in basic_results:
                logger.info(f"✓ 基本予測: 成功率 {basic_results['success_rate']:.2%}, "
                          f"平均時間 {basic_results['avg_processing_time']:.4f}秒")
            else:
                logger.info(f"✗ 基本予測: エラー - {basic_results['error']}")
            
            if 'error' not in async_results:
                logger.info(f"✓ 非同期予測: 成功率 {async_results['success_rate']:.2%}")
            else:
                logger.info(f"✗ 非同期予測: エラー - {async_results['error']}")
            
            if 'error' not in batch_results:
                logger.info(f"✓ バッチ予測: 成功率 {batch_results['success_rate']:.2%}, "
                          f"平均時間 {batch_results['avg_processing_time']:.4f}秒")
            else:
                logger.info(f"✗ バッチ予測: エラー - {batch_results['error']}")
            
            if 'error' not in concurrent_results:
                logger.info(f"✓ 並行予測: 成功率 {concurrent_results['success_rate']:.2%}, "
                          f"平均時間 {concurrent_results['avg_processing_time']:.4f}秒")
            else:
                logger.info(f"✗ 並行予測: エラー - {concurrent_results['error']}")
            
            if 'error' not in perf_results:
                final_metrics = perf_results['updated_metrics']
                logger.info(f"✓ パフォーマンス: 平均時間 {final_metrics['performance']['avg_processing_time']:.4f}秒, "
                          f"キャッシュヒット率 {final_metrics['performance']['cache_hit_rate']:.2%}")
            else:
                logger.info(f"✗ パフォーマンステスト: エラー - {perf_results['error']}")
            
            # パフォーマンス推奨事項
            logger.info("\n=== システム推奨事項 ===")
            
            if 'error' not in basic_results and basic_results['avg_processing_time'] > 0.1:
                logger.info("! 基本予測時間が100msを超えています。設定の最適化を検討してください。")
            
            if 'error' not in batch_results and batch_results['avg_processing_time'] > 0.05:
                logger.info("! バッチ予測時間が50msを超えています。並列度を上げることを検討してください。")
            else:
                logger.info("✓ 予測処理速度は良好です。")
            
            all_success = all([
                'error' not in basic_results,
                'error' not in async_results,
                'error' not in batch_results,
                'error' not in concurrent_results,
                'error' not in perf_results
            ])
            
            if all_success:
                logger.info("✓ すべてのテストが正常に完了しました。")
            else:
                logger.info("! 一部のテストでエラーが発生しました。ログを確認してください。")
        
        logger.info("\nリアルタイム推論最適化システムのテストが完了しました。")
        
    except Exception as e:
        logger.error(f"総合テスト中にエラーが発生: {e}")
        raise
    
    finally:
        # パフォーマンス監視停止
        try:
            performance_monitor.stop_monitoring_thread()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())