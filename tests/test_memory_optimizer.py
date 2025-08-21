"""
メモリ・計算最適化システムのテスト
システムリソース効率とメモリ管理の評価
"""

import logging
import time
import gc
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# プロジェクトモジュール
from utils.memory_compute_optimizer import (
    MemoryComputeOptimizer,
    OptimizationConfig,
    create_memory_optimizer,
    create_aggressive_config,
    create_conservative_config,
    memory_optimized
)
from utils.performance_monitor import performance_monitor, measure_time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_memory_intensive_data() -> List[pd.DataFrame]:
    """メモリ集約的なデータ生成"""
    logger.info("メモリ集約的データを生成中...")
    
    dataframes = []
    for i in range(10):
        df = pd.DataFrame({
            'large_strings': [f'large_string_value_{j}_{i}' * 100 for j in range(1000)],
            'float_data': np.random.random(1000),
            'int_data': np.random.randint(0, 1000000, 1000),
            'category_data': np.random.choice(['A', 'B', 'C', 'D', 'E'], 1000),
            'datetime_data': pd.date_range('2023-01-01', periods=1000, freq='H')
        })
        dataframes.append(df)
    
    total_memory = sum(df.memory_usage(deep=True).sum() for df in dataframes) / 1024 / 1024
    logger.info(f"生成完了: {len(dataframes)}個のDataFrame, 総メモリ: {total_memory:.1f}MB")
    
    return dataframes


def test_memory_monitoring(optimizer: MemoryComputeOptimizer):
    """メモリ監視テスト"""
    logger.info("=== メモリ監視テスト ===")
    
    try:
        # 初期メモリプロファイル
        initial_profile = optimizer._get_memory_profile()
        logger.info(f"初期メモリ使用量: {initial_profile.process_memory_mb:.1f}MB "
                   f"({initial_profile.memory_percent:.1f}%)")
        
        # メモリ集約的な処理を実行
        memory_data = create_memory_intensive_data()
        
        # メモリ増加後のプロファイル
        after_profile = optimizer._get_memory_profile()
        memory_increase = after_profile.process_memory_mb - initial_profile.process_memory_mb
        
        logger.info(f"処理後メモリ使用量: {after_profile.process_memory_mb:.1f}MB "
                   f"({after_profile.memory_percent:.1f}%)")
        logger.info(f"メモリ増加量: {memory_increase:.1f}MB")
        
        # ガベージコレクション情報
        logger.info("ガベージコレクション統計:")
        for gen, count in after_profile.gc_collections.items():
            logger.info(f"  世代{gen}: {count}オブジェクト")
        
        # オブジェクト統計
        logger.info("主要オブジェクトタイプ:")
        for obj_type, count in list(after_profile.object_counts.items())[:5]:
            logger.info(f"  {obj_type}: {count}個")
        
        # クリーンアップ
        del memory_data
        
        return {
            "success": True,
            "initial_memory_mb": initial_profile.process_memory_mb,
            "peak_memory_mb": after_profile.process_memory_mb,
            "memory_increase_mb": memory_increase,
            "gc_collections": after_profile.gc_collections,
            "top_objects": after_profile.object_counts
        }
        
    except Exception as e:
        logger.error(f"メモリ監視テストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_dataframe_memory_optimization(optimizer: MemoryComputeOptimizer):
    """DataFrameメモリ最適化テスト"""
    logger.info("=== DataFrameメモリ最適化テスト ===")
    
    try:
        # 最適化前のDataFrame作成
        df = pd.DataFrame({
            'large_int': np.random.randint(0, 100, 5000).astype('int64'),
            'small_int': np.random.randint(0, 5, 5000).astype('int64'),
            'large_float': np.random.random(5000).astype('float64'),
            'small_float': (np.random.random(5000) * 10).astype('float64'),
            'category_str': np.random.choice(['Type1', 'Type2', 'Type3'], 5000),
            'high_cardinality': [f'unique_{i}' for i in range(5000)],
            'boolean_as_int': np.random.randint(0, 2, 5000).astype('int64')
        })
        
        original_memory = df.memory_usage(deep=True).sum()
        logger.info(f"最適化前メモリ: {original_memory/1024/1024:.2f}MB")
        
        # 最適化実行
        with measure_time("DataFrameメモリ最適化"):
            optimized_df = optimizer.optimize_dataframe_memory(df)
        
        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        reduction = (original_memory - optimized_memory) / original_memory * 100
        
        logger.info(f"最適化後メモリ: {optimized_memory/1024/1024:.2f}MB")
        logger.info(f"メモリ削減率: {reduction:.1f}%")
        
        # データ型変化の確認
        logger.info("データ型の変化:")
        for col in df.columns:
            original_type = df[col].dtype
            optimized_type = optimized_df[col].dtype
            if original_type != optimized_type:
                logger.info(f"  {col}: {original_type} → {optimized_type}")
        
        return {
            "success": True,
            "original_memory_mb": original_memory / 1024 / 1024,
            "optimized_memory_mb": optimized_memory / 1024 / 1024,
            "reduction_percent": reduction,
            "columns_optimized": sum(1 for col in df.columns 
                                   if df[col].dtype != optimized_df[col].dtype)
        }
        
    except Exception as e:
        logger.error(f"DataFrameメモリ最適化テストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_chunked_processing(optimizer: MemoryComputeOptimizer):
    """チャンク分割処理テスト"""
    logger.info("=== チャンク分割処理テスト ===")
    
    try:
        # 大きなDataFrame作成
        large_df = pd.DataFrame({
            'value1': np.random.random(20000),
            'value2': np.random.random(20000),
            'category': np.random.choice(['A', 'B', 'C'], 20000)
        })
        
        original_memory = large_df.memory_usage(deep=True).sum() / 1024 / 1024
        logger.info(f"処理対象データサイズ: {large_df.shape}, メモリ: {original_memory:.1f}MB")
        
        # 処理関数定義
        def heavy_processing(df_chunk):
            # 重い処理のシミュレーション
            result = df_chunk.copy()
            result['processed_value'] = result['value1'] * result['value2']
            result['category_encoded'] = result['category'].astype('category').cat.codes
            return result.groupby('category').agg({
                'processed_value': ['mean', 'sum', 'std'],
                'value1': 'count'
            }).reset_index()
        
        # 通常処理（比較用）
        start_time = time.time()
        normal_result = heavy_processing(large_df)
        normal_time = time.time() - start_time
        
        # チャンク処理
        start_time = time.time()
        chunked_result = optimizer.chunked_processing(
            large_df, 
            heavy_processing, 
            chunk_size_mb=5.0
        )
        chunked_time = time.time() - start_time
        
        logger.info(f"通常処理時間: {normal_time:.4f}秒")
        logger.info(f"チャンク処理時間: {chunked_time:.4f}秒")
        logger.info(f"結果一致: {normal_result.shape == chunked_result.shape}")
        
        # メモリ効率の確認
        memory_efficiency = "良好" if chunked_time < normal_time * 1.5 else "要改善"
        
        return {
            "success": True,
            "data_size_mb": original_memory,
            "normal_time": normal_time,
            "chunked_time": chunked_time,
            "time_ratio": chunked_time / normal_time,
            "results_match": normal_result.shape == chunked_result.shape,
            "memory_efficiency": memory_efficiency
        }
        
    except Exception as e:
        logger.error(f"チャンク分割処理テストエラー: {e}")
        return {"success": False, "error": str(e)}


@memory_optimized(threshold_mb=10.0)
def memory_intensive_function():
    """メモリ集約的な関数（デコレータテスト用）"""
    # 大量のデータを作成
    data_list = []
    for i in range(100):
        df = pd.DataFrame({
            'data': np.random.random(1000),
            'index': range(1000)
        })
        data_list.append(df)
    
    # 処理
    combined = pd.concat(data_list, ignore_index=True)
    result = combined.groupby('index').sum()
    
    return result


def test_memory_optimized_decorator():
    """メモリ最適化デコレータテスト"""
    logger.info("=== メモリ最適化デコレータテスト ===")
    
    try:
        initial_memory = optimization_stats_before = {}
        
        # デコレータ適用関数の実行
        start_time = time.time()
        result = memory_intensive_function()
        execution_time = time.time() - start_time
        
        logger.info(f"デコレータ適用関数実行時間: {execution_time:.4f}秒")
        logger.info(f"結果サイズ: {result.shape}")
        logger.info(f"結果メモリ: {result.memory_usage(deep=True).sum()/1024/1024:.2f}MB")
        
        return {
            "success": True,
            "execution_time": execution_time,
            "result_size": result.shape,
            "result_memory_mb": result.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
    except Exception as e:
        logger.error(f"メモリ最適化デコレータテストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_forced_optimization(optimizer: MemoryComputeOptimizer):
    """強制最適化テスト"""
    logger.info("=== 強制最適化テスト ===")
    
    try:
        # メモリを意図的に消費
        memory_consumers = []
        for i in range(50):
            df = pd.DataFrame({
                'data': np.random.random(1000),
                'text': [f'text_{j}' for j in range(1000)]
            })
            memory_consumers.append(df)
        
        # 最適化前の状態
        before_profile = optimizer._get_memory_profile()
        logger.info(f"最適化前メモリ: {before_profile.process_memory_mb:.1f}MB")
        
        # 強制最適化実行
        optimization_result = optimizer.force_optimization()
        
        # 最適化後の状態
        after_profile = optimizer._get_memory_profile()
        memory_reduction = before_profile.process_memory_mb - after_profile.process_memory_mb
        
        logger.info(f"最適化後メモリ: {after_profile.process_memory_mb:.1f}MB")
        logger.info(f"メモリ削減量: {memory_reduction:.1f}MB")
        
        # 最適化結果の詳細
        if "garbage_collection" in optimization_result:
            gc_result = optimization_result["garbage_collection"]
            logger.info(f"ガベージコレクション: {gc_result['collected']}オブジェクト回収")
        
        if "weak_cache" in optimization_result:
            cache_result = optimization_result["weak_cache"]
            logger.info(f"弱参照キャッシュ: {cache_result['cleaned']}エントリクリーンアップ")
        
        # クリーンアップ
        del memory_consumers
        
        return {
            "success": True,
            "memory_before_mb": before_profile.process_memory_mb,
            "memory_after_mb": after_profile.process_memory_mb,
            "memory_reduction_mb": memory_reduction,
            "optimization_details": optimization_result
        }
        
    except Exception as e:
        logger.error(f"強制最適化テストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_configuration_comparison():
    """設定比較テスト"""
    logger.info("=== 最適化設定比較テスト ===")
    
    try:
        configs = {
            "標準設定": OptimizationConfig(),
            "積極的設定": create_aggressive_config(),
            "控えめ設定": create_conservative_config()
        }
        
        results = {}
        
        for config_name, config in configs.items():
            logger.info(f"\n{config_name}でテスト中...")
            
            with create_memory_optimizer(config) as optimizer:
                # 短時間でのメモリ処理テスト
                test_data = pd.DataFrame({
                    'data': np.random.random(5000),
                    'category': np.random.choice(['A', 'B', 'C'], 5000)
                })
                
                start_time = time.time()
                optimized_data = optimizer.optimize_dataframe_memory(test_data)
                processing_time = time.time() - start_time
                
                # 最適化レポート取得
                report = optimizer.get_optimization_report()
                
                results[config_name] = {
                    "processing_time": processing_time,
                    "memory_reduction": (
                        (test_data.memory_usage(deep=True).sum() - 
                         optimized_data.memory_usage(deep=True).sum()) / 
                        test_data.memory_usage(deep=True).sum() * 100
                    ),
                    "current_memory_mb": report["current_memory"]["process_mb"],
                    "optimization_stats": report["optimization_stats"]
                }
                
                logger.info(f"  処理時間: {processing_time:.4f}秒")
                logger.info(f"  メモリ削減率: {results[config_name]['memory_reduction']:.1f}%")
                logger.info(f"  現在のメモリ: {report['current_memory']['process_mb']:.1f}MB")
        
        # 最高性能設定の特定
        best_config = min(results.keys(), 
                         key=lambda k: results[k]["processing_time"])
        
        logger.info(f"\n最高性能設定: {best_config}")
        logger.info(f"処理時間: {results[best_config]['processing_time']:.4f}秒")
        
        return {"success": True, "results": results, "best_config": best_config}
        
    except Exception as e:
        logger.error(f"設定比較テストエラー: {e}")
        return {"success": False, "error": str(e)}


def main():
    """メイン実行関数"""
    logger.info("メモリ・計算最適化システム - 総合テスト開始")
    logger.info("=" * 60)
    
    try:
        # 積極的設定で最適化システム作成
        config = create_aggressive_config()
        
        with create_memory_optimizer(config) as optimizer:
            
            print("\n" + "=" * 60)
            
            # 1. メモリ監視テスト
            monitoring_results = test_memory_monitoring(optimizer)
            
            print("\n" + "=" * 60)
            
            # 2. DataFrameメモリ最適化テスト
            dataframe_results = test_dataframe_memory_optimization(optimizer)
            
            print("\n" + "=" * 60)
            
            # 3. チャンク分割処理テスト
            chunked_results = test_chunked_processing(optimizer)
            
            print("\n" + "=" * 60)
            
            # 4. メモリ最適化デコレータテスト
            decorator_results = test_memory_optimized_decorator()
            
            print("\n" + "=" * 60)
            
            # 5. 強制最適化テスト
            forced_results = test_forced_optimization(optimizer)
            
            print("\n" + "=" * 60)
        
        # 6. 設定比較テスト
        comparison_results = test_configuration_comparison()
        
        print("\n" + "=" * 60)
        
        # 総合結果表示
        logger.info("=== 総合テスト結果 ===")
        
        if monitoring_results.get("success"):
            logger.info(f"✓ メモリ監視: ピークメモリ {monitoring_results['peak_memory_mb']:.1f}MB, "
                      f"増加量 {monitoring_results['memory_increase_mb']:.1f}MB")
        else:
            logger.info(f"✗ メモリ監視: エラー - {monitoring_results.get('error', '不明')}")
        
        if dataframe_results.get("success"):
            logger.info(f"✓ DataFrameメモリ最適化: {dataframe_results['reduction_percent']:.1f}% 削減, "
                      f"{dataframe_results['columns_optimized']}列最適化")
        else:
            logger.info(f"✗ DataFrameメモリ最適化: エラー - {dataframe_results.get('error', '不明')}")
        
        if chunked_results.get("success"):
            logger.info(f"✓ チャンク分割処理: 時間比 {chunked_results['time_ratio']:.2f}, "
                      f"効率: {chunked_results['memory_efficiency']}")
        else:
            logger.info(f"✗ チャンク分割処理: エラー - {chunked_results.get('error', '不明')}")
        
        if decorator_results.get("success"):
            logger.info(f"✓ メモリ最適化デコレータ: 実行時間 {decorator_results['execution_time']:.4f}秒")
        else:
            logger.info(f"✗ メモリ最適化デコレータ: エラー - {decorator_results.get('error', '不明')}")
        
        if forced_results.get("success"):
            logger.info(f"✓ 強制最適化: {forced_results['memory_reduction_mb']:.1f}MB 削減")
        else:
            logger.info(f"✗ 強制最適化: エラー - {forced_results.get('error', '不明')}")
        
        if comparison_results.get("success"):
            best_config = comparison_results['best_config']
            logger.info(f"✓ 設定比較: 最高性能設定「{best_config}」")
        else:
            logger.info(f"✗ 設定比較: エラー - {comparison_results.get('error', '不明')}")
        
        # システム推奨事項
        logger.info("\n=== システム推奨事項 ===")
        
        all_success = all([
            monitoring_results.get("success", False),
            dataframe_results.get("success", False),
            chunked_results.get("success", False),
            decorator_results.get("success", False),
            forced_results.get("success", False),
            comparison_results.get("success", False)
        ])
        
        if all_success:
            logger.info("✓ すべてのテストが正常に完了しました。")
            
            # パフォーマンス推奨事項
            if dataframe_results.get('reduction_percent', 0) > 30:
                logger.info("✓ 効果的なメモリ最適化が機能しています。")
            else:
                logger.info("! メモリ最適化の効果を改善できる可能性があります。")
            
            if chunked_results.get('time_ratio', 2.0) < 1.5:
                logger.info("✓ チャンク処理による効率化が良好です。")
            else:
                logger.info("! チャンク処理の設定調整を検討してください。")
            
        else:
            logger.info("! 一部のテストでエラーが発生しました。ログを確認してください。")
        
        logger.info("\nメモリ・計算最適化システムのテストが完了しました。")
        
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
    main()