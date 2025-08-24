#!/usr/bin/env python3
"""
強化された予想システム
BoatraceOpenAPI Programs & Previewsを活用した高精度予想
"""

import requests
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import random
import os
import sys

# 高度MLモデルのインポート
try:
    from advanced_ml_predictor import AdvancedMLPredictor
    HAS_ADVANCED_ML = True
except ImportError:
    HAS_ADVANCED_ML = False

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedPredictor:
    """Programs & Previews APIを活用した強化予想システム"""
    
    def __init__(self):
        self.programs_base_url = "https://boatraceopenapi.github.io/programs/v2"
        self.previews_base_url = "https://boatraceopenapi.github.io/previews/v2"
        
        # ML予想システム初期化
        self.ml_predictor = None
        if HAS_ADVANCED_ML:
            try:
                self.ml_predictor = AdvancedMLPredictor()
                logger.info("高度ML予想システム有効")
            except Exception as e:
                logger.error(f"ML予想システム初期化エラー: {e}")
                self.ml_predictor = None
        
        # 重み係数（競艇実情反映版）
        self.weights = {
            'position_advantage': 0.45,     # コース別有利性（最重要）
            'national_win_rate': 0.12,      # 全国勝率
            'local_win_rate': 0.08,         # 当地勝率
            'start_timing': 0.12,           # スタートタイミング（重要）
            'motor_performance': 0.08,      # モーター性能
            'boat_performance': 0.05,       # ボート性能
            'exhibition_time': 0.05,        # 展示タイム
            'weather_conditions': 0.03,     # 気象条件
            'ml_prediction': 0.02           # ML予想（補助的）
        }
        
        # 的中率データキャッシュ
        self.accuracy_data = None
        self.accuracy_last_loaded = 0
    
    def load_accuracy_data(self) -> Optional[Dict]:
        """的中率データを読み込み（キャッシュ機能付き）"""
        try:
            accuracy_file = 'cache/latest_accuracy.json'
            
            # ファイルが存在しない場合
            if not os.path.exists(accuracy_file):
                logger.debug("的中率データファイルが存在しません")
                return None
            
            # キャッシュが新しい場合はそのまま使用（10分間キャッシュ）
            current_time = time.time()
            if self.accuracy_data and (current_time - self.accuracy_last_loaded) < 600:
                return self.accuracy_data
            
            # ファイルから読み込み
            with open(accuracy_file, 'r', encoding='utf-8') as f:
                self.accuracy_data = json.load(f)
                self.accuracy_last_loaded = current_time
            
            logger.debug("的中率データ読み込み完了")
            return self.accuracy_data
            
        except Exception as e:
            logger.warning(f"的中率データ読み込みエラー: {e}")
            return None
    
    def calculate_accuracy_factor(self, venue_id: int) -> float:
        """会場別的中率要因を計算"""
        try:
            accuracy_data = self.load_accuracy_data()
            if not accuracy_data:
                return 0.5  # デフォルト値
            
            # 全体的中率
            overall_accuracy = accuracy_data.get('summary', {}).get('win_accuracy', 50.0) / 100.0
            
            # 会場別的中率を計算（利用可能な場合）
            venue_accuracy = 0.5
            races = accuracy_data.get('races', [])
            venue_races = [r for r in races if r.get('venue_id') == venue_id]
            
            if venue_races:
                venue_hits = sum(1 for r in venue_races if r.get('is_hit', False))
                venue_total = len(venue_races)
                venue_accuracy = venue_hits / venue_total if venue_total > 0 else 0.5
            
            # 全体と会場別の加重平均
            accuracy_factor = (overall_accuracy * 0.6 + venue_accuracy * 0.4)
            
            # 0.2 〜 0.8 の範囲に正規化
            accuracy_factor = max(0.2, min(0.8, accuracy_factor))
            
            logger.debug(f"会場{venue_id}的中率要因: {accuracy_factor:.3f}")
            return accuracy_factor
            
        except Exception as e:
            logger.warning(f"的中率要因計算エラー: {e}")
            return 0.5
    
    def fetch_programs_data(self, date_str: str = 'today') -> Optional[Dict]:
        """Programs APIからデータを取得"""
        try:
            url = f"{self.programs_base_url}/{date_str}.json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Programs API取得失敗: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Programs API取得エラー: {e}")
            return None
    
    def fetch_previews_data(self, date_str: str = 'today') -> Optional[Dict]:
        """Previews APIからデータを取得"""
        try:
            url = f"{self.previews_base_url}/{date_str}.json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Previews API取得失敗: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Previews API取得エラー: {e}")
            return None
    
    def calculate_enhanced_prediction(self, venue_id: int, race_number: int, date_str: str = 'today') -> Optional[Dict]:
        """強化された予想計算"""
        try:
            # 両APIからデータを取得
            programs_data = self.fetch_programs_data(date_str)
            previews_data = self.fetch_previews_data(date_str)
            
            if not programs_data or not previews_data:
                logger.error("APIデータ取得失敗")
                return None
            
            # 該当レースのデータを検索
            target_program = None
            target_preview = None
            
            for program in programs_data.get('programs', []):
                if program.get('race_stadium_number') == venue_id and program.get('race_number') == race_number:
                    target_program = program
                    break
            
            for preview in previews_data.get('previews', []):
                if preview.get('race_stadium_number') == venue_id and preview.get('race_number') == race_number:
                    target_preview = preview
                    break
            
            if not target_program or not target_preview:
                logger.warning(f"対象レースが見つかりません: venue={venue_id}, race={race_number}")
                return None
            
            # 予想計算実行
            return self._calculate_race_prediction(target_program, target_preview)
            
        except Exception as e:
            logger.error(f"強化予想計算エラー: {e}")
            return None
    
    def _calculate_race_prediction(self, program: Dict, preview: Dict) -> Dict:
        """レース予想計算メイン処理"""
        try:
            program_boats = {boat['racer_boat_number']: boat for boat in program.get('boats', [])}
            preview_boats = {boat['racer_boat_number']: boat for boat in preview.get('boats', [])}
            
            predictions = {}
            racer_data = []
            
            # 各艇の予想値計算
            for boat_num in range(1, 7):
                if boat_num in program_boats and boat_num in preview_boats:
                    prog_boat = program_boats[boat_num]
                    prev_boat = preview_boats[boat_num]
                    
                    score = self._calculate_boat_score(prog_boat, prev_boat, preview)
                    predictions[boat_num] = score
                    
                    # レーサー詳細データ（テンプレート互換性を確保、None値を完全排除）
                    analysis = self._generate_analysis(prog_boat, prev_boat, boat_num)
                    
                    racer_info = {
                        'number': boat_num,
                        'name': prog_boat.get('racer_name', '不明'),
                        'prediction': score if score is not None else 0.0,
                        # テンプレート互換フィールド（None値を完全に排除）
                        'win_rate': prog_boat.get('racer_national_top_1_percent', 0) or 0,
                        'local_win_rate': prog_boat.get('racer_local_top_1_percent', 0) or 0,
                        'place_rate': prog_boat.get('racer_national_top_2_percent', 0) or 0,
                        'average_st': prev_boat.get('racer_start_timing', 0.17) or 0.17,
                        # 分析用の詳細データ
                        'national_win_rate': prog_boat.get('racer_national_top_1_percent', 0) or 0,
                        'motor_rate': prog_boat.get('racer_assigned_motor_top_2_percent', 0) or 0,
                        'boat_rate': prog_boat.get('racer_assigned_boat_top_2_percent', 0) or 0,
                        'start_timing': prev_boat.get('racer_start_timing', 0.17) or 0.17,
                        'exhibition_time': prev_boat.get('racer_exhibition_time', 0) or 0,
                        'analysis': analysis if analysis is not None else {
                            'base_strength': 0.0,
                            'lane_advantage': 0.15,
                            'local_adaptation': 0.0,
                            'st_factor': 1.0
                        }
                    }
                    racer_data.append(racer_info)
            
            # ソート
            sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
            racer_data.sort(key=lambda x: x['prediction'], reverse=True)
            
            # 推奨買い目計算
            win_recommendation = sorted_predictions[0][0] if sorted_predictions else 1
            place_recommendations = [boat for boat, _ in sorted_predictions[:3]]
            
            # 信頼度計算
            confidence = self._calculate_confidence(predictions, preview)
            
            return {
                'predictions': {str(boat): score for boat, score in predictions.items()},
                'racers': racer_data,
                'recommended_win': win_recommendation,
                'recommended_place': place_recommendations,
                'confidence': confidence,
                'race_conditions': {
                    'wind': preview.get('race_wind', 0),
                    'wave': preview.get('race_wave', 0),
                    'weather': preview.get('race_weather_number', 1),
                    'temperature': preview.get('race_temperature', 25),
                    'water_temp': preview.get('race_water_temperature', 25)
                },
                'enhanced': True,
                'api_sources': ['BoatraceOpenAPI_Programs', 'BoatraceOpenAPI_Previews']
            }
            
        except Exception as e:
            logger.error(f"レース予想計算エラー: {e}")
            return None
    
    def _calculate_boat_score(self, prog_boat: Dict, prev_boat: Dict, race_conditions: Dict) -> float:
        """各艇のスコア計算"""
        try:
            score = 0.0
            boat_number = prog_boat.get('racer_boat_number', 1)
            
            # コース別有利性（実績統計版：実際の勝率を反映）
            position_advantages = {
                1: 0.50,  # 1号艇：統計上約50%の勝率
                2: 0.15,  # 2号艇：統計上約15%の勝率
                3: 0.12,  # 3号艇：統計上約12%の勝率  
                4: 0.10,  # 4号艇：統計上約10%の勝率
                5: 0.08,  # 5号艇：統計上約8%の勝率
                6: 0.05   # 6号艇：統計上約5%の勝率
            }
            position_advantage = position_advantages.get(boat_number, 0.15)
            score += position_advantage * self.weights['position_advantage']
            
            # 勝率の時系列分析（重み付き平均）
            performance_score = self._calculate_performance_trend(prog_boat)
            score += performance_score * (self.weights['national_win_rate'] + self.weights['local_win_rate'])
            
            # モーター・ボート性能の複合評価
            motor_boat_score = self._calculate_motor_boat_score(prog_boat)
            score += motor_boat_score * (self.weights['motor_performance'] + self.weights['boat_performance'])
            
            # スタートタイミング評価（0.15前後が理想）
            start_timing = prev_boat.get('racer_start_timing', 0.17)
            if start_timing is not None:
                timing_score = max(0, 1 - abs(abs(start_timing) - 0.15) * 10)
                score += timing_score * self.weights['start_timing']
            
            # 展示航走データの総合評価
            exhibition_score = self._calculate_exhibition_score(prev_boat, boat_number)
            score += exhibition_score * self.weights['exhibition_time']
            
            # 気象条件の詳細補正
            weather_adjustment = self._calculate_weather_adjustment(prog_boat, race_conditions, boat_number)
            score += weather_adjustment * self.weights['weather_conditions']
            
            # ML予想の統合（利用可能な場合）
            ml_score = self._get_ml_prediction(prog_boat, race_conditions, boat_number)
            score += ml_score * self.weights['ml_prediction']
            
            # 的中率履歴要因（新追加）
            venue_id = race_conditions.get('race_stadium_number', 1)
            accuracy_factor = self.calculate_accuracy_factor(venue_id)
            # 的中率が高い会場では保守的に、低い会場では積極的に予想を調整
            accuracy_adjustment = (accuracy_factor - 0.5) * 0.5  # -0.15 〜 +0.15 の調整
            score += accuracy_adjustment * self.weights['accuracy_history']
            
            # ランダム性を削除（予想の安定性確保のため）
            # randomness = (random.random() - 0.5) * 0.02  # 削除: 順位変動の原因
            # score += randomness
            
            return min(1.0, max(0.0, score))  # 0.0-1.0に制限
            
        except Exception as e:
            logger.error(f"艇スコア計算エラー: {e}")
            return 0.0
    
    def _generate_analysis(self, prog_boat: Dict, prev_boat: Dict, boat_number: int) -> Dict:
        """レーサー分析データ生成"""
        analysis = {}
        
        # テンプレート期待フィールド
        national_win = prog_boat.get('racer_national_top_1_percent', 0) / 100
        local_win = prog_boat.get('racer_local_top_1_percent', 0) / 100
        
        # 基本実力（国体勝率をベースに計算）
        analysis['base_strength'] = national_win
        
        # 艇番有利性（コース別有利性を計算）
        position_advantages = {
            1: 0.35, 2: 0.18, 3: 0.16, 4: 0.10, 5: 0.08, 6: 0.06
        }
        analysis['lane_advantage'] = position_advantages.get(boat_number, 0.15)
        
        # 当地適性
        analysis['local_adaptation'] = local_win
        
        # ST補正係数
        start_timing = prev_boat.get('racer_start_timing', 0.17)
        if start_timing is not None:
            analysis['st_factor'] = max(0.5, 1 - abs(abs(start_timing) - 0.15) * 2)
        else:
            analysis['st_factor'] = 1.0
        
        # 従来フィールド（互換性のため）
        analysis['national_strength'] = national_win * 100
        analysis['motor_bonus'] = prog_boat.get('racer_assigned_motor_top_2_percent', 0)
        analysis['boat_bonus'] = prog_boat.get('racer_assigned_boat_top_2_percent', 0)
        analysis['start_evaluation'] = self._evaluate_start_timing(start_timing)
        analysis['exhibition_evaluation'] = self._evaluate_exhibition_time(prev_boat.get('racer_exhibition_time', 0))
        
        return analysis
    
    def _evaluate_start_timing(self, timing: float) -> str:
        """スタートタイミング評価"""
        if timing is None:
            return "unknown"
        if abs(timing) <= 0.05:
            return "excellent"
        elif abs(timing) <= 0.10:
            return "good"
        elif abs(timing) <= 0.15:
            return "average"
        else:
            return "poor"
    
    def _calculate_exhibition_score(self, prev_boat: Dict, boat_number: int) -> float:
        """展示航走データの総合スコア計算"""
        try:
            total_score = 0.0
            
            # 展示タイム（基本評価）
            exhibition_time = prev_boat.get('racer_exhibition_time', 7.0)
            if exhibition_time > 0:
                # コース別の理想タイム設定
                ideal_times = {1: 6.7, 2: 6.8, 3: 6.9, 4: 7.0, 5: 7.1, 6: 7.2}
                ideal_time = ideal_times.get(boat_number, 6.9)
                
                # 理想タイムとの差を評価
                time_diff = abs(exhibition_time - ideal_time)
                time_score = max(0, 1 - time_diff * 2)  # 0.5秒差で0点
                total_score += time_score * 0.4
            
            # 直線タイム（利用可能な場合）
            straight_time = prev_boat.get('racer_straight_time', 0)
            if straight_time > 0:
                # 理想的な直線タイム（6.5-7.0秒）
                straight_score = max(0, (7.0 - straight_time) / 0.5)
                total_score += straight_score * 0.3
            
            # ターンタイム（利用可能な場合）
            turn_time = prev_boat.get('racer_turn_time', 0)
            if turn_time > 0:
                # 理想的なターンタイム
                turn_score = max(0, 1 - (turn_time - 33.0) / 10.0)  # 33秒を基準
                total_score += turn_score * 0.3
            
            # 展示タイムが他艇との比較での順位も考慮（APIから取得可能なら）
            exhibition_rank = prev_boat.get('racer_exhibition_rank', 0)
            if exhibition_rank > 0:
                rank_score = max(0, (7 - exhibition_rank) / 6)  # 1位=1.0, 6位=0.16
                total_score = max(total_score, rank_score)  # より良いスコアを採用
            
            return min(1.0, total_score)
            
        except Exception as e:
            logger.error(f"展示スコア計算エラー: {e}")
            return 0.5
    
    def _calculate_motor_boat_score(self, prog_boat: Dict) -> float:
        """モーター・ボート性能の複合評価"""
        try:
            # 基本性能
            motor_perf = prog_boat.get('racer_assigned_motor_top_2_percent', 0) / 100
            boat_perf = prog_boat.get('racer_assigned_boat_top_2_percent', 0) / 100
            
            # 節間成績（最近の成績）
            recent_motor_win = prog_boat.get('racer_assigned_motor_recent_win_rate', 0) / 100
            recent_boat_win = prog_boat.get('racer_assigned_boat_recent_win_rate', 0) / 100
            
            # 組み合わせ評価
            base_score = (motor_perf + boat_perf) / 2
            recent_score = (recent_motor_win + recent_boat_win) / 2
            
            # 最近の成績を重視（7:3の比率）
            final_score = base_score * 0.3 + recent_score * 0.7
            
            # モーター・ボートの相性評価
            if motor_perf > 0.15 and boat_perf > 0.15:
                final_score += 0.1  # 両方良い場合はボーナス
            elif motor_perf > 0.2 or boat_perf > 0.2:
                final_score += 0.05  # どちらか一方が特に良い場合
            
            return min(1.0, final_score)
            
        except Exception as e:
            logger.error(f"モーター・ボートスコア計算エラー: {e}")
            return 0.0
    
    def _calculate_weather_adjustment(self, prog_boat: Dict, race_conditions: Dict, boat_number: int) -> float:
        """気象条件による詳細補正"""
        try:
            adjustment = 0.0
            
            wind = race_conditions.get('race_wind', 0)
            wave = race_conditions.get('race_wave', 0)
            temperature = race_conditions.get('race_temperature', 25)
            water_temp = race_conditions.get('race_water_temperature', 25)
            weather = race_conditions.get('race_weather_number', 1)  # 1:晴 2:曇 3:雨
            
            # 基本的な荒天補正
            rough_conditions = wind >= 3 or wave >= 3
            if rough_conditions:
                # 経験豊富な選手を優遇
                age = prog_boat.get('racer_age', 30)
                experience_bonus = min(0.15, (age - 25) * 0.01)
                adjustment += experience_bonus
                
                # コース別有利性の変化
                if boat_number == 1:
                    adjustment += 0.1  # 1号艇は荒天でさらに有利
                elif boat_number in [2, 3]:
                    adjustment += 0.05  # 2, 3号艇も比較的有利
                else:
                    adjustment -= 0.05  # 4, 5, 6号艇は不利
            
            # 風向きの影響（可能なら）
            wind_direction = race_conditions.get('race_wind_direction', 0)
            if wind_direction > 0:
                # 向かい風の場合は1号艇がより有利
                if wind_direction in [1, 2] and boat_number == 1:  # 向かい風
                    adjustment += 0.05
                elif wind_direction in [3, 4] and boat_number >= 4:  # 追い風
                    adjustment += 0.03  # 4-6号艇が差しやすくなる
            
            # 気温・水温による影響
            temp_diff = abs(temperature - 25)  # 25度を基準
            water_temp_diff = abs(water_temp - 25)
            
            if temp_diff > 10 or water_temp_diff > 5:
                # 極端な気温・水温では経験が重要
                local_win = prog_boat.get('racer_local_top_1_percent', 0)
                if local_win > 20:  # 当地成績が良い選手
                    adjustment += 0.05
            
            # 雨の影響
            if weather == 3:  # 雨天
                # スタートの上手い選手を優遇
                st_rate = prog_boat.get('racer_start_timing_rate', 0)
                if st_rate > 0.6:
                    adjustment += 0.05
                
                # 1号艇の有利性がさらに増加
                if boat_number == 1:
                    adjustment += 0.08
            
            return min(1.0, adjustment)
            
        except Exception as e:
            logger.error(f"気象補正計算エラー: {e}")
            return 0.0
    
    def _calculate_performance_trend(self, prog_boat: Dict) -> float:
        """過去成績の時系列分析（トレンド評価）"""
        try:
            # 各期間の勝率データ
            national_win = prog_boat.get('racer_national_top_1_percent', 0) / 100
            local_win = prog_boat.get('racer_local_top_1_percent', 0) / 100
            recent_win = prog_boat.get('racer_recent_win_rate', 0) / 100  # 最近の勝率
            
            # 節間成績（最も重要）
            season_win = prog_boat.get('racer_season_win_rate', national_win) / 100
            
            # 時系列重み（最近ほど重要）
            weights = {
                'recent': 0.4,    # 直近成績
                'season': 0.3,    # 節間成績
                'local': 0.2,     # 当地成績
                'national': 0.1   # 全国成績
            }
            
            # 重み付き平均計算
            weighted_score = (
                recent_win * weights['recent'] +
                season_win * weights['season'] +
                local_win * weights['local'] +
                national_win * weights['national']
            )
            
            # トレンド分析（上昇・下降傾向）
            trend_bonus = 0.0
            if recent_win > national_win * 1.1:  # 最近調子が良い
                trend_bonus += 0.05
            elif recent_win < national_win * 0.9:  # 最近調子が悪い
                trend_bonus -= 0.05
            
            # 当地適性ボーナス
            if local_win > national_win * 1.2:  # 当地で特に強い
                trend_bonus += 0.08
            
            # 年齢による補正
            age = prog_boat.get('racer_age', 30)
            if age <= 25:  # 若手の勢い
                trend_bonus += 0.02
            elif age >= 45:  # ベテランの安定性低下
                trend_bonus -= 0.03
            
            final_score = weighted_score + trend_bonus
            return min(1.0, max(0.0, final_score))
            
        except Exception as e:
            logger.error(f"パフォーマンストレンド計算エラー: {e}")
            # フォールバック: 基本勝率の平均
            national = prog_boat.get('racer_national_top_1_percent', 0) / 100
            local = prog_boat.get('racer_local_top_1_percent', 0) / 100
            return (national + local) / 2
    
    def _evaluate_exhibition_time(self, time: float) -> str:
        """展示タイム評価"""
        if time <= 0:
            return "unknown"
        elif time <= 6.6:
            return "excellent"
        elif time <= 6.8:
            return "good"
        elif time <= 7.0:
            return "average"
        else:
            return "poor"
    
    def _get_ml_prediction(self, prog_boat: Dict, race_conditions: Dict, boat_number: int) -> float:
        """ML予想システムからの予測値を取得"""
        try:
            if not self.ml_predictor or not hasattr(self.ml_predictor, 'predict_for_boat'):
                # MLシステムが利用不可の場合はフォールバック
                national = prog_boat.get('racer_national_top_1_percent', 0) / 100
                local = prog_boat.get('racer_local_top_1_percent', 0) / 100
                return (national + local) / 2
            
            # MLシステム用の特徴量を構築
            features = {
                'venue_id': race_conditions.get('venue_id', 0),
                'race_number': race_conditions.get('race_number', 0),
                'racer_boat_number': boat_number,
                'racer_national_top_1_percent': prog_boat.get('racer_national_top_1_percent', 0),
                'racer_local_top_1_percent': prog_boat.get('racer_local_top_1_percent', 0),
                'racer_assigned_motor_top_2_percent': prog_boat.get('racer_assigned_motor_top_2_percent', 0),
                'racer_assigned_boat_top_2_percent': prog_boat.get('racer_assigned_boat_top_2_percent', 0),
                'race_wind': race_conditions.get('race_wind', 0),
                'race_wave': race_conditions.get('race_wave', 0),
                'race_temperature': race_conditions.get('race_temperature', 20),
                'race_water_temperature': race_conditions.get('race_water_temperature', 20)
            }
            
            # ML予測実行
            prediction_score = self.ml_predictor.predict_for_boat(features)
            return min(1.0, max(0.0, prediction_score))
            
        except Exception as e:
            logger.error(f"ML予想取得エラー: {e}")
            # エラー時はフォールバック
            national = prog_boat.get('racer_national_top_1_percent', 0) / 100
            local = prog_boat.get('racer_local_top_1_percent', 0) / 100
            return (national + local) / 2
    
    def _calculate_confidence(self, predictions: Dict, race_conditions: Dict) -> float:
        """競艇特性を考慮した信頼度計算"""
        try:
            values = list(predictions.values())
            if len(values) < 2:
                return 0.5
            
            # 1号艇の予想値を基準とした信頼度計算
            boat_1_score = predictions.get(1, 0)
            max_score = max(values)
            
            # 1号艇が最高スコアかつ十分高い場合は高信頼度
            if boat_1_score == max_score and boat_1_score > 0.4:
                base_confidence = 0.8
            elif max_score > 0.3:  # 明確な有力候補がいる場合
                base_confidence = 0.7
            else:  # 混戦の場合
                base_confidence = 0.5
            
            # スコア差による信頼度調整
            sorted_values = sorted(values, reverse=True)
            if len(sorted_values) >= 2:
                score_diff = sorted_values[0] - sorted_values[1]
                confidence = base_confidence + (score_diff * 0.5)
            else:
                confidence = base_confidence
            
            # 気象条件による補正（より詳細）
            wind = race_conditions.get('race_wind', 0)
            wave = race_conditions.get('race_wave', 0)
            
            # 荒天時の補正（1号艇有利性が増すため、むしろ信頼度を上げる場合も）
            if wind >= 5 or wave >= 4:
                if boat_1_score == max_score:
                    confidence *= 1.1  # 1号艇予想時は荒天で信頼度アップ
                else:
                    confidence *= 0.7  # その他は信頼度ダウン
            elif wind >= 3 or wave >= 3:
                confidence *= 0.9  # 軽微な悪条件
            
            return confidence
            
        except Exception as e:
            logger.error(f"信頼度計算エラー: {e}")
            return 0.5

# メイン実行部
if __name__ == "__main__":
    predictor = EnhancedPredictor()
    
    # テスト実行
    print("=== Enhanced Predictor テスト ===")
    result = predictor.calculate_enhanced_prediction(23, 1)  # 唐津1R
    
    if result:
        print("強化予想結果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("予想計算失敗")