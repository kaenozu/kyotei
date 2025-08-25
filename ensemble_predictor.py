#!/usr/bin/env python3
"""
アンサンブル予想システム
複数の予想手法を統合した高精度予想エンジン
"""

import json
import logging
import numpy as np
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os

# 既存の予想システムをインポート
try:
    from enhanced_predictor import EnhancedPredictor
    from advanced_ml_predictor import AdvancedMLPredictor
    HAS_ENHANCED = True
    HAS_ADVANCED_ML = True
except ImportError as e:
    logging.warning(f"予想システムインポートエラー: {e}")
    HAS_ENHANCED = False
    HAS_ADVANCED_ML = False

logger = logging.getLogger(__name__)

class EnsemblePredictor:
    """アンサンブル予想システム"""
    
    def __init__(self):
        self.predictors = {}
        self.weights = {}
        
        # 各予想システム初期化
        self._init_predictors()
        
        # アンサンブル重み設定
        self._init_weights()
        
        # パフォーマンス履歴
        self.performance_history = {}
        
    def _init_predictors(self):
        """各予想システムの初期化"""
        try:
            # 1. 強化予想システム
            if HAS_ENHANCED:
                self.predictors['enhanced'] = EnhancedPredictor()
                logger.info("強化予想システム初期化完了")
            
            # 2. 高度ML予想システム  
            if HAS_ADVANCED_ML:
                self.predictors['advanced_ml'] = AdvancedMLPredictor()
                logger.info("高度ML予想システム初期化完了")
            
            # 3. 統計ベース予想システム
            self.predictors['statistical'] = StatisticalPredictor()
            logger.info("統計ベース予想システム初期化完了")
            
            # 4. 形態分析予想システム
            self.predictors['pattern'] = PatternAnalysisPredictor()
            logger.info("形態分析予想システム初期化完了")
            
        except Exception as e:
            logger.error(f"予想システム初期化エラー: {e}")
    
    def _init_weights(self):
        """アンサンブル重み設定"""
        # 基本重み（的中率に基づく調整）
        base_weights = {
            'enhanced': 0.35,      # 実績のあるメインシステム
            'advanced_ml': 0.25,   # ML学習システム  
            'statistical': 0.20,   # 統計分析
            'pattern': 0.20        # 形態分析
        }
        
        # 利用可能なシステムに基づいて重みを調整
        available_systems = list(self.predictors.keys())
        total_weight = sum(base_weights[sys] for sys in available_systems)
        
        for system in available_systems:
            self.weights[system] = base_weights[system] / total_weight
        
        logger.info(f"アンサンブル重み: {self.weights}")
    
    def predict_race(self, race_data: Dict, preview_data: Dict = None) -> Dict:
        """レース予想（アンサンブル）"""
        try:
            predictions = {}
            boat_scores = {}
            
            # 各システムから予想を取得
            for system_name, predictor in self.predictors.items():
                try:
                    if system_name == 'enhanced':
                        # EnhancedPredictorは直接レース計算を実行
                        pred_result = self._get_enhanced_predictions(predictor, race_data, preview_data)
                    elif system_name == 'advanced_ml' and hasattr(predictor, 'predict_for_boat'):
                        pred_result = self._get_ml_predictions(predictor, race_data)
                    else:
                        pred_result = predictor.predict_race(race_data, preview_data)
                    
                    predictions[system_name] = pred_result
                    
                except Exception as e:
                    logger.warning(f"{system_name}システム予想エラー: {e}")
                    continue
            
            # アンサンブル統合
            ensemble_result = self._ensemble_predictions(predictions)
            
            # 信頼度計算
            confidence = self._calculate_ensemble_confidence(predictions)
            
            # 最終結果
            result = {
                'recommended_win': ensemble_result['recommended_win'],
                'recommended_place': ensemble_result['recommended_place'],
                'confidence': confidence,
                'individual_predictions': predictions,
                'ensemble_method': 'weighted_voting',
                'system_weights': self.weights
            }
            
            return result
            
        except Exception as e:
            logger.error(f"アンサンブル予想エラー: {e}")
            # フォールバック予想
            return self._fallback_prediction(race_data)
    
    def _get_enhanced_predictions(self, enhanced_predictor, race_data: Dict, preview_data: Dict = None) -> Dict:
        """EnhancedPredictorからの予想取得"""
        try:
            # EnhancedPredictorの内部計算メソッドを直接使用
            if hasattr(enhanced_predictor, '_calculate_race_prediction'):
                result = enhanced_predictor._calculate_race_prediction(race_data, preview_data or {})
                
                # 結果フォーマット統一
                return {
                    'recommended_win': result.get('recommended_win', 1),
                    'recommended_place': result.get('recommended_place', [1, 2, 3]),
                    'boat_scores': result.get('predictions', {}),
                    'confidence': result.get('confidence', 0.5),
                    'racers': result.get('racers', [])
                }
            else:
                # フォールバック：統計的予想
                return self._statistical_fallback(race_data)
                
        except Exception as e:
            logger.error(f"Enhanced予想取得エラー: {e}")
            return self._statistical_fallback(race_data)
    
    def _get_ml_predictions(self, ml_predictor, race_data: Dict) -> Dict:
        """ML予想システムからの予想取得"""
        try:
            boats = race_data.get('boats', [])
            ml_scores = {}
            
            for boat in boats:
                boat_number = boat.get('boat_number') or boat.get('racer_boat_number', 1)
                
                # ML予想用特徴量構築
                features = {
                    'venue_id': race_data.get('race_stadium_number', 1),
                    'race_number': race_data.get('race_number', 1),
                    'racer_boat_number': boat_number,
                    'racer_national_top_1_percent': boat.get('racer_national_top_1_percent', 0),
                    'racer_local_top_1_percent': boat.get('racer_local_top_1_percent', 0),
                    'racer_national_top_2_percent': boat.get('racer_national_top_2_percent', 0),
                    'racer_average_start_timing': boat.get('racer_average_start_timing', 0.17),
                    'race_distance': race_data.get('race_distance', 1800)
                }
                
                ml_score = ml_predictor.predict_for_boat(features)
                ml_scores[boat_number] = ml_score
            
            # 推奨艇決定
            sorted_boats = sorted(ml_scores.items(), key=lambda x: x[1], reverse=True)
            recommended_win = sorted_boats[0][0] if sorted_boats else 1
            recommended_place = [x[0] for x in sorted_boats[:3]]
            
            return {
                'recommended_win': recommended_win,
                'recommended_place': recommended_place,
                'boat_scores': ml_scores,
                'confidence': max(ml_scores.values()) if ml_scores else 0.5
            }
            
        except Exception as e:
            logger.error(f"ML予想取得エラー: {e}")
            return {'recommended_win': 1, 'recommended_place': [1, 2, 3], 'confidence': 0.3}
    
    def _ensemble_predictions(self, predictions: Dict) -> Dict:
        """予想統合処理（重み付き投票）"""
        try:
            boat_ensemble_scores = {}
            
            # 各艇のスコアを重み付きで統合
            for system_name, pred_data in predictions.items():
                weight = self.weights.get(system_name, 0)
                if weight <= 0:
                    continue
                
                # 各システムの艇別スコアを取得
                if 'boat_scores' in pred_data:
                    boat_scores = pred_data['boat_scores']
                elif 'racers' in pred_data:
                    boat_scores = {r['number']: r['prediction'] for r in pred_data['racers']}
                elif 'recommended_win' in pred_data:
                    # 推奨艇から逆算してスコア生成
                    boat_scores = self._generate_scores_from_recommendation(pred_data)
                else:
                    continue
                
                # 重み付けして統合
                for boat_num, score in boat_scores.items():
                    if boat_num not in boat_ensemble_scores:
                        boat_ensemble_scores[boat_num] = 0.0
                    boat_ensemble_scores[boat_num] += score * weight
            
            # 最終推奨艇決定
            if boat_ensemble_scores:
                sorted_boats = sorted(boat_ensemble_scores.items(), key=lambda x: x[1], reverse=True)
                recommended_win = sorted_boats[0][0]
                recommended_place = [x[0] for x in sorted_boats[:3]]
            else:
                # フォールバック
                recommended_win = 1
                recommended_place = [1, 2, 3]
            
            return {
                'recommended_win': recommended_win,
                'recommended_place': recommended_place,
                'boat_scores': boat_ensemble_scores
            }
            
        except Exception as e:
            logger.error(f"予想統合エラー: {e}")
            return {'recommended_win': 1, 'recommended_place': [1, 2, 3], 'boat_scores': {}}
    
    def _generate_scores_from_recommendation(self, pred_data: Dict) -> Dict:
        """推奨艇情報からスコアを逆算"""
        scores = {}
        recommended_win = pred_data.get('recommended_win', 1)
        recommended_place = pred_data.get('recommended_place', [1, 2, 3])
        confidence = pred_data.get('confidence', 0.5)
        
        # 6艇分のスコア生成
        for boat_num in range(1, 7):
            if boat_num == recommended_win:
                scores[boat_num] = confidence * 0.8 + 0.2
            elif boat_num in recommended_place[:3]:
                idx = recommended_place.index(boat_num)
                scores[boat_num] = confidence * (0.6 - idx * 0.1) + 0.1
            else:
                scores[boat_num] = 0.1
        
        return scores
    
    def _calculate_ensemble_confidence(self, predictions: Dict) -> float:
        """アンサンブル信頼度計算"""
        try:
            confidences = []
            total_weight = 0
            
            for system_name, pred_data in predictions.items():
                weight = self.weights.get(system_name, 0)
                if weight <= 0:
                    continue
                
                system_confidence = pred_data.get('confidence', 0.5)
                confidences.append(system_confidence * weight)
                total_weight += weight
            
            if total_weight > 0:
                weighted_confidence = sum(confidences) / total_weight
                
                # システム間の一致度も考慮
                agreement_bonus = self._calculate_agreement_bonus(predictions)
                final_confidence = min(0.95, weighted_confidence + agreement_bonus)
                
                return final_confidence
            
            return 0.5
            
        except Exception as e:
            logger.error(f"信頼度計算エラー: {e}")
            return 0.5
    
    def _calculate_agreement_bonus(self, predictions: Dict) -> float:
        """システム間一致度ボーナス"""
        try:
            recommended_wins = []
            for pred_data in predictions.values():
                if 'recommended_win' in pred_data:
                    recommended_wins.append(pred_data['recommended_win'])
            
            if len(recommended_wins) < 2:
                return 0.0
            
            # 最頻値の出現回数
            from collections import Counter
            win_counts = Counter(recommended_wins)
            max_count = max(win_counts.values())
            total_count = len(recommended_wins)
            
            # 一致率に基づくボーナス
            agreement_ratio = max_count / total_count
            if agreement_ratio >= 0.75:
                return 0.1  # 75%以上一致
            elif agreement_ratio >= 0.5:
                return 0.05  # 50%以上一致
            
            return 0.0
            
        except Exception as e:
            logger.error(f"一致度ボーナス計算エラー: {e}")
            return 0.0
    
    def _statistical_fallback(self, race_data: Dict) -> Dict:
        """統計的フォールバック予想"""
        try:
            boats = race_data.get('boats', [])
            if not boats:
                return self._fallback_prediction(race_data)
            
            boat_scores = {}
            for boat in boats:
                boat_number = boat.get('boat_number') or boat.get('racer_boat_number', 1)
                win_rate = boat.get('racer_national_top_1_percent', 0) / 100
                lane_bonus = {1: 0.3, 2: 0.1, 3: 0.08, 4: 0.06, 5: 0.04, 6: 0.02}.get(boat_number, 0.05)
                boat_scores[boat_number] = win_rate + lane_bonus
            
            sorted_boats = sorted(boat_scores.items(), key=lambda x: x[1], reverse=True)
            return {
                'recommended_win': sorted_boats[0][0] if sorted_boats else 1,
                'recommended_place': [x[0] for x in sorted_boats[:3]],
                'boat_scores': boat_scores,
                'confidence': max(boat_scores.values()) if boat_scores else 0.4
            }
        except Exception:
            return self._fallback_prediction(race_data)
    
    def _fallback_prediction(self, race_data: Dict) -> Dict:
        """フォールバック予想"""
        return {
            'recommended_win': 1,
            'recommended_place': [1, 2, 3],
            'confidence': 0.3,
            'note': 'フォールバック予想（アンサンブルエラー）'
        }


class StatisticalPredictor:
    """統計ベース予想システム"""
    
    def predict_race(self, race_data: Dict, preview_data: Dict = None) -> Dict:
        """統計分析による予想"""
        try:
            boats = race_data.get('boats', [])
            boat_scores = {}
            
            for boat in boats:
                boat_number = boat.get('boat_number') or boat.get('racer_boat_number', 1)
                
                # 統計スコア計算
                score = 0.0
                
                # 全国勝率（40%）
                national_win_rate = boat.get('racer_national_top_1_percent', 0)
                score += (national_win_rate / 100) * 0.4
                
                # 当地勝率（30%）
                local_win_rate = boat.get('racer_local_top_1_percent', national_win_rate)
                score += (local_win_rate / 100) * 0.3
                
                # コース有利度（20%）
                position_advantages = {1: 0.55, 2: 0.14, 3: 0.12, 4: 0.10, 5: 0.06, 6: 0.03}
                score += position_advantages.get(boat_number, 0.1) * 0.2
                
                # 連対率（10%）
                place_rate = boat.get('racer_national_top_2_percent', 0)
                score += (place_rate / 100) * 0.1
                
                boat_scores[boat_number] = score
            
            # 推奨艇決定
            sorted_boats = sorted(boat_scores.items(), key=lambda x: x[1], reverse=True)
            recommended_win = sorted_boats[0][0] if sorted_boats else 1
            recommended_place = [x[0] for x in sorted_boats[:3]]
            
            return {
                'recommended_win': recommended_win,
                'recommended_place': recommended_place,
                'boat_scores': boat_scores,
                'confidence': max(boat_scores.values()) if boat_scores else 0.5
            }
            
        except Exception as e:
            logger.error(f"統計予想エラー: {e}")
            return {'recommended_win': 1, 'recommended_place': [1, 2, 3], 'confidence': 0.4}


class PatternAnalysisPredictor:
    """形態分析予想システム"""
    
    def predict_race(self, race_data: Dict, preview_data: Dict = None) -> Dict:
        """形態分析による予想"""
        try:
            boats = race_data.get('boats', [])
            boat_scores = {}
            
            for boat in boats:
                boat_number = boat.get('boat_number') or boat.get('racer_boat_number', 1)
                
                # パターンスコア計算
                score = 0.0
                
                # 基本パターン（勝率×コース）
                win_rate = boat.get('racer_national_top_1_percent', 0) / 100
                lane_factor = {1: 1.2, 2: 0.9, 3: 0.8, 4: 0.7, 5: 0.6, 6: 0.5}.get(boat_number, 0.7)
                score += win_rate * lane_factor * 0.5
                
                # ST適性パターン
                st_timing = abs(boat.get('racer_average_start_timing', 0.17))
                if st_timing <= 0.15:
                    st_bonus = 0.2
                elif st_timing <= 0.18:
                    st_bonus = 0.1
                else:
                    st_bonus = 0.0
                score += st_bonus
                
                # 機器適性パターン  
                motor_rate = boat.get('racer_assigned_motor_top_2_percent', 0)
                boat_rate = boat.get('racer_assigned_boat_top_2_percent', 0)
                equipment_bonus = (motor_rate + boat_rate) / 200 * 0.3
                score += equipment_bonus
                
                boat_scores[boat_number] = score
            
            # 推奨艇決定
            sorted_boats = sorted(boat_scores.items(), key=lambda x: x[1], reverse=True)
            recommended_win = sorted_boats[0][0] if sorted_boats else 1
            recommended_place = [x[0] for x in sorted_boats[:3]]
            
            return {
                'recommended_win': recommended_win,
                'recommended_place': recommended_place,
                'boat_scores': boat_scores,
                'confidence': max(boat_scores.values()) if boat_scores else 0.5
            }
            
        except Exception as e:
            logger.error(f"形態分析予想エラー: {e}")
            return {'recommended_win': 1, 'recommended_place': [1, 2, 3], 'confidence': 0.4}


if __name__ == '__main__':
    # テスト実行
    ensemble = EnsemblePredictor()
    
    # サンプルレースデータ
    sample_race = {
        'race_stadium_number': 1,
        'race_number': 5,
        'race_distance': 1800,
        'boats': [
            {'boat_number': 1, 'racer_national_top_1_percent': 25.0, 'racer_local_top_1_percent': 30.0},
            {'boat_number': 2, 'racer_national_top_1_percent': 20.0, 'racer_local_top_1_percent': 25.0},
            {'boat_number': 3, 'racer_national_top_1_percent': 15.0, 'racer_local_top_1_percent': 20.0},
            {'boat_number': 4, 'racer_national_top_1_percent': 10.0, 'racer_local_top_1_percent': 15.0},
            {'boat_number': 5, 'racer_national_top_1_percent': 8.0, 'racer_local_top_1_percent': 12.0},
            {'boat_number': 6, 'racer_national_top_1_percent': 5.0, 'racer_local_top_1_percent': 8.0}
        ]
    }
    
    result = ensemble.predict_race(sample_race)
    print(f"アンサンブル予想結果: {result}")