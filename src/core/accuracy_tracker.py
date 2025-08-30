
# !/usr/bin/env python3
"""
的中率追跡・管理システム
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
    """的中率追跡クラス"""

    def __init__(self):
        self.db_path = 'cache/accuracy_tracker.db'
        self.venue_mapping = {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
        self._init_database()

    def _init_database(self):
        """データベース初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 予想データテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        race_date TEXT NOT NULL,
                        venue_id INTEGER NOT NULL,
                        venue_name TEXT NOT NULL,
                        race_number INTEGER NOT NULL,
                        predicted_win INTEGER,
                        predicted_place TEXT,
                        predicted_trifecta TEXT,
                        confidence REAL,
                        prediction_data TEXT,
                        timestamp TEXT NOT NULL,
                        UNIQUE(race_date, venue_id, race_number)
                    )
                ''')

                # 結果データテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS race_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        race_date TEXT NOT NULL,
                        venue_id INTEGER NOT NULL,
                        venue_name TEXT NOT NULL,
                        race_number INTEGER NOT NULL,
                        winning_boat INTEGER,
                        place_results TEXT,
                        result_data TEXT,
                        timestamp TEXT NOT NULL,
                        UNIQUE(race_date, venue_id, race_number)
                    )
                ''')

                # --- スキーマ修正：trifecta_resultカラムを安全に追加 ---
                try:
                    cursor.execute("ALTER TABLE race_results ADD COLUMN trifecta_result TEXT")
                    conn.commit()
                    logger.info("DBスキーマ更新: `race_results`テーブルに`trifecta_result`カラムを追加しました。")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        pass  # カラムが既に存在する場合は何もしない
                    else:
                        raise # その他のDBエラーは再送出
                # --- スキーマ修正完了 ---

                # 的中記録テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS accuracy_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prediction_id INTEGER,
                        result_id INTEGER,
                        is_win_hit BOOLEAN,
                        is_place_hit BOOLEAN,
                        is_trifecta_hit BOOLEAN,
                        hit_status TEXT,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY(prediction_id) REFERENCES predictions(id),
                        FOREIGN KEY(result_id) REFERENCES race_results(id)
                    )
                ''')

                # レース詳細データテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS race_details (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        race_date TEXT NOT NULL,
                        venue_id INTEGER NOT NULL,
                        venue_name TEXT NOT NULL,
                        race_number INTEGER NOT NULL,
                        race_data TEXT,
                        prediction_data TEXT,
                        timestamp TEXT NOT NULL,
                        UNIQUE(race_date, venue_id, race_number)
                    )
                ''')

                conn.commit()
                logger.info("データベース初期化完了")
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")

    def save_prediction(self, race_data: Dict, prediction_result: Dict):
        """予想データを保存"""
        try:
            venue_id = race_data.get('race_stadium_number')
            race_number = race_data.get('race_number')
            venue_name = self.venue_mapping.get(venue_id, '不明')
            race_date = datetime.now().strftime('%Y-%m-%d')

            predicted_win = prediction_result.get('recommended_win') or prediction_result.get('predicted_win', 1)
            predicted_place = prediction_result.get('recommended_place') or prediction_result.get('predicted_place', [1, 2, 3])
            confidence = prediction_result.get('confidence', 0.5)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO predictions
                    (race_date, venue_id, venue_name, race_number, predicted_win, predicted_place, confidence, prediction_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (race_date, venue_id, venue_name, race_number, predicted_win,
                      json.dumps(predicted_place), confidence, json.dumps(prediction_result),
                      datetime.now().isoformat()))

                conn.commit()
                logger.debug(f"予想データ保存: {venue_name} {race_number}R")
        except Exception as e:
            logger.error(f"予想データ保存エラー: {e}")

    def save_race_details(self, race_data: Dict, prediction_result: Dict):
        """レース詳細データを保存"""
        try:
            venue_id = race_data.get('race_stadium_number')
            race_number = race_data.get('race_number')
            venue_name = self.venue_mapping.get(venue_id, '不明')
            race_date = datetime.now().strftime('%Y-%m-%d')

            # 発走時間を抽出（複数の可能なフィールド名から取得）
            start_time = (race_data.get('race_close_time') or 
                         race_data.get('start_time') or 
                         race_data.get('race_time') or 
                         race_data.get('close_time'))
            
            # レースタイトルを取得
            race_title = race_data.get('race_title', f'第{race_number}レース')

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO race_details
                    (race_date, venue_id, venue_name, race_number, start_time, race_title, 
                     race_data, boats_data, prediction_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (race_date, venue_id, venue_name, race_number, start_time, race_title,
                      json.dumps(race_data), json.dumps(race_data.get('boats', [])), json.dumps(prediction_result),
                      datetime.now().isoformat()))

                conn.commit()
                logger.debug(f"レース詳細データ保存: {venue_name} {race_number}R (発走: {start_time})")
        except Exception as e:
            logger.error(f"レース詳細データ保存エラー: {e}")

    def get_race_details(self, venue_id: int, race_number: int, race_date: Optional[str] = None) -> Optional[Dict]:
        """レース詳細データを取得"""
        try:
            if race_date is None:
                race_date = datetime.now().strftime('%Y-%m-%d')

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT race_data, prediction_data, venue_name
                    FROM race_details
                    WHERE venue_id = ? AND race_number = ? AND race_date = ?
                ''', (venue_id, race_number, race_date))

                row = cursor.fetchone()
                if row:
                    race_data_json, prediction_data_json, venue_name = row
                    return {
                        'race_data': json.loads(race_data_json) if race_data_json else {},
                        'prediction_data': json.loads(prediction_data_json) if prediction_data_json else {},
                        'venue_name': venue_name
                    }
                return None
        except Exception as e:
            logger.error(f"レース詳細データ取得エラー: {e}")
            return None

    def get_race_results(self, venue_id: int, race_number: int, race_date: Optional[str] = None) -> Optional[Dict]:
        """レース結果データを取得"""
        try:
            if race_date is None:
                race_date = datetime.now().strftime('%Y-%m-%d')

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # テーブル構造を動的に確認してクエリを調整
                cursor.execute("PRAGMA table_info(race_results)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # timestampカラムの存在確認
                timestamp_col = 'timestamp' if 'timestamp' in columns else 'fetched_at' if 'fetched_at' in columns else "datetime('now')"
                trifecta_col = 'trifecta_result' if 'trifecta_result' in columns else 'NULL'
                
                query = f'''
                    SELECT winning_boat, place_results, {trifecta_col}, result_data, {timestamp_col}
                    FROM race_results
                    WHERE venue_id = ? AND race_number = ? AND race_date = ?
                '''
                
                cursor.execute(query, (venue_id, race_number, race_date))

                row = cursor.fetchone()
                if row:
                    winning_boat, place_results_json, trifecta_result, result_data_json, timestamp = row
                    
                    # JSON文字列をパース
                    place_results = json.loads(place_results_json) if place_results_json else []
                    result_data = json.loads(result_data_json) if result_data_json else {}
                    
                    return {
                        'winning_boat': winning_boat,
                        'place_results': place_results,  # [1,2,3] 形式の着順リスト
                        'trifecta_result': trifecta_result,  # 三連単結果（例: "1-2-3"）
                        'result_data': result_data,
                        'result_time': timestamp,
                        'has_results': True
                    }
                return None
        except Exception as e:
            logger.error(f"レース結果データ取得エラー: {e}")
            return None

    def calculate_accuracy(self, target_date: Optional[str] = None, date_range_days: int = 1) -> Dict[str, Any]:
        """的中率を計算"""
        try:
            if target_date is None:
                target_date = datetime.now().strftime('%Y-%m-%d')

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 日付範囲の設定
                if date_range_days == 1:
                    date_condition = "rd.race_date = ?"
                    date_params = (target_date,)
                else:
                    # 複数日対応
                    end_date = datetime.strptime(target_date, '%Y-%m-%d')
                    start_date = end_date - timedelta(days=date_range_days-1)
                    date_condition = "rd.race_date BETWEEN ? AND ?"
                    date_params = (start_date.strftime('%Y-%m-%d'), target_date)

                # 基本統計 - race_detailsテーブルから取得（単勝・複勝・三連単対応）
                cursor.execute(f'''
                    SELECT COUNT(*) as total_predictions,
                           COUNT(CASE WHEN JSON_EXTRACT(rd.prediction_data, '$.recommended_win') = rr.winning_boat THEN 1 END) as win_hits,
                           COUNT(CASE WHEN JSON_EXTRACT(rd.prediction_data, '$.recommended_win') = rr.winning_boat
                                      OR JSON_EXTRACT(rd.prediction_data, '$.recommended_win') = JSON_EXTRACT(rr.place_results, '$[1]')
                                 THEN 1 END) as place_hits,
                           COUNT(CASE WHEN rr.trifecta_result IS NOT NULL
                                      AND JSON_EXTRACT(rd.prediction_data, '$.recommended_trifecta') = rr.trifecta_result
                                 THEN 1 END) as trifecta_hits
                    FROM race_details rd
                    LEFT JOIN race_results rr ON rd.venue_id = rr.venue_id AND rd.race_number = rr.race_number AND rd.race_date = rr.race_date
                    WHERE {date_condition} AND rr.winning_boat IS NOT NULL
                ''', date_params)

                stats = cursor.fetchone()
                total_predictions = stats[0] if stats else 0
                win_hits = stats[1] if stats else 0
                place_hits = stats[2] if stats else 0
                trifecta_hits = stats[3] if stats else 0

                win_accuracy = (win_hits / total_predictions * 100) if total_predictions > 0 else 0
                place_accuracy = (place_hits / total_predictions * 100) if total_predictions > 0 else 0
                trifecta_accuracy = (trifecta_hits / total_predictions * 100) if total_predictions > 0 else 0

                # レース別詳細（race_detailsテーブルから取得してデータソースを統一）
                # まずデータを取得してから発走時間でソート
                cursor.execute(f'''
                    SELECT rd.venue_id, rd.venue_name, rd.race_number, rd.prediction_data,
                           rr.winning_boat, rr.place_results, rr.trifecta_result, rd.race_date, rd.race_data
                    FROM race_details rd
                    LEFT JOIN race_results rr ON rd.venue_id = rr.venue_id AND rd.race_number = rr.race_number AND rd.race_date = rr.race_date
                    WHERE {date_condition}
                ''', date_params)

                races = []
                for row in cursor.fetchall():
                    venue_id, venue_name, race_number, prediction_data_json, winning_boat, place_results_json, trifecta_result, race_date, race_data_json = row

                    # prediction_dataからJSONを解析
                    prediction_data = json.loads(prediction_data_json) if prediction_data_json else {}
                    predicted_win = prediction_data.get('recommended_win')
                    predicted_place = prediction_data.get('recommended_place', [])
                    predicted_trifecta = prediction_data.get('recommended_trifecta')

                    # 予想データに保存された信頼度を直接使用
                    confidence = prediction_data.get('confidence', 0.5)

                    # race_dataから発走時間を取得（race_closed_atから時刻部分のみを抽出）
                    start_time = '未定'
                    if race_data_json:
                        try:
                            race_data = json.loads(race_data_json)
                            # race_closed_atから時刻部分のみを抽出
                            race_closed_at = race_data.get('race_closed_at')
                            if race_closed_at:
                                # "2025-08-25 15:19:00" から "15:19" を抽出
                                if ' ' in race_closed_at:
                                    time_part = race_closed_at.split(' ')[1]  # "15:19:00"
                                    start_time = time_part[:5]  # "15:19" (秒を除く)
                                else:
                                    start_time = race_closed_at
                            else:
                                start_time = race_data.get('start_time', '未定')
                        except (json.JSONDecodeError, TypeError):
                            start_time = '未定'

                    is_hit = (predicted_win == winning_boat) if (predicted_win is not None and winning_boat is not None) else None
                    is_trifecta_hit = (predicted_trifecta == trifecta_result) if (predicted_trifecta is not None and trifecta_result is not None) else None

                    # actual_resultフィールドを構築
                    actual_result = None
                    if winning_boat is not None:
                        place_results = json.loads(place_results_json) if place_results_json else []
                        actual_result = {
                            'win': winning_boat,
                            'place': place_results[:2] if len(place_results) >= 2 else [],
                            'trifecta': trifecta_result
                        }

                    # hit_statusフィールドを構築（テンプレート用）
                    hit_status = 'pending'
                    if is_hit is True:
                        hit_status = 'hit'
                    elif is_hit is False:
                        hit_status = 'miss'

                    # ソート用のタイムスタンプを作成（race_dataから取得）
                    sort_timestamp = '9999-12-31 23:59:59'  # デフォルト値
                    if race_data_json:
                        try:
                            race_data = json.loads(race_data_json)
                            race_closed_at = race_data.get('race_closed_at')
                            if race_closed_at:
                                sort_timestamp = race_closed_at
                        except (json.JSONDecodeError, TypeError):
                            pass

                    races.append({
                        'venue_id': venue_id,
                        'venue_name': venue_name,
                        'race_number': race_number,
                        'predicted_win': predicted_win,
                        'predicted_trifecta': predicted_trifecta,
                        'winning_boat': winning_boat,
                        'actual_result': actual_result,
                        'is_hit': is_hit,
                        'is_trifecta_hit': is_trifecta_hit,
                        'hit_status': hit_status,
                        'confidence': confidence or 0.5,
                        'date': race_date,
                        'start_time': start_time,
                        'sort_timestamp': sort_timestamp
                    })

                # 発走時間でソート（昇順）
                races.sort(key=lambda x: x['sort_timestamp'])

                # 存在するレースのみフィルタリング
                valid_races = self._filter_existing_races(races, target_date)
                logger.info(f"存在チェック: {len(races)}件から{len(valid_races)}件にフィルタ")

                # sort_timestampフィールドを除去（表示用ではないため）
                for race in valid_races:
                    race.pop('sort_timestamp', None)

                return {
                    'summary': {
                        'total_predictions': total_predictions,
                        'win_hits': win_hits,
                        'win_accuracy': round(win_accuracy, 1),
                        'place_hits': place_hits,
                        'place_accuracy': round(place_accuracy, 1),
                        'trifecta_hits': trifecta_hits,
                        'trifecta_accuracy': round(trifecta_accuracy, 1)
                    },
                    'races': valid_races,
                    'venues': self.venue_mapping
                }
        except Exception as e:
            logger.error(f"的中率計算エラー: {e}")
            return {
                'summary': {
                    'total_predictions': 0,
                    'win_hits': 0,
                    'win_accuracy': 0.0,
                    'place_hits': 0,
                    'place_accuracy': 0.0,
                    'trifecta_hits': 0,
                    'trifecta_accuracy': 0.0
                },
                'races': [],
                'venues': self.venue_mapping
            }

    def _filter_existing_races(self, races: List[Dict], target_date: str) -> List[Dict]:
        """存在するレースのみフィルタリング"""
        try:
            # 現在のAPIデータから有効なレース一覧を取得
            import requests
            import json
            from datetime import datetime

            # 今日のレースのみチェック
            if target_date == datetime.now().strftime('%Y-%m-%d'):
                try:
                    response = requests.get('https://boatraceopenapi.github.io/programs/v2/today.json', timeout=5)
                    if response.status_code == 200:
                        api_data = response.json()
                        valid_race_keys = set()

                        for program in api_data.get('programs', []):
                            venue_id = program.get('race_stadium_number')
                            race_number = program.get('race_number')
                            if venue_id and race_number:
                                valid_race_keys.add(f"{venue_id}_{race_number}")

                        # 有効なレースのみフィルタ
                        filtered_races = []
                        for race in races:
                            race_key = f"{race['venue_id']}_{race['race_number']}"
                            if race_key in valid_race_keys:
                                filtered_races.append(race)
                            else:
                                logger.debug(f"非存在レースを除外: {race['venue_name']} {race['race_number']}R")

                        return filtered_races

                except Exception as e:
                    logger.warning(f"APIチェックエラー: {e}")

            # APIチェックが失敗した場合、すべてを返す
            return races

        except Exception as e:
            logger.error(f"レースフィルタリングエラー: {e}")
            return races
