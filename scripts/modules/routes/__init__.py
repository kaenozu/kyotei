#!/usr/bin/env python3
"""
Routes Package - ルート統合管理
分割されたルートハンドラーの統合インポート
"""

from .core_routes import CoreRoutes
from .prediction_routes import PredictionRoutes
from .api_routes import APIRoutes
from .investment_routes import InvestmentRoutes
from .admin_routes import AdminRoutes

__all__ = ['RouteManager', 'CoreRoutes', 'PredictionRoutes', 'APIRoutes', 'InvestmentRoutes', 'AdminRoutes']

class RouteManager:
    """統合ルートマネージャー"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class, enhanced_predictor_class=None):
        """
        全ルートハンドラーを初期化・統合
        
        Args:
            app: Flaskアプリケーション
            fetcher: APIフェッチャー
            accuracy_tracker_class: 的中率追跡クラス
            enhanced_predictor_class: 強化予想クラス（オプション）
        """
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        self.EnhancedPredictor = enhanced_predictor_class
        
        # 各ルートハンドラーを初期化
        self.core_routes = CoreRoutes(app, fetcher)
        self.prediction_routes = PredictionRoutes(app, fetcher, accuracy_tracker_class, enhanced_predictor_class)
        self.api_routes = APIRoutes(app, fetcher, accuracy_tracker_class)
        self.investment_routes = InvestmentRoutes(app, fetcher, accuracy_tracker_class)
        self.admin_routes = AdminRoutes(app, fetcher, accuracy_tracker_class)
        
        # 統合完了ログ
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== ルートハンドラー統合完了 ===")
        logger.info("Core Routes: メインページ・テスト")
        logger.info("Prediction Routes: 予想詳細・強化予想")
        logger.info("API Routes: レース一覧・キャッシュ管理")
        logger.info("Investment Routes: 投資・ダッシュボード")
        logger.info("Admin Routes: 的中率・結果更新")
    
    def get_route_stats(self):
        """ルート統計情報取得"""
        return {
            'total_routes': len(self.app.url_map._rules),
            'core_routes': 2,      # index, test
            'prediction_routes': 2, # predict_race, get_enhanced_prediction
            'api_routes': 6,       # api_races系
            'investment_routes': 5, # ダッシュボード系
            'admin_routes': 3      # accuracy, update-results
        }