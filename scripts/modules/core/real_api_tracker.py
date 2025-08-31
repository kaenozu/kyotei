#!/usr/bin/env python3
"""
実際のAPIデータを使用する的中率追跡システム
ダミーデータを一切使用せず、BoatraceOpenAPIから実データを取得
"""

import requests
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class RealAPITracker:
    """実際のAPI取得による的中率追跡システム"""
    
    def __init__(self):
        self.db_path = 'cache/accuracy_tracker.db'
        self.api_base_url = 'https://boatraceopenapi.github.io'
        self.venue_mapping = self._get_venue_mapping()  # 属性として追加
        self._ensure_database()
    
    def _get_venue_mapping(self) -> Dict[int, str]:
        """会場IDと会場名のマッピング"""
        return {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
        
    def _ensure_database(self):
        """データベースの初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 予想データテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS race_details (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venue_id INTEGER,
                        race_number INTEGER,
                        race_date TEXT,
                        prediction_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(venue_id, race_number, race_date)
                    )
                ''')
                
                # 結果データテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS race_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venue_id INTEGER,
                        race_number INTEGER,
                        race_date TEXT,
                        venue_name TEXT,
                        winning_boat INTEGER,
                        place_results TEXT,
                        trifecta_result TEXT,
                        result_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(venue_id, race_number, race_date)
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
    
    def get_today_races(self) -> List[Dict]:
        """今日開催中の全レースを取得"""
        try:
            # 今日のレースデータを取得
            today_url = f"{self.api_base_url}/programs/v2/today.json"
            response = requests.get(today_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                races = data.get('programs', [])
                logger.info(f"今日のレースデータ取得成功: {len(races)}レース")
                return races
            else:
                logger.error(f"APIエラー: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"今日のレース取得エラー: {e}")
            return []
    
    def get_race_results(self, venue_id: int, race_number: int, date: str = None) -> Dict:
        """指定レースの結果を取得"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # データベースから結果を確認
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT venue_id, race_number, race_date, winning_boat, 
                           place_results, venue_name
                    FROM race_results
                    WHERE venue_id = ? AND race_number = ? AND race_date = ?
                ''', (venue_id, race_number, date))
                
                row = cursor.fetchone()
                if row:
                    venue_id, race_number, race_date, winning_boat, place_results, venue_name = row
                    try:
                        place_list = json.loads(place_results) if place_results else []
                    except:
                        place_list = []
                    
                    return {
                        'venue_id': venue_id,
                        'venue_name': venue_name,
                        'race_number': race_number,
                        'race_date': race_date,
                        'winning_boat': winning_boat,
                        'place_results': place_list,
                        'status': 'found'
                    }
            
            # データベースにない場合、APIから過去の結果を取得
            api_result = self._get_race_result_from_api(venue_id, race_number, date)
            if api_result and api_result.get('status') == 'found':
                return api_result
            
            return {
                'venue_id': venue_id,
                'race_number': race_number,
                'race_date': date,
                'winning_boat': None,
                'place_results': [],
                'status': 'not_found'
            }
            
        except Exception as e:
            logger.error(f"レース結果取得エラー: {e}")
            return {
                'venue_id': venue_id,
                'race_number': race_number,
                'race_date': date,
                'winning_boat': None,
                'place_results': [],
                'status': 'error',
                'error': str(e)
            }
    
    def calculate_accuracy(self, date: str = None) -> Dict:
        """指定日の的中率を計算（実際のデータベースから）"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"的中率計算（DB使用）: {date}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 指定日の予想データを取得
                cursor.execute('''
                    SELECT p.id, p.race_date, p.venue_id, p.venue_name, p.race_number,
                           p.predicted_win, p.predicted_place, p.confidence, p.prediction_data,
                           r.actual_results, r.is_hit, r.is_place_hit, r.is_trifecta_hit
                    FROM predictions p
                    LEFT JOIN results r ON p.venue_id = r.venue_id 
                                       AND p.race_number = r.race_number 
                                       AND p.race_date = r.date_str
                    WHERE p.race_date = ?
                    ORDER BY p.venue_id, p.race_number
                ''', (date,))
                
                prediction_data = cursor.fetchall()
                
                if not prediction_data:
                    logger.warning(f"指定日の予想データが見つかりません: {date}")
                    return self._empty_accuracy_data(date)
                
                # データの処理
                races = []
                total_predictions = len(prediction_data)
                completed_races = 0
                win_hits = 0
                place_hits = 0
                trifecta_hits = 0
                
                for row in prediction_data:
                    (pred_id, race_date, venue_id, venue_name, race_number,
                     predicted_win, predicted_place_str, confidence, prediction_data_json,
                     actual_results, is_hit, is_place_hit, is_trifecta_hit) = row
                    
                    # 予想データをパース
                    try:
                        predicted_place = json.loads(predicted_place_str) if predicted_place_str else []
                    except:
                        predicted_place = []
                    
                    # 結果があるかチェック
                    has_result = actual_results is not None
                    if has_result:
                        completed_races += 1
                        if is_hit:
                            win_hits += 1
                        if is_place_hit:
                            place_hits += 1
                        if is_trifecta_hit:
                            trifecta_hits += 1
                    
                    # ヒット状況の表示
                    if has_result:
                        if is_hit:
                            hit_status = '◯'
                        elif is_place_hit:
                            hit_status = '△'  
                        else:
                            hit_status = '×'
                    else:
                        hit_status = '待'
                    
                    # 実際の結果をパース
                    actual_results_list = []
                    if actual_results:
                        try:
                            actual_results_list = json.loads(actual_results) if isinstance(actual_results, str) else actual_results
                        except:
                            actual_results_list = []
                
                    # レース情報の構築
                    race_info = {
                        'venue_id': venue_id,
                        'venue_name': venue_name,
                        'race_number': race_number,
                        'race_date': race_date,
                        'start_time': '未定',  # 時間データが不足している場合
                        'race_title': f'第{race_number}レース',
                        'confidence': confidence or 0.5,
                        'prediction': {
                            'predicted_win': predicted_win,
                            'predicted_place': predicted_place,
                            'confidence': confidence or 0.5
                        },
                        'result': actual_results_list if has_result else None,
                        'is_win_hit': is_hit,
                        'is_place_hit': is_place_hit,  
                        'is_trifecta_hit': is_trifecta_hit,
                        'has_result': has_result,
                        'status': 'completed' if has_result else 'pending',
                        'predicted_win': predicted_win,
                        'predicted_place': predicted_place,
                        'winning_boat': actual_results_list[0] if actual_results_list else None,
                        'place_results': actual_results_list[:3] if actual_results_list else None,
                        'hit_status': hit_status
                    }
                    races.append(race_info)
                
                # 統計計算
                win_accuracy = (win_hits / completed_races * 100) if completed_races > 0 else 0
                place_accuracy = (place_hits / completed_races * 100) if completed_races > 0 else 0
                trifecta_accuracy = (trifecta_hits / completed_races * 100) if completed_races > 0 else 0
                
                logger.info(f"的中率計算完了（DB使用）: {date} - 予想{total_predictions}件（完了{completed_races}件）, 単勝:{win_accuracy:.1f}%, 複勝:{place_accuracy:.1f}%")
                
                return {
                    'summary': {
                        'total_predictions': total_predictions,
                        'completed_races': completed_races,
                        'pending_races': total_predictions - completed_races,
                        'win_hits': win_hits,
                        'win_accuracy': round(win_accuracy, 1),
                        'place_hits': place_hits,
                        'place_accuracy': round(place_accuracy, 1),
                        'trifecta_hits': trifecta_hits,
                        'trifecta_accuracy': round(trifecta_accuracy, 1),
                        'completion_rate': round((completed_races / total_predictions * 100), 1) if total_predictions > 0 else 0
                    },
                    'races': races,
                    'venues': self.venue_mapping
                }
            
        except Exception as e:
            logger.error(f"的中率計算エラー: {e}")
            return self._empty_accuracy_data(date)
    
    def _generate_real_prediction(self, race_data: Dict) -> Optional[Dict]:
        """実際のAPIデータに基づく予想アルゴリズム"""
        try:
            # APIから実際のレーサーデータ、ボートデータが含まれているかチェック
            if not race_data or not race_data.get('boats'):
                logger.debug("レースデータが不足しているため予想をスキップします")
                return None
            
            boats = race_data.get('boats', [])
            if len(boats) < 6:  # 競艇は6艇
                logger.debug("レーサーデータが不完全のため予想をスキップします")
                return None
            
            venue_id = race_data.get('race_stadium_number')
            if not venue_id:
                logger.debug("会場データが不足しているため予想をスキップします")
                return None
            
            # 実際のAPIデータに基づく予想計算
            boat_scores = []
            
            for boat in boats:
                boat_number = boat.get('racer_boat_number', 0)
                if boat_number == 0:
                    continue
                
                # 各要素のスコア計算
                score = self._calculate_boat_score(boat)
                boat_scores.append({
                    'boat_number': boat_number,
                    'score': score,
                    'boat_data': boat
                })
            
            if len(boat_scores) < 6:
                logger.debug("有効な艇データが不足しているため予想をスキップします")
                return None
            
            # スコア順にソート
            boat_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # 予想結果を生成
            predicted_win = boat_scores[0]['boat_number']
            predicted_place = [boat['boat_number'] for boat in boat_scores[:3]]
            # 1位と2位のスコア差に基づく信頼度計算
            max_score = boat_scores[0]['score']
            second_score = boat_scores[1]['score'] if len(boat_scores) > 1 else 0.0
            confidence = min(0.95, max(0.05, (((max_score - second_score) / max_score if max_score > 0 else 0.0) * 0.9 + 0.05)))
            
            logger.info(f"予想完了: 単勝={predicted_win}号艇, 複勝={predicted_place}, 信頼度={confidence:.2%}")
            
            # テンプレート用のレーサーデータを生成
            racers = []
            for boat_score in boat_scores:
                boat_data = boat_score['boat_data']
                racers.append({
                    'boat_number': boat_score['boat_number'],
                    'name': boat_data.get('racer_name', f"{boat_score['boat_number']}号艇"),
                    'racer_name': boat_data.get('racer_name', f"{boat_score['boat_number']}号艇"),
                    'prediction_score': boat_score['score'] / max_score if max_score > 0 else 0.0,  # 0-1の範囲に正規化
                    'win_rate': boat_data.get('racer_national_top_1_percent', 0),
                    'local_win_rate': boat_data.get('racer_local_top_1_percent', 0),
                    'place_rate': boat_data.get('racer_national_top_3_percent', 0),
                    'average_st': boat_data.get('racer_average_start_timing', 0.17),
                    'stats': {},
                    'analysis': {
                        'base_strength': boat_data.get('racer_national_top_1_percent', 0) / 100.0,
                        'local_adaptation': boat_data.get('racer_local_top_1_percent', 0) / 100.0,
                        'lane_advantage': 0.1 + (7-boat_score['boat_number']) * 0.02,
                        'st_factor': 1.0 + boat_data.get('racer_average_start_timing', 0.17)
                    }
                })
            
            return {
                'predicted_win': predicted_win,
                'predicted_place': predicted_place,
                'recommended_win': str(predicted_win),
                'recommended_place': predicted_place,
                'confidence': confidence,
                'racers': racers,
                'predictions': {
                    'win': str(predicted_win),
                    'place': predicted_place,
                    'trifecta': predicted_place
                },
                'betting_recommendations': {
                    'win': f'{predicted_win}号艇単勝推奨',
                    'place': f'複勝推奨: {"-".join(map(str, predicted_place[:3]))}',
                    'primary': {
                        'icon': '🎯',
                        'risk_level': f'信頼度{confidence:.0%}',
                        'strategy': f'{predicted_win}号艇単勝'
                    },
                    'risk_based': [
                        {
                            'level': '推奨',
                            'bet': f'{predicted_win}号艇単勝',
                            'amount': 500,
                            'boats': [predicted_win],
                            'type': '単勝',
                            'confidence': confidence
                        }
                    ],
                    'trifecta_combos': [
                        {'combo': '-'.join(map(str, predicted_place[:3])), 'amount': 300}
                    ],
                    'budget_allocation': {
                        'win': 500,
                        'place': 300,
                        'trifecta': 200
                    }
                },
                'race_status': 'active',
                'display_mode': 'prediction'
            }
            
        except Exception as e:
            logger.error(f"予想計算エラー: {e}")
            return None
    
    def _calculate_boat_score(self, boat_data: Dict) -> float:
        """艇別総合スコア計算（実際のAPIデータベース）"""
        try:
            total_score = 0.0
            
            # 1. 全国勝率 (重み: 18%)
            national_win_rate = boat_data.get('racer_national_top_1_percent', 0)
            if national_win_rate:
                total_score += national_win_rate * 0.18
            
            # 2. 当地勝率 (重み: 12%) 
            local_win_rate = boat_data.get('racer_local_top_1_percent', 0)
            if local_win_rate:
                total_score += local_win_rate * 0.12
            
            # 3. モーター性能 (重み: 12%)
            motor_performance = boat_data.get('racer_assigned_motor_top_2_percent', 0)
            if motor_performance:
                total_score += motor_performance * 0.12
            
            # 4. ボート性能 (重み: 8%)
            boat_performance = boat_data.get('racer_assigned_boat_top_2_percent', 0)
            if boat_performance:
                total_score += boat_performance * 0.08
            
            # 5. スタートタイミング (重み: 10%) - 値が小さいほど良い
            start_timing = boat_data.get('racer_average_start_timing', 0.2)
            if start_timing and start_timing > 0:
                # 0.10が理想的なタイミング、0.20以上は減点
                timing_score = max(0, (0.20 - start_timing) * 100)
                total_score += timing_score * 0.10
            
            # 6. レーサークラス (重み: 15%)
            racer_class = boat_data.get('racer_class_number', 4)
            if racer_class:
                # A1=1, A2=2, B1=3, B2=4 - 数字が小さいほど上位クラス
                class_score = max(0, (5 - racer_class) * 6)  # A1=24pt, A2=18pt, B1=12pt, B2=6pt
                total_score += class_score * 0.15
                
            # 7. 年齢・経験値 (重み: 10%)
            age = boat_data.get('racer_age', 35)
            if age:
                # 25-35歳が最も良い、それ以外は減点
                if 25 <= age <= 35:
                    age_score = 15
                elif 20 <= age < 25 or 35 < age <= 45:
                    age_score = 10
                else:
                    age_score = 5
                total_score += age_score * 0.10
            
            # 8. フライング・出遅れ (重み: 8%)
            flying_count = boat_data.get('racer_flying_count', 0)
            late_count = boat_data.get('racer_late_count', 0)
            penalty_score = max(0, 10 - (flying_count * 3 + late_count * 2))
            total_score += penalty_score * 0.08
            
            # 9. 複勝率 (重み: 7%)
            place_rate = boat_data.get('racer_national_top_3_percent', 0)
            if place_rate:
                total_score += place_rate * 0.07
            
            return total_score
            
        except Exception as e:
            logger.error(f"スコア計算エラー: {e}")
            return 0.0
    
    def _get_historical_races(self, date: str) -> List[Dict]:
        """過去の日付のレースデータを取得（APIとデータベースを統合）"""
        try:
            # データベースから予想・結果データを取得
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 予想データを取得（race_detailsテーブルから）
            cursor.execute('''SELECT venue_id, race_number, prediction_data
                             FROM race_details 
                             WHERE race_date = ? 
                             ORDER BY venue_id, race_number''', (date,))
            predictions = cursor.fetchall()
            
            # 結果データを取得（race_resultsテーブルから）
            cursor.execute('''SELECT venue_id, race_number, winning_boat, place_results, trifecta_result
                             FROM race_results 
                             WHERE race_date = ? 
                             ORDER BY venue_id, race_number''', (date,))
            results = cursor.fetchall()
            
            conn.close()
            
            # データベースデータから直接レース一覧を構築
            races = []
            venue_mapping = self._get_venue_mapping()
            
            # 予想データをベースにレース一覧を作成
            for pred in predictions:
                venue_id = pred[0]
                race_number = pred[1]
                
                race_info = {
                    'race_stadium_number': venue_id,
                    'venue_name': venue_mapping.get(venue_id, f'会場{venue_id}'),
                    'race_number': race_number,
                    'race_date': date,
                    'race_title': f'第{race_number}レース',
                    'start_time': '不明',
                    'confidence': 0.0,
                    'has_api_data': False  # 過去データなのでAPIデータなし
                }
                
                # 現在のprediction（pred）から予想データを解析
                prediction = None
                try:
                    prediction_json = json.loads(pred[2]) if pred[2] else {}
                    prediction = {
                        'predicted_win': prediction_json.get('recommended_win'),
                        'predicted_place': prediction_json.get('recommended_place', []),
                        'confidence': prediction_json.get('confidence', 0.0)
                    }
                    race_info['confidence'] = prediction_json.get('confidence', 0.0)
                except (json.JSONDecodeError, IndexError):
                    logger.warning(f"予想データ解析失敗: {pred}")
                    prediction = {
                        'predicted_win': None,
                        'predicted_place': [],
                        'confidence': 0.0,
                        'is_historical': True
                    }
                
                
                race_info['prediction'] = prediction
                
                # 結果データを追加（race_resultsテーブルから）
                result = None
                for res in results:
                    if res[0] == venue_id and res[1] == race_number:
                        winning_boat = res[2]
                        place_results = json.loads(res[3]) if res[3] else []
                        trifecta_result = res[4]
                        
                        result = {
                            'venue_id': venue_id,
                            'venue_name': venue_mapping.get(venue_id, f'会場{venue_id}'),
                            'race_number': race_number,
                            'race_date': date,
                            'winning_boat': winning_boat,
                            'place_results': place_results,
                            'trifecta_result': trifecta_result,
                            'status': 'found'
                        }
                        
                        # 的中判定
                        if prediction and prediction.get('predicted_win'):
                            race_info['is_win_hit'] = (str(winning_boat) == str(prediction['predicted_win']))
                            race_info['is_place_hit'] = str(winning_boat) in [str(p) for p in prediction.get('predicted_place', [])]
                        else:
                            race_info['is_win_hit'] = False
                            race_info['is_place_hit'] = False
                        
                        race_info['is_trifecta_hit'] = False  # 三連単判定は複雑なので一旦False
                        race_info['has_result'] = True
                        race_info['status'] = 'completed'
                        break
                
                if not result:
                    # 結果データがない場合
                    result = {
                        'venue_id': venue_id,
                        'venue_name': venue_mapping.get(venue_id, f'会場{venue_id}'),
                        'race_number': race_number,
                        'race_date': date,
                        'winning_boat': None,
                        'place_results': [],
                        'status': 'no_result'
                    }
                    race_info['is_win_hit'] = False
                    race_info['is_place_hit'] = False
                    race_info['is_trifecta_hit'] = False
                    race_info['has_result'] = False
                    race_info['status'] = 'pending'
                
                race_info['result'] = result
                
                # テンプレート用の追加情報
                race_info['predicted_win'] = prediction['predicted_win']
                race_info['predicted_place'] = prediction['predicted_place']
                race_info['winning_boat'] = result.get('winning_boat')
                race_info['place_results'] = result.get('place_results', [])
                race_info['hit_status'] = '○' if race_info.get('is_win_hit') else '×'
                
                races.append(race_info)
            
            races.sort(key=lambda x: (x['race_stadium_number'], x['race_number']))
            
            logger.info(f"過去のレース統合取得成功: {date} ({len(races)}レース)")
            return races
            
        except Exception as e:
            logger.error(f"過去のレースデータ取得エラー: {date} - {e}")
            return []
    
    def _get_api_historical_races(self, date: str) -> List[Dict]:
        """APIから過去のレース情報を取得"""
        try:
            # 日付をYYYYMMDD形式に変換
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_str = date_obj.strftime('%Y%m%d')
            
            # 過去のレースデータを取得
            programs_url = f"{self.api_base_url}/programs/v2/{date_str}.json"
            response = requests.get(programs_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                programs = data.get('programs', [])
                logger.info(f"API過去レース取得成功: {date} ({len(programs)}レース)")
                return programs
            elif response.status_code == 404:
                logger.info(f"API過去レースなし: {date} (開催なし)")
                return []
            else:
                logger.warning(f"API過去レース取得失敗: {date} (HTTP {response.status_code})")
                return []
                
        except Exception as e:
            logger.error(f"API過去レース取得エラー: {date} - {e}")
            return []
    
    def _get_race_result_from_api(self, venue_id: int, race_number: int, date: str) -> Dict:
        """APIから過去のレース結果を取得"""
        try:
            # 日付をYYYYMMDD形式に変換
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_str = date_obj.strftime('%Y%m%d')
            
            # 過去のレース結果データを取得
            results_url = f"{self.api_base_url}/results/v2/{date_str}.json"
            response = requests.get(results_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # 指定されたレースを検索
                for result in results:
                    if (result.get('race_stadium_number') == venue_id and 
                        result.get('race_number') == race_number):
                        
                        # 結果データを解析
                        winning_boat = None
                        place_results = []
                        
                        # 勝利艇を特定
                        boats = result.get('boats', [])
                        for boat in boats:
                            if boat.get('arrival_order') == 1:
                                winning_boat = boat.get('boat_number')
                                break
                        
                        # 順位結果を構築
                        sorted_boats = sorted(boats, key=lambda x: x.get('arrival_order', 999))
                        place_results = [boat.get('boat_number') for boat in sorted_boats if boat.get('arrival_order')]
                        
                        venue_mapping = self._get_venue_mapping()
                        venue_name = venue_mapping.get(venue_id, f'会場{venue_id}')
                        
                        # データベースに保存
                        self._save_race_result_to_db(
                            venue_id, race_number, date, venue_name,
                            winning_boat, place_results, result
                        )
                        
                        logger.info(f"過去のレース結果取得・保存: {venue_name} {race_number}R {date} - 勝者={winning_boat}号艇")
                        
                        return {
                            'venue_id': venue_id,
                            'venue_name': venue_name,
                            'race_number': race_number,
                            'race_date': date,
                            'winning_boat': winning_boat,
                            'place_results': place_results,
                            'status': 'found'
                        }
                
                logger.info(f"指定レース結果なし: {venue_id}_{race_number} {date}")
                return {'status': 'not_found'}
                
            elif response.status_code == 404:
                logger.info(f"過去のレース結果データなし: {date} (開催なし)")
                return {'status': 'not_found'}
            else:
                logger.warning(f"過去のレース結果取得失敗: {date} (HTTP {response.status_code})")
                return {'status': 'error', 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"過去のレース結果取得エラー: {venue_id}_{race_number} {date} - {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _save_race_result_to_db(self, venue_id: int, race_number: int, date: str, 
                               venue_name: str, winning_boat: int, place_results: List[int], 
                               result_data: Dict):
        """レース結果をデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO race_results 
                    (venue_id, race_number, race_date, venue_name, winning_boat, 
                     place_results, trifecta_result, result_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    venue_id, race_number, date, venue_name, winning_boat,
                    json.dumps(place_results), 
                    json.dumps(place_results[:3]) if len(place_results) >= 3 else json.dumps([]),
                    json.dumps(result_data)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"レース結果保存エラー: {e}")
    
    def _empty_accuracy_data(self, date: str) -> Dict:
        """空のレポートデータ"""
        return {
            'summary': {
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
            },
            'races': [],
            'venues': self._get_venue_mapping()
        }
    
    def _get_venue_mapping(self) -> Dict[int, str]:
        """競艇場マッピング"""
        return {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
    
    def save_race_details(self, race_data: Dict, prediction_data: Dict) -> bool:
        """レース詳細の保存"""
        try:
            venue_id = race_data.get('race_stadium_number')
            race_number = race_data.get('race_number')
            race_date = datetime.now().strftime('%Y-%m-%d')
            
            # 発走時間を抽出（複数の可能なフィールド名から取得）
            start_time = (race_data.get('race_close_time') or 
                         race_data.get('start_time') or 
                         race_data.get('race_time') or 
                         race_data.get('close_time'))
            
            # その他の詳細情報を取得
            venue_name = self.venue_mapping.get(venue_id, f'会場{venue_id}')
            race_title = race_data.get('race_title', f'第{race_number}レース')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO race_details 
                    (race_date, venue_id, venue_name, race_number, start_time, race_title, 
                     race_data, boats_data, prediction_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (race_date, venue_id, venue_name, race_number, start_time, race_title,
                      json.dumps(race_data), json.dumps(race_data.get('boats', [])), 
                      json.dumps(prediction_data), datetime.now().isoformat()))
                conn.commit()
            
            logger.info(f"レース詳細保存: {venue_name} {race_number}R (発走: {start_time})")
            return True
            
        except Exception as e:
            logger.error(f"レース詳細保存エラー: {e}")
            return False
    
    def get_race_details(self, venue_id: int, race_number: int, date: str = None) -> Dict:
        """レース詳細の取得"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 正しいスキーマに基づいてクエリ修正
                cursor.execute('''
                    SELECT venue_id, race_number, race_date, prediction_data, venue_name
                    FROM race_details
                    WHERE venue_id = ? AND race_number = ? AND race_date = ?
                ''', (venue_id, race_number, date))
                
                row = cursor.fetchone()
                if row:
                    venue_id, race_number, race_date, prediction_data, venue_name = row
                    try:
                        prediction = json.loads(prediction_data) if prediction_data else {}
                    except:
                        prediction = {}
                    
                    venue_mapping = self._get_venue_mapping()
                    return {
                        'venue_id': venue_id,
                        'venue_name': venue_mapping.get(venue_id, '不明'),
                        'race_number': race_number,
                        'race_date': race_date,
                        'prediction': prediction,
                        'status': 'found'
                    }
                else:
                    venue_mapping = self._get_venue_mapping()
                    return {
                        'venue_id': venue_id,
                        'venue_name': venue_mapping.get(venue_id, '不明'),
                        'race_number': race_number,
                        'race_date': date,
                        'prediction': {},
                        'status': 'not_found'
                    }
                    
        except Exception as e:
            logger.error(f"レース詳細取得エラー: {e}")
            venue_mapping = self._get_venue_mapping()
            return {
                'venue_id': venue_id,
                'venue_name': venue_mapping.get(venue_id, '不明'),
                'race_number': race_number,
                'race_date': date,
                'prediction': {},
                'status': 'error',
                'error': str(e)
            }
    
    def get_all_races_by_date(self, date_str: str) -> List[Dict]:
        """指定日付のすべてのレースを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT rd.venue_id, rd.race_number, rd.race_title, 
                           rd.start_time, vm.venue_name
                    FROM race_details rd
                    LEFT JOIN (
                        SELECT 1 as venue_id, '桐生' as venue_name UNION ALL
                        SELECT 2, '戸田' UNION ALL SELECT 3, '江戸川' UNION ALL
                        SELECT 4, '平和島' UNION ALL SELECT 5, '多摩川' UNION ALL
                        SELECT 6, '浜名湖' UNION ALL SELECT 7, '蒲郡' UNION ALL
                        SELECT 8, '常滑' UNION ALL SELECT 9, '津' UNION ALL
                        SELECT 10, '三国' UNION ALL SELECT 11, 'びわこ' UNION ALL
                        SELECT 12, '住之江' UNION ALL SELECT 13, '尼崎' UNION ALL
                        SELECT 14, '鳴門' UNION ALL SELECT 15, '丸亀' UNION ALL
                        SELECT 16, '児島' UNION ALL SELECT 17, '宮島' UNION ALL
                        SELECT 18, '徳山' UNION ALL SELECT 19, '下関' UNION ALL
                        SELECT 20, '若松' UNION ALL SELECT 21, '芦屋' UNION ALL
                        SELECT 22, '福岡' UNION ALL SELECT 23, '唐津' UNION ALL
                        SELECT 24, '大村'
                    ) vm ON rd.venue_id = vm.venue_id
                    WHERE rd.race_date = ?
                    ORDER BY rd.venue_id, rd.race_number
                """, (date_str,))
                
                races = []
                for row in cursor.fetchall():
                    race = {
                        'venue_id': row[0],
                        'race_number': row[1], 
                        'race_title': row[2] or '',
                        'start_time': row[3],
                        'venue_name': row[4] or f'会場{row[0]}'
                    }
                    races.append(race)
                    
                logger.info(f"指定日付 {date_str} のレース {len(races)} 件を取得")
                return races
                
        except Exception as e:
            logger.error(f"日付別レース取得エラー: {e}")
            return []