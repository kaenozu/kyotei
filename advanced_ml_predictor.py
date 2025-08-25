#!/usr/bin/env python3
"""
Advanced ML Predictor for Kyotei (Boatrace)
機械学習による高度な競艇予想システム
"""

import os
import json
import logging
import sqlite3
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

# ログ設定
logger = logging.getLogger(__name__)

class AdvancedMLPredictor:
    """機械学習による高度な競艇予想クラス"""
    
    def __init__(self):
        self.db_path = 'cache/accuracy_tracker.db'
        self.model_cache_path = 'cache/ml_models.pkl'
        self.scaler_cache_path = 'cache/ml_scaler.pkl'
        
        # アンサンブルモデル
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000
            )
        }
        
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = [
            'venue_id', 'race_number', 'racer_boat_number',
            'racer_national_top_1_percent', 'racer_local_top_1_percent',
            'racer_national_top_2_percent', 'racer_average_start_timing',
            'race_distance', 'hour_of_day', 'day_of_week'
        ]
        
        # モデルロード試行
        self._load_models()
        
        # データが不足している場合は学習実行
        if not self.is_trained:
            self._train_models()
    
    def _load_models(self) -> bool:
        """キャッシュされたモデルをロード"""
        try:
            if (os.path.exists(self.model_cache_path) and 
                os.path.exists(self.scaler_cache_path)):
                
                with open(self.model_cache_path, 'rb') as f:
                    self.models = pickle.load(f)
                
                with open(self.scaler_cache_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                self.is_trained = True
                logger.info("キャッシュされたMLモデルをロードしました")
                return True
        except Exception as e:
            logger.warning(f"MLモデルキャッシュロードエラー: {e}")
        
        return False
    
    def _save_models(self) -> None:
        """モデルをキャッシュに保存"""
        try:
            os.makedirs('cache', exist_ok=True)
            
            with open(self.model_cache_path, 'wb') as f:
                pickle.dump(self.models, f)
            
            with open(self.scaler_cache_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            logger.info("MLモデルをキャッシュに保存しました")
        except Exception as e:
            logger.error(f"MLモデル保存エラー: {e}")
    
    def _extract_training_data(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """データベースから学習データを抽出"""
        try:
            if not os.path.exists(self.db_path):
                logger.warning("データベースファイルが存在しません")
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                # 予想データと結果データを結合して取得
                query = """
                SELECT 
                    rd.venue_id,
                    rd.race_number, 
                    JSON_EXTRACT(rd.prediction_data, '$.recommended_win') as predicted_win,
                    rd.race_data,
                    rr.winning_boat,
                    rd.race_date
                FROM race_details rd
                LEFT JOIN race_results rr 
                    ON rd.venue_id = rr.venue_id 
                    AND rd.race_number = rr.race_number 
                    AND rd.race_date = rr.race_date
                WHERE rr.winning_boat IS NOT NULL
                    AND rd.race_data IS NOT NULL
                ORDER BY rd.race_date DESC
                LIMIT 1000
                """
                
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                if not rows:
                    logger.warning("学習データが不足しています")
                    return None
                
                features_list = []
                targets_list = []
                
                for row in rows:
                    venue_id, race_number, predicted_win, race_data_json, winning_boat, race_date = row
                    
                    if not race_data_json:
                        continue
                    
                    try:
                        race_data = json.loads(race_data_json)
                        boats = race_data.get('boats', [])
                        
                        # 各艇についてデータ生成
                        for boat in boats:
                            features = self._extract_boat_features(boat, race_data, venue_id, race_number, race_date)
                            if features is not None:
                                features_list.append(features)
                                # 1着なら1、そうでなければ0
                                is_winner = 1 if boat.get('racer_boat_number') == winning_boat else 0
                                targets_list.append(is_winner)
                    
                    except (json.JSONDecodeError, KeyError) as e:
                        continue
                
                if len(features_list) < 50:  # 最低限のデータ数チェック
                    logger.warning("学習に必要な最低限のデータが不足しています")
                    return None
                
                X = np.array(features_list)
                y = np.array(targets_list)
                
                logger.info(f"学習データ抽出完了: {len(X)}件の特徴量、{np.sum(y)}件の的中")
                return X, y
                
        except Exception as e:
            logger.error(f"学習データ抽出エラー: {e}")
            return None
    
    def _extract_boat_features(self, boat: Dict, race_data: Dict, venue_id: int, race_number: int, race_date: str) -> Optional[List[float]]:
        """艇の特徴量を抽出"""
        try:
            # 基本特徴量
            features = [
                float(venue_id),
                float(race_number),
                float(boat.get('racer_boat_number', 0)),
                float(boat.get('racer_national_top_1_percent', 0)),
                float(boat.get('racer_local_top_1_percent', 0) or boat.get('racer_national_top_1_percent', 0)),
                float(boat.get('racer_national_top_2_percent', 0)),
                float(boat.get('racer_average_start_timing', 0.17)),
                float(race_data.get('race_distance', 1800)),
            ]
            
            # 時間特徴量
            try:
                dt = datetime.strptime(race_date, '%Y-%m-%d')
                features.extend([
                    float(dt.hour if hasattr(dt, 'hour') else 15),  # デフォルト15時
                    float(dt.weekday())
                ])
            except:
                features.extend([15.0, 0.0])  # デフォルト値
            
            return features
            
        except Exception as e:
            return None
    
    def _train_models(self) -> None:
        """モデルの学習を実行"""
        try:
            logger.info("機械学習モデルの学習を開始...")
            
            data = self._extract_training_data()
            if data is None:
                logger.warning("学習データが不足しているため、ダミーモデルを使用します")
                self.is_trained = False
                return
            
            X, y = data
            
            # データの前処理
            X_scaled = self.scaler.fit_transform(X)
            
            # 学習・テストデータ分割
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # 各モデルを学習
            model_scores = {}
            for name, model in self.models.items():
                logger.info(f"モデル学習中: {name}")
                
                # 学習
                model.fit(X_train, y_train)
                
                # テストデータで評価
                y_pred = model.predict(X_test)
                score = accuracy_score(y_test, y_pred)
                model_scores[name] = score
                
                logger.info(f"{name} テスト精度: {score:.4f}")
            
            # クロスバリデーション
            best_model_name = max(model_scores.items(), key=lambda x: x[1])[0]
            best_model = self.models[best_model_name]
            
            cv_scores = cross_val_score(best_model, X_scaled, y, cv=5)
            logger.info(f"最良モデル {best_model_name} CV精度: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
            
            self.is_trained = True
            self._save_models()
            
            logger.info("機械学習モデルの学習が完了しました")
            
        except Exception as e:
            logger.error(f"モデル学習エラー: {e}")
            self.is_trained = False
    
    def predict_for_boat(self, features: Dict) -> float:
        """指定された艇の勝利確率を予測"""
        try:
            if not self.is_trained:
                # 未学習の場合はフォールバック
                national = features.get('racer_national_top_1_percent', 0) / 100
                local = features.get('racer_local_top_1_percent', national * 100) / 100
                return max(0.1, min(0.9, (national + local) / 2))
            
            # 特徴量ベクトル構築
            feature_vector = [
                float(features.get('venue_id', 0)),
                float(features.get('race_number', 0)),
                float(features.get('racer_boat_number', 0)),
                float(features.get('racer_national_top_1_percent', 0)),
                float(features.get('racer_local_top_1_percent', features.get('racer_national_top_1_percent', 0))),
                float(features.get('racer_national_top_2_percent', 0)),
                float(features.get('racer_average_start_timing', 0.17)),
                float(features.get('race_distance', 1800)),
                float(datetime.now().hour),
                float(datetime.now().weekday())
            ]
            
            # 正規化
            X = self.scaler.transform([feature_vector])
            
            # アンサンブル予測（確率平均）
            predictions = []
            for model in self.models.values():
                if hasattr(model, 'predict_proba'):
                    prob = model.predict_proba(X)[0][1]  # 勝利確率
                else:
                    prob = model.predict(X)[0]
                predictions.append(prob)
            
            # 平均を取って返す
            ensemble_score = np.mean(predictions)
            
            # 0.05 - 0.95の範囲にクリップ
            return max(0.05, min(0.95, ensemble_score))
            
        except Exception as e:
            logger.error(f"ML予測エラー: {e}")
            # エラー時はフォールバック
            national = features.get('racer_national_top_1_percent', 0) / 100
            local = features.get('racer_local_top_1_percent', national * 100) / 100
            return max(0.1, min(0.9, (national + local) / 2))
    
    def retrain_if_needed(self) -> None:
        """必要に応じてモデルを再学習"""
        try:
            # モデルファイルが1週間以上古い場合は再学習
            if os.path.exists(self.model_cache_path):
                file_age = datetime.now().timestamp() - os.path.getmtime(self.model_cache_path)
                if file_age > 7 * 24 * 3600:  # 7日間
                    logger.info("モデルが古いため再学習を実行します")
                    self._train_models()
        except Exception as e:
            logger.error(f"再学習チェックエラー: {e}")
    
    def get_model_info(self) -> Dict:
        """モデル情報を取得"""
        return {
            'is_trained': self.is_trained,
            'models': list(self.models.keys()),
            'feature_columns': self.feature_columns,
            'cache_exists': os.path.exists(self.model_cache_path)
        }

if __name__ == '__main__':
    # テスト実行
    predictor = AdvancedMLPredictor()
    
    # サンプル予測
    sample_features = {
        'venue_id': 1,
        'race_number': 5,
        'racer_boat_number': 1,
        'racer_national_top_1_percent': 25.0,
        'racer_local_top_1_percent': 30.0,
        'racer_national_top_2_percent': 45.0,
        'racer_average_start_timing': 0.15,
        'race_distance': 1800
    }
    
    prediction = predictor.predict_for_boat(sample_features)
    print(f"サンプル予測: {prediction:.4f}")
    
    info = predictor.get_model_info()
    print(f"モデル情報: {info}")