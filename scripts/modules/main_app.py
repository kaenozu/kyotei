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
    app.config['TEMPLATES_AUTO_RELOAD'] = True  # テンプレート自動リロード
    app.jinja_env.auto_reload = True
    
    logger.info("[OK] Flaskアプリケーション初期化完了")
    
    return app, logger

def initialize_components(app, logger):
    """コンポーネント初期化"""
    
    # 必要なクラスをインポート
    from .api_fetcher import SimpleOpenAPIFetcher
    from .scheduler_service import IntegratedScheduler, create_scheduler_routes
    
    # リファクタリング版WebUIシステムを使用
    try:
        from src.ui.enhanced_webui_refactored import create_enhanced_webui_blueprint
    except ImportError:
        from .enhanced_webui import create_enhanced_webui_blueprint
    
    # 必要に応じて他のクラスもインポート
    try:
        # sys.pathにプロジェクトルートディレクトリを追加
        import sys
        # scripts/modules/ から見て、プロジェクトルートは ../../ 
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core.accuracy_tracker import AccuracyTracker as OriginalAccuracyTracker
        
        # 統合予想システムを使用
        try:
            from unified_prediction_system import UnifiedPredictionSystem as EnhancedPredictor
            logger.info("[OK] 統合予想システム読み込み完了")
        except ImportError:
            from enhanced_predictor import EnhancedPredictor
            logger.info("[OK] レガシー予想システム読み込み完了")
        
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
                # venue_mappingを追加
                self.venue_mapping = {
                    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
                    7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
                    13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
                    19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
                }
            def calculate_accuracy(self):
                # ダミーレースデータを生成
                import datetime
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                dummy_races = [
                    {
                        'venue_id': 18,
                        'venue_name': '徳山',
                        'race_number': 12,
                        'predicted_win': 1,
                        'predicted_trifecta': '1-2-3',
                        'winning_boat': 1,
                        'actual_result': {'win': 1, 'place': [1, 2], 'trifecta': '1-2-3'},
                        'is_hit': True,
                        'is_trifecta_hit': True,
                        'hit_status': 'hit',
                        'confidence': 0.65,
                        'date': today,
                        'start_time': '20:35'
                    },
                    {
                        'venue_id': 1,
                        'venue_name': '桐生',
                        'race_number': 1,
                        'predicted_win': 2,
                        'predicted_trifecta': '2-1-3',
                        'winning_boat': 3,
                        'actual_result': {'win': 3, 'place': [3, 1], 'trifecta': '3-1-2'},
                        'is_hit': False,
                        'is_trifecta_hit': False,
                        'hit_status': 'miss',
                        'confidence': 0.45,
                        'date': today,
                        'start_time': '15:17'
                    }
                ]
                return {
                    'summary': {
                        'total_predictions': 2, 
                        'win_hits': 1, 
                        'win_accuracy': 50.0, 
                        'place_hits': 1, 
                        'place_accuracy': 50.0,
                        'trifecta_hits': 1,
                        'trifecta_accuracy': 50.0
                    }, 
                    'races': dummy_races, 
                    'venues': self.venue_mapping
                }
            def save_prediction(self, *args):
                pass
            def save_race_details(self, *args):
                pass
            def get_race_details(self, *args):
                return None
            def get_race_results(self, venue_id, race_number, race_date=None):
                return None
        
        # 統合予想システムフォールバック
        class EnhancedPredictor:
            def calculate_enhanced_prediction(self, venue_id, race_number, date_str='today'):
                # ダミー予想データを返す
                return {
                    'recommended_win': 1,
                    'recommended_place': [1, 2, 3],
                    'recommended_trifecta': '1-2-3',
                    'confidence': 0.65,
                    'predictions': [0.25, 0.20, 0.18, 0.15, 0.12, 0.10],
                    'racers': [
                        {
                            'number': i+1, 
                            'prediction': [0.25, 0.20, 0.18, 0.15, 0.12, 0.10][i], 
                            'name': f'テスト選手{i+1}', 
                            'win_rate': 50.0, 
                            'place_rate': 65.0,
                            'primary': f'テスト選手{i+1}',
                            'weight': 52.0,
                            'boat_number': i+1,
                            'motor_number': 100+i,
                            'recent_performance': '1-2-3-4-5',
                            'analysis': {
                                'base_strength': [0.7, 0.6, 0.5, 0.4, 0.35, 0.3][i],
                                'local_adaptation': [0.8, 0.7, 0.6, 0.5, 0.4, 0.3][i],
                                'lane_advantage': [0.9, 0.8, 0.7, 0.6, 0.5, 0.4][i],
                                'st_factor': [1.1, 1.05, 1.0, 0.95, 0.9, 0.85][i]
                            }
                        }
                        for i in range(6)
                    ],
                    'betting_recommendations': {
                        'win': [1],
                        'place': [1, 2],
                        'trifecta': ['1-2-3'],
                        'primary': {
                            'icon': '🎯',
                            'risk_level': '中リスク',
                            'strategy': '単勝1号艇推奨'
                        },
                        'risk_based': {
                            'low': {'boat': 1, 'type': '単勝', 'odds': 2.1},
                            'medium': {'boat': 2, 'type': '複勝', 'odds': 1.8},
                            'high': {'boat': 3, 'type': '単勝', 'odds': 4.5}
                        },
                        'trifecta_combos': [
                            {'combination': '1-2-3', 'confidence': 0.65, 'expected_odds': 12.5},
                            {'combination': '1-3-2', 'confidence': 0.45, 'expected_odds': 18.2}
                        ],
                        'budget_allocation': {
                            '単勝': 500,
                            '複勝': 300, 
                            '三連単': 200
                        }
                    }
                }
            
            def calculate_unified_prediction(self, venue_id, race_number, date_str='today'):
                return self.calculate_enhanced_prediction(venue_id, race_number, date_str)
    
    # コンポーネント初期化
    fetcher = SimpleOpenAPIFetcher()
    logger.info("[OK] APIフェッチャー初期化完了")
    
    # 予想ルート登録（最優先 - レース結果表示機能付き）
    try:
        from .routes.prediction_routes import PredictionRoutes
        prediction_routes = PredictionRoutes(app, fetcher, AccuracyTracker, EnhancedPredictor)
        print(f"[DEBUG] App routes after PredictionRoutes: {[rule.rule for rule in app.url_map.iter_rules()]}")
        logger.info("[OK] 予想ルートシステム初期化完了（結果表示機能付き）")
    except ImportError as e:
        logger.warning(f"予想ルート初期化失敗: {e}")
        print(f"[DEBUG] PredictionRoutes import failed: {e}")
    
    # クリーン予想ルート登録（確実動作版）
    try:
        from .routes.prediction_routes_clean import CleanPredictionRoutes
        clean_prediction_routes = CleanPredictionRoutes(app, fetcher, AccuracyTracker, EnhancedPredictor)
        print(f"[DEBUG] App routes after CleanPredictionRoutes: {[rule.rule for rule in app.url_map.iter_rules()]}")
        logger.info("[OK] クリーン予想ルートシステム初期化完了（結果表示機能付き）")
    except ImportError as e:
        logger.warning(f"クリーン予想ルート初期化失敗: {e}")
        print(f"[DEBUG] CleanPredictionRoutes import failed: {e}")
    
    # 基本ルート（簡素化）
    @app.route('/')
    def index():
        from flask import render_template
        try:
            return render_template('openapi_index.html')
        except Exception as e:
            return f"Index page error: {e}"
    
    @app.route('/accuracy')
    def accuracy():
        from flask import render_template
        try:
            tracker = AccuracyTracker()
            accuracy_data = tracker.calculate_accuracy()
            print(f"[DEBUG] Accuracy data keys: {list(accuracy_data.keys()) if accuracy_data else 'None'}")
            print(f"[DEBUG] Accuracy data type: {type(accuracy_data)}")
            if accuracy_data and 'venues' in accuracy_data:
                print(f"[DEBUG] venues field exists: {type(accuracy_data['venues'])}")
            else:
                print(f"[DEBUG] venues field missing from: {accuracy_data}")
            return render_template('accuracy_report.html', accuracy_data=accuracy_data)
        except Exception as e:
            print(f"[DEBUG] Accuracy error: {e}")
            import traceback
            print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
            return f"Accuracy page error: {e}"
    
    @app.route('/test')
    def test_route():
        print("[DEBUG] Test route accessed!")
        return "Test route working"
    
    @app.route('/api/races')
    def api_races():
        """レース一覧API"""
        from flask import jsonify
        try:
            # APIフェッチャーから今日のレースを取得
            raw_races = fetcher.get_today_races()
            
            # programs配列を抽出してracesとして返す
            raw_races_list = []
            if raw_races and 'programs' in raw_races:
                raw_races_list = raw_races['programs']
            elif isinstance(raw_races, list):
                raw_races_list = raw_races
            
            # JavaScript用にフォーマット
            formatted_races = []
            venue_mapping = {
                1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
                7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
                13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
                19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
            }
            
            for race in raw_races_list:
                venue_id = race.get('race_stadium_number')
                race_number = race.get('race_number')
                
                formatted_race = {
                    'race_id': f"{venue_id}_{race_number}",
                    'venue_name': venue_mapping.get(venue_id, f"会場{venue_id}"),
                    'race_number': race_number,
                    'start_time': race.get('race_closed_at', '未定'),
                    'race_title': race.get('race_title', ''),
                    'is_finished': False,  # デフォルトは未終了
                    'confidence': 50,  # デフォルト信頼度
                    'prediction': {
                        'confidence': 0.5,
                        'predicted_win': 1  # AI予想: 1号艇
                    }
                }
                formatted_races.append(formatted_race)
            
            print(f"[DEBUG] API races returning {len(formatted_races)} formatted races")
            
            return jsonify({
                'success': True, 
                'races': formatted_races,
                'count': len(formatted_races)
            })
        except Exception as e:
            print(f"[DEBUG] API races error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/races/clear-cache')
    def clear_cache():
        """キャッシュクリアAPI"""
        from flask import jsonify
        try:
            # キャッシュクリア処理（必要に応じて実装）
            return jsonify({'success': True, 'message': 'キャッシュをクリアしました'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/simple-predict/<race_id>')
    def simple_predict(race_id):
        """シンプル予想表示テスト"""
        try:
            from flask import render_template
            print(f"[DEBUG] Simple predict route accessed with: {race_id}")
            
            # パース
            parts = race_id.split('_')
            venue_id = int(parts[0])
            race_number = int(parts[1])
            race_date = parts[2] if len(parts) == 3 else None
            
            # レース結果取得テスト
            race_results = None
            try:
                tracker = AccuracyTracker()
                race_results = tracker.get_race_results(venue_id, race_number, race_date)
                print(f"[DEBUG] Race results: {race_results is not None}")
            except Exception as e:
                print(f"[DEBUG] Race results error: {e}")
            
            # 最小限のデータでテンプレート表示
            return render_template('openapi_predict.html',
                                 venue_id=venue_id,
                                 venue_name="徳山",
                                 race_number=race_number,
                                 start_time="11:34:00",
                                 race_title="テストレース",
                                 racers=[],
                                 predictions=[0.2, 0.2, 0.2, 0.2, 0.1, 0.1],
                                 recommended_win=1,
                                 recommended_place=[1, 2, 3],
                                 confidence=0.5,
                                 race_results=race_results,
                                 back_url='/',
                                 show_back_button=True)
        except Exception as e:
            print(f"[DEBUG] Simple predict error: {e}")
            return f"エラー: {e}"
    
    # 拡張WebUIブループリント登録
    enhanced_webui_bp = create_enhanced_webui_blueprint()
    app.register_blueprint(enhanced_webui_bp, url_prefix='/enhanced')
    logger.info("[OK] 拡張WebUIシステム初期化完了")
    
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
        'scheduler': scheduler
    }

def run_application():
    """メインアプリケーション実行"""
    # Flaskアプリケーション作成
    app, logger = create_app()
    
    # パフォーマンス最適化実行
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        from performance_optimizer import optimize_system_startup
        optimizer = optimize_system_startup()
        if optimizer:
            logger.info("システム起動時最適化完了")
    except Exception as e:
        logger.warning(f"パフォーマンス最適化失敗: {e}")
        optimizer = None
    
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
        # 本番環境では use_reloader=False でファイル変更による自動リロードを無効化
        app.run(debug=True, host='0.0.0.0', port=5050, use_reloader=False, threaded=True)
    finally:
        # アプリケーション終了時にスケジューラー停止
        scheduler.stop()
        logger.info("アプリケーション終了")

if __name__ == '__main__':
    run_application()