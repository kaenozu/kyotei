#!/usr/bin/env python3
"""
Main App Module
メインのFlaskアプリケーション統合モジュール
"""

import logging
import os
import sys
from flask import Flask

# ログ設定（共通）
def setup_logging():
    """ログ設定"""
    # ログディレクトリ作成
    os.makedirs("logs", exist_ok=True)
    
    # UTF-8を強制してUnicodeエラーを回避
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    # ログフォーマット（絵文字は使用せずASCII文字のみ）
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # ファイルハンドラー（UTF-8で保存）
    file_handler = logging.FileHandler('logs/web_app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 外部ライブラリのログレベル調整
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

def create_app():
    """Flaskアプリケーション作成・設定"""
    
    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Flaskアプリケーション作成
    app = Flask(__name__, 
                template_folder='../../templates',
                static_folder='../../static')
    
    # 設定
    app.config['SECRET_KEY'] = 'boatrace-openapi-system-2025'
    
    logger.info("[OK] Flaskアプリケーション初期化完了")
    
    return app, logger

def initialize_components(app, logger):
    """コンポーネント初期化"""
    
    # 必要なクラスをインポート
    from .api_fetcher import SimpleOpenAPIFetcher
    from .routes import RouteManager
    from .scheduler_service import IntegratedScheduler, create_scheduler_routes
    
    # 必要に応じて他のクラスもインポート
    try:
        # sys.pathにプロジェクトルートディレクトリを追加
        import sys
        # scripts/modules/ から見て、プロジェクトルートは ../../ 
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core.accuracy_tracker import AccuracyTracker as OriginalAccuracyTracker
        from enhanced_predictor import EnhancedPredictor
        
        # AccuracyTrackerのパス修正版クラス
        class AccuracyTracker(OriginalAccuracyTracker):
            def __init__(self):
                super().__init__()
                # プロジェクトルートからの絶対パスでcache/にアクセス
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                self.db_path = os.path.join(project_root, 'cache', 'accuracy_tracker.db')
        
        logger.info("[OK] 外部クラスインポート成功")
        
    except ImportError as e:
        logger.warning(f"外部クラスインポート失敗: {e}")
        # フォールバック用に実際のメソッドを持つダミークラス
        class AccuracyTracker:
            def __init__(self):
                # プロジェクトルートからの絶対パスでcache/にアクセス
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                self.db_path = os.path.join(project_root, 'cache', 'accuracy_tracker.db')
            def calculate_accuracy(self):
                return {'summary': {'total_predictions': 0, 'win_hits': 0, 'win_accuracy': 0}, 'races': [], 'venues': {}}
            def save_prediction(self, *args):
                pass
            def save_race_details(self, *args):
                pass
            def get_race_details(self, *args):
                return None
        
        class EnhancedPredictor:
            def calculate_enhanced_prediction(self, venue_id, race_number, date_str='today'):
                return None
    
    # コンポーネント初期化
    fetcher = SimpleOpenAPIFetcher()
    logger.info("[OK] APIフェッチャー初期化完了")
    
    # 分割されたルートハンドラー初期化
    route_manager = RouteManager(
        app=app, 
        fetcher=fetcher,
        accuracy_tracker_class=AccuracyTracker,
        enhanced_predictor_class=EnhancedPredictor
    )
    logger.info("[OK] 分割ルートハンドラー初期化完了")
    
    # スケジューラー初期化
    scheduler = IntegratedScheduler(
        fetcher=fetcher,
        accuracy_tracker_class=AccuracyTracker,
        enhanced_predictor_class=EnhancedPredictor
    )
    
    # スケジューラーAPIルート作成
    create_scheduler_routes(app, scheduler)
    logger.info("[OK] スケジューラーサービス初期化完了")
    
    return {
        'fetcher': fetcher,
        'route_manager': route_manager,
        'scheduler': scheduler
    }

def run_application():
    """メインアプリケーション実行"""
    # アプリケーション作成
    app, logger = create_app()
    
    # コンポーネント初期化
    components = initialize_components(app, logger)
    
    print("=" * 50)
    print("BoatraceOpenAPI専用競艇予想システム")
    print("統合スケジューラー機能付き")
    print("URL: http://localhost:5001")
    print("=" * 50)
    
    # スケジューラーを自動開始
    scheduler = components['scheduler']
    scheduler.start()
    print("統合スケジューラー開始: AM6時データ取得, 毎時結果更新")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5001)
    finally:
        # アプリケーション終了時にスケジューラー停止
        scheduler.stop()
        logger.info("アプリケーション終了")

if __name__ == '__main__':
    run_application()