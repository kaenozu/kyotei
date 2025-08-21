"""
高速データパイプラインのテスト
データ処理速度とパフォーマンスの評価
"""

import logging
import asyncio
import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any, AsyncGenerator
import tempfile
import warnings
warnings.filterwarnings('ignore')

# プロジェクトモジュール
from data.high_speed_data_pipeline import (
    HighSpeedDataPipeline,
    PipelineConfig,
    create_high_speed_pipeline,
    create_optimized_config,
    create_memory_optimized_config
)
from utils.performance_monitor import performance_monitor, measure_time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_large_test_data(n_rows: int = 10000, n_cols: int = 20) -> pd.DataFrame:
    """大規模テストデータ生成"""
    logger.info(f"テストデータ生成中... ({n_rows}行 x {n_cols}列)")
    
    np.random.seed(42)
    
    data = {}
    
    # 数値列
    for i in range(n_cols // 2):
        if i % 3 == 0:
            data[f'float_col_{i}'] = np.random.normal(0, 1, n_rows)
        elif i % 3 == 1:
            data[f'int_col_{i}'] = np.random.randint(0, 1000, n_rows)
        else:
            data[f'category_col_{i}'] = np.random.choice(['A', 'B', 'C', 'D'], n_rows)
    
    # 文字列列
    for i in range(n_cols // 2, n_cols):
        if i % 2 == 0:
            data[f'string_col_{i}'] = [f'value_{j}_{i}' for j in range(n_rows)]
        else:
            data[f'date_col_{i}'] = pd.date_range('2023-01-01', periods=n_rows, freq='H')
    
    df = pd.DataFrame(data)
    memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024
    logger.info(f"テストデータ生成完了: {memory_usage:.1f}MB")
    
    return df


def test_basic_dataframe_processing(pipeline: HighSpeedDataPipeline):
    """基本的なDataFrame処理テスト"""
    logger.info("=== 基本DataFrame処理テスト ===")
    
    try:
        # テストデータ生成
        test_df = generate_large_test_data(5000, 15)
        
        # 処理関数定義
        def simple_operations(df):
            # 基本的な統計操作
            df = df.copy()
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) > 0:
                df['mean_value'] = df[numeric_cols].mean(axis=1)
                df['sum_value'] = df[numeric_cols].sum(axis=1)
            
            return df
        
        # 処理実行
        start_time = time.time()
        result_df = pipeline.process_dataframe(test_df, [simple_operations])
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        logger.info(f"処理結果:")
        logger.info(f"  入力データサイズ: {test_df.shape}")
        logger.info(f"  出力データサイズ: {result_df.shape}")
        logger.info(f"  処理時間: {processing_time:.4f}秒")
        logger.info(f"  スループット: {len(test_df)/processing_time:.0f}行/秒")
        
        # キャッシュテスト
        cache_start = time.time()
        cached_result = pipeline.process_dataframe(test_df, [simple_operations])
        cache_end = time.time()
        cache_time = cache_end - cache_start
        
        logger.info(f"  キャッシュ処理時間: {cache_time:.4f}秒")
        logger.info(f"  キャッシュ高速化: {processing_time/cache_time:.1f}倍")
        
        return {
            "success": True,
            "processing_time": processing_time,
            "cache_time": cache_time,
            "throughput": len(test_df) / processing_time,
            "speedup": processing_time / cache_time
        }
        
    except Exception as e:
        logger.error(f"基本DataFrame処理テストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_memory_optimization(pipeline: HighSpeedDataPipeline):
    """メモリ最適化テスト"""
    logger.info("=== メモリ最適化テスト ===")
    
    try:
        # メモリ使用量の多いデータ生成
        test_df = pd.DataFrame({
            'large_int': np.random.randint(0, 100, 10000).astype('int64'),
            'small_int': np.random.randint(0, 5, 10000).astype('int64'),
            'large_float': np.random.random(10000).astype('float64'),
            'category_str': np.random.choice(['Type1', 'Type2', 'Type3'], 10000),
            'unique_str': [f'unique_{i}' for i in range(10000)]
        })
        
        original_memory = test_df.memory_usage(deep=True).sum()
        logger.info(f"最適化前メモリ使用量: {original_memory/1024/1024:.2f}MB")
        
        # メモリ最適化実行
        optimized_df = pipeline.optimize_dataframe_memory(test_df)
        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        
        reduction = (original_memory - optimized_memory) / original_memory * 100
        
        logger.info(f"最適化後メモリ使用量: {optimized_memory/1024/1024:.2f}MB")
        logger.info(f"メモリ削減率: {reduction:.1f}%")
        
        # データ型確認
        logger.info("最適化後のデータ型:")
        for col, dtype in optimized_df.dtypes.items():
            logger.info(f"  {col}: {dtype}")
        
        return {
            "success": True,
            "original_memory_mb": original_memory / 1024 / 1024,
            "optimized_memory_mb": optimized_memory / 1024 / 1024,
            "reduction_percent": reduction
        }
        
    except Exception as e:
        logger.error(f"メモリ最適化テストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_batch_processing(pipeline: HighSpeedDataPipeline):
    """バッチ処理テスト"""
    logger.info("=== バッチ処理テスト ===")
    
    try:
        # バッチデータ生成
        batch_data = []
        for i in range(100):
            data = {
                'id': i,
                'value': np.random.random(),
                'category': np.random.choice(['A', 'B', 'C']),
                'timestamp': time.time() + i
            }
            batch_data.append(data)
        
        # 変換関数定義
        def transform_item(item):
            item['processed_value'] = item['value'] * 2
            item['processed_at'] = time.time()
            return item
        
        # 並列バッチ処理
        start_time = time.time()
        results_parallel = pipeline.batch_transform(batch_data, transform_item, parallel=True)
        parallel_time = time.time() - start_time
        
        # シーケンシャルバッチ処理
        start_time = time.time()
        results_sequential = pipeline.batch_transform(batch_data, transform_item, parallel=False)
        sequential_time = time.time() - start_time
        
        logger.info(f"バッチ処理結果:")
        logger.info(f"  バッチサイズ: {len(batch_data)}")
        logger.info(f"  並列処理時間: {parallel_time:.4f}秒")
        logger.info(f"  シーケンシャル処理時間: {sequential_time:.4f}秒")
        logger.info(f"  並列処理の高速化: {sequential_time/parallel_time:.1f}倍")
        logger.info(f"  成功率: {len([r for r in results_parallel if r is not None])/len(batch_data):.2%}")
        
        return {
            "success": True,
            "parallel_time": parallel_time,
            "sequential_time": sequential_time,
            "speedup": sequential_time / parallel_time,
            "success_rate": len([r for r in results_parallel if r is not None]) / len(batch_data)
        }
        
    except Exception as e:
        logger.error(f"バッチ処理テストエラー: {e}")
        return {"success": False, "error": str(e)}


async def test_streaming_processing(pipeline: HighSpeedDataPipeline):
    """ストリーミング処理テスト"""
    logger.info("=== ストリーミング処理テスト ===")
    
    try:
        # ストリーミングデータジェネレータ
        async def data_generator():
            for i in range(50):
                data = {
                    'id': i,
                    'value': np.random.random(),
                    'timestamp': time.time()
                }
                yield data
                await asyncio.sleep(0.01)  # 少し間隔を空ける
        
        # ストリーミングプロセッサ
        def stream_processor(item):
            item['processed_value'] = item['value'] ** 2
            item['processed_at'] = time.time()
            return item
        
        # ストリーミング処理実行
        start_time = time.time()
        results = []
        
        async for result in pipeline.process_stream(data_generator(), stream_processor, batch_size=10):
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        successful_results = [r for r in results if r.success]
        
        logger.info(f"ストリーミング処理結果:")
        logger.info(f"  総処理時間: {processing_time:.4f}秒")
        logger.info(f"  処理アイテム数: {len(results)}")
        logger.info(f"  成功数: {len(successful_results)}")
        logger.info(f"  成功率: {len(successful_results)/len(results):.2%}")
        
        if successful_results:
            avg_processing_time = sum(r.processing_time for r in successful_results) / len(successful_results)
            logger.info(f"  平均アイテム処理時間: {avg_processing_time:.4f}秒")
        
        return {
            "success": True,
            "total_time": processing_time,
            "items_processed": len(results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "avg_item_time": avg_processing_time if successful_results else 0
        }
        
    except Exception as e:
        logger.error(f"ストリーミング処理テストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_file_io_performance(pipeline: HighSpeedDataPipeline):
    """ファイルI/Oパフォーマンステスト"""
    logger.info("=== ファイルI/Oパフォーマンステスト ===")
    
    try:
        # テストデータ生成
        test_df = generate_large_test_data(10000, 10)
        
        formats = ["csv", "parquet", "pickle"]
        results = {}
        
        for format_name in formats:
            try:
                with tempfile.NamedTemporaryFile(suffix=f".{format_name}", delete=False) as tmp:
                    filepath = tmp.name
                
                # 保存テスト
                save_start = time.time()
                pipeline.save_high_speed(test_df, filepath, format_name)
                save_time = time.time() - save_start
                
                # 読み込みテスト
                load_start = time.time()
                loaded_df = pipeline.load_high_speed(filepath, format_name)
                load_time = time.time() - load_start
                
                # ファイルサイズ確認
                import os
                file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
                
                results[format_name] = {
                    "save_time": save_time,
                    "load_time": load_time,
                    "file_size_mb": file_size,
                    "data_matches": test_df.shape == loaded_df.shape
                }
                
                logger.info(f"{format_name.upper()}形式:")
                logger.info(f"  保存時間: {save_time:.4f}秒")
                logger.info(f"  読み込み時間: {load_time:.4f}秒")
                logger.info(f"  ファイルサイズ: {file_size:.2f}MB")
                logger.info(f"  データ一致: {results[format_name]['data_matches']}")
                
                # ファイル削除
                os.unlink(filepath)
                
            except Exception as e:
                logger.warning(f"{format_name}形式テストエラー: {e}")
                results[format_name] = {"error": str(e)}
        
        return {"success": True, "results": results}
        
    except Exception as e:
        logger.error(f"ファイルI/Oテストエラー: {e}")
        return {"success": False, "error": str(e)}


def test_pipeline_performance_comparison():
    """パイプラインパフォーマンス比較テスト"""
    logger.info("=== パイプライン設定比較テスト ===")
    
    try:
        # 異なる設定でパイプライン作成
        configs = {
            "標準設定": PipelineConfig(),
            "最適化設定": create_optimized_config(),
            "メモリ最適化設定": create_memory_optimized_config()
        }
        
        test_df = generate_large_test_data(5000, 10)
        
        def processing_function(df):
            return df.groupby(df.columns[0]).agg({
                col: 'mean' for col in df.select_dtypes(include=[np.number]).columns
            }).reset_index()
        
        results = {}
        
        for config_name, config in configs.items():
            logger.info(f"\n{config_name}でテスト中...")
            
            with create_high_speed_pipeline(config) as pipeline:
                start_time = time.time()
                result_df = pipeline.process_dataframe(test_df, [processing_function])
                end_time = time.time()
                
                processing_time = end_time - start_time
                metrics = pipeline.get_performance_metrics()
                
                results[config_name] = {
                    "processing_time": processing_time,
                    "throughput": len(test_df) / processing_time,
                    "metrics": metrics
                }
                
                logger.info(f"  処理時間: {processing_time:.4f}秒")
                logger.info(f"  スループット: {len(test_df)/processing_time:.0f}行/秒")
                logger.info(f"  キャッシュヒット率: {metrics['cache']['hit_rate']:.2%}")
        
        # 最高性能の設定を特定
        best_config = min(results.keys(), key=lambda k: results[k]["processing_time"])
        
        logger.info(f"\n最高性能設定: {best_config}")
        logger.info(f"最高スループット: {results[best_config]['throughput']:.0f}行/秒")
        
        return {"success": True, "results": results, "best_config": best_config}
        
    except Exception as e:
        logger.error(f"パフォーマンス比較テストエラー: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """メイン実行関数"""
    logger.info("高速データパイプライン - 総合テスト開始")
    logger.info("=" * 60)
    
    try:
        # 最適化設定でパイプライン作成
        config = create_optimized_config()
        
        with create_high_speed_pipeline(config) as pipeline:
            
            print("\n" + "=" * 60)
            
            # 1. 基本DataFrame処理テスト
            basic_results = test_basic_dataframe_processing(pipeline)
            
            print("\n" + "=" * 60)
            
            # 2. メモリ最適化テスト
            memory_results = test_memory_optimization(pipeline)
            
            print("\n" + "=" * 60)
            
            # 3. バッチ処理テスト
            batch_results = test_batch_processing(pipeline)
            
            print("\n" + "=" * 60)
            
            # 4. ストリーミング処理テスト
            stream_results = await test_streaming_processing(pipeline)
            
            print("\n" + "=" * 60)
            
            # 5. ファイルI/Oテスト
            io_results = test_file_io_performance(pipeline)
            
            print("\n" + "=" * 60)
        
        # 6. パフォーマンス比較テスト
        comparison_results = test_pipeline_performance_comparison()
        
        print("\n" + "=" * 60)
        
        # 総合結果表示
        logger.info("=== 総合テスト結果 ===")
        
        if basic_results.get("success"):
            logger.info(f"✓ 基本DataFrame処理: スループット {basic_results['throughput']:.0f}行/秒, "
                      f"キャッシュ高速化 {basic_results['speedup']:.1f}倍")
        else:
            logger.info(f"✗ 基本DataFrame処理: エラー - {basic_results.get('error', '不明')}")
        
        if memory_results.get("success"):
            logger.info(f"✓ メモリ最適化: {memory_results['reduction_percent']:.1f}% 削減 "
                      f"({memory_results['original_memory_mb']:.1f}MB → {memory_results['optimized_memory_mb']:.1f}MB)")
        else:
            logger.info(f"✗ メモリ最適化: エラー - {memory_results.get('error', '不明')}")
        
        if batch_results.get("success"):
            logger.info(f"✓ バッチ処理: 並列高速化 {batch_results['speedup']:.1f}倍, "
                      f"成功率 {batch_results['success_rate']:.2%}")
        else:
            logger.info(f"✗ バッチ処理: エラー - {batch_results.get('error', '不明')}")
        
        if stream_results.get("success"):
            logger.info(f"✓ ストリーミング処理: 成功率 {stream_results['success_rate']:.2%}, "
                      f"平均処理時間 {stream_results['avg_item_time']:.4f}秒")
        else:
            logger.info(f"✗ ストリーミング処理: エラー - {stream_results.get('error', '不明')}")
        
        if io_results.get("success"):
            formats_tested = len([r for r in io_results['results'].values() if 'error' not in r])
            logger.info(f"✓ ファイルI/O: {formats_tested}形式対応")
        else:
            logger.info(f"✗ ファイルI/O: エラー - {io_results.get('error', '不明')}")
        
        if comparison_results.get("success"):
            best_config = comparison_results['best_config']
            best_throughput = comparison_results['results'][best_config]['throughput']
            logger.info(f"✓ パフォーマンス比較: 最高性能設定「{best_config}」, "
                      f"スループット {best_throughput:.0f}行/秒")
        else:
            logger.info(f"✗ パフォーマンス比較: エラー - {comparison_results.get('error', '不明')}")
        
        # システム推奨事項
        logger.info("\n=== システム推奨事項 ===")
        
        all_success = all([
            basic_results.get("success", False),
            memory_results.get("success", False),
            batch_results.get("success", False),
            stream_results.get("success", False),
            io_results.get("success", False),
            comparison_results.get("success", False)
        ])
        
        if all_success:
            logger.info("✓ すべてのテストが正常に完了しました。")
            
            # パフォーマンス推奨事項
            if basic_results.get('throughput', 0) > 10000:
                logger.info("✓ 高いデータ処理スループットを達成しています。")
            else:
                logger.info("! データ処理スループットの改善を検討してください。")
            
            if memory_results.get('reduction_percent', 0) > 30:
                logger.info("✓ 効果的なメモリ最適化が機能しています。")
            else:
                logger.info("! メモリ最適化の設定を見直してください。")
            
        else:
            logger.info("! 一部のテストでエラーが発生しました。ログを確認してください。")
        
        logger.info("\n高速データパイプラインのテストが完了しました。")
        
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