"""
高度なアンサンブル予想システム v1.0

スタッキング、ブレンディング、動的重み調整による
複数モデルの統合予想システム
"""
import numpy as np
import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score
import warnings
warnings.filterwarnings('ignore')


class AdvancedEnsembleSystem:
    def __init__(self, db_path='cache/accuracy_tracker.db'):
        """高度アンサンブルシステム初期化"""
        self.db_path = db_path
        self.models = {}
        self.model_weights = {}
        self.meta_learner = None
        self.performance_history = {}
        self._init_base_models()
        self._load_model_performance()
    
    def _init_base_models(self):
        """ベースモデルの初期化"""
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100, 
                random_state=42,
                max_depth=10,
                min_samples_split=5
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'logistic': LogisticRegression(
                random_state=42,
                max_iter=1000,
                C=1.0
            ),
            'neural_network': MLPClassifier(
                hidden_layer_sizes=(50, 25),
                random_state=42,
                max_iter=500,
                alpha=0.01
            )
        }
        
        # 初期重み（均等）
        num_models = len(self.models)
        initial_weight = 1.0 / num_models
        self.model_weights = {
            name: initial_weight for name in self.models.keys()
        }
    
    def _load_model_performance(self):
        """過去のモデル性能履歴をロード"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # パフォーマンステーブルが存在しない場合は作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    date_str TEXT NOT NULL,
                    accuracy REAL,
                    precision_score REAL,
                    recall_score REAL,
                    roi REAL,
                    weight REAL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 過去7日間の性能データを取得
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT model_name, AVG(accuracy) as avg_accuracy, 
                       AVG(precision_score) as avg_precision,
                       AVG(roi) as avg_roi, AVG(weight) as avg_weight
                FROM model_performance 
                WHERE date_str >= ?
                GROUP BY model_name
            ''', (seven_days_ago,))
            
            results = cursor.fetchall()
            for row in results:
                model_name, avg_acc, avg_prec, avg_roi, avg_weight = row
                self.performance_history[model_name] = {
                    'accuracy': avg_acc or 0.5,
                    'precision': avg_prec or 0.5,
                    'roi': avg_roi or 0.0,
                    'weight': avg_weight or (1.0 / len(self.models))
                }
            
            conn.close()
            print(f"[INFO] モデル性能履歴ロード完了: {len(self.performance_history)}件")
        
        except Exception as e:
            print(f"[ERROR] 性能履歴ロードエラー: {e}")
            # デフォルト性能値を設定
            for model_name in self.models.keys():
                self.performance_history[model_name] = {
                    'accuracy': 0.5,
                    'precision': 0.5,
                    'roi': 0.0,
                    'weight': 1.0 / len(self.models)
                }
    
    def prepare_features(self, race_data):
        """レースデータから特徴量を準備"""
        try:
            features = []
            
            for racer in race_data.get('racers', []):
                feature_vector = [
                    float(racer.get('nationwide_rate', 0.0)) / 100.0,
                    float(racer.get('local_rate', 0.0)) / 100.0,
                    float(racer.get('motor_rate', 0.0)) / 100.0,
                    float(racer.get('boat_rate', 0.0)) / 100.0,
                    float(racer.get('start_timing', 0.0)),
                    int(racer.get('pit_number', 1)) / 6.0,
                    float(racer.get('weight', 50.0)) / 100.0,
                    int(racer.get('age', 30)) / 60.0,
                    int(racer.get('class', 'B2')[-1]) / 3.0 if racer.get('class', 'B2')[-1].isdigit() else 0.5
                ]
                features.extend(feature_vector)
            
            # 足りない特徴量を0で埋める
            while len(features) < 54:  # 6艇 × 9特徴量
                features.append(0.0)
                
            return np.array(features[:54]).reshape(1, -1)
        
        except Exception as e:
            print(f"[ERROR] 特徴量準備エラー: {e}")
            return np.zeros((1, 54))
    
    def dynamic_weight_adjustment(self):
        """動的重み調整"""
        try:
            total_score = 0.0
            model_scores = {}
            
            for model_name in self.models.keys():
                perf = self.performance_history.get(model_name, {})
                # ROI重視の総合スコア計算
                accuracy_score = perf.get('accuracy', 0.5)
                roi_score = max(0.0, perf.get('roi', 0.0)) / 100.0  # ROI正規化
                precision_score = perf.get('precision', 0.5)
                
                # 重み付き総合スコア
                combined_score = (
                    0.4 * accuracy_score +
                    0.4 * roi_score +
                    0.2 * precision_score
                )
                
                model_scores[model_name] = max(0.01, combined_score)  # 最小値保証
                total_score += model_scores[model_name]
            
            # 正規化
            if total_score > 0:
                for model_name in self.models.keys():
                    self.model_weights[model_name] = model_scores[model_name] / total_score
            
            print(f"[INFO] 動的重み調整完了: {self.model_weights}")
        
        except Exception as e:
            print(f"[ERROR] 動的重み調整エラー: {e}")
    
    def stacking_prediction(self, X, y=None, fit=False):
        """スタッキング予測"""
        try:
            base_predictions = []
            
            if fit and y is not None:
                # ベースモデルの学習
                for name, model in self.models.items():
                    try:
                        model.fit(X, y)
                        pred = model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else model.predict(X)
                        base_predictions.append(pred)
                    except Exception as e:
                        print(f"[WARNING] {name}モデル学習エラー: {e}")
                        base_predictions.append(np.full(len(y), 0.5))
                
                # メタ学習器の学習
                if len(base_predictions) > 0:
                    meta_features = np.column_stack(base_predictions)
                    self.meta_learner = LogisticRegression(random_state=42, max_iter=1000)
                    self.meta_learner.fit(meta_features, y)
                    print("[INFO] スタッキング学習完了")
            
            else:
                # 予測フェーズ
                for name, model in self.models.items():
                    try:
                        if hasattr(model, 'predict_proba'):
                            pred = model.predict_proba(X)[:, 1]
                        else:
                            pred = model.predict(X)
                        base_predictions.append(pred)
                    except:
                        base_predictions.append(np.array([0.5] * len(X)))
                
                if len(base_predictions) > 0 and self.meta_learner is not None:
                    meta_features = np.column_stack(base_predictions)
                    return self.meta_learner.predict_proba(meta_features)[:, 1]
            
            return np.array([0.5] * len(X))
        
        except Exception as e:
            print(f"[ERROR] スタッキング予測エラー: {e}")
            return np.array([0.5] * len(X))
    
    def blending_prediction(self, X):
        """ブレンディング予測"""
        try:
            weighted_predictions = []
            total_weight = sum(self.model_weights.values())
            
            for name, model in self.models.items():
                try:
                    weight = self.model_weights.get(name, 0.25)
                    
                    if hasattr(model, 'predict_proba'):
                        pred = model.predict_proba(X)[:, 1]
                    else:
                        pred = model.predict(X)
                    
                    weighted_pred = pred * (weight / total_weight) if total_weight > 0 else pred * 0.25
                    weighted_predictions.append(weighted_pred)
                
                except Exception as e:
                    print(f"[WARNING] {name}ブレンディングエラー: {e}")
                    weighted_predictions.append(np.array([0.125] * len(X)))
            
            if weighted_predictions:
                return np.sum(weighted_predictions, axis=0)
            else:
                return np.array([0.5] * len(X))
        
        except Exception as e:
            print(f"[ERROR] ブレンディング予測エラー: {e}")
            return np.array([0.5] * len(X))
    
    def train_ensemble(self):
        """アンサンブルモデルの学習"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 学習データの取得（過去30日間）
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT p.predicted_boats, r.actual_results, p.venue_id, p.race_number
                FROM predictions p
                JOIN results r ON p.venue_id = r.venue_id 
                    AND p.race_number = r.race_number 
                    AND p.date_str = r.date_str
                WHERE p.date_str >= ? AND r.actual_results IS NOT NULL
                ORDER BY p.timestamp DESC
                LIMIT 1000
            ''', (thirty_days_ago,))
            
            training_data = cursor.fetchall()
            conn.close()
            
            if len(training_data) < 50:
                print(f"[WARNING] 学習データ不足: {len(training_data)}件")
                return False
            
            # 特徴量とラベルの準備
            X = []
            y = []
            
            for pred_boats, actual_results, venue_id, race_number in training_data:
                try:
                    # 簡易特徴量生成（実際の実装では詳細な特徴量が必要）
                    features = np.random.rand(54)  # プレースホルダー
                    X.append(features)
                    
                    # ラベル生成（1位的中かどうか）
                    pred_first = int(pred_boats.split(',')[0]) if pred_boats else 1
                    actual_first = int(actual_results.split(',')[0]) if actual_results else 0
                    y.append(1 if pred_first == actual_first else 0)
                
                except:
                    continue
            
            if len(X) < 50:
                print("[WARNING] 有効な学習データが不十分")
                return False
            
            X = np.array(X)
            y = np.array(y)
            
            # スタッキング学習
            self.stacking_prediction(X, y, fit=True)
            
            # 動的重み調整
            self.dynamic_weight_adjustment()
            
            print(f"[INFO] アンサンブル学習完了: {len(training_data)}件のデータで学習")
            return True
        
        except Exception as e:
            print(f"[ERROR] アンサンブル学習エラー: {e}")
            return False
    
    def predict(self, race_data):
        """統合予想実行"""
        try:
            # 特徴量準備
            X = self.prepare_features(race_data)
            
            # 複数手法による予想
            stacking_pred = self.stacking_prediction(X)
            blending_pred = self.blending_prediction(X)
            
            # 最終予想（スタッキング70%, ブレンディング30%）
            final_confidence = 0.7 * stacking_pred[0] + 0.3 * blending_pred[0]
            
            # 予想結果生成
            racers = race_data.get('racers', [])
            racer_scores = []
            
            for i, racer in enumerate(racers):
                # 個別スコア計算
                base_score = (
                    float(racer.get('nationwide_rate', 0)) * 0.3 +
                    float(racer.get('local_rate', 0)) * 0.2 +
                    float(racer.get('motor_rate', 0)) * 0.2 +
                    float(racer.get('boat_rate', 0)) * 0.1 +
                    (1.0 - float(racer.get('start_timing', 0.17)) / 0.5) * 0.2
                )
                
                # アンサンブル補正
                ensemble_bonus = final_confidence * 10 * (1.0 - i * 0.1)
                total_score = base_score + ensemble_bonus
                
                racer_scores.append({
                    'pit_number': racer.get('pit_number', i+1),
                    'score': max(0, total_score),
                    'confidence': final_confidence
                })
            
            # スコア順にソート
            racer_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # 予想結果
            predicted_order = [r['pit_number'] for r in racer_scores[:3]]
            avg_confidence = sum(r['confidence'] for r in racer_scores) / len(racer_scores)
            
            result = {
                'win': predicted_order[0],
                'place': predicted_order[:2],
                'trifecta': predicted_order,
                'confidence': min(0.95, avg_confidence * 100),
                'method': 'Advanced Ensemble (Stacking + Blending)',
                'model_weights': self.model_weights.copy(),
                'stacking_confidence': stacking_pred[0],
                'blending_confidence': blending_pred[0]
            }
            
            print(f"[INFO] アンサンブル予想完了: 1位={predicted_order[0]}, 信頼度={avg_confidence:.1%}")
            return result
        
        except Exception as e:
            print(f"[ERROR] アンサンブル予想エラー: {e}")
            # フォールバック予想
            racers = race_data.get('racers', [])
            if racers:
                return {
                    'win': racers[0].get('pit_number', 1),
                    'place': [1, 2],
                    'trifecta': [1, 2, 3],
                    'confidence': 50.0,
                    'method': 'Fallback Prediction',
                    'error': str(e)
                }
    
    def update_model_performance(self, model_results):
        """モデル性能の更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            for model_name, metrics in model_results.items():
                cursor.execute('''
                    INSERT INTO model_performance 
                    (model_name, date_str, accuracy, precision_score, recall_score, roi, weight)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model_name,
                    date_str,
                    metrics.get('accuracy', 0.5),
                    metrics.get('precision', 0.5),
                    metrics.get('recall', 0.5),
                    metrics.get('roi', 0.0),
                    self.model_weights.get(model_name, 0.25)
                ))
            
            conn.commit()
            conn.close()
            print(f"[INFO] モデル性能更新完了: {len(model_results)}件")
        
        except Exception as e:
            print(f"[ERROR] モデル性能更新エラー: {e}")


def test_advanced_ensemble():
    """テスト実行"""
    print("=== 高度アンサンブルシステム テスト開始 ===")
    
    ensemble = AdvancedEnsembleSystem()
    
    # 学習テスト
    print("\n1. アンサンブル学習テスト")
    training_success = ensemble.train_ensemble()
    print(f"学習結果: {'成功' if training_success else '失敗'}")
    
    # 予想テスト
    print("\n2. アンサンブル予想テスト")
    test_race_data = {
        'racers': [
            {'pit_number': 1, 'nationwide_rate': 6.8, 'local_rate': 7.2, 'motor_rate': 8.1, 'boat_rate': 7.5, 'start_timing': 0.15},
            {'pit_number': 2, 'nationwide_rate': 5.9, 'local_rate': 6.1, 'motor_rate': 7.3, 'boat_rate': 6.8, 'start_timing': 0.18},
            {'pit_number': 3, 'nationwide_rate': 5.2, 'local_rate': 5.8, 'motor_rate': 6.9, 'boat_rate': 6.2, 'start_timing': 0.16},
            {'pit_number': 4, 'nationwide_rate': 4.8, 'local_rate': 5.1, 'motor_rate': 6.1, 'boat_rate': 5.9, 'start_timing': 0.19},
            {'pit_number': 5, 'nationwide_rate': 4.3, 'local_rate': 4.7, 'motor_rate': 5.8, 'boat_rate': 5.3, 'start_timing': 0.21},
            {'pit_number': 6, 'nationwide_rate': 3.9, 'local_rate': 4.2, 'motor_rate': 5.2, 'boat_rate': 4.8, 'start_timing': 0.23}
        ]
    }
    
    prediction = ensemble.predict(test_race_data)
    print(f"予想結果: {prediction}")
    
    # 重み表示
    print(f"\n3. モデル重み: {ensemble.model_weights}")
    
    print("\n=== テスト完了 ===")
    return prediction


if __name__ == "__main__":
    test_advanced_ensemble()