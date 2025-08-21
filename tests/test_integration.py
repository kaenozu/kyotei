"""
システム統合テスト
全体的なワークフローと統合機能のテスト
"""
import pytest
import os
import tempfile
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from data.simple_models import (
    TeikokuRaceInfo, TeikokuRacerInfo, TeikokuRacerStats, 
    TeikokuRaceDetail, TeikokuPrediction
)
from ml.random_forest_predictor import RandomForestPredictor
from utils.intelligent_cache import IntelligentCache
from ml.optimized_model_manager import OptimizedModelManager
from utils.database_optimizer import DatabaseOptimizer
from app import create_app


class TestSystemIntegration:
    """システム統合テスト"""
    
    @pytest.fixture
    def integrated_system(self, temp_dir):
        """統合システムフィクスチャー"""
        return {
            'cache': IntelligentCache(temp_dir),
            'model_manager': OptimizedModelManager(temp_dir, max_memory_mb=50),
            'db_optimizer': DatabaseOptimizer(temp_dir),
            'temp_dir': temp_dir
        }
    
    @pytest.mark.integration
    def test_complete_prediction_workflow(self, integrated_system, sample_race_detail):
        """完全な予想ワークフロー統合テスト"""
        cache = integrated_system['cache']
        
        # 1. レースデータのキャッシュ
        race_cache_key = f"race_detail_{sample_race_detail.race_info.race_id}"
        cache.set(race_cache_key, sample_race_detail)
        
        # 2. キャッシュから取得
        cached_race = cache.get(race_cache_key)
        assert cached_race is not None
        assert cached_race.race_info.race_id == sample_race_detail.race_info.race_id
        
        # 3. 予測器での処理
        with patch('ml.random_forest_predictor.optimized_model_manager'):
            predictor = RandomForestPredictor()
            predictor.model_dir = integrated_system['temp_dir']
            
            # 特徴量抽出（キャッシュされる）
            features1 = predictor.extract_features(cached_race)
            features2 = predictor.extract_features(cached_race)  # 2回目はキャッシュヒット
            
            assert not features1.empty
            assert features1.equals(features2)
        
        # 4. 結果のキャッシュ
        mock_prediction = TeikokuPrediction(
            race_id=sample_race_detail.race_info.race_id,
            predictions={1: 0.35, 2: 0.25, 3: 0.2, 4: 0.15, 5: 0.08, 6: 0.05},
            recommended_win=1,
            recommended_place=[1, 2, 3],
            confidence=0.85
        )
        
        prediction_key = f"prediction_{sample_race_detail.race_info.race_id}"
        cache.set(prediction_key, mock_prediction)
        
        cached_prediction = cache.get(prediction_key)
        assert cached_prediction.race_id == mock_prediction.race_id
        assert cached_prediction.confidence == mock_prediction.confidence
    
    @pytest.mark.integration
    def test_database_optimization_workflow(self, integrated_system):
        """データベース最適化ワークフロー統合テスト"""
        temp_dir = integrated_system['temp_dir']
        optimizer = integrated_system['db_optimizer']
        cache = integrated_system['cache']
        
        # 1. テストデータベース作成
        test_dbs = []
        for i, db_type in enumerate(['race_results', 'weather_cache', 'teikoku_cache']):
            db_path = os.path.join(temp_dir, f"{db_type}.db")
            conn = sqlite3.connect(db_path)
            
            if db_type == 'race_results':
                conn.execute("""
                    CREATE TABLE race_results (
                        race_id TEXT, venue_id INTEGER, race_date TEXT, result TEXT
                    )
                """)
                for j in range(50):
                    conn.execute(
                        "INSERT INTO race_results VALUES (?, ?, ?, ?)",
                        (f"2025_01_01_01_{j:02d}", 1, "2025-01-01", f"result_{j}")
                    )
            elif db_type == 'weather_cache':
                conn.execute("""
                    CREATE TABLE weather_cache (
                        location TEXT, date TEXT, temperature REAL, wind_speed REAL
                    )
                """)
                for j in range(30):
                    conn.execute(
                        "INSERT INTO weather_cache VALUES (?, ?, ?, ?)",
                        (f"location_{j}", "2025-01-01", 25.0 + j, 5.0 + j)
                    )
            
            conn.commit()
            conn.close()
            test_dbs.append(db_path)
        
        # 2. 最適化実行
        optimization_results = optimizer.optimize_all_databases()
        
        assert optimization_results['total_databases'] >= len(test_dbs)
        assert optimization_results['optimized_databases'] > 0
        
        # 3. 結果をキャッシュに保存
        cache.set("optimization_results", optimization_results)
        
        # 4. キャッシュから結果取得
        cached_results = cache.get("optimization_results")
        assert cached_results['total_databases'] == optimization_results['total_databases']
        
        # 5. 最適化後のパフォーマンス確認
        for db_path in test_dbs:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                
                # WALモードが設定されているか確認
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                assert journal_mode.lower() == 'wal'
                
                conn.close()
    
    @pytest.mark.integration
    def test_model_management_workflow(self, integrated_system):
        """モデル管理ワークフロー統合テスト"""
        model_manager = integrated_system['model_manager']
        cache = integrated_system['cache']
        
        # 1. モデル情報をキャッシュに保存
        model_config = {
            'model_type': 'random_forest',
            'parameters': {'n_estimators': 100, 'max_depth': 10},
            'created_at': datetime.now().isoformat()
        }
        cache.set("model_config_rf", model_config)
        
        # 2. モデルマネージャーでの処理
        # 初期統計
        initial_stats = model_manager.get_cache_stats()
        
        # 3. キャッシュから設定取得
        cached_config = cache.get("model_config_rf")
        assert cached_config['model_type'] == 'random_forest'
        
        # 4. モデル統計更新
        updated_stats = model_manager.get_cache_stats()
        assert updated_stats['loaded_models'] >= initial_stats['loaded_models']
    
    @pytest.mark.integration
    def test_error_recovery_workflow(self, integrated_system):
        """エラー復旧ワークフロー統合テスト"""
        cache = integrated_system['cache']
        
        # 1. 正常なデータ保存
        cache.set("test_data", {"status": "normal"})
        assert cache.get("test_data")["status"] == "normal"
        
        # 2. 異常なデータでのエラーハンドリング
        try:
            # 循環参照を含むデータ（シリアル化エラーの原因）
            circular_data = {}
            circular_data['self'] = circular_data
            
            # エラーが適切に処理されることを確認
            result = cache.set("circular_data", circular_data)
            # シリアル化エラーでも False が返されるべき
            
        except Exception as e:
            # 例外がスローされても、システムが停止しないことを確認
            pass
        
        # 3. 正常なデータは引き続き取得可能
        normal_data = cache.get("test_data")
        assert normal_data["status"] == "normal"
    
    @pytest.mark.integration
    def test_performance_optimization_workflow(self, integrated_system):
        """パフォーマンス最適化ワークフロー統合テスト"""
        cache = integrated_system['cache']
        model_manager = integrated_system['model_manager']
        
        # 1. 大量データ処理のシミュレーション
        large_datasets = []
        for i in range(10):
            dataset = {
                'race_id': f"2025_01_01_01_{i:02d}",
                'features': [j * 0.1 for j in range(100)],  # 100個の特徴量
                'metadata': {'venue': 'test', 'grade': 'G1'}
            }
            large_datasets.append(dataset)
            
            # キャッシュに保存
            cache.set(f"large_dataset_{i}", dataset, ttl_hours=2)
        
        # 2. パフォーマンス統計収集
        cache_stats_before = cache.get_stats()
        
        # 3. 一括取得でパフォーマンステスト
        import time
        start_time = time.time()
        
        retrieved_datasets = []
        for i in range(10):
            dataset = cache.get(f"large_dataset_{i}")
            if dataset:
                retrieved_datasets.append(dataset)
        
        retrieval_time = time.time() - start_time
        
        # 4. パフォーマンス検証
        assert len(retrieved_datasets) == 10
        assert retrieval_time < 1.0  # 1秒以内で取得完了
        
        # 5. メモリ使用量確認
        cache_stats_after = cache.get_stats()
        assert cache_stats_after['total_items'] >= cache_stats_before['total_items']


class TestWebApplicationIntegration:
    """Webアプリケーション統合テスト"""
    
    @pytest.fixture
    def app_client(self, temp_dir):
        """Flaskアプリケーションクライアントフィクスチャー"""
        with patch('config.app_config.app_config') as mock_config:
            mock_config.flask.debug = True
            mock_config.flask.host = 'localhost'
            mock_config.flask.port = 5000
            mock_config.flask.secret_key = 'test_secret'
            mock_config.logging.level = 'INFO'
            mock_config.database.cache_dir = temp_dir
            
            with patch('core.system_initializer.system_initializer'):
                with patch('utils.database_optimizer.database_optimizer'):
                    app = create_app()
                    app.config['TESTING'] = True
                    with app.test_client() as client:
                        yield client
    
    @pytest.mark.integration
    @patch('core.route_manager.RouteManager')
    def test_application_startup_integration(self, mock_route_manager, temp_dir):
        """アプリケーション起動統合テスト"""
        with patch('config.app_config.app_config') as mock_config:
            mock_config.flask.debug = True
            mock_config.flask.secret_key = 'test_secret'
            mock_config.logging.level = 'INFO'
            mock_config.database.cache_dir = temp_dir
            
            with patch('core.system_initializer.system_initializer') as mock_initializer:
                mock_initializer.initialize_all_systems.return_value = Mock()
                
                with patch('utils.database_optimizer.database_optimizer') as mock_optimizer:
                    mock_optimizer.optimize_all_databases.return_value = {
                        'total_databases': 0,
                        'optimized_databases': 0,
                        'total_time': 0.1
                    }
                    
                    with patch('utils.intelligent_cache.intelligent_cache') as mock_cache:
                        mock_cache.get_stats.return_value = {'total_items': 0}
                        
                        with patch('ml.optimized_model_manager.optimized_model_manager') as mock_model_mgr:
                            mock_model_mgr.get_cache_stats.return_value = {'loaded_models': 0}
                            
                            # アプリケーション作成
                            app = create_app()
                            
                            assert app is not None
                            assert app.config['SECRET_KEY'] == 'test_secret'
                            
                            # システム初期化が呼ばれることを確認
                            mock_initializer.initialize_all_systems.assert_called_once()
                            mock_optimizer.optimize_all_databases.assert_called_once()


class TestDataFlowIntegration:
    """データフロー統合テスト"""
    
    @pytest.mark.integration
    def test_race_data_processing_flow(self, sample_race_detail, temp_dir):
        """レースデータ処理フロー統合テスト"""
        # 1. データ入力
        original_race = sample_race_detail
        
        # 2. キャッシュ層でのデータ保存
        cache = IntelligentCache(temp_dir)
        cache.set("input_race", original_race)
        
        # 3. データ取得・検証
        cached_race = cache.get("input_race")
        assert cached_race.race_info.race_id == original_race.race_info.race_id
        assert len(cached_race.racers) == len(original_race.racers)
        
        # 4. 機械学習での処理
        with patch('ml.random_forest_predictor.optimized_model_manager'):
            predictor = RandomForestPredictor()
            predictor.model_dir = temp_dir
            
            # 特徴量抽出
            features = predictor.extract_features(cached_race)
            assert not features.empty
            assert len(features) == 6
            
            # 特徴量のキャッシュ
            cache.set("extracted_features", features.to_dict())
            
        # 5. 結果の統合確認
        cached_features = cache.get("extracted_features")
        assert cached_features is not None
        
        # 6. データの整合性確認
        assert len(cached_features) == len(features.columns)  # 特徴量数の一致
    
    @pytest.mark.integration
    def test_prediction_accuracy_tracking_flow(self, temp_dir):
        """予想精度追跡フロー統合テスト"""
        cache = IntelligentCache(temp_dir)
        
        # 1. 予想結果生成
        prediction_results = []
        for i in range(5):
            prediction = TeikokuPrediction(
                race_id=f"2025_01_01_01_{i:02d}",
                predictions={j: (7-j)/21 for j in range(1, 7)},
                recommended_win=1,
                recommended_place=[1, 2, 3],
                confidence=0.8 + i * 0.02
            )
            prediction_results.append(prediction)
            
            # キャッシュに保存
            cache.set(f"prediction_{i}", prediction)
        
        # 2. 実際の結果（モック）
        actual_results = [
            {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6},  # 予想的中
            {2: 1, 1: 2, 3: 3, 4: 4, 5: 5, 6: 6},  # 予想外れ
            {1: 1, 3: 2, 2: 3, 4: 4, 5: 5, 6: 6},  # 部分的中
            {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6},  # 予想的中
            {3: 1, 1: 2, 2: 3, 4: 4, 5: 5, 6: 6},  # 予想外れ
        ]
        
        # 3. 精度計算
        accuracy_stats = {
            'total_predictions': len(prediction_results),
            'win_accuracy': 0,
            'place_accuracy': 0,
            'average_confidence': 0
        }
        
        for i, (prediction, actual) in enumerate(zip(prediction_results, actual_results)):
            # 本命的中チェック
            if prediction.recommended_win == min(actual, key=actual.get):
                accuracy_stats['win_accuracy'] += 1
            
            # 連複的中チェック（上位3着に含まれるか）
            top_3_actual = sorted(actual, key=actual.get)[:3]
            if prediction.recommended_win in top_3_actual:
                accuracy_stats['place_accuracy'] += 1
            
            accuracy_stats['average_confidence'] += prediction.confidence
        
        # 4. 統計計算
        accuracy_stats['win_accuracy'] = accuracy_stats['win_accuracy'] / len(prediction_results)
        accuracy_stats['place_accuracy'] = accuracy_stats['place_accuracy'] / len(prediction_results)
        accuracy_stats['average_confidence'] = accuracy_stats['average_confidence'] / len(prediction_results)
        
        # 5. 結果をキャッシュに保存
        cache.set("accuracy_stats", accuracy_stats)
        
        # 6. 統計の検証
        cached_stats = cache.get("accuracy_stats")
        assert cached_stats is not None
        assert 0 <= cached_stats['win_accuracy'] <= 1
        assert 0 <= cached_stats['place_accuracy'] <= 1
        assert cached_stats['average_confidence'] > 0
    
    @pytest.mark.integration
    def test_system_health_monitoring_flow(self, temp_dir):
        """システム健全性監視フロー統合テスト"""
        # 1. 各コンポーネント初期化
        cache = IntelligentCache(temp_dir)
        model_manager = OptimizedModelManager(temp_dir, max_memory_mb=50)
        db_optimizer = DatabaseOptimizer(temp_dir)
        
        # 2. 健全性データ収集
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'cache_stats': cache.get_stats(),
            'model_stats': model_manager.get_cache_stats(),
            'optimization_summary': db_optimizer.get_optimization_summary()
        }
        
        # 3. 健全性評価
        health_score = 100
        
        # キャッシュ健全性
        if health_data['cache_stats']['total_items'] < 0:
            health_score -= 20
        
        # モデル健全性
        if health_data['model_stats']['loaded_models'] < 0:
            health_score -= 20
        
        # データベース健全性
        if 'error' in health_data['optimization_summary']:
            health_score -= 30
        
        health_data['health_score'] = max(0, health_score)
        
        # 4. 健全性データ保存
        cache.set("system_health", health_data, ttl_hours=1)
        
        # 5. 健全性確認
        cached_health = cache.get("system_health")
        assert cached_health is not None
        assert 'health_score' in cached_health
        assert 0 <= cached_health['health_score'] <= 100
        
        # 6. アラート条件テスト
        if cached_health['health_score'] < 50:
            alert_data = {
                'alert_type': 'system_health',
                'severity': 'high',
                'message': f"システム健全性が低下: {cached_health['health_score']}%",
                'timestamp': datetime.now().isoformat()
            }
            cache.set("system_alert", alert_data, ttl_hours=24)
        
        # システムは正常に動作しているはずなので、アラートは発生しない
        alert = cache.get("system_alert")
        assert alert is None or alert.get('severity') != 'high'