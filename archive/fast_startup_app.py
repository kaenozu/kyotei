#!/usr/bin/env python3
"""
競艇予想システム - 高速起動版メインアプリケーション
起動時間を大幅に短縮した最適化バージョン
"""

import sys
import time
import logging
from pathlib import Path

# プロジェクトパスをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 基本設定（軽量）
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FastStartupApp:
    """高速起動アプリケーション"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("高速起動アプリケーション初期化開始")
        
        # 軽量な初期化のみ実行
        self.predictor = None
        self.web_app = None
        self._components_loaded = False
    
    def _load_core_components(self):
        """コアコンポーネントの遅延ロード"""
        if self._components_loaded:
            return
        
        logger.info("コアコンポーネント遅延ロード開始")
        
        try:
            # 遅延ローダーの初期化
            from src.utils.lazy_loader import lazy_loader
            logger.info("遅延ローダー初期化完了")
            
            # 最適化プレディクターの初期化
            from src.core.optimized_predictor import OptimizedBoatracePredictor
            self.predictor = OptimizedBoatracePredictor()
            logger.info("最適化プレディクター初期化完了")
            
            self._components_loaded = True
            
        except Exception as e:
            logger.error(f"コアコンポーネント読み込みエラー: {e}")
            raise
    
    def run_prediction_test(self):
        """予想テスト実行"""
        try:
            self._load_core_components()
            
            logger.info("予想テスト開始")
            
            # テスト予想実行（軽量）
            prediction = self.predictor.predict_race(12, 1)  # 住之江1R
            
            if prediction:
                print(f"[SUCCESS] 予想テスト成功")
                print(f"  会場: {prediction.get('venue_name')}")
                print(f"  推奨艇: {prediction.get('recommended_win')}号艇")
                print(f"  信頼度: {prediction.get('confidence', 0):.2f}")
            else:
                print("[WARNING] 予想データが取得できませんでした")
            
            return prediction is not None
            
        except Exception as e:
            logger.error(f"予想テストエラー: {e}")
            return False
    
    def start_web_server(self, port: int = 5000):
        """Webサーバー起動"""
        try:
            self._load_core_components()
            
            logger.info("Webサーバー起動準備")
            
            # Flaskの遅延ロード
            from src.utils.lazy_loader import lazy_loader
            flask_module = lazy_loader.get('flask')
            Flask = flask_module.Flask
            
            # 軽量なWebアプリ作成
            app = Flask(__name__)
            
            @app.route('/')
            def index():
                startup_time = time.time() - self.start_time
                return {
                    'status': 'running',
                    'startup_time': f"{startup_time:.2f}秒",
                    'components_loaded': self._components_loaded,
                    'version': '2.0-FastStartup'
                }
            
            @app.route('/predict/<int:venue_id>/<int:race_number>')
            def predict(venue_id, race_number):
                prediction = self.predictor.predict_race(venue_id, race_number)
                if prediction:
                    return prediction
                else:
                    return {'error': '予想データが取得できませんでした'}, 404
            
            @app.route('/status')
            def status():
                return {
                    'predictor_status': self.predictor.get_optimization_status() if self.predictor else None,
                    'startup_time': time.time() - self.start_time,
                    'components_loaded': self._components_loaded
                }
            
            print(f"[START] 高速Webサーバー起動 (ポート: {port})")
            print(f"[INFO] 起動時間: {time.time() - self.start_time:.2f}秒")
            print(f"[URL] http://localhost:{port}")
            
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
            
        except Exception as e:
            logger.error(f"Webサーバー起動エラー: {e}")
            raise
    
    def run_performance_benchmark(self):
        """パフォーマンスベンチマーク"""
        print("\n[BENCHMARK] 高速起動パフォーマンステスト")
        
        # 基本起動時間
        basic_startup_time = time.time() - self.start_time
        print(f"  基本起動時間: {basic_startup_time:.3f}秒")
        
        # コンポーネントロード時間
        component_start = time.time()
        self._load_core_components()
        component_time = time.time() - component_start
        print(f"  コンポーネントロード時間: {component_time:.3f}秒")
        
        # 予想実行時間
        if self.predictor:
            prediction_start = time.time()
            success = self.run_prediction_test()
            prediction_time = time.time() - prediction_start
            print(f"  予想実行時間: {prediction_time:.3f}秒")
            print(f"  予想成功: {'OK' if success else 'ERROR'}")
        
        total_time = time.time() - self.start_time
        print(f"  総実行時間: {total_time:.3f}秒")
        
        # 最適化効果の評価
        if total_time < 5:
            print("[EXCELLENT] 起動時間が5秒未満：優秀")
        elif total_time < 10:
            print("[GOOD] 起動時間が10秒未満：良好")
        else:
            print("[WARNING] 起動時間が10秒以上：改善が必要")
        
        return total_time


def main():
    """メイン実行"""
    print("=" * 60)
    print("競艇予想システム - 高速起動版")
    print("=" * 60)
    
    app = FastStartupApp()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'test':
            # 予想テスト
            success = app.run_prediction_test()
            sys.exit(0 if success else 1)
            
        elif command == 'benchmark':
            # パフォーマンステスト
            total_time = app.run_performance_benchmark()
            sys.exit(0 if total_time < 10 else 1)
            
        elif command == 'web':
            # Webサーバー起動
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
            app.start_web_server(port)
            
        else:
            print(f"未知のコマンド: {command}")
            sys.exit(1)
    else:
        # デフォルト：パフォーマンステスト
        app.run_performance_benchmark()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] ユーザーによる中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        print(f"[ERROR] 実行エラー: {e}")
        sys.exit(1)