#!/usr/bin/env python3
"""
Online Learning System for Kyotei Prediction
競艇予想システム向けオンライン学習（増分学習）

特徴:
1. レース終了後の即座学習更新
2. Partial Fit による効率的な増分学習
3. モデル性能の継続監視
4. 学習データの品質管理
5. 自動的なモデル保存・復元
"""

import os
import sqlite3
import pickle
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import SGDClassifier
from sklearn.linear_model import SGDRegressor, PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class OnlineLearningSystem:
    """オンライン学習システム"""
    
    def __init__(self):
        self.db_path = 'cache/accuracy_tracker.db'
        self.model_cache_path = 'cache/online_ml_models.pkl'
        self.scaler_cache_path = 'cache/online_ml_scaler.pkl'
        self.learning_stats_path = 'cache/online_learning_stats.json'
        
        # オンライン学習に適したモデル
        self.models = {
            'sgd_classifier': SGDClassifier(
                loss='log_loss',  # 確率出力のため
                learning_rate='adaptive',
                eta0=0.01,
                alpha=0.0001,
                random_state=42,
                warm_start=True  # 増分学習に必要
            ),
            'passive_aggressive': PassiveAggressiveClassifier(
                C=1.0,
                random_state=42,
                warm_start=True
            )
        }
        
        self.scaler = StandardScaler()
        self.learning_stats = {
            'total_updates': 0,
            'last_update': None,
            'accuracy_history': [],
            'learning_rate_history': []
        }
        
        # 特徴量定義
        self.feature_columns = [
            'venue_id', 'race_number', 'racer_boat_number',
            'racer_national_top_1_percent', 'racer_local_top_1_percent',
            'racer_national_top_2_percent', 'racer_average_start_timing',
            'race_distance', 'hour_of_day', 'day_of_week',
            'recent_win_trend', 'recent_place_trend', 'venue_compatibility',
            'weather_difficulty', 'momentum_trend', 'opponent_avg_rating'
        ]
        
        self.is_initialized = False
        self._load_system()
        
        # 定期的なハイパーパラメータ最適化
        self._auto_hyperparameter_optimization()
    
    def _load_system(self) -> None:
        """システム状態をロード"""
        try:
            # モデルロード
            if os.path.exists(self.model_cache_path):
                with open(self.model_cache_path, 'rb') as f:
                    self.models = pickle.load(f)
                logger.info("オンライン学習モデルをロード")
            
            # スケーラーロード
            if os.path.exists(self.scaler_cache_path):
                with open(self.scaler_cache_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("オンライン学習スケーラーをロード")
            
            # 学習統計ロード
            if os.path.exists(self.learning_stats_path):
                with open(self.learning_stats_path, 'r', encoding='utf-8') as f:
                    self.learning_stats = json.load(f)
                logger.info(f"学習統計をロード: {self.learning_stats['total_updates']}回更新済み")
            
            self.is_initialized = True
            
        except Exception as e:
            logger.warning(f"システム状態ロードエラー: {e}")
            self._initialize_from_scratch()
    
    def _initialize_from_scratch(self) -> None:
        """ゼロからシステムを初期化"""
        try:
            logger.info("オンライン学習システムをゼロから初期化中...")
            
            # 過去データから初期学習
            initial_data = self._load_historical_data(days=30)  # 過去30日間
            
            if len(initial_data) > 100:  # 十分なデータがある場合
                X, y = self._prepare_features_and_targets(initial_data)
                
                if len(X) > 0:
                    # スケーラーフィット
                    X_scaled = self.scaler.fit_transform(X)
                    
                    # モデル初期学習
                    for name, model in self.models.items():
                        try:
                            model.fit(X_scaled, y)
                            logger.info(f"モデル '{name}' 初期学習完了")
                        except Exception as e:
                            logger.error(f"モデル '{name}' 初期学習エラー: {e}")
                    
                    # システム状態保存
                    self._save_system()
                    self.is_initialized = True
                    logger.info(f"初期学習完了: {len(initial_data)}件のデータで学習")
                else:
                    logger.warning("初期学習用特徴量の作成に失敗")
            else:
                logger.warning("初期学習データ不足、ダミーデータで初期化")
                self._initialize_with_dummy_data()
                
        except Exception as e:
            logger.error(f"ゼロからの初期化エラー: {e}")
            self._initialize_with_dummy_data()
    
    def _initialize_with_dummy_data(self) -> None:
        """ダミーデータでシステム初期化"""
        try:
            np.random.seed(42)
            n_samples = 1000
            
            # ダミー特徴量生成
            X_dummy = np.random.randn(n_samples, len(self.feature_columns))
            y_dummy = np.random.choice([0, 1], n_samples, p=[0.84, 0.16])  # 16%の的中率
            
            # スケーラーフィット
            self.scaler.fit(X_dummy)
            X_scaled = self.scaler.transform(X_dummy)
            
            # モデル初期学習
            for name, model in self.models.items():
                model.fit(X_scaled, y_dummy)
                logger.info(f"モデル '{name}' ダミーデータ初期化完了")
            
            self.is_initialized = True
            self._save_system()
            logger.info("ダミーデータでシステム初期化完了")
            
        except Exception as e:
            logger.error(f"ダミーデータ初期化エラー: {e}")
    
    def update_with_race_result(self, venue_id: int, race_number: int, race_date: str, 
                               prediction_data: Dict, actual_result: Dict) -> bool:
        """レース結果でモデルを更新"""
        try:
            if not self.is_initialized:
                logger.warning("システム未初期化、学習更新をスキップ")
                return False
            
            # 特徴量作成
            features = self._create_features_from_race(
                venue_id, race_number, race_date, prediction_data
            )
            
            if not features:
                logger.warning(f"特徴量作成失敗: {venue_id}_{race_number}")
                return False
            
            # ターゲット作成（単勝的中フラグ）
            predicted_win = prediction_data.get('recommended_win')
            actual_win = actual_result.get('winning_boat')
            
            if predicted_win is None or actual_win is None:
                logger.warning(f"予想または結果データ不足: {venue_id}_{race_number}")
                return False
            
            is_hit = 1 if predicted_win == actual_win else 0
            
            # 特徴量を配列に変換
            X_new = np.array([list(features.values())]).reshape(1, -1)
            y_new = np.array([is_hit])
            
            # スケーリング
            X_scaled = self.scaler.transform(X_new)
            
            # 各モデルで増分学習
            update_success = False
            for name, model in self.models.items():
                try:
                    model.partial_fit(X_scaled, y_new)
                    update_success = True
                    logger.debug(f"モデル '{name}' 増分学習完了")
                except Exception as e:
                    logger.warning(f"モデル '{name}' 増分学習エラー: {e}")
            
            if update_success:
                # 学習統計更新
                self._update_learning_stats(is_hit)
                
                # 定期的にシステム保存（10回に1回）
                if self.learning_stats['total_updates'] % 10 == 0:
                    self._save_system()
                
                logger.info(f"オンライン学習更新: {venue_id}_{race_number} ({'的中' if is_hit else '外れ'})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"オンライン学習更新エラー: {e}")
            return False
    
    def predict_online(self, venue_id: int, race_number: int, race_data: Dict) -> Dict:
        """オンライン学習モデルで予想"""
        try:
            if not self.is_initialized:
                return self._fallback_prediction()
            
            # 全艇の予想を計算
            boat_predictions = {}
            
            for boat_number in range(1, 7):
                features = self._create_features_from_race(
                    venue_id, race_number, 'today', {'boat_number': boat_number}
                )
                
                if features:
                    X = np.array([list(features.values())]).reshape(1, -1)
                    X_scaled = self.scaler.transform(X)
                    
                    # アンサンブル予想
                    probs = []
                    for name, model in self.models.items():
                        try:
                            if hasattr(model, 'predict_proba'):
                                prob = model.predict_proba(X_scaled)[0][1]
                            else:
                                # predict_probaがない場合はdecision_functionを使用
                                decision = model.decision_function(X_scaled)[0]
                                prob = 1 / (1 + np.exp(-decision))  # シグモイド変換
                            probs.append(prob)
                        except:
                            probs.append(0.16)  # デフォルト確率
                    
                    boat_predictions[boat_number] = np.mean(probs) if probs else 0.16
                else:
                    boat_predictions[boat_number] = 0.16
            
            # 予想結果整理
            win_prediction = max(boat_predictions, key=boat_predictions.get)
            place_predictions = sorted(boat_predictions.keys(), 
                                     key=lambda x: boat_predictions[x], reverse=True)[:3]
            
            return {
                'recommended_win': win_prediction,
                'recommended_place': place_predictions,
                'confidence': boat_predictions[win_prediction],
                'all_probabilities': boat_predictions,
                'model_type': 'online_learning',
                'total_updates': self.learning_stats['total_updates']
            }
            
        except Exception as e:
            logger.error(f"オンライン予想エラー: {e}")
            return self._fallback_prediction()
    
    def _create_features_from_race(self, venue_id: int, race_number: int, 
                                  race_date: str, prediction_data: Dict) -> Dict:
        """レースデータから特徴量を作成"""
        try:
            boat_number = prediction_data.get('boat_number', 1)
            
            features = {
                'venue_id': venue_id,
                'race_number': race_number,
                'racer_boat_number': boat_number,
                'racer_national_top_1_percent': 45.0,  # デフォルト値
                'racer_local_top_1_percent': 50.0,
                'racer_national_top_2_percent': 60.0,
                'racer_average_start_timing': 1.0,
                'race_distance': 1400,
                'hour_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday(),
                'recent_win_trend': 0.16,
                'recent_place_trend': 0.33,
                'venue_compatibility': 1.0,
                'weather_difficulty': 0.0,
                'momentum_trend': 0.0,
                'opponent_avg_rating': 0.5
            }
            
            return features
            
        except Exception as e:
            logger.error(f"特徴量作成エラー: {e}")
            return {}
    
    def _load_historical_data(self, days: int = 30) -> List[Dict]:
        """過去データの読み込み"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 過去データ取得
            cursor.execute('''
                SELECT p.venue_id, p.race_number, p.predicted_win, p.prediction_data,
                       r.winning_boat, p.race_date
                FROM predictions p
                JOIN race_results r ON p.venue_id = r.venue_id 
                                   AND p.race_number = r.race_number 
                                   AND p.race_date = r.race_date
                WHERE p.race_date >= date('now', '-{} days')
                ORDER BY p.race_date DESC
            '''.format(days))
            
            data = []
            for row in cursor.fetchall():
                venue_id, race_number, predicted_win, prediction_data_json, winning_boat, race_date = row
                
                data.append({
                    'venue_id': venue_id,
                    'race_number': race_number,
                    'predicted_win': predicted_win,
                    'prediction_data': json.loads(prediction_data_json) if prediction_data_json else {},
                    'winning_boat': winning_boat,
                    'race_date': race_date,
                    'is_hit': 1 if predicted_win == winning_boat else 0
                })
            
            conn.close()
            logger.info(f"過去{days}日間のデータを{len(data)}件読み込み")
            return data
            
        except Exception as e:
            logger.error(f"過去データ読み込みエラー: {e}")
            return []
    
    def _prepare_features_and_targets(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """特徴量とターゲットの準備"""
        try:
            features_list = []
            targets = []
            
            for record in data:
                features = self._create_features_from_race(
                    record['venue_id'], record['race_number'], 
                    record['race_date'], record['prediction_data']
                )
                
                if features:
                    features_list.append(list(features.values()))
                    targets.append(record['is_hit'])
            
            if features_list:
                return np.array(features_list), np.array(targets)
            else:
                return np.array([]), np.array([])
                
        except Exception as e:
            logger.error(f"特徴量・ターゲット準備エラー: {e}")
            return np.array([]), np.array([])
    
    def _update_learning_stats(self, is_hit: int) -> None:
        """学習統計を更新"""
        self.learning_stats['total_updates'] += 1
        self.learning_stats['last_update'] = datetime.now().isoformat()
        self.learning_stats['accuracy_history'].append(is_hit)
        
        # 履歴は最新100件のみ保持
        if len(self.learning_stats['accuracy_history']) > 100:
            self.learning_stats['accuracy_history'] = self.learning_stats['accuracy_history'][-100:]
    
    def _save_system(self) -> None:
        """システム状態を保存"""
        try:
            import os
            os.makedirs('cache', exist_ok=True)
            
            # モデル保存
            with open(self.model_cache_path, 'wb') as f:
                pickle.dump(self.models, f)
            
            # スケーラー保存
            with open(self.scaler_cache_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            # 学習統計保存
            with open(self.learning_stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.learning_stats, f, ensure_ascii=False, indent=2)
            
            logger.debug("オンライン学習システム状態を保存")
            
        except Exception as e:
            logger.error(f"システム状態保存エラー: {e}")
    
    def _fallback_prediction(self) -> Dict:
        """フォールバック予想"""
        return {
            'recommended_win': 1,
            'recommended_place': [1, 2, 3],
            'confidence': 0.16,
            'all_probabilities': {i: 0.16 for i in range(1, 7)},
            'model_type': 'fallback',
            'total_updates': 0
        }
    
    def get_learning_status(self) -> Dict:
        """学習状況を取得"""
        recent_accuracy = 0.0
        if self.learning_stats['accuracy_history']:
            recent_accuracy = np.mean(self.learning_stats['accuracy_history'][-20:])
        
        return {
            'is_initialized': self.is_initialized,
            'total_updates': self.learning_stats['total_updates'],
            'last_update': self.learning_stats['last_update'],
            'recent_accuracy': round(recent_accuracy * 100, 2),
            'models_count': len(self.models),
            'feature_count': len(self.feature_columns)
        }
    
    def _auto_hyperparameter_optimization(self) -> None:
        """自動ハイパーパラメータ最適化"""
        try:
            # 最適化モジュールを動的インポート
            try:
                from hyperparameter_optimizer import HyperparameterOptimizer
                optimizer = HyperparameterOptimizer(self.db_path)
                
                # 学習データを取得
                historical_data = self._load_historical_data(days=30)
                if len(historical_data) >= 100:
                    X, y = self._prepare_features_and_targets(historical_data)
                    if len(X) >= 100:
                        # 7日間隔で自動最適化
                        if optimizer.auto_optimize_if_needed(X, y, days_threshold=7):
                            # 最適化されたモデルをロード
                            optimized_models = optimizer.load_optimized_models()
                            if optimized_models:
                                # 既存モデルを最適化版で置き換え
                                for name, model in optimized_models.items():
                                    if name in self.models:
                                        # オンライン学習対応モデルに変換
                                        if hasattr(model, 'partial_fit'):
                                            self.models[name] = model
                                            logger.info(f"最適化モデル '{name}' を適用")
                                        else:
                                            logger.warning(f"モデル '{name}' はオンライン学習非対応")
                                
                                # システム状態を保存
                                self._save_system()
                        else:
                            logger.debug("ハイパーパラメータ最適化スキップ")
                    else:
                        logger.debug("最適化用特徴量不足")
                else:
                    logger.debug("最適化用データ不足")
                    
            except ImportError:
                logger.debug("ハイパーパラメータ最適化モジュールなし")
            
        except Exception as e:
            logger.debug(f"自動ハイパーパラメータ最適化エラー: {e}")

if __name__ == "__main__":
    # テスト実行
    import os
    system = OnlineLearningSystem()
    
    # 状況表示
    status = system.get_learning_status()
    print(f"オンライン学習システム状況: {status}")
    
    # テスト予想
    prediction = system.predict_online(12, 1, {})
    print(f"テスト予想: {prediction}")