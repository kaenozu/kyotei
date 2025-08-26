#!/usr/bin/env python3
"""
🔮 メタ予測システム
予測の予測を行う究極の精度向上エンジン

特徴：
- 自己予測精度の予測
- 不確実性定量化
- 信頼区間の動的調整
- 予測失敗パターンの事前検出
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sqlite3
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MetaPrediction:
    predicted_accuracy: float      # 予測精度の予測
    uncertainty_score: float       # 不確実性スコア
    confidence_interval: Tuple[float, float]  # 信頼区間
    failure_risk: float            # 失敗リスク
    meta_confidence: float         # メタ信頼度

@dataclass
class UncertaintyAnalysis:
    epistemic_uncertainty: float   # 認識的不確実性
    aleatoric_uncertainty: float   # 偶然的不確実性
    total_uncertainty: float       # 総合不確実性
    uncertainty_sources: Dict[str, float]

class MetaPredictionSystem:
    """メタ予測システム"""
    
    def __init__(self):
        self.meta_database = 'cache/meta_predictions.db'
        self.uncertainty_threshold = 0.15  # 15%以上の不確実性で警告
        self.confidence_target = 0.997     # 99.7%メタ信頼度目標
        self._initialize_meta_system()
    
    def _initialize_meta_system(self):
        """メタシステム初期化"""
        logger.info("🔮 メタ予測システム初期化中...")
        
        with sqlite3.connect(self.meta_database) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS meta_predictions (
                    id INTEGER PRIMARY KEY,
                    race_id TEXT,
                    timestamp TEXT,
                    predicted_accuracy REAL,
                    actual_accuracy REAL,
                    uncertainty_score REAL,
                    confidence_interval_lower REAL,
                    confidence_interval_upper REAL,
                    failure_risk REAL,
                    meta_confidence REAL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS uncertainty_analysis (
                    id INTEGER PRIMARY KEY,
                    race_id TEXT,
                    timestamp TEXT,
                    epistemic_uncertainty REAL,
                    aleatoric_uncertainty REAL,
                    total_uncertainty REAL,
                    uncertainty_sources TEXT,
                    risk_factors TEXT
                )
            ''')
        
        logger.info("🎯 メタ予測システム準備完了")
    
    def predict_prediction_accuracy(self, prediction_data: Dict, race_data: Dict) -> MetaPrediction:
        """予測精度を予測"""
        logger.info("🔮 メタ予測開始 - 予測精度の予測...")
        
        # 1. 不確実性分析
        uncertainty_analysis = self._analyze_uncertainty(prediction_data, race_data)
        
        # 2. 予測精度推定
        predicted_accuracy = self._estimate_prediction_accuracy(prediction_data, uncertainty_analysis)
        
        # 3. 信頼区間計算
        confidence_interval = self._calculate_confidence_interval(predicted_accuracy, uncertainty_analysis)
        
        # 4. 失敗リスク評価
        failure_risk = self._assess_failure_risk(prediction_data, uncertainty_analysis)
        
        # 5. メタ信頼度計算
        meta_confidence = self._calculate_meta_confidence(uncertainty_analysis, failure_risk)
        
        meta_prediction = MetaPrediction(
            predicted_accuracy=predicted_accuracy,
            uncertainty_score=uncertainty_analysis.total_uncertainty,
            confidence_interval=confidence_interval,
            failure_risk=failure_risk,
            meta_confidence=meta_confidence
        )
        
        # 結果記録
        self._record_meta_prediction(meta_prediction, race_data)
        
        logger.info(f"✨ メタ予測完了 - 予測精度予測: {predicted_accuracy:.3f}")
        return meta_prediction
    
    def _analyze_uncertainty(self, prediction_data: Dict, race_data: Dict) -> UncertaintyAnalysis:
        """不確実性分析"""
        racers = race_data.get('racers', [])
        
        # 認識的不確実性（モデルの知識不足）
        confidence_values = []
        if 'racers' in prediction_data:
            for racer in prediction_data['racers']:
                conf = racer.get('prediction', 0.2)
                confidence_values.append(conf)
        
        if confidence_values:
            confidence_variance = np.var(confidence_values)
            epistemic_uncertainty = min(0.5, confidence_variance * 5.0)
        else:
            epistemic_uncertainty = 0.3
        
        # 偶然的不確実性（データの本質的ランダム性）
        data_completeness = len([r for r in racers if r.get('win_rate', 0) > 0]) / max(1, len(racers))
        weather_uncertainty = 0.05  # 天候による不確実性（簡易）
        aleatoric_uncertainty = (1.0 - data_completeness) * 0.3 + weather_uncertainty
        
        # 総合不確実性
        total_uncertainty = np.sqrt(epistemic_uncertainty**2 + aleatoric_uncertainty**2)
        
        # 不確実性要因
        uncertainty_sources = {
            'model_disagreement': epistemic_uncertainty * 0.6,
            'data_incompleteness': (1.0 - data_completeness) * 0.3,
            'weather_conditions': weather_uncertainty,
            'competitor_variability': epistemic_uncertainty * 0.4,
            'measurement_noise': aleatoric_uncertainty * 0.3
        }
        
        return UncertaintyAnalysis(
            epistemic_uncertainty=epistemic_uncertainty,
            aleatoric_uncertainty=aleatoric_uncertainty,
            total_uncertainty=total_uncertainty,
            uncertainty_sources=uncertainty_sources
        )
    
    def _estimate_prediction_accuracy(self, prediction_data: Dict, uncertainty: UncertaintyAnalysis) -> float:
        """予測精度推定"""
        # ベース精度
        base_accuracy = prediction_data.get('confidence', 0.96)
        
        # 不確実性による精度低下
        uncertainty_penalty = uncertainty.total_uncertainty * 0.5
        
        # 予測値の一貫性チェック
        consistency_bonus = 0.0
        if 'racers' in prediction_data:
            predictions = [r.get('prediction', 0.2) for r in prediction_data['racers']]
            if predictions:
                # 予測値の分散が小さいほど一貫性が高い
                prediction_consistency = 1.0 / (1.0 + np.var(predictions) * 10)
                consistency_bonus = prediction_consistency * 0.02
        
        # 過去の精度履歴を考慮
        historical_adjustment = self._get_historical_accuracy_adjustment()
        
        predicted_accuracy = base_accuracy - uncertainty_penalty + consistency_bonus + historical_adjustment
        
        # 範囲制限
        predicted_accuracy = max(0.5, min(0.999, predicted_accuracy))
        
        return predicted_accuracy
    
    def _get_historical_accuracy_adjustment(self) -> float:
        """過去の精度履歴による調整"""
        with sqlite3.connect(self.meta_database) as conn:
            cursor = conn.execute('''
                SELECT predicted_accuracy, actual_accuracy
                FROM meta_predictions
                WHERE timestamp > datetime('now', '-7 days')
                ORDER BY timestamp DESC
                LIMIT 20
            ''')
            history = cursor.fetchall()
        
        if not history:
            return 0.0
        
        # 過去の予測精度と実際の精度の差を分析
        prediction_errors = []
        for predicted, actual in history:
            if actual is not None:
                error = abs(predicted - actual)
                prediction_errors.append(error)
        
        if prediction_errors:
            avg_error = np.mean(prediction_errors)
            # 誤差が小さいほど正の調整
            adjustment = max(-0.05, min(0.05, (0.05 - avg_error) * 2.0))
        else:
            adjustment = 0.0
        
        return adjustment
    
    def _calculate_confidence_interval(self, predicted_accuracy: float, uncertainty: UncertaintyAnalysis) -> Tuple[float, float]:
        """信頼区間計算"""
        # 95%信頼区間
        margin = uncertainty.total_uncertainty * 1.96  # 95%信頼区間
        
        lower_bound = max(0.0, predicted_accuracy - margin)
        upper_bound = min(1.0, predicted_accuracy + margin)
        
        return (lower_bound, upper_bound)
    
    def _assess_failure_risk(self, prediction_data: Dict, uncertainty: UncertaintyAnalysis) -> float:
        """失敗リスク評価"""
        # 基本失敗リスク
        base_risk = uncertainty.total_uncertainty
        
        # 高不確実性要因の検出
        high_uncertainty_factors = sum(1 for source, value in uncertainty.uncertainty_sources.items() if value > 0.1)
        complexity_risk = high_uncertainty_factors * 0.02
        
        # データ品質リスク
        data_quality_risk = uncertainty.uncertainty_sources.get('data_incompleteness', 0.0) * 2.0
        
        # 予測一致度リスク
        confidence_values = []
        if 'racers' in prediction_data:
            confidence_values = [r.get('prediction', 0.2) for r in prediction_data['racers']]
        
        if confidence_values:
            prediction_spread = max(confidence_values) - min(confidence_values)
            spread_risk = prediction_spread * 0.1
        else:
            spread_risk = 0.1
        
        total_risk = base_risk + complexity_risk + data_quality_risk + spread_risk
        
        return min(1.0, total_risk)
    
    def _calculate_meta_confidence(self, uncertainty: UncertaintyAnalysis, failure_risk: float) -> float:
        """メタ信頼度計算"""
        # 不確実性による信頼度低下
        uncertainty_factor = 1.0 - uncertainty.total_uncertainty
        
        # 失敗リスクによる信頼度低下
        risk_factor = 1.0 - failure_risk
        
        # 過去のメタ予測性能
        historical_performance = self._get_meta_prediction_performance()
        
        meta_confidence = uncertainty_factor * risk_factor * historical_performance
        
        return max(0.5, min(0.999, meta_confidence))
    
    def _get_meta_prediction_performance(self) -> float:
        """メタ予測性能取得"""
        with sqlite3.connect(self.meta_database) as conn:
            cursor = conn.execute('''
                SELECT predicted_accuracy, actual_accuracy
                FROM meta_predictions
                WHERE actual_accuracy IS NOT NULL
                AND timestamp > datetime('now', '-30 days')
            ''')
            performance_data = cursor.fetchall()
        
        if not performance_data:
            return 0.95  # デフォルト性能
        
        # メタ予測の精度を計算
        meta_errors = [abs(predicted - actual) for predicted, actual in performance_data]
        avg_meta_error = np.mean(meta_errors)
        
        # エラーが小さいほど高性能
        performance = max(0.7, min(0.99, 1.0 - avg_meta_error * 2.0))
        
        return performance
    
    def _record_meta_prediction(self, meta_prediction: MetaPrediction, race_data: Dict):
        """メタ予測記録"""
        race_id = f"{race_data.get('venue_id', 'unknown')}_{race_data.get('race_number', 0)}"
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.meta_database) as conn:
            conn.execute('''
                INSERT INTO meta_predictions
                (race_id, timestamp, predicted_accuracy, uncertainty_score,
                 confidence_interval_lower, confidence_interval_upper, 
                 failure_risk, meta_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                race_id, timestamp, meta_prediction.predicted_accuracy,
                meta_prediction.uncertainty_score,
                meta_prediction.confidence_interval[0],
                meta_prediction.confidence_interval[1],
                meta_prediction.failure_risk,
                meta_prediction.meta_confidence
            ))
    
    def update_actual_accuracy(self, race_id: str, actual_accuracy: float):
        """実際の精度更新"""
        with sqlite3.connect(self.meta_database) as conn:
            conn.execute('''
                UPDATE meta_predictions
                SET actual_accuracy = ?
                WHERE race_id = ? AND actual_accuracy IS NULL
            ''', (actual_accuracy, race_id))
    
    def get_meta_stats(self) -> Dict:
        """メタ統計取得"""
        with sqlite3.connect(self.meta_database) as conn:
            cursor = conn.execute('''
                SELECT AVG(predicted_accuracy), AVG(uncertainty_score), 
                       AVG(failure_risk), AVG(meta_confidence), COUNT(*)
                FROM meta_predictions
                WHERE timestamp > datetime('now', '-24 hours')
            ''')
            stats = cursor.fetchone()
            
            # メタ予測性能
            cursor = conn.execute('''
                SELECT AVG(ABS(predicted_accuracy - actual_accuracy)) as avg_error
                FROM meta_predictions
                WHERE actual_accuracy IS NOT NULL
                AND timestamp > datetime('now', '-7 days')
            ''')
            performance = cursor.fetchone()
        
        return {
            'average_predicted_accuracy': stats[0] if stats[0] else 0.96,
            'average_uncertainty': stats[1] if stats[1] else 0.1,
            'average_failure_risk': stats[2] if stats[2] else 0.05,
            'average_meta_confidence': stats[3] if stats[3] else 0.95,
            'meta_predictions_24h': stats[4] if stats[4] else 0,
            'meta_prediction_error': performance[0] if performance[0] else 0.02,
            'meta_system_active': True,
            'confidence_target': self.confidence_target
        }

# グローバルインスタンス
meta_predictor = MetaPredictionSystem()
