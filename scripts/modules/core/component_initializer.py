#!/usr/bin/env python3
"""
コンポーネント初期化管理
システムコンポーネントの初期化と依存関係管理
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)

def initialize_components(app, logger):
    """システムコンポーネントを初期化"""
    try:
        # パスの追加
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        sys.path.append(parent_dir)
        
        # 各種コンポーネントの初期化
        components = {}
        
        # APIフェッチャーの初期化
        components['fetcher'] = _initialize_api_fetcher()
        
        # データベース関連の初期化
        components['accuracy_tracker'], components['enhanced_predictor'] = _initialize_database_components()
        
        # ルートハンドラーの初期化
        components['route_handlers'] = _initialize_route_handlers(app, components)
        
        # スケジューラーの初期化
        components['scheduler'] = _initialize_scheduler(
            components['fetcher'], 
            components['accuracy_tracker'], 
            components['enhanced_predictor']
        )
        
        logger.info("[OK] 全コンポーネント初期化完了")
        return components
        
    except Exception as e:
        logger.error(f"コンポーネント初期化エラー: {e}")
        raise

def _initialize_api_fetcher():
    """APIフェッチャーの初期化"""
    try:
        from api_fetcher import SimpleOpenAPIFetcher
        fetcher = SimpleOpenAPIFetcher()
        logger.info("[OK] APIフェッチャー初期化完了")
        return fetcher
    except ImportError as e:
        logger.warning(f"外部APIフェッチャーの読み込み失敗: {e}")
        # フォールバック処理
        return None

def _initialize_database_components():
    """データベース関連コンポーネントの初期化"""
    try:
        # 実際のAPIデータベースの AccuracyTracker を使用
        try:
            # プロジェクトルートのsrcディレクトリを追加
            component_dir = os.path.dirname(os.path.abspath(__file__))  # core/
            modules_dir = os.path.dirname(component_dir)  # modules/
            scripts_dir = os.path.dirname(modules_dir)  # scripts/
            project_root = os.path.dirname(scripts_dir)  # kyotei/
            src_path = os.path.join(project_root, 'src')
            src_core_path = os.path.join(project_root, 'src', 'core')
            
            # パスの追加（優先順位を高く設定）
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            if src_core_path not in sys.path:
                sys.path.insert(0, src_core_path)
                
            from accuracy_tracker import AccuracyTracker
            accuracy_tracker_class = AccuracyTracker
            logger.info("実際のAccuracyTrackerを使用")
        except ImportError as e:
            logger.error(f"AccuracyTracker読み込み失敗: {e}")
            # ダミーではなく、実際のAPIからデータ取得するクラスを作成
            try:
                from .real_api_tracker import RealAPITracker
                accuracy_tracker_class = RealAPITracker
                logger.info("実際のAPI取得システムを使用")
            except ImportError as e2:
                logger.error(f"RealAPITracker読み込み失敗: {e2}")
                logger.error("実際のデータ取得システムが利用できません")
                raise ImportError("ダミーデータの使用は禁止されています。実際のAPIデータ取得システムが必要です。")
        
        try:
            from enhanced_predictor import EnhancedPredictor
            enhanced_predictor_class = EnhancedPredictor
            logger.info("実際のEnhancedPredictorを使用")
        except ImportError:
            # ダミーではなく、実際の予想アルゴリズムを使用
            try:
                from .real_predictor import RealEnhancedPredictor
                enhanced_predictor_class = RealEnhancedPredictor
                logger.info("実際の予想アルゴリズムを使用")
            except ImportError:
                logger.error("実際の予想アルゴリズムが利用できません")
                raise ImportError("ダミー予想システムの使用は禁止されています。実際の予想アルゴリズムが必要です。")
        
        return accuracy_tracker_class, enhanced_predictor_class
        
    except Exception as e:
        logger.error(f"データベースコンポーネント初期化エラー: {e}")
        raise

def _initialize_route_handlers(app, components):
    """ルートハンドラーの初期化"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from routes.prediction_routes import PredictionRoutes
        from routes.basic_routes import BasicRoutes
        from routes.admin_routes import AdminRoutes
        from routes.api_routes import APIRoutes
        from routes.core_routes import CoreRoutes
        
        # AI総合ダッシュボード関連ルートの初期化を試行
        enhanced_webui_routes = None
        investment_handler = None
        
        try:
            from routes.investment.handler import InvestmentHandler
            investment_handler = InvestmentHandler(app, components['fetcher'], components['accuracy_tracker'])
            logger.info("投資ダッシュボードルートを初期化")
        except ImportError as e:
            logger.warning(f"投資ダッシュボードルートの初期化失敗: {e}")
        except Exception as e:
            logger.warning(f"投資ダッシュボードルート初期化エラー: {e}")
            investment_handler = None
        
        try:
            from .enhanced_webui_routes import EnhancedWebUIRoutes
            from .enhanced_webui_data_generator import EnhancedWebUIDataGenerator
            data_generator = EnhancedWebUIDataGenerator()
            enhanced_webui_routes = EnhancedWebUIRoutes(data_generator, None)  # chart_generatorはNoneで初期化
            app.register_blueprint(enhanced_webui_routes.blueprint)  # Blueprintを登録
            logger.info("AI総合ダッシュボードルートを初期化")
        except ImportError as e:
            logger.warning(f"AI総合ダッシュボードルートの初期化失敗: {e}")
        except Exception as e:
            logger.warning(f"AI総合ダッシュボードBlueprint登録エラー: {e}")
            enhanced_webui_routes = None
        
        # 各ルートハンドラーの初期化
        basic_routes = BasicRoutes(app, components['fetcher'])
        
        prediction_routes = PredictionRoutes(app, components['fetcher'], 
                                           components['accuracy_tracker'], 
                                           components['enhanced_predictor'])
        
        admin_routes = AdminRoutes(app, components['fetcher'], 
                                 components['accuracy_tracker'])
        
        api_routes = APIRoutes(app, components['fetcher'], components['accuracy_tracker'])
        core_routes = CoreRoutes(app, components['fetcher'])
        
        logger.info("[OK] ルートハンドラー初期化完了")
        
        return {
            'basic': basic_routes,
            'prediction': prediction_routes,
            'admin': admin_routes,
            'api': api_routes,
            'core': core_routes,
            'enhanced_webui': enhanced_webui_routes,
            'investment': investment_handler
        }
        
    except Exception as e:
        logger.error(f"ルートハンドラー初期化エラー: {e}")
        raise

def _initialize_scheduler(fetcher, accuracy_tracker_class, enhanced_predictor_class):
    """スケジューラーの初期化"""
    try:
        from scheduler_service import IntegratedScheduler
        scheduler = IntegratedScheduler(fetcher, accuracy_tracker_class, enhanced_predictor_class)
        logger.info("[OK] スケジューラー初期化完了")
        return scheduler
    except ImportError as e:
        logger.warning(f"スケジューラー初期化失敗: {e}")
        return None