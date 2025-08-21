#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU加速化予測システムのテストスクリプト

目標：現在の0.12秒から0.01-0.05秒への10-12倍の処理速度向上を検証
"""

import time
import numpy as np
import pandas as pd
import torch
import psutil
import gc
from typing import Dict, Any, List
from pathlib import Path

# 必要なモジュールのインポート
try:
    from ml.gpu_accelerated_predictor import GPUAcceleratedPredictor
    from ml.realtime_inference_optimizer import RealtimeInferenceOptimizer
    from data.simple_models import TeikokuRaceInfo, TeikokuRacerInfo
except ImportError as e:
    print(f"Module import error: {e}")
    print("Required modules not found.")


class GPUPerformanceTester:
    """GPU加速化システムのパフォーマンステスト"""
    
    def __init__(self):
        self.gpu_predictor = None
        self.cpu_predictor = None
        self.test_results = {}
        
    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        print("Setup test environment...")
        
        # GPU利用可能性チェック
        if torch.cuda.is_available():
            print(f"CUDA available: {torch.cuda.get_device_name(0)}")
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
        else:
            print("CUDA not available - CPU testing only")
            
        # 予測システム初期化
        try:
            self.gpu_predictor = GPUAcceleratedPredictor()
            self.cpu_predictor = RealtimeInferenceOptimizer()
            print("Prediction systems initialized successfully")
        except Exception as e:
            print(f"Prediction system initialization error: {e}")
            
    def generate_test_data(self, num_races: int = 1000) -> pd.DataFrame:
        """テスト用データ生成"""
        print(f"Generating test data... ({num_races} races)")
        
        np.random.seed(42)
        
        # レーサー情報生成
        racers_data = []
        for race_id in range(num_races):
            for racer_num in range(1, 7):  # 1-6号艇
                racer_data = {
                    'race_id': f"race_{race_id:04d}",
                    'racer_number': racer_num,
                    'racer_name': f"選手{race_id:04d}_{racer_num}",
                    'age': np.random.randint(20, 60),
                    'weight': np.random.uniform(45, 80),
                    'recent_performance': np.random.uniform(0.0, 1.0),
                    'win_rate': np.random.uniform(0.1, 0.8),
                    'course_win_rate': np.random.uniform(0.1, 0.6),
                    'motor_score': np.random.uniform(0.3, 0.9),
                    'boat_score': np.random.uniform(0.3, 0.9),
                    'weather_factor': np.random.uniform(0.8, 1.2),
                    'course_difficulty': np.random.uniform(0.7, 1.3),
                    'starting_position': racer_num,
                    'training_score': np.random.uniform(0.4, 1.0),
                    'exhibition_score': np.random.uniform(0.4, 1.0),
                    'recent_avg_time': np.random.uniform(6.8, 7.2),
                    'start_timing': np.random.uniform(-0.2, 0.2),
                    'turn_skill': np.random.uniform(0.3, 1.0),
                    'straight_speed': np.random.uniform(0.4, 1.0),
                    'experience_years': np.random.randint(1, 30),
                    'venue_experience': np.random.randint(0, 100),
                    'opponent_strength': np.random.uniform(0.3, 0.9),
                    'recent_form': np.random.uniform(0.2, 1.0),
                    'physical_condition': np.random.uniform(0.7, 1.0)
                }
                racers_data.append(racer_data)
                
        df = pd.DataFrame(racers_data)
        print(f"✅ テストデータ生成完了: {len(df)}行")
        return df
        
    def measure_prediction_speed(self, predictor, test_data: pd.DataFrame, 
                               num_iterations: int = 100) -> Dict[str, float]:
        """予測速度測定"""
        print(f"⏱️  予測速度測定中... ({num_iterations}回)")
        
        times = []
        predictions = []
        
        # ウォームアップ実行
        for _ in range(10):
            try:
                if hasattr(predictor, 'predict_gpu'):
                    _ = predictor.predict_gpu(test_data.head(6))
                else:
                    _ = predictor.predict_realtime(test_data.head(6))
            except Exception:
                pass
                
        # 実測定
        for i in range(num_iterations):
            start_time = time.perf_counter()
            
            try:
                if hasattr(predictor, 'predict_gpu'):
                    prediction = predictor.predict_gpu(test_data.head(6))
                else:
                    prediction = predictor.predict_realtime(test_data.head(6))
                    
                end_time = time.perf_counter()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                predictions.append(prediction)
                
            except Exception as e:
                print(f"予測エラー (iteration {i}): {e}")
                continue
                
        if not times:
            return {"error": "測定失敗"}
            
        return {
            "mean_time": np.mean(times),
            "median_time": np.median(times),
            "min_time": np.min(times),
            "max_time": np.max(times),
            "std_time": np.std(times),
            "total_predictions": len(predictions),
            "success_rate": len(predictions) / num_iterations,
            "throughput_per_second": 1.0 / np.mean(times)
        }
        
    def measure_memory_usage(self, predictor, test_data: pd.DataFrame) -> Dict[str, float]:
        """メモリ使用量測定"""
        print("💾 メモリ使用量測定中...")
        
        process = psutil.Process()
        
        # 初期メモリ使用量
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_gpu_memory = 0
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            initial_gpu_memory = torch.cuda.memory_allocated() / 1024 / 1024  # MB
            
        # 予測実行
        try:
            if hasattr(predictor, 'predict_gpu'):
                _ = predictor.predict_gpu(test_data.head(6))
            else:
                _ = predictor.predict_realtime(test_data.head(6))
        except Exception as e:
            print(f"メモリ測定中の予測エラー: {e}")
            
        # 最終メモリ使用量
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_gpu_memory = 0
        
        if torch.cuda.is_available():
            final_gpu_memory = torch.cuda.memory_allocated() / 1024 / 1024  # MB
            
        return {
            "cpu_memory_initial_mb": initial_memory,
            "cpu_memory_final_mb": final_memory,
            "cpu_memory_usage_mb": final_memory - initial_memory,
            "gpu_memory_initial_mb": initial_gpu_memory,
            "gpu_memory_final_mb": final_gpu_memory,
            "gpu_memory_usage_mb": final_gpu_memory - initial_gpu_memory
        }
        
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """包括的ベンチマークテスト実行"""
        print("🚀 包括的ベンチマークテスト開始")
        print("=" * 60)
        
        # テストデータ生成
        test_data = self.generate_test_data(1000)
        
        results = {
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_data_size": len(test_data),
            "cuda_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
        }
        
        # GPU予測システムテスト
        if self.gpu_predictor and torch.cuda.is_available():
            print("\n🔥 GPU加速化予測システムテスト")
            print("-" * 40)
            
            # 速度測定
            gpu_speed_results = self.measure_prediction_speed(
                self.gpu_predictor, test_data, num_iterations=100
            )
            results["gpu_speed"] = gpu_speed_results
            
            # メモリ測定
            gpu_memory_results = self.measure_memory_usage(
                self.gpu_predictor, test_data
            )
            results["gpu_memory"] = gpu_memory_results
            
            print(f"   平均処理時間: {gpu_speed_results.get('mean_time', 0):.4f}秒")
            print(f"   スループット: {gpu_speed_results.get('throughput_per_second', 0):.1f} predictions/sec")
            
        # CPU予測システムテスト (比較用)
        if self.cpu_predictor:
            print("\n💻 CPU予測システムテスト (比較用)")
            print("-" * 40)
            
            # 速度測定
            cpu_speed_results = self.measure_prediction_speed(
                self.cpu_predictor, test_data, num_iterations=50
            )
            results["cpu_speed"] = cpu_speed_results
            
            # メモリ測定
            cpu_memory_results = self.measure_memory_usage(
                self.cpu_predictor, test_data
            )
            results["cpu_memory"] = cpu_memory_results
            
            print(f"   平均処理時間: {cpu_speed_results.get('mean_time', 0):.4f}秒")
            print(f"   スループット: {cpu_speed_results.get('throughput_per_second', 0):.1f} predictions/sec")
            
        # パフォーマンス比較
        if "gpu_speed" in results and "cpu_speed" in results:
            gpu_time = results["gpu_speed"].get("mean_time", float('inf'))
            cpu_time = results["cpu_speed"].get("mean_time", float('inf'))
            
            if gpu_time > 0 and cpu_time > 0:
                speedup = cpu_time / gpu_time
                results["speedup_factor"] = speedup
                
                print(f"\n⚡ パフォーマンス比較")
                print("-" * 40)
                print(f"   GPU処理時間: {gpu_time:.4f}秒")
                print(f"   CPU処理時間: {cpu_time:.4f}秒")
                print(f"   加速率: {speedup:.1f}倍")
                
                # 目標達成チェック
                target_time_min = 0.01  # 目標最小時間
                target_time_max = 0.05  # 目標最大時間
                target_speedup_min = 10  # 目標加速率最小
                
                print(f"\n🎯 目標達成状況")
                print("-" * 40)
                print(f"   目標処理時間: {target_time_min}-{target_time_max}秒")
                print(f"   実際処理時間: {gpu_time:.4f}秒 {'✅' if target_time_min <= gpu_time <= target_time_max else '❌'}")
                print(f"   目標加速率: {target_speedup_min}倍以上")
                print(f"   実際加速率: {speedup:.1f}倍 {'✅' if speedup >= target_speedup_min else '❌'}")
                
        return results
        
    def save_benchmark_results(self, results: Dict[str, Any]):
        """ベンチマーク結果の保存"""
        print("\n💾 ベンチマーク結果保存中...")
        
        # 結果ディレクトリ作成
        results_dir = Path("benchmark_results")
        results_dir.mkdir(exist_ok=True)
        
        # 結果ファイル保存
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"gpu_benchmark_{timestamp}.json"
        
        import json
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"✅ ベンチマーク結果保存完了: {results_file}")
        
        # サマリーレポート生成
        self.generate_summary_report(results, results_dir / f"gpu_summary_{timestamp}.txt")
        
    def generate_summary_report(self, results: Dict[str, Any], report_path: Path):
        """サマリーレポート生成"""
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("🚀 GPU加速化予測システム - ベンチマーク結果サマリー\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"テスト実行日時: {results.get('test_timestamp', 'N/A')}\n")
            f.write(f"CUDA利用可能: {'はい' if results.get('cuda_available', False) else 'いいえ'}\n")
            f.write(f"GPU名: {results.get('gpu_name', 'N/A')}\n")
            f.write(f"テストデータサイズ: {results.get('test_data_size', 0)}行\n\n")
            
            # GPU性能結果
            if "gpu_speed" in results:
                gpu_speed = results["gpu_speed"]
                f.write("🔥 GPU加速化システム性能\n")
                f.write("-" * 40 + "\n")
                f.write(f"平均処理時間: {gpu_speed.get('mean_time', 0):.4f}秒\n")
                f.write(f"最速処理時間: {gpu_speed.get('min_time', 0):.4f}秒\n")
                f.write(f"スループット: {gpu_speed.get('throughput_per_second', 0):.1f} predictions/sec\n")
                f.write(f"成功率: {gpu_speed.get('success_rate', 0) * 100:.1f}%\n\n")
                
            # CPU性能結果
            if "cpu_speed" in results:
                cpu_speed = results["cpu_speed"]
                f.write("💻 CPU システム性能 (比較用)\n")
                f.write("-" * 40 + "\n")
                f.write(f"平均処理時間: {cpu_speed.get('mean_time', 0):.4f}秒\n")
                f.write(f"最速処理時間: {cpu_speed.get('min_time', 0):.4f}秒\n")
                f.write(f"スループット: {cpu_speed.get('throughput_per_second', 0):.1f} predictions/sec\n")
                f.write(f"成功率: {cpu_speed.get('success_rate', 0) * 100:.1f}%\n\n")
                
            # 加速率
            if "speedup_factor" in results:
                speedup = results["speedup_factor"]
                f.write("⚡ 加速率\n")
                f.write("-" * 40 + "\n")
                f.write(f"GPU vs CPU: {speedup:.1f}倍高速化\n\n")
                
            # 目標達成評価
            f.write("🎯 目標達成評価\n")
            f.write("-" * 40 + "\n")
            f.write("目標: 処理速度10-12倍向上 (0.12秒 → 0.01-0.05秒)\n")
            
            if "gpu_speed" in results:
                gpu_time = results["gpu_speed"].get("mean_time", float('inf'))
                current_baseline = 0.12  # 現在のベースライン
                actual_improvement = current_baseline / gpu_time if gpu_time > 0 else 0
                
                f.write(f"実績: {actual_improvement:.1f}倍向上 ({gpu_time:.4f}秒)\n")
                f.write(f"目標達成: {'✅ 達成' if actual_improvement >= 10 else '❌ 未達成'}\n")
                
        print(f"✅ サマリーレポート生成完了: {report_path}")


def main():
    """メイン実行関数"""
    print("🚀 GPU加速化予測システム - パフォーマンステスト開始")
    print("=" * 70)
    
    # テスター初期化
    tester = GPUPerformanceTester()
    
    try:
        # 環境セットアップ
        tester.setup_test_environment()
        
        # ベンチマーク実行
        benchmark_results = tester.run_comprehensive_benchmark()
        
        # 結果保存
        tester.save_benchmark_results(benchmark_results)
        
        print("\n🎉 テスト完了！")
        print("詳細な結果は benchmark_results/ ディレクトリをご確認ください。")
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()