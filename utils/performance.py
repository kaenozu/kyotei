"""
パフォーマンス監視・プロファイリングシステム
"""
import time
import threading
import functools
import logging
import psutil
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Callable, Any, Optional
from pathlib import Path
import json

from config.settings import BASE_DIR, PERFORMANCE_CONFIG # PERFORMANCE_CONFIGをインポート


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    cache_hit_rate: float
    active_threads: int
    response_time_ms: float
    operation_type: str = "unknown"


class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.monitoring = False
        self.monitor_thread = None
        self.logger = logging.getLogger(__name__)
        self.metrics_file = BASE_DIR / "logs" / "performance_metrics.json"
        
        # 操作別の応答時間追跡
        self.operation_times: Dict[str, List[float]] = {}
        self.lock = threading.RLock()
    
    def start_monitoring(self, interval: int = PERFORMANCE_CONFIG['monitor_interval']):
        """監視開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,), 
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("パフォーマンス監視を開始しました")
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("パフォーマンス監視を停止しました")
    
    def _monitor_loop(self, interval: int):
        """監視ループ"""
        while self.monitoring:
            try:
                # システムメトリクス取得
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                memory_mb = memory.used / 1024 / 1024
                
                # キャッシュヒット率取得
                from utils.cache import cache
                cache_info = cache.get_cache_info()
                hit_rate = cache_info.get('hit_rate', 0.0)
                
                # アクティブスレッド数
                active_threads = threading.active_count()
                
                # 最新の応答時間（平均）
                avg_response_time = self._get_average_response_time()
                
                # メトリクス記録
                metrics = PerformanceMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    cache_hit_rate=hit_rate,
                    active_threads=active_threads,
                    response_time_ms=avg_response_time,
                    operation_type="system_monitor"
                )
                
                with self.lock:
                    self.metrics_history.append(metrics)
                    
                    # 履歴サイズ制限（最新1000件のみ保持）
                    if len(self.metrics_history) > 1000:
                        self.metrics_history = self.metrics_history[-1000:]
                
                # 定期的にファイルに保存
                if len(self.metrics_history) % 10 == 0:
                    self._save_metrics_to_file()
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"監視エラー: {e}")
                time.sleep(interval)
    
    def _get_average_response_time(self) -> float:
        """平均応答時間を計算"""
        with self.lock:
            all_times = []
            for times_list in self.operation_times.values():
                all_times.extend(times_list[-10:])  # 最新10件のみ
            
            return sum(all_times) / len(all_times) if all_times else 0.0
    
    def record_operation_time(self, operation: str, duration_ms: float):
        """操作時間を記録"""
        with self.lock:
            if operation not in self.operation_times:
                self.operation_times[operation] = []
            
            self.operation_times[operation].append(duration_ms)
            
            # 各操作の履歴は最新100件のみ保持
            if len(self.operation_times[operation]) > 100:
                self.operation_times[operation] = self.operation_times[operation][-100:]
    
    def get_performance_report(self, minutes: int = 10) -> Dict:
        """パフォーマンスレポート取得"""
        cutoff_time = time.time() - (minutes * 60)
        
        with self.lock:
            recent_metrics = [
                m for m in self.metrics_history 
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {"error": "データが不十分です"}
        
        # 統計計算
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_mb for m in recent_metrics]
        cache_rates = [m.cache_hit_rate for m in recent_metrics]
        response_times = [m.response_time_ms for m in recent_metrics]
        
        # 操作別統計
        operation_stats = {}
        for op, times in self.operation_times.items():
            if times:
                operation_stats[op] = {
                    "count": len(times),
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times)
                }
        
        return {
            "period_minutes": minutes,
            "sample_count": len(recent_metrics),
            "cpu_usage": {
                "avg": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values)
            },
            "memory_usage": {
                "avg_mb": sum(memory_values) / len(memory_values),
                "min_mb": min(memory_values),
                "max_mb": max(memory_values),
                "peak_mb": max(memory_values)
            },
            "cache_performance": {
                "avg_hit_rate": sum(cache_rates) / len(cache_rates),
                "min_hit_rate": min(cache_rates),
                "max_hit_rate": max(cache_rates)
            },
            "response_times": {
                "avg_ms": sum(response_times) / len(response_times),
                "min_ms": min(response_times),
                "max_ms": max(response_times)
            },
            "operation_stats": operation_stats,
            "current_metrics": recent_metrics[-1] if recent_metrics else None,
            "status": self._determine_system_status(recent_metrics)
        }
    
    def _determine_system_status(self, metrics: List[PerformanceMetrics]) -> str:
        """システム状態を判定"""
        if not metrics:
            return "unknown"
        
        latest = metrics[-1]
        
        # 複数の指標で総合判定
        if latest.cpu_percent > PERFORMANCE_CONFIG['cpu_critical_threshold']:
            return "critical"
        elif latest.cpu_percent > PERFORMANCE_CONFIG['cpu_warning_threshold']:
            return "warning"
        elif latest.memory_mb > PERFORMANCE_CONFIG['memory_critical_threshold_mb']:
            return "critical"
        elif latest.memory_mb > PERFORMANCE_CONFIG['memory_warning_threshold_mb']:
            return "warning"
        elif latest.cache_hit_rate < PERFORMANCE_CONFIG['cache_hit_rate_critical_threshold']:
            return "critical"
        elif latest.cache_hit_rate < PERFORMANCE_CONFIG['cache_hit_rate_warning_threshold']:
            return "warning"
        else:
            return "healthy"
    
    def _save_metrics_to_file(self):
        """メトリクスをファイルに保存"""
        try:
            # ログディレクトリを作成
            self.metrics_file.parent.mkdir(exist_ok=True, parents=True)
            
            # 最新100件のメトリクスを保存
            with self.lock:
                recent_metrics = self.metrics_history[-100:]
            
            metrics_data = [asdict(m) for m in recent_metrics]
            
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"メトリクス保存エラー: {e}")


def performance_timer(operation_name: str = None):
    """パフォーマンス測定デコレータ"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # パフォーマンス監視システムに記録
                if hasattr(performance_monitor, 'record_operation_time'):
                    performance_monitor.record_operation_time(op_name, duration_ms)
                
                # ログに記録（遅い処理のみ）
                if duration_ms > 1000:  # 1秒以上
                    logging.getLogger(__name__).warning(
                        f"⏱️  遅い処理検出: {op_name} - {duration_ms:.1f}ms"
                    )
                elif duration_ms > 100:  # 100ms以上
                    logging.getLogger(__name__).info(
                        f"⏱️  {op_name}: {duration_ms:.1f}ms"
                    )
        
        return wrapper
    return decorator


class ResourceMonitor:
    """リソース使用量監視クラス"""
    
    @staticmethod
    def get_system_info() -> Dict:
        """システム情報取得"""
        try:
            # CPU情報
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # メモリ情報
            memory = psutil.virtual_memory()
            
            # ディスク情報
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else 0,
                    "usage_percent": psutil.cpu_percent(interval=1)
                },
                "memory": {
                    "total_mb": memory.total / 1024 / 1024,
                    "available_mb": memory.available / 1024 / 1024,
                    "used_mb": memory.used / 1024 / 1024,
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / 1024 / 1024 / 1024,
                    "free_gb": disk.free / 1024 / 1024 / 1024,
                    "used_gb": disk.used / 1024 / 1024 / 1024,
                    "percent": (disk.used / disk.total) * 100
                },
                "processes": len(psutil.pids()),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"システム情報取得エラー: {e}")
            return {}
    
    @staticmethod
    def check_resource_limits() -> Dict[str, bool]:
        """リソース制限チェック"""
        try:
            system_info = ResourceMonitor.get_system_info()
            
            return {
                "cpu_healthy": system_info.get("cpu", {}).get("usage_percent", 100) < PERFORMANCE_CONFIG['cpu_warning_threshold'],
                "memory_healthy": system_info.get("memory", {}).get("percent", 100) < (PERFORMANCE_CONFIG['memory_warning_threshold_mb'] / (system_info.get("memory", {}).get("total_mb", 1) + 0.000001)) * 100,
                "disk_healthy": system_info.get("disk", {}).get("percent", 100) < 90,
                "overall_healthy": all([
                    system_info.get("cpu", {}).get("usage_percent", 100) < PERFORMANCE_CONFIG['cpu_warning_threshold'],
                    system_info.get("memory", {}).get("percent", 100) < (PERFORMANCE_CONFIG['memory_warning_threshold_mb'] / (system_info.get("memory", {}).get("total_mb", 1) + 0.000001)) * 100,
                    system_info.get("disk", {}).get("percent", 100) < 90
                ])
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"リソース制限チェックエラー: {e}")
            return {"overall_healthy": False}


# グローバルパフォーマンス監視インスタンス
performance_monitor = PerformanceMonitor()


def start_performance_monitoring():
    """パフォーマンス監視を開始"""
    performance_monitor.start_monitoring()

def stop_performance_monitoring():
    """パフォーマンス監視を停止"""
    performance_monitor.stop_monitoring()

def get_performance_summary() -> str:
    """パフォーマンス要約を文字列で取得"""
    try:
        report = performance_monitor.get_performance_report(minutes=5)
        
        if "error" in report:
            return "パフォーマンスデータが不足しています"
        
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "🔴",
            "unknown": "❓"
        }
        
        emoji = status_emoji.get(report["status"], "❓")
        
        summary = f"""{emoji} システム状態: {report["status"]}
CPU使用率: {report["cpu_usage"]["avg"]:.1f}% (最大: {report["cpu_usage"]["max"]:.1f}%)
メモリ使用量: {report["memory_usage"]["avg_mb"]:.1f}MB (ピーク: {report["memory_usage"]["peak_mb"]:.1f}MB)
キャッシュヒット率: {report["cache_performance"]["avg_hit_rate"]:.1%}
平均応答時間: {report["response_times"]["avg_ms"]:.1f}ms"""
        
        return summary
        
    except Exception as e:
        return f"パフォーマンス要約取得エラー: {e}"


if __name__ == "__main__":
    # テスト実行
    print("パフォーマンス監視テスト開始...")
    
    start_performance_monitoring()
    
    # テスト関数
    @performance_timer("test_function")
    def test_slow_function():
        import time
        time.sleep(0.1)  # 100ms待機
        return "test_result"
    
    # テスト実行
    for i in range(5):
        result = test_slow_function()
        time.sleep(1)
    
    # レポート表示
    time.sleep(15)  # 15秒待機してデータ収集
    
    print("\n📊 パフォーマンスレポート:")
    print(get_performance_summary())
    
    report = performance_monitor.get_performance_report(minutes=1)
    print(f"\n操作統計: {report.get('operation_stats', {})}")
    
    stop_performance_monitoring()
    print("\nテスト完了")
