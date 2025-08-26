#!/usr/bin/env python3
"""
Advanced Feature Engineering for Kyotei ML System
競艇予想システム向け高度特徴量エンジニアリング

追加特徴量:
1. 過去成績の時系列特徴量
2. 対戦相手との相性
3. 気象条件の組み合わせ
4. 会場特性との適性
5. レーサーの調子（直近パフォーマンス）
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class AdvancedFeatureEngineer:
    """高度特徴量エンジニアリング"""
    
    def __init__(self, db_path: str = 'cache/accuracy_tracker.db'):
        self.db_path = db_path
        self.venue_characteristics = self._load_venue_characteristics()
    
    def _load_venue_characteristics(self) -> Dict:
        """会場特性データ"""
        return {
            1: {'water_type': 'river', 'size': 'medium', 'wind_factor': 0.8},    # 桐生
            2: {'water_type': 'lake', 'size': 'small', 'wind_factor': 0.6},      # 戸田
            3: {'water_type': 'river', 'size': 'large', 'wind_factor': 1.2},     # 江戸川
            4: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.0},      # 平和島
            5: {'water_type': 'river', 'size': 'medium', 'wind_factor': 0.9},    # 多摩川
            6: {'water_type': 'lake', 'size': 'large', 'wind_factor': 0.7},      # 浜名湖
            7: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.1},      # 蒲郡
            8: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.0},      # 常滑
            9: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.0},      # 津
            10: {'water_type': 'sea', 'size': 'small', 'wind_factor': 0.9},     # 三国
            11: {'water_type': 'lake', 'size': 'large', 'wind_factor': 0.8},    # びわこ
            12: {'water_type': 'sea', 'size': 'large', 'wind_factor': 1.1},     # 住之江
            13: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.0},    # 尼崎
            14: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.2},    # 鳴門
            15: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.1},    # 丸亀
            16: {'water_type': 'sea', 'size': 'large', 'wind_factor': 1.3},     # 児島
            17: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.0},    # 宮島
            18: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.1},    # 徳山
            19: {'water_type': 'sea', 'size': 'large', 'wind_factor': 1.2},     # 下関
            20: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.1},    # 若松
            21: {'water_type': 'sea', 'size': 'small', 'wind_factor': 1.0},     # 芦屋
            22: {'water_type': 'river', 'size': 'large', 'wind_factor': 1.1},   # 福岡
            23: {'water_type': 'sea', 'size': 'medium', 'wind_factor': 1.2},    # 唐津
            24: {'water_type': 'sea', 'size': 'large', 'wind_factor': 1.0},     # 大村
        }
    
    def create_advanced_features(self, race_data: Dict, racer_data: Dict, venue_id: int, race_number: int) -> Dict:
        """高度特徴量の作成"""
        features = {}
        
        # 1. 時系列特徴量
        features.update(self._create_temporal_features(racer_data, venue_id))
        
        # 2. 会場適性特徴量
        features.update(self._create_venue_compatibility_features(racer_data, venue_id))
        
        # 3. 気象条件組み合わせ特徴量
        features.update(self._create_weather_interaction_features(race_data, venue_id))
        
        # 4. レーサー調子指標
        features.update(self._create_momentum_features(racer_data, venue_id))
        
        # 5. 対戦相手との相性
        features.update(self._create_matchup_features(racer_data, race_data))
        
        # 6. レース条件特徴量
        features.update(self._create_race_context_features(race_data, race_number))
        
        return features
    
    def _create_temporal_features(self, racer_data: Dict, venue_id: int) -> Dict:
        """時系列特徴量"""
        features = {}
        
        try:
            # 過去7日間の成績トレンド
            recent_races = self._get_recent_race_history(racer_data.get('racer_id', 0), days=7)
            
            if recent_races:
                features['recent_win_trend'] = np.mean([r.get('is_win', 0) for r in recent_races])
                features['recent_place_trend'] = np.mean([r.get('is_place', 0) for r in recent_races])
                features['recent_race_count'] = len(recent_races)
                
                # 成績の分散（安定性指標）
                win_variance = np.var([r.get('is_win', 0) for r in recent_races]) if len(recent_races) > 1 else 0
                features['performance_stability'] = 1 / (1 + win_variance)
            else:
                features['recent_win_trend'] = 0.16  # デフォルト値
                features['recent_place_trend'] = 0.33
                features['recent_race_count'] = 0
                features['performance_stability'] = 0.5
            
            # 週末効果
            now = datetime.now()
            features['is_weekend'] = 1 if now.weekday() >= 5 else 0
            features['day_of_week_sin'] = np.sin(2 * np.pi * now.weekday() / 7)
            features['day_of_week_cos'] = np.cos(2 * np.pi * now.weekday() / 7)
            
        except Exception as e:
            logger.warning(f"時系列特徴量作成エラー: {e}")
            features.update({
                'recent_win_trend': 0.16, 'recent_place_trend': 0.33,
                'recent_race_count': 0, 'performance_stability': 0.5,
                'is_weekend': 0, 'day_of_week_sin': 0, 'day_of_week_cos': 0
            })
        
        return features
    
    def _create_venue_compatibility_features(self, racer_data: Dict, venue_id: int) -> Dict:
        """会場適性特徴量"""
        features = {}
        
        try:
            venue_chars = self.venue_characteristics.get(venue_id, {})
            
            # 会場タイプエンコーディング
            water_type = venue_chars.get('water_type', 'sea')
            features['is_river_venue'] = 1 if water_type == 'river' else 0
            features['is_lake_venue'] = 1 if water_type == 'lake' else 0
            features['is_sea_venue'] = 1 if water_type == 'sea' else 0
            
            # 会場サイズエンコーディング
            size = venue_chars.get('size', 'medium')
            features['is_small_venue'] = 1 if size == 'small' else 0
            features['is_large_venue'] = 1 if size == 'large' else 0
            
            # 会場特性とレーサー特性の相性
            racer_national = racer_data.get('racer_national_top_1_percent', 50) / 100
            racer_local = racer_data.get('racer_local_top_1_percent', 50) / 100
            
            # 当地成績との適性度
            features['venue_compatibility'] = racer_local / max(racer_national, 0.01)
            features['venue_experience_advantage'] = min(racer_local - racer_national + 0.5, 1.0)
            
        except Exception as e:
            logger.warning(f"会場適性特徴量作成エラー: {e}")
            features.update({
                'is_river_venue': 0, 'is_lake_venue': 0, 'is_sea_venue': 1,
                'is_small_venue': 0, 'is_large_venue': 0,
                'venue_compatibility': 1.0, 'venue_experience_advantage': 0.5
            })
        
        return features
    
    def _create_weather_interaction_features(self, race_data: Dict, venue_id: int) -> Dict:
        """気象条件組み合わせ特徴量"""
        features = {}
        
        try:
            wind_speed = race_data.get('race_wind', 0)
            wave_height = race_data.get('race_wave', 0)
            temperature = race_data.get('race_temperature', 20)
            venue_chars = self.venue_characteristics.get(venue_id, {})
            wind_factor = venue_chars.get('wind_factor', 1.0)
            
            # 風の影響度（会場特性考慮）
            features['adjusted_wind_impact'] = wind_speed * wind_factor
            features['wind_wave_interaction'] = wind_speed * wave_height
            features['weather_difficulty'] = (wind_speed + wave_height) / 2
            
            # 気温による影響
            features['temperature_normalized'] = (temperature - 20) / 20  # 20度を基準に正規化
            features['is_extreme_weather'] = 1 if (wind_speed > 5 or wave_height > 3 or abs(temperature - 20) > 15) else 0
            
            # 風向きの推定（簡易版）
            hour = datetime.now().hour
            features['estimated_wind_direction'] = np.sin(2 * np.pi * hour / 24)  # 時間による風向き変化
            
        except Exception as e:
            logger.warning(f"気象特徴量作成エラー: {e}")
            features.update({
                'adjusted_wind_impact': 0, 'wind_wave_interaction': 0,
                'weather_difficulty': 0, 'temperature_normalized': 0,
                'is_extreme_weather': 0, 'estimated_wind_direction': 0
            })
        
        return features
    
    def _create_momentum_features(self, racer_data: Dict, venue_id: int) -> Dict:
        """レーサー調子指標"""
        features = {}
        
        try:
            # 直近の成績から調子を判定
            racer_id = racer_data.get('racer_id', 0)
            recent_results = self._get_recent_race_history(racer_id, days=14)
            
            if recent_results and len(recent_results) >= 3:
                # 直近3レース vs その前の期間の比較
                latest_3 = recent_results[:3]
                older_results = recent_results[3:] if len(recent_results) > 3 else recent_results
                
                latest_avg = np.mean([r.get('finish_position', 6) for r in latest_3])
                older_avg = np.mean([r.get('finish_position', 6) for r in older_results])
                
                # 調子の向上度（着順が良くなるほど負の値なので反転）
                features['momentum_trend'] = (older_avg - latest_avg) / 6  # -1~1に正規化
                features['current_form_rating'] = max(0, 1 - latest_avg / 6)  # 0~1
                
                # 連続成績
                win_streak = 0
                place_streak = 0
                for result in latest_3:
                    if result.get('is_win', False):
                        win_streak += 1
                    else:
                        break
                
                for result in latest_3:
                    if result.get('is_place', False):
                        place_streak += 1
                    else:
                        break
                
                features['win_streak'] = min(win_streak, 3)
                features['place_streak'] = min(place_streak, 3)
            else:
                features['momentum_trend'] = 0
                features['current_form_rating'] = 0.5
                features['win_streak'] = 0
                features['place_streak'] = 0
                
        except Exception as e:
            logger.warning(f"調子指標作成エラー: {e}")
            features.update({
                'momentum_trend': 0, 'current_form_rating': 0.5,
                'win_streak': 0, 'place_streak': 0
            })
        
        return features
    
    def _create_matchup_features(self, racer_data: Dict, race_data: Dict) -> Dict:
        """対戦相手との相性特徴量"""
        features = {}
        
        try:
            # 対戦相手の平均成績
            opponents_data = race_data.get('racers', [])
            current_racer_id = racer_data.get('racer_id', 0)
            
            opponent_ratings = []
            for opponent in opponents_data:
                if opponent.get('racer_id', 0) != current_racer_id:
                    national_rate = opponent.get('racer_national_top_1_percent', 50) / 100
                    opponent_ratings.append(national_rate)
            
            if opponent_ratings:
                features['opponent_avg_rating'] = np.mean(opponent_ratings)
                features['opponent_strength_variance'] = np.var(opponent_ratings)
                features['relative_strength'] = (racer_data.get('racer_national_top_1_percent', 50) / 100) / max(np.mean(opponent_ratings), 0.01)
            else:
                features['opponent_avg_rating'] = 0.5
                features['opponent_strength_variance'] = 0
                features['relative_strength'] = 1.0
                
        except Exception as e:
            logger.warning(f"相性特徴量作成エラー: {e}")
            features.update({
                'opponent_avg_rating': 0.5,
                'opponent_strength_variance': 0,
                'relative_strength': 1.0
            })
        
        return features
    
    def _create_race_context_features(self, race_data: Dict, race_number: int) -> Dict:
        """レース条件特徴量"""
        features = {}
        
        try:
            # レース番号の影響
            features['race_number_normalized'] = race_number / 12  # 1~12Rを0~1に正規化
            features['is_first_race'] = 1 if race_number == 1 else 0
            features['is_final_race'] = 1 if race_number == 12 else 0
            features['is_prime_time'] = 1 if 6 <= race_number <= 10 else 0  # メインレース時間帯
            
            # 距離の影響
            distance = race_data.get('race_distance', 1400)
            features['distance_normalized'] = (distance - 1200) / 600  # 1200-1800mを0-1に正規化
            features['is_short_distance'] = 1 if distance <= 1400 else 0
            features['is_long_distance'] = 1 if distance >= 1600 else 0
            
            # 時間帯の影響
            hour = datetime.now().hour
            features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
            features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
            features['is_morning_race'] = 1 if 8 <= hour <= 11 else 0
            features['is_afternoon_race'] = 1 if 12 <= hour <= 16 else 0
            features['is_evening_race'] = 1 if 17 <= hour <= 20 else 0
            
        except Exception as e:
            logger.warning(f"レース条件特徴量作成エラー: {e}")
            features.update({
                'race_number_normalized': race_number / 12,
                'is_first_race': 0, 'is_final_race': 0, 'is_prime_time': 0,
                'distance_normalized': 0.33, 'is_short_distance': 1, 'is_long_distance': 0,
                'hour_sin': 0, 'hour_cos': 1, 'is_morning_race': 0,
                'is_afternoon_race': 1, 'is_evening_race': 0
            })
        
        return features
    
    def _get_recent_race_history(self, racer_id: int, days: int = 7) -> List[Dict]:
        """直近の成績履歴を取得（ダミーデータ）"""
        try:
            # 実際の実装では accuracy_tracker.db から取得
            # ここではダミーデータを生成
            np.random.seed(racer_id + days)  # 再現性のため
            
            race_count = np.random.randint(0, days // 2 + 1)  # 0~days/2レース
            results = []
            
            for i in range(race_count):
                finish_pos = np.random.choice([1, 2, 3, 4, 5, 6], p=[0.16, 0.16, 0.16, 0.16, 0.16, 0.20])
                results.append({
                    'finish_position': finish_pos,
                    'is_win': finish_pos == 1,
                    'is_place': finish_pos <= 3,
                    'race_date': (datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"成績履歴取得エラー: {e}")
            return []

if __name__ == "__main__":
    # テスト実行
    engineer = AdvancedFeatureEngineer()
    
    test_race_data = {
        'race_wind': 2, 'race_wave': 1, 'race_temperature': 25,
        'race_distance': 1400, 'racers': []
    }
    test_racer_data = {
        'racer_id': 1234, 'racer_national_top_1_percent': 45,
        'racer_local_top_1_percent': 52
    }
    
    features = engineer.create_advanced_features(test_race_data, test_racer_data, 12, 6)
    print(f"生成特徴量数: {len(features)}")
    print("主要特徴量:", {k: f"{v:.3f}" if isinstance(v, float) else v for k, v in list(features.items())[:10]})