#!/usr/bin/env python3
"""
API Routes - APIエンドポイント関連
レース一覧、進捗確認、キャッシュ管理など
"""

import json
import sqlite3
import uuid
import asyncio
import logging
from datetime import datetime
from flask import jsonify

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_fetcher import VENUE_MAPPING, normalize_prediction_data, run_async_in_thread

logger = logging.getLogger(__name__)

class APIRoutes:
    """API関連ルートハンドラー"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class):
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        
        # レース一覧キャッシュ
        self.race_list_cache = {
            'data': None,
            'timestamp': 0,
            'expiry_minutes': 5
        }
        
        # 進捗管理
        self.race_loading_progress = None
        
        self._register_routes()
    
    def _register_routes(self):
        """API関連ルートを登録"""
        self.app.add_url_rule('/api/races', 'api_races', self.api_races)
        self.app.add_url_rule('/api/races/progress', 'api_races_progress', self.api_races_progress)
        self.app.add_url_rule('/api/races/status/<progress_id>', 'api_races_status', self.api_races_status)
        self.app.add_url_rule('/api/races/async', 'api_races_async', self.api_races_async)
        self.app.add_url_rule('/api/races/clear-cache', 'clear_races_cache', self.clear_races_cache)
        self.app.add_url_rule('/api/races/cache-status', 'cache_status', self.cache_status)
    
    def api_races(self):
        """レース一覧API（キャッシュ機能付き）"""
        logger.info("=== api_races実行開始 ===")
        try:
            # キャッシュからデータを取得してみる
            cached_result = self._get_cached_race_list()
            if cached_result:
                return jsonify(cached_result)
            
            # キャッシュがない場合、新しいデータを取得
            logger.info("キャッシュなし、新規データ取得を開始")
            data = self.fetcher.get_today_races()
            
            if not data or 'programs' not in data:
                return jsonify({
                    'success': False,
                    'error': 'レースデータを取得できませんでした'
                })
            
            races = []
            current_time = datetime.now()
            race_date = current_time.strftime('%Y-%m-%d')
            
            # データベースから予想データと結果データを取得
            prediction_data = {}
            result_data = {}
            
            try:
                tracker = self.AccuracyTracker()
                with sqlite3.connect(tracker.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 今日の最新予想データを race_details テーブルから取得
                    cursor.execute("""
                        SELECT venue_id, race_number, prediction_data
                        FROM race_details 
                        WHERE race_date = ?
                    """, (race_date,))
                    
                    for row in cursor.fetchall():
                        venue_id, race_number, prediction_data_json = row
                        key = f"{venue_id}_{race_number}"
                        try:
                            prediction_json = json.loads(prediction_data_json) if prediction_data_json else {}
                            predicted_win = prediction_json.get('recommended_win') or prediction_json.get('predicted_win', 1)
                            predicted_place = prediction_json.get('recommended_place') or prediction_json.get('predicted_place', [1, 2, 3])
                            confidence = prediction_json.get('confidence', 0.5)
                        except:
                            predicted_win = 1
                            predicted_place = [1, 2, 3]
                            confidence = 0.5
                        
                        prediction_data[key] = {
                            'predicted_win': predicted_win,
                            'predicted_place': predicted_place,
                            'confidence': confidence
                        }
                    
                    # 今日の結果データを取得
                    cursor.execute("""
                        SELECT venue_id, race_number, winning_boat, place_results
                        FROM race_results 
                        WHERE race_date = ?
                    """, (race_date,))
                    
                    for row in cursor.fetchall():
                        venue_id, race_number, winning_boat, place_results_json = row
                        key = f"{venue_id}_{race_number}"
                        try:
                            place_results = json.loads(place_results_json) if place_results_json else []
                        except:
                            place_results = []
                        
                        result_data[key] = {
                            'winning_boat': winning_boat,
                            'place_results': place_results
                        }
                        
            except Exception as e:
                logger.warning(f"予想・結果データ取得エラー: {e}")
            
            # 軽量化: 詳細予想は必要に応じて遅延ロード
            enhanced_predictions = {}  # 空の辞書で初期化し高速化
            
            for program in data['programs']:
                venue_name = VENUE_MAPPING.get(program['race_stadium_number'], '不明')
                start_time = program.get('race_closed_at', '未定')
                venue_id = program['race_stadium_number']
                race_number = program['race_number']
                race_key = f"{venue_id}_{race_number}"
                
                # レース状態を判定
                is_finished = self._check_race_finished(start_time, current_time)
                race_time = self._parse_race_time(start_time, current_time)
                
                # 予想データと結果データを追加
                prediction = prediction_data.get(race_key)
                result = result_data.get(race_key) if is_finished and race_time else None
                
                # 詳細予想システムの結果を優先使用
                if race_key in enhanced_predictions:
                    raw_prediction = enhanced_predictions[race_key]
                    logger.info(f"並列計算予想使用 {venue_name} {race_number}R: 推奨={raw_prediction.get('recommended_win')}, 複勝={raw_prediction.get('recommended_place')}")
                    prediction = normalize_prediction_data(raw_prediction)
                elif prediction:
                    logger.debug(f"データベース予想使用 {venue_name} {race_number}R")
                    prediction = normalize_prediction_data(prediction)
                else:
                    # フォールバック予想
                    raw_prediction = {
                        'predicted_win': 1,
                        'predicted_place': [1, 2, 3],
                        'confidence': 0.5
                    }
                    logger.info(f"デフォルト予想使用 {venue_name} {race_number}R")
                    prediction = normalize_prediction_data(raw_prediction)
                
                race_info = {
                    'venue_id': venue_id,
                    'venue_name': venue_name,
                    'race_number': race_number,
                    'start_time': start_time,
                    'race_title': program.get('race_title', ''),
                    'race_id': f"{venue_id:02d}_{race_number:02d}",
                    'is_finished': is_finished,
                    'prediction': prediction,
                    'result': result
                }
                races.append(race_info)
            
            # ソート: 未終了レースを時刻順で先に、終了レースを後に
            races.sort(key=self._race_sort_key)
            
            result = {
                'success': True,
                'races': races,
                'total_races': len(races),
                'timestamp': current_time.isoformat()
            }
            
            # 結果をキャッシュに保存
            self._save_race_list_to_cache(result)
            logger.info(f"=== api_races完了: {len(races)}件のレース ===")
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"API races error: {e}")
            return jsonify({
                'success': False,
                'error': f'レース一覧の取得に失敗しました: {str(e)}'
            })
    
    def api_races_progress(self):
        """レース一覧取得の進捗確認API"""
        progress_id = str(uuid.uuid4())
        
        # 進捗情報を初期化
        self.race_loading_progress = {
            'progress_id': progress_id,
            'status': 'started',
            'progress': 0,
            'message': 'レースデータ取得を開始しています...'
        }
        
        return jsonify({
            'progress_id': progress_id,
            'status': 'started'
        })
    
    def api_races_status(self, progress_id):
        """レース一覧取得の進捗状況を返すAPI"""
        if not self.race_loading_progress or self.race_loading_progress.get('progress_id') != progress_id:
            return jsonify({'error': 'Progress ID not found'}), 404
        
        return jsonify(self.race_loading_progress)
    
    def api_races_async(self):
        """非同期レース一覧取得API"""
        try:
            # 非同期でレース一覧を取得（キャッシュ無視）
            result = run_async_in_thread(self._fetch_races_async())
            return jsonify(result)
        except Exception as e:
            logger.error(f"Async API races error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    async def _fetch_races_async(self):
        """非同期レース取得処理"""
        try:
            data = await self.fetcher.get_today_races_async()
            if not data:
                return {'success': False, 'error': 'No race data available'}
            
            races = []
            for program in data.get('programs', []):
                race_info = {
                    'venue_id': program['race_stadium_number'],
                    'venue_name': VENUE_MAPPING.get(program['race_stadium_number'], '不明'),
                    'race_number': program['race_number'],
                    'start_time': program.get('race_closed_at', '未定'),
                    'race_title': program.get('race_title', ''),
                    'race_id': f"{program['race_stadium_number']:02d}_{program['race_number']:02d}"
                }
                races.append(race_info)
            
            return {
                'success': True,
                'races': races,
                'total_races': len(races)
            }
            
        except Exception as e:
            logger.error(f"Async race fetch error: {e}")
            return {'success': False, 'error': str(e)}
    
    def clear_races_cache(self):
        """レース一覧キャッシュクリア"""
        self._clear_race_list_cache()
        return jsonify({
            'success': True,
            'message': 'キャッシュをクリアしました'
        })
    
    def cache_status(self):
        """キャッシュ状態確認"""
        current_time = time.time()
        cache_age_minutes = (current_time - self.race_list_cache['timestamp']) / 60
        
        return jsonify({
            'cached': self.race_list_cache['data'] is not None,
            'cache_age_minutes': round(cache_age_minutes, 1),
            'expiry_minutes': self.race_list_cache['expiry_minutes'],
            'is_expired': cache_age_minutes >= self.race_list_cache['expiry_minutes']
        })
    
    def _get_cached_race_list(self):
        """キャッシュされたレース一覧を取得"""
        current_time = time.time()
        cache_age_minutes = (current_time - self.race_list_cache['timestamp']) / 60
        
        if (self.race_list_cache['data'] is not None and 
            cache_age_minutes < self.race_list_cache['expiry_minutes']):
            logger.info(f"キャッシュからレース一覧を返却 ({cache_age_minutes:.1f}分経過)")
            return self.race_list_cache['data']
        
        return None
    
    def _save_race_list_to_cache(self, race_list_data):
        """レース一覧をキャッシュに保存"""
        import time
        self.race_list_cache['data'] = race_list_data
        self.race_list_cache['timestamp'] = time.time()
        logger.info(f"レース一覧をキャッシュに保存: {len(race_list_data.get('races', []))}件")
    
    def _clear_race_list_cache(self):
        """レース一覧キャッシュをクリア"""
        self.race_list_cache['data'] = None
        self.race_list_cache['timestamp'] = 0
        logger.info("レース一覧キャッシュをクリアしました")
    
    def _check_race_finished(self, start_time, current_time):
        """レース終了判定"""
        try:
            if start_time == '未定':
                return False
            race_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            return current_time > race_time + timedelta(minutes=10)
        except:
            return False
    
    def _parse_race_time(self, start_time, current_time):
        """レース時刻解析"""
        try:
            if start_time == '未定':
                return None
            race_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            return race_time
        except:
            return None
    
    def _race_sort_key(self, race):
        """レースソート用キー"""
        try:
            start_time = race['start_time']
            if start_time == '未定':
                return (1, 9999, race['venue_id'])  # 終了したものの後ろ
            
            race_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            current_time = datetime.now()
            
            if race['is_finished']:
                return (1, race_time.hour * 60 + race_time.minute, race['venue_id'])
            else:
                return (0, race_time.hour * 60 + race_time.minute, race['venue_id'])
        except:
            return (2, 9999, race.get('venue_id', 999))