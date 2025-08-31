#!/usr/bin/env python3
"""
的中率追跡・管理システム（comprehensive_kyotei.db対応版）
予想データと結果データを管理し、的中率を計算・表示する
"""

import sqlite3
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AccuracyTracker:
    """的中率追跡クラス（新スキーマ対応）"""

    def __init__(self):
        self.db_path = 'cache/comprehensive_kyotei.db'
        self.venue_mapping = {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
        logger.info(f"AccuracyTracker DB path: {self.db_path}")

    def get_all_races_by_date(self, date_str: str) -> List[Dict]:
        """指定日付のすべてのレースを取得（comprehensive_kyotei.db対応）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        p.venue_id, p.venue_name, p.race_number, 
                        p.predicted_win, p.predicted_place, p.predicted_trifecta,
                        p.confidence, p.created_at,
                        r.winning_boat, r.second_boat, r.third_boat,
                        ri.start_time, ri.race_title
                    FROM predictions p
                    LEFT JOIN race_results r ON p.race_date = r.race_date 
                                             AND p.venue_id = r.venue_id 
                                             AND p.race_number = r.race_number
                    LEFT JOIN race_info ri ON p.race_date = ri.race_date 
                                            AND p.venue_id = ri.venue_id 
                                            AND p.race_number = ri.race_number
                    WHERE p.race_date = ?
                    ORDER BY p.venue_id, p.race_number
                ''', (date_str,))
                
                races = []
                for row in cursor.fetchall():
                    venue_id, venue_name, race_number, predicted_win, predicted_place, predicted_trifecta, confidence, created_at, winning_boat, second_boat, third_boat, start_time, race_title = row
                    
                    # 予想データを整理
                    predicted_place_list = []
                    if predicted_place:
                        try:
                            predicted_place_list = list(map(int, predicted_place.split(',')))
                        except:
                            predicted_place_list = [predicted_win] if predicted_win else []
                    
                    predicted_trifecta_list = []
                    if predicted_trifecta:
                        try:
                            predicted_trifecta_list = list(map(int, predicted_trifecta.split(',')))
                        except:
                            predicted_trifecta_list = predicted_place_list[:3] if len(predicted_place_list) >= 3 else []
                    
                    # 結果データを整理
                    actual_results = []
                    has_result = winning_boat is not None
                    if has_result:
                        actual_results = [winning_boat, second_boat, third_boat]
                    
                    # 的中判定
                    is_win_hit = 0
                    is_place_hit = 0
                    is_trifecta_hit = 0
                    
                    if has_result and predicted_win:
                        # 単勝判定
                        is_win_hit = 1 if predicted_win == winning_boat else 0
                        
                        # 複勝判定（1-3位内）
                        is_place_hit = 1 if predicted_win in actual_results else 0
                        
                        # 三連単判定
                        if len(predicted_trifecta_list) >= 3:
                            is_trifecta_hit = 1 if predicted_trifecta_list == actual_results else 0
                    
                    # ステータス判定
                    status = 'completed' if has_result else 'pending'
                    hit_status = '○' if has_result and (is_win_hit or is_place_hit) else '×' if has_result else '待'
                    
                    race_data = {
                        'venue_id': venue_id,
                        'venue_name': venue_name or self.venue_mapping.get(venue_id, '不明'),
                        'race_number': race_number,
                        'race_date': date_str,
                        'start_time': start_time if start_time and start_time != '未定' else '不明',
                        'race_title': race_title or f'第{race_number}レース',
                        'confidence': confidence or 0.5,
                        'prediction': {
                            'predicted_win': predicted_win,
                            'predicted_place': predicted_place_list,
                            'confidence': confidence or 0.5
                        },
                        'result': actual_results if has_result else None,
                        'is_win_hit': is_win_hit,
                        'is_place_hit': is_place_hit,
                        'is_trifecta_hit': is_trifecta_hit,
                        'has_result': has_result,
                        'status': status,
                        'predicted_win': predicted_win,
                        'predicted_place': predicted_place_list,
                        'winning_boat': winning_boat,
                        'place_results': actual_results if has_result else None,
                        'hit_status': hit_status
                    }
                    
                    races.append(race_data)
                
                logger.debug(f'{date_str}のrace_list長さ={len(races)}, 最初のレース={races[0] if races else "なし"}')
                return races
                
        except Exception as e:
            logger.error(f"レース一覧取得エラー ({date_str}): {e}")
            return []

    def calculate_accuracy(self, target_date: Optional[str] = None, date_range_days: int = 1) -> Dict[str, Any]:
        """的中率を計算（comprehensive_kyotei.db対応）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 日付条件
                if target_date:
                    date_condition = "AND p.race_date = ?"
                    date_params = (target_date,)
                else:
                    date_condition = ""
                    date_params = ()
                
                # 基本統計を取得
                query = f'''
                    SELECT 
                        COUNT(*) as total_predictions,
                        COUNT(CASE WHEN p.predicted_win = r.winning_boat THEN 1 END) as win_hits,
                        COUNT(CASE WHEN p.predicted_win IN (r.winning_boat, r.second_boat, r.third_boat) THEN 1 END) as place_hits,
                        COUNT(CASE WHEN p.predicted_trifecta = (r.winning_boat || ',' || r.second_boat || ',' || r.third_boat) THEN 1 END) as trifecta_hits,
                        COUNT(r.race_date) as completed_races
                    FROM predictions p
                    LEFT JOIN race_results r ON p.race_date = r.race_date 
                                             AND p.venue_id = r.venue_id 
                                             AND p.race_number = r.race_number
                    WHERE 1=1 {date_condition}
                '''
                
                cursor.execute(query, date_params)
                stats = cursor.fetchone()
                
                if not stats:
                    return {
                        'total_predictions': 0,
                        'completed_races': 0,
                        'pending_races': 0,
                        'win_hits': 0,
                        'win_accuracy': 0.0,
                        'place_hits': 0,
                        'place_accuracy': 0.0,
                        'trifecta_hits': 0,
                        'trifecta_accuracy': 0.0,
                        'completion_rate': 0.0
                    }
                
                total_predictions, win_hits, place_hits, trifecta_hits, completed_races = stats
                pending_races = total_predictions - completed_races
                
                # 的中率計算
                win_accuracy = (win_hits / total_predictions * 100) if total_predictions > 0 else 0
                place_accuracy = (place_hits / total_predictions * 100) if total_predictions > 0 else 0
                trifecta_accuracy = (trifecta_hits / total_predictions * 100) if total_predictions > 0 else 0
                completion_rate = (completed_races / total_predictions * 100) if total_predictions > 0 else 0
                
                summary = {
                    'total_predictions': total_predictions,
                    'completed_races': completed_races,
                    'pending_races': pending_races,
                    'win_hits': win_hits,
                    'win_accuracy': round(win_accuracy, 1),
                    'place_hits': place_hits,
                    'place_accuracy': round(place_accuracy, 1),
                    'trifecta_hits': trifecta_hits,
                    'trifecta_accuracy': round(trifecta_accuracy, 1),
                    'completion_rate': round(completion_rate, 1)
                }
                
                logger.info(f"的中率計算完了(DB使用): {target_date} - 予想{total_predictions}件(結果{completed_races}件), 単勝:{win_accuracy:.1f}%, 複勝:{place_accuracy:.1f}%")
                logger.info(f"calculate_accuracy完了: summary={summary}")
                return summary
                
        except Exception as e:
            logger.error(f"的中率計算エラー: {e}")
            return {
                'total_predictions': 0,
                'completed_races': 0,
                'pending_races': 0,
                'win_hits': 0,
                'win_accuracy': 0.0,
                'place_hits': 0,
                'place_accuracy': 0.0,
                'trifecta_hits': 0,
                'trifecta_accuracy': 0.0,
                'completion_rate': 0.0
            }

    def get_race_details(self, venue_id: int, race_number: int, race_date: Optional[str] = None) -> Optional[Dict]:
        """レース詳細を取得（簡略化版）"""
        if race_date is None:
            race_date = datetime.now().strftime('%Y-%m-%d')
        
        races = self.get_all_races_by_date(race_date)
        for race in races:
            if race['venue_id'] == venue_id and race['race_number'] == race_number:
                return race
        return None

    def get_race_results(self, venue_id: int, race_number: int, race_date: Optional[str] = None) -> Optional[Dict]:
        """レース結果を取得"""
        race_detail = self.get_race_details(venue_id, race_number, race_date)
        if race_detail and race_detail['has_result']:
            return {
                'winning_boat': race_detail['winning_boat'],
                'place_results': race_detail['place_results'],
                'result_data': {},
                'has_results': True
            }
        return None

    def save_prediction(self, venue_id: int, race_number: int, prediction_data: Dict, race_date: Optional[str] = None):
        """予想データ保存（ダミー実装）"""
        pass

    def save_race_details(self, venue_id: int, race_number: int, race_details: Dict, race_date: Optional[str] = None):
        """レース詳細保存（ダミー実装）"""
        pass

    def _generate_real_prediction(self, venue_id: int, race_number: int, race_data: Optional[Dict] = None, race_date: Optional[str] = None) -> Optional[Dict]:
        """実際のレーサーデータを使用した予想生成"""
        try:
            # race_dateが指定されていない場合は今日の日付を使用
            if race_date is None:
                race_date = datetime.now().strftime('%Y-%m-%d')
            
            # データベースから実際のレーサーデータを取得
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT boat_number, racer_name, racer_age, racer_weight,
                           nationwide_win_rate, nationwide_place_rate, 
                           local_win_rate, local_place_rate,
                           motor_win_rate, motor_place_rate,
                           boat_win_rate, boat_place_rate,
                           start_timing
                    FROM racer_details 
                    WHERE venue_id = ? AND race_number = ? AND race_date = ?
                    ORDER BY boat_number
                ''', (venue_id, race_number, race_date))
                
                racer_rows = cursor.fetchall()
                
                if not racer_rows:
                    logger.warning(f"実際のレーサーデータが見つかりません: {venue_id}_{race_number}")
                    return None
                
                # 各艇の強さを実際のデータで計算
                racers = []
                boat_scores = {}
                
                for row in racer_rows:
                    boat_number, racer_name, age, weight, nat_win, nat_place, local_win, local_place, motor_win, motor_place, boat_win, boat_place, st_timing = row
                    
                    # 競艇理論に基づく予想スコア計算
                    # 全国勝率(25%) + 当地勝率(20%) + モーター(15%) + ボート(10%) + ST(15%) + その他要素(15%)
                    nat_win_score = (nat_win / 100) * 0.25 if nat_win else 0
                    local_win_score = (local_win / 100) * 0.20 if local_win else 0
                    motor_score = (motor_win / 100) * 0.15 if motor_win else 0
                    boat_score = (boat_win / 100) * 0.10 if boat_win else 0
                    
                    # STタイミング（0.15秒以下が優秀）
                    st_score = max(0, (0.20 - st_timing) * 10) * 0.15 if st_timing else 0
                    
                    # 年齢・体重による補正（経験と体重バランス）
                    age_factor = 0.9 if age > 45 else 1.0 if age > 35 else 1.1
                    weight_factor = 1.1 if weight < 50 else 1.0 if weight < 55 else 0.95
                    
                    # 艇番による補正（インコース有利）
                    position_bonus = [0.15, 0.10, 0.05, 0.0, -0.05, -0.10][boat_number - 1]
                    
                    total_score = (nat_win_score + local_win_score + motor_score + boat_score + st_score + position_bonus) * age_factor * weight_factor
                    boat_scores[boat_number] = total_score
                    
                    # 予想スコアを0-1の範囲に正規化（表示用）
                    display_score = min(1.0, max(0.1, total_score))
                    
                    racers.append({
                        'boat_number': boat_number,
                        'racer_name': racer_name,
                        'name': racer_name,  # テンプレート用
                        'age': age,
                        'weight': weight,
                        'prediction_score': display_score,
                        'win_rate': nat_win / 100 if nat_win else 0,
                        'local_win_rate': local_win / 100 if local_win else 0,
                        'place_rate': nat_place / 100 if nat_place else 0,
                        'average_st': st_timing if st_timing else 0.16,
                        'motor_performance': motor_win / 100 if motor_win else 0,
                        'boat_performance': boat_win / 100 if boat_win else 0,
                        'analysis': {
                            'base_strength': nat_win_score,
                            'local_adaptation': local_win_score,
                            'equipment_advantage': motor_score + boat_score,
                            'st_factor': st_score,
                            'position_advantage': position_bonus
                        }
                    })
                
                # スコア順でソート して予想を決定
                sorted_boats = sorted(boat_scores.items(), key=lambda x: x[1], reverse=True)
                predicted_win = sorted_boats[0][0]
                predicted_place = [boat[0] for boat in sorted_boats[:3]]
                
                # 信頼度計算（1位と2位の差が大きいほど信頼度が高い）
                top_score = sorted_boats[0][1]
                second_score = sorted_boats[1][1] if len(sorted_boats) > 1 else 0
                score_gap = top_score - second_score
                confidence = min(0.9, max(0.4, 0.6 + (score_gap * 2)))
                
                # 実際のレーサー名を使用した推奨文言
                winner_name = next(r['racer_name'] for r in racers if r['boat_number'] == predicted_win)
                
                return {
                    'racers': racers,
                    'predictions': {
                        'win': str(predicted_win),
                        'place': predicted_place,
                        'trifecta': predicted_place
                    },
                    'recommended_win': str(predicted_win),
                    'recommended_place': predicted_place,
                    'confidence': confidence,
                    'betting_recommendations': {
                        'win': f'{predicted_win}号艇 {winner_name}推奨',
                        'place': f'複勝: {",".join([f"{p}号艇" for p in predicted_place])}',
                        'primary': {
                            'icon': '🎯',
                            'risk_level': '高信頼' if confidence > 0.7 else '標準',
                            'strategy': f'{predicted_win}号艇 {winner_name} 単勝'
                        },
                        'risk_based': [
                            {
                                'level': '低リスク',
                                'bet': f'複勝 {predicted_place[0]}-{predicted_place[1]}',
                                'amount': 500,
                                'boats': predicted_place[:2],
                                'type': '低リスク',
                                'confidence': confidence * 0.9
                            },
                            {
                                'level': '中リスク',
                                'bet': f'単勝 {predicted_win}号艇',
                                'amount': 300,
                                'boats': [predicted_win],
                                'type': '中リスク',
                                'confidence': confidence
                            }
                        ],
                        'trifecta_combos': [
                            {'combo': f'{predicted_place[0]}-{predicted_place[1]}-{predicted_place[2]}', 'amount': 200}
                        ],
                        'budget_allocation': {
                            'win': 300,
                            'place': 500,
                            'trifecta': 200
                        }
                    },
                    'data_source': 'real_racers',
                    'analysis_note': f'実際のレーサーデータ（{len(racers)}名）を使用した予想です。'
                }
                
        except Exception as e:
            logger.error(f"実際データ予想生成エラー: {e}")
            return None