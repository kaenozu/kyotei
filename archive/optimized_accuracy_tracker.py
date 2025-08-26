#!/usr/bin/env python3
"""
最適化的中率追跡・管理システム
既存AccuracyTrackerに高速化機能を統合（完全互換）
"""

import os
import sys
import time
from pathlib import Path

# 既存システムをベースに拡張
from accuracy_tracker import AccuracyTracker as BaseAccuracyTracker
import logging

logger = logging.getLogger(__name__)

class OptimizedAccuracyTracker(BaseAccuracyTracker):
    """最適化AccuracyTracker（既存機能完全継承 + 高速化）"""
    
    def __init__(self, db_path: str = "cache/accuracy_tracker.db", enable_optimization: bool = True):
        # 既存初期化を実行
        super().__init__(db_path)
        
        self.enable_optimization = enable_optimization
        self.cache_timeout = 300  # 5分間キャッシュ
        self._cache = {}
        
        if enable_optimization:
            logger.info("AccuracyTracker最適化機能有効")
            self._setup_optimizations()
        else:
            logger.info("AccuracyTracker標準モード")
    
    def _setup_optimizations(self):
        """最適化機能セットアップ"""
        try:
            # 遅延ローダーが利用可能な場合のみ使用
            try:
                sys.path.insert(0, str(Path(__file__).parent / 'src'))
                from src.utils.lazy_loader import lazy_loader
                self.lazy_loader = lazy_loader
                logger.info("遅延ローダー統合完了")
            except ImportError:
                self.lazy_loader = None
                logger.info("遅延ローダー未使用（標準モード）")
                
            # キャッシュ初期化
            self._cache = {
                'accuracy_summary': None,
                'accuracy_summary_time': 0
            }
            
        except Exception as e:
            logger.warning(f"最適化セットアップエラー（標準モードで継続）: {e}")
            self.enable_optimization = False
    
    def get_accuracy_summary_fast(self) -> dict:
        """高速化された的中率サマリー（キャッシュ付き）"""
        if not self.enable_optimization:
            return super().calculate_accuracy()
        
        try:
            # キャッシュチェック
            current_time = time.time()
            cache_key = 'accuracy_summary'
            
            if (cache_key in self._cache and 
                self._cache[cache_key] and
                current_time - self._cache['accuracy_summary_time'] < self.cache_timeout):
                
                logger.debug("AccuracyTrackerキャッシュヒット")
                return self._cache[cache_key]
            
            # 新規計算
            start_time = time.time()
            result = super().calculate_accuracy()
            calc_time = time.time() - start_time
            
            # キャッシュ保存
            self._cache[cache_key] = result
            self._cache['accuracy_summary_time'] = current_time
            
            logger.debug(f"的中率計算完了: {calc_time:.3f}秒")
            return result
            
        except Exception as e:
            logger.error(f"高速化的中率計算エラー、標準版で実行: {e}")
            return super().calculate_accuracy()
    
    def save_prediction_optimized(self, prediction_data: dict, async_save: bool = True):
        """最適化された予想保存（非同期オプション）"""
        if not self.enable_optimization or not async_save:
            return super().save_prediction(prediction_data)
        
        try:
            # 非同期保存機能が利用可能な場合
            import threading
            
            def save_async():
                try:
                    super().save_prediction(prediction_data)
                    # キャッシュクリア（データ更新のため）
                    if 'accuracy_summary' in self._cache:
                        self._cache['accuracy_summary'] = None
                except Exception as e:
                    logger.error(f"非同期保存エラー: {e}")
            
            # 非同期実行
            thread = threading.Thread(target=save_async, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            logger.warning(f"非同期保存失敗、同期保存で実行: {e}")
            return super().save_prediction(prediction_data)
    
    def save_prediction(self, prediction_data: dict):
        """予想保存（統合インターフェース）"""
        # 最適化が有効な場合は最適化版を使用
        if self.enable_optimization:
            return self.save_prediction_optimized(prediction_data, async_save=False)
        else:
            return super().save_prediction(prediction_data)
    
    def clear_cache(self):
        """キャッシュクリア"""
        if hasattr(self, '_cache'):
            self._cache.clear()
            logger.info("AccuracyTrackerキャッシュクリア")
    
    def get_cache_status(self) -> dict:
        """キャッシュ状態取得"""
        if not self.enable_optimization:
            return {'optimization_enabled': False}
        
        return {
            'optimization_enabled': True,
            'cache_size': len(self._cache),
            'cache_items': list(self._cache.keys()),
            'lazy_loader_available': self.lazy_loader is not None
        }
    
    def get_system_status(self) -> dict:
        """システム状態取得（拡張版）"""
        base_status = {
            'database_path': self.db_path,
            'venue_count': len(self.venue_mapping)
        }
        
        if self.enable_optimization:
            base_status.update({
                'optimization_enabled': True,
                'cache_status': self.get_cache_status()
            })
        
        return base_status


def create_accuracy_tracker(optimization: bool = None) -> OptimizedAccuracyTracker:
    """AccuracyTracker作成（統合ファクトリ）"""
    
    # 環境変数による制御
    if optimization is None:
        optimization = os.getenv('USE_OPTIMIZATION', '1') == '1'
    
    logger.info(f"AccuracyTracker作成: 最適化{'ON' if optimization else 'OFF'}")
    
    try:
        return OptimizedAccuracyTracker(enable_optimization=optimization)
    except Exception as e:
        logger.error(f"OptimizedAccuracyTracker作成失敗、標準版で作成: {e}")
        return BaseAccuracyTracker()


# 既存コードとの互換性のため
AccuracyTracker = OptimizedAccuracyTracker

# モジュールレベルでの利用
def get_default_tracker():
    """デフォルトトラッカー取得"""
    return create_accuracy_tracker()


if __name__ == "__main__":
    """テスト実行"""
    print("=" * 60)
    print("最適化AccuracyTracker テスト")
    print("=" * 60)
    
    # 最適化版テスト
    print("\n[TEST] 最適化版AccuracyTracker")
    tracker_opt = OptimizedAccuracyTracker(enable_optimization=True)
    
    start_time = time.time()
    summary = tracker_opt.get_accuracy_summary_fast()
    elapsed = time.time() - start_time
    
    print(f"的中率計算時間: {elapsed:.3f}秒")
    print(f"総レース数: {summary.get('total_races', 0)}")
    print(f"的中率: {summary.get('overall_accuracy', 0)}%")
    
    print(f"\nシステム状態:")
    status = tracker_opt.get_system_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 標準版との比較
    print("\n[TEST] 標準版AccuracyTracker")
    tracker_std = OptimizedAccuracyTracker(enable_optimization=False)
    
    start_time = time.time()
    summary_std = tracker_std.calculate_accuracy()
    elapsed_std = time.time() - start_time
    
    print(f"的中率計算時間: {elapsed_std:.3f}秒")
    print(f"結果一致: {summary == summary_std}")
    
    if elapsed_std > 0:
        improvement = ((elapsed_std - elapsed) / elapsed_std) * 100
        print(f"高速化効果: {improvement:.1f}%改善")
    
    print("\n[SUCCESS] 統合AccuracyTracker テスト完了")