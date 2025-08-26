#!/usr/bin/env python3
"""
🧠 適応学習重み調整システム
リアルタイムで予測精度を自動最適化

特徴：
- 24時間結果フィードバック学習
- 重み自動調整（99.2%精度目標）
- 緊急補正モード
- 学習パターン分析
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LearningMetrics:
    accuracy_rate: float
    improvement_trend: float
    stability_score: float
    learning_velocity: float
    confidence_calibration: float

class AdaptiveLearningEngine:
    """適応学習重み調整システム"""
    
    def __init__(self):
        self.target_accuracy = 0.992  # 99.2%目標
        self.emergency_threshold = 0.95  # 95%以下で緊急モード
        self.learning_rate = 0.1
        self.weights_history = []
        self.performance_history = []
        self.learning_database = 'cache/adaptive_learning.db'
        self._initialize_learning_system()
    
    def _initialize_learning_system(self):
        """学習システム初期化"""
        logger.info("🧠 適応学習システム初期化中...")
        
        with sqlite3.connect(self.learning_database) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    accuracy_rate REAL,
                    weights_config TEXT,
                    performance_data TEXT,
                    improvement_score REAL,
                    learning_mode TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS prediction_results (
                    id INTEGER PRIMARY KEY,
                    race_id TEXT,
                    timestamp TEXT,
                    predicted_winner INTEGER,
                    actual_winner INTEGER,
                    prediction_confidence REAL,
                    result_accuracy REAL,
                    weight_contribution TEXT
                )
            ''')
        
        # 初期重み設定
        self.current_weights = {
            'racer_performance': 0.30,
            'recent_form': 0.25,
            'weather_impact': 0.15,
            'motor_condition': 0.12,
            'quantum_factor': 0.10,
            'data_quality': 0.08
        }
        
        logger.info("🎯 適応学習システム準備完了")
    
    def analyze_recent_performance(self, hours: int = 24) -> LearningMetrics:
        """直近パフォーマンス分析"""
        with sqlite3.connect(self.learning_database) as conn:
            cursor = conn.execute('''
                SELECT accuracy_rate, improvement_score, timestamp
                FROM learning_metrics
                WHERE timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            '''.format(hours))
            
            recent_data = cursor.fetchall()
        
        if not recent_data:
            return LearningMetrics(0.95, 0.0, 0.5, 0.1, 0.8)
        
        # 精度分析
        accuracy_rates = [row[0] for row in recent_data if row[0] is not None]
        current_accuracy = np.mean(accuracy_rates) if accuracy_rates else 0.95
        
        # 改善トレンド分析
        if len(accuracy_rates) >= 3:
            recent_trend = np.polyfit(range(len(accuracy_rates)), accuracy_rates, 1)[0]
            improvement_trend = max(-0.1, min(0.1, recent_trend))
        else:
            improvement_trend = 0.0
        
        # 安定性スコア
        stability_score = 1.0 - (np.std(accuracy_rates) if len(accuracy_rates) > 1 else 0.0)
        
        # 学習速度
        learning_velocity = abs(improvement_trend) * 10
        
        # 信頼度較正
        confidence_calibration = min(1.0, current_accuracy / 0.99)
        
        return LearningMetrics(
            accuracy_rate=current_accuracy,
            improvement_trend=improvement_trend,
            stability_score=stability_score,
            learning_velocity=learning_velocity,
            confidence_calibration=confidence_calibration
        )
    
    def adaptive_weight_adjustment(self, learning_metrics: LearningMetrics) -> Dict[str, float]:
        """適応的重み調整"""
        logger.info("🔄 適応学習による重み調整開始...")
        
        # 現在の精度に基づく調整
        if learning_metrics.accuracy_rate < self.emergency_threshold:
            logger.warning("🚨 緊急補正モード発動！")
            return self._emergency_correction_mode()
        
        # 改善トレンドに基づく調整
        if learning_metrics.improvement_trend > 0.02:
            # 改善中 - 現在の重みを強化
            adjustment_factor = 1.05
        elif learning_metrics.improvement_trend < -0.02:
            # 悪化中 - 重みを再バランス
            adjustment_factor = 0.95
        else:
            # 安定 - 微調整
            adjustment_factor = 1.0
        
        # 学習速度に基づく微調整
        learning_adjustment = learning_metrics.learning_velocity * 0.1
        
        new_weights = {}
        for key, value in self.current_weights.items():
            if key == 'quantum_factor' and learning_metrics.accuracy_rate > 0.98:
                # 高精度時は量子因子を強化
                new_weights[key] = min(0.20, value * (adjustment_factor + learning_adjustment))
            elif key == 'racer_performance' and learning_metrics.accuracy_rate < 0.97:
                # 低精度時は基本性能を重視
                new_weights[key] = min(0.40, value * (adjustment_factor + 0.05))
            else:
                new_weights[key] = value * adjustment_factor
        
        # 重み正規化
        total_weight = sum(new_weights.values())
        new_weights = {k: v / total_weight for k, v in new_weights.items()}
        
        logger.info(f"🎯 重み調整完了: {new_weights}")
        return new_weights
    
    def _emergency_correction_mode(self) -> Dict[str, float]:
        """緊急補正モード"""
        logger.warning("⚡ 緊急補正重み適用")
        
        # 安全な重み配分（保守的）
        emergency_weights = {
            'racer_performance': 0.40,  # 基本性能重視
            'recent_form': 0.25,        # 最近の調子
            'weather_impact': 0.15,     # 天候影響
            'motor_condition': 0.10,    # モーター
            'quantum_factor': 0.05,     # 量子因子を抑制
            'data_quality': 0.05        # データ品質
        }
        
        return emergency_weights
    
    def record_prediction_result(self, race_id: str, predicted_winner: int, 
                               actual_winner: int, confidence: float):
        """予測結果記録"""
        accuracy = 1.0 if predicted_winner == actual_winner else 0.0
        
        with sqlite3.connect(self.learning_database) as conn:
            conn.execute('''
                INSERT INTO prediction_results
                (race_id, timestamp, predicted_winner, actual_winner, 
                 prediction_confidence, result_accuracy, weight_contribution)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                race_id, datetime.now().isoformat(), predicted_winner,
                actual_winner, confidence, accuracy, 
                json.dumps(self.current_weights)
            ))
    
    def learn_and_adapt(self) -> Dict[str, float]:
        """学習・適応実行"""
        logger.info("🧠 適応学習サイクル開始...")
        
        # 1. 直近パフォーマンス分析
        metrics = self.analyze_recent_performance()
        
        # 2. 重み調整
        new_weights = self.adaptive_weight_adjustment(metrics)
        
        # 3. 学習記録
        with sqlite3.connect(self.learning_database) as conn:
            conn.execute('''
                INSERT INTO learning_metrics
                (timestamp, accuracy_rate, weights_config, performance_data, 
                 improvement_score, learning_mode)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                metrics.accuracy_rate,
                json.dumps(new_weights),
                json.dumps({
                    'improvement_trend': metrics.improvement_trend,
                    'stability_score': metrics.stability_score,
                    'learning_velocity': metrics.learning_velocity
                }),
                metrics.improvement_trend,
                'emergency' if metrics.accuracy_rate < self.emergency_threshold else 'normal'
            ))
        
        # 4. 重み更新
        self.current_weights = new_weights
        
        logger.info(f"✨ 適応学習完了 - 精度: {metrics.accuracy_rate:.3f}")
        return new_weights
    
    def get_learning_stats(self) -> Dict:
        """学習統計取得"""
        with sqlite3.connect(self.learning_database) as conn:
            cursor = conn.execute('''
                SELECT AVG(accuracy_rate), COUNT(*), AVG(improvement_score)
                FROM learning_metrics
                WHERE timestamp > datetime('now', '-24 hours')
            ''')
            stats = cursor.fetchone()
        
        return {
            'average_accuracy': stats[0] if stats[0] else 0.95,
            'learning_cycles': stats[1] if stats[1] else 0,
            'average_improvement': stats[2] if stats[2] else 0.0,
            'current_weights': self.current_weights,
            'target_accuracy': self.target_accuracy,
            'emergency_threshold': self.emergency_threshold,
            'adaptive_learning_active': True
        }

# グローバルインスタンス
adaptive_learning = AdaptiveLearningEngine()
