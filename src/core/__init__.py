"""
競艇予想システム - リファクタリング版コアモジュール

このモジュールは責任の分離により保守性を向上させた設計です：
- predictor_base.py: 基本予測システム（APIデータ取得、基本重み係数管理）
- weight_manager.py: 重み調整管理システム（動的重み調整、適応的重み学習）
- ml_integration.py: 機械学習統合システム（MLモデル管理、アンサンブル学習）
- prediction_calculator.py: 予想計算システム（艇別スコア計算、ベッティング推奨）
- cache_manager.py: キャッシュ管理システム（API・Redis・メモリキャッシュ統合）
- enhanced_predictor_refactored.py: 統合メインシステム
"""

from .predictor_base import PredictorBase
from .weight_manager import WeightManager
from .ml_integration import MLIntegrationSystem
from .prediction_calculator import PredictionCalculator
from .cache_manager import CacheManager
from .enhanced_predictor_refactored import EnhancedPredictorRefactored

__all__ = [
    "PredictorBase",
    "WeightManager", 
    "MLIntegrationSystem",
    "PredictionCalculator",
    "CacheManager",
    "EnhancedPredictorRefactored"
]

__version__ = "4.2.0"
__author__ = "Kyotei Prediction System"
