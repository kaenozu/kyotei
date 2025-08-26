#!/usr/bin/env python3
"""
競艇予想システム - 統合メインアプリケーション
既存システムと最適化機能を統合（デメリットなし）
"""

import sys
import os
import time
import logging
from pathlib import Path

# プロジェクトパスの設定
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 基本設定
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegratedBoatraceSystem:
    """統合競艇予想システム（既存互換・高速起動対応）"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("統合システム起動開始")
        
        # 設定管理
        self.use_fast_startup = os.getenv('FAST_STARTUP', '1') == '1'
        self.use_optimization = os.getenv('USE_OPTIMIZATION', '1') == '1'
        
        # システムコンポーネント
        self.accuracy_tracker = None
        self.predictor = None
        self.web_server = None
        
        # 互換性確保のため既存システムを優先
        self._init_system()
    
    def _init_system(self):
        """システム初期化（段階的統合）"""
        try:
            logger.info("システム初期化開始")
            
            # 既存AccuracyTrackerを使用（完全互換）
            logger.info("AccuracyTracker初期化中...")
            from accuracy_tracker import AccuracyTracker
            self.accuracy_tracker = AccuracyTracker()
            logger.info("AccuracyTracker初期化完了")
            
            # 予想エンジンの選択（最適化版 or 既存版）
            if self.use_optimization and self.use_fast_startup:
                logger.info("最適化予想エンジン使用")
                try:
                    from src.core.optimized_predictor import OptimizedBoatracePredictor
                    self.predictor = OptimizedBoatracePredictor()
                    logger.info("最適化予想エンジン初期化完了")
                except Exception as e:
                    logger.warning(f"最適化エンジン初期化失敗、既存版にフォールバック: {e}")
                    self._init_legacy_predictor()
            else:
                logger.info("既存予想エンジン使用")
                self._init_legacy_predictor()
                
        except Exception as e:
            logger.error(f"システム初期化エラー: {e}")
            raise
    
    def _init_legacy_predictor(self):
        """既存予想エンジン初期化"""
        try:
            # 既存のenhanced_predictorを使用
            from enhanced_predictor import EnhancedPredictionSystem
            self.predictor = EnhancedPredictionSystem()
            logger.info("既存予想エンジン初期化完了")
        except ImportError:
            # advanced_ml_predictorにフォールバック
            try:
                from advanced_ml_predictor import AdvancedMLPredictor
                self.predictor = AdvancedMLPredictor()
                logger.info("ML予想エンジン初期化完了")
            except Exception as e:
                logger.error(f"既存エンジン初期化失敗: {e}")
                raise
    
    def predict_race(self, venue_id: int, race_number: int, date_str: str = 'today') -> dict:
        """レース予想（統合インターフェース）"""
        try:
            # 最適化エンジン使用時
            if hasattr(self.predictor, 'predict_race'):
                result = self.predictor.predict_race(venue_id, race_number, date_str)
                if result:
                    # AccuracyTrackerで追跡
                    self.accuracy_tracker.save_prediction(result)
                    return result
            
            # 既存エンジン使用時の代替処理
            elif hasattr(self.predictor, 'predict_for_race'):
                result = self.predictor.predict_for_race(venue_id, race_number)
                if result:
                    # 形式を統一
                    formatted_result = {
                        'venue_id': venue_id,
                        'venue_name': self.accuracy_tracker.venue_mapping.get(venue_id, f"会場{venue_id}"),
                        'race_number': race_number,
                        'recommended_win': result.get('top_boat', 1),
                        'recommended_place': result.get('top_3_boats', [1, 2, 3]),
                        'confidence': result.get('confidence', 0.5),
                        'prediction_time': time.time()
                    }
                    self.accuracy_tracker.save_prediction(formatted_result)
                    return formatted_result
            
            return None
            
        except Exception as e:
            logger.error(f"予想実行エラー: {e}")
            return None
    
    def run_accuracy_analysis(self):
        """的中率分析実行（既存互換）"""
        try:
            logger.info("的中率分析開始")
            summary = self.accuracy_tracker.calculate_accuracy()
            
            print("\n" + "="*60)
            print("競艇予想システム - 的中率サマリー")
            print("="*60)
            print(f"予想レース数: {summary.get('total_races', 0)}レース")
            print(f"単勝的中率: {summary.get('overall_accuracy', 0)}%")
            print(f"複勝的中率: {summary.get('place_accuracy', 0)}%") 
            print(f"三連単的中率: {summary.get('trifecta_accuracy', 0)}%")
            print(f"単勝的中数: {summary.get('hits', 0)}レース")
            print(f"単勝外れ数: {summary.get('misses', 0)}レース")
            print("="*60)
            
            return summary
            
        except Exception as e:
            logger.error(f"的中率分析エラー: {e}")
            return {}
    
    def start_web_server(self, port: int = 5000):
        """Webサーバー起動（統合版）"""
        try:
            logger.info(f"統合Webサーバー起動準備 (ポート: {port})")
            
            # Flaskの初期化（最適化版 or 既存版）
            if self.use_optimization:
                try:
                    from src.utils.lazy_loader import lazy_loader
                    flask_module = lazy_loader.get('flask')
                    Flask = flask_module.Flask
                    logger.info("最適化Flask使用")
                except:
                    from flask import Flask
                    logger.info("標準Flask使用")
            else:
                from flask import Flask
            
            app = Flask(__name__)
            
            # 統合APIエンドポイント
            @app.route('/')
            def index():
                startup_time = time.time() - self.start_time
                return {
                    'system': '統合競艇予想システム',
                    'version': '3.0-Integrated',
                    'startup_time': f"{startup_time:.2f}秒",
                    'optimization_enabled': self.use_optimization,
                    'fast_startup_enabled': self.use_fast_startup,
                    'predictor_type': type(self.predictor).__name__
                }
            
            @app.route('/predict/<int:venue_id>/<int:race_number>')
            def predict_api(venue_id, race_number):
                result = self.predict_race(venue_id, race_number)
                if result:
                    return result
                else:
                    return {'error': '予想データが取得できませんでした'}, 404
            
            @app.route('/accuracy')
            def accuracy_api():
                return self.accuracy_tracker.calculate_accuracy()
            
            @app.route('/system/status')
            def system_status():
                return {
                    'startup_time': time.time() - self.start_time,
                    'predictor_loaded': self.predictor is not None,
                    'accuracy_tracker_loaded': self.accuracy_tracker is not None,
                    'optimization_status': {
                        'fast_startup': self.use_fast_startup,
                        'optimization_enabled': self.use_optimization
                    }
                }
            
            print(f"\n統合Webサーバー起動完了")
            print(f"アクセス: http://localhost:{port}")
            print(f"起動時間: {time.time() - self.start_time:.2f}秒")
            print(f"最適化機能: {'ON' if self.use_optimization else 'OFF'}")
            
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
            
        except Exception as e:
            logger.error(f"Webサーバー起動エラー: {e}")
            raise
    
    def run_prediction_test(self):
        """統合予想テスト"""
        try:
            logger.info("統合予想テスト開始")
            
            # テスト用レース
            test_races = [(12, 1), (15, 1), (24, 1)]
            results = []
            
            for venue_id, race_number in test_races:
                print(f"\n[TEST] {self.accuracy_tracker.venue_mapping.get(venue_id)}競艇場 第{race_number}レース")
                
                prediction = self.predict_race(venue_id, race_number)
                if prediction:
                    print(f"  推奨単勝: {prediction.get('recommended_win')}号艇")
                    print(f"  推奨複勝: {prediction.get('recommended_place', [])[:3]}")
                    print(f"  信頼度: {prediction.get('confidence', 0):.2f}")
                    results.append(prediction)
                else:
                    print("  [WARNING] 予想データ取得失敗")
            
            print(f"\n[RESULT] テスト完了: {len(results)}/{len(test_races)} 成功")
            return len(results) == len(test_races)
            
        except Exception as e:
            logger.error(f"予想テストエラー: {e}")
            return False
    
    def get_system_info(self):
        """システム情報取得"""
        return {
            'startup_time': time.time() - self.start_time,
            'optimization_enabled': self.use_optimization,
            'fast_startup_enabled': self.use_fast_startup,
            'predictor_type': type(self.predictor).__name__ if self.predictor else 'None',
            'components': {
                'accuracy_tracker': self.accuracy_tracker is not None,
                'predictor': self.predictor is not None
            }
        }


def main():
    """メイン実行"""
    print("=" * 70)
    print("競艇予想システム - 統合版（既存互換・高速起動対応）")
    print("=" * 70)
    
    try:
        system = IntegratedBoatraceSystem()
        
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == 'test':
                # 予想テスト
                success = system.run_prediction_test()
                print(f"\n[INFO] システム情報:")
                info = system.get_system_info()
                for key, value in info.items():
                    print(f"  {key}: {value}")
                sys.exit(0 if success else 1)
                
            elif command == 'accuracy':
                # 的中率分析
                system.run_accuracy_analysis()
                sys.exit(0)
                
            elif command == 'web':
                # Webサーバー起動
                port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
                system.start_web_server(port)
                
            else:
                print(f"未知のコマンド: {command}")
                print("利用可能なコマンド: test, accuracy, web")
                sys.exit(1)
        else:
            # デフォルト: 統合テスト
            print("\n[INFO] 統合システムテスト実行")
            system.run_prediction_test()
            system.run_accuracy_analysis()
            
            print(f"\n[INFO] システム情報:")
            info = system.get_system_info()
            for key, value in info.items():
                print(f"  {key}: {value}")
    
    except KeyboardInterrupt:
        print("\n[STOP] ユーザーによる中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"統合システムエラー: {e}")
        print(f"[ERROR] 統合システムエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()