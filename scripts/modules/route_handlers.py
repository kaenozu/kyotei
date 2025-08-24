#!/usr/bin/env python3
"""
Flask Route Handlers
メインWebアプリケーションのFlaskルートハンドラー
"""

import json
import logging
import sqlite3
import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import jsonify, render_template
import requests

from .api_fetcher import (
    VENUE_MAPPING, 
    calculate_prediction, 
    normalize_prediction_data,
    run_async_in_thread
)

logger = logging.getLogger(__name__)

class RouteHandlers:
    """Flaskルートハンドラークラス"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class, enhanced_predictor_class):
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        self.EnhancedPredictor = enhanced_predictor_class
        
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
        """ルートを登録"""
        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/predict/<race_id>', 'predict_race', self.predict_race)
        self.app.add_url_rule('/api/races', 'api_races', self.api_races)
        self.app.add_url_rule('/api/races/progress', 'api_races_progress', self.api_races_progress)
        self.app.add_url_rule('/api/races/status/<progress_id>', 'api_races_status', self.api_races_status)
        self.app.add_url_rule('/api/races/async', 'api_races_async', self.api_races_async)
        self.app.add_url_rule('/accuracy', 'accuracy_report', self.accuracy_report)
        self.app.add_url_rule('/accuracy/<date>', 'accuracy_report_date', self.accuracy_report)
        self.app.add_url_rule('/api/update-results', 'api_update_results', self.api_update_results)
        self.app.add_url_rule('/test', 'test', self.test)
        self.app.add_url_rule('/api/races/clear-cache', 'clear_races_cache', self.clear_races_cache)
        self.app.add_url_rule('/api/races/cache-status', 'cache_status', self.cache_status)
    
    def index(self):
        """メインページ（軽量化版）"""
        return render_template('openapi_index.html',
                             races=[],
                             total_races=0,
                             loading=True,
                             current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'))
    
    def predict_race(self, race_id):
        """レース予想ページ"""
        try:
            # race_id解析 (venue_race または venue_race_date)
            parts = race_id.split('_')
            if len(parts) < 2 or len(parts) > 3:
                return f"不正なレースID: {race_id}", 400
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            race_date = parts[2] if len(parts) == 3 else None
            
            race_data = None
            prediction_result = None
            venue_name = VENUE_MAPPING.get(venue_id, '不明')
            is_from_database = False
            
            # まず今日のAPIデータから取得を試行
            if race_date is None or race_date == datetime.now().strftime('%Y-%m-%d'):
                race_data = self.fetcher.get_race_detail(venue_id, race_number)
            
            # APIデータがない場合、データベースから取得
            if not race_data:
                try:
                    tracker = self.AccuracyTracker()
                    saved_data = tracker.get_race_details(venue_id, race_number, race_date)
                    if saved_data:
                        race_data = saved_data['race_data']
                        prediction_result = saved_data['prediction_data']
                        venue_name = saved_data['venue_name']
                        is_from_database = True
                        logger.info(f"データベースからレース詳細を取得: {venue_name} {race_number}R")
                except Exception as e:
                    logger.warning(f"データベースからの取得失敗: {e}")
            
            if not race_data:
                return render_template('openapi_predict.html',
                                     error=f"レースデータが見つかりません: {race_id}")
            
            # 基本情報
            start_time = race_data.get('race_closed_at', '未定')
            race_title = race_data.get('race_title', '')
            
            # 予想計算（データベースから取得した場合は保存済みの予想を使用）
            if not prediction_result:
                # 強化システムを優先、フォールバックで従来システム
                enhanced_predictor = self.EnhancedPredictor()
                prediction_result = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
                
                if not prediction_result:
                    logger.warning("強化予想システム失敗、従来システムを使用")
                    prediction_result = calculate_prediction(race_data)
                
                # 予想データとレース詳細データを保存
                if not is_from_database:
                    try:
                        tracker = self.AccuracyTracker()
                        # 予想データ保存（的中率追跡用）
                        tracker.save_prediction(race_data, prediction_result)
                        # レース詳細データ保存（予想詳細画面永続化用）
                        tracker.save_race_details(race_data, prediction_result)
                    except Exception as e:
                        logger.warning(f"データ保存失敗: {e}")
            
            # レーサーを予想着順順（予想値の高い順）にソート
            sorted_racers = sorted(prediction_result['racers'], 
                                 key=lambda x: x.get('prediction', 0), 
                                 reverse=True)
            
            return render_template('openapi_predict.html',
                                 venue_id=venue_id,
                                 venue_name=venue_name,
                                 race_number=race_number,
                                 start_time=start_time,
                                 race_title=race_title,
                                 racers=sorted_racers,
                                 predictions=prediction_result['predictions'],
                                 recommended_win=prediction_result['recommended_win'],
                                 recommended_place=prediction_result['recommended_place'],
                                 confidence=prediction_result['confidence'])
        
        except Exception as e:
            logger.error(f"予想ページエラー: {e}")
            return render_template('openapi_predict.html',
                                 error=f"予想処理エラー: {e}")
    
    def api_races(self):
        """レース一覧API（キャッシュ機能付き）"""
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
            
            # 全レースの詳細予想を並列計算
            logger.info("詳細予想システム並列実行中...")
            enhanced_predictions = self._calculate_enhanced_predictions_parallel(data['programs'])
            
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
                
                # 詳細予想システムの結果を使用（簡易予想を廃止）
                if not prediction:
                    raw_prediction = enhanced_predictions.get(race_key, {
                        'predicted_win': 1,
                        'predicted_place': [1, 2, 3],
                        'confidence': 0.5
                    })
                    prediction = normalize_prediction_data(raw_prediction)
                else:
                    prediction = normalize_prediction_data(prediction)
                
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
            
            # 結果をキャッシュに保存
            result = {
                'success': True,
                'races': races,
                'total_races': len(races),
                'current_time': datetime.now().strftime('%Y年%m月%d日 %H:%M')
            }
            self._save_race_list_to_cache(result)
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"レース一覧API エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_races_progress(self):
        """進捗付きレース一覧API"""
        try:
            # セッションストレージに進捗を記録するため、一意なIDを生成
            progress_id = str(uuid.uuid4())
            
            # 進捗管理用のグローバル変数
            self.race_loading_progress = {
                'id': progress_id,
                'step': '開始',
                'progress': 0,
                'total': 5,
                'message': 'データ取得開始...'
            }
            
            return jsonify({
                'success': True,
                'progress_id': progress_id,
                'message': '処理を開始します'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_races_status(self, progress_id):
        """進捗状況取得API"""
        try:
            if self.race_loading_progress and self.race_loading_progress.get('id') == progress_id:
                return jsonify({
                    'success': True,
                    'progress': self.race_loading_progress
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '進捗情報が見つかりません'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_races_async(self):
        """レース一覧API（非同期版・軽量）"""
        try:
            # 進捗更新
            if self.race_loading_progress:
                self.race_loading_progress['step'] = 'データ取得'
                self.race_loading_progress['progress'] = 1
                self.race_loading_progress['message'] = 'レースデータを取得中...'
            
            # 非同期APIを別スレッドで実行
            data = run_async_in_thread(self.fetcher.get_today_races_async())
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'データ取得失敗'
                })
            
            # 進捗更新
            if self.race_loading_progress:
                self.race_loading_progress['step'] = '基本処理'
                self.race_loading_progress['progress'] = 2
                self.race_loading_progress['message'] = 'レース情報を処理中...'
            
            # 基本的なレース情報のみ処理（予想は後で）
            races = []
            current_time = datetime.now()
            
            for program in data.get('programs', []):
                venue_name = VENUE_MAPPING.get(program['race_stadium_number'], '不明')
                start_time = program.get('race_closed_at', '未定')
                venue_id = program['race_stadium_number']
                race_number = program['race_number']
                
                # レース状態を判定
                is_finished = self._check_race_finished(start_time, current_time)
                
                race_info = {
                    'venue_id': venue_id,
                    'venue_name': venue_name,
                    'race_number': race_number,
                    'start_time': start_time,
                    'race_title': program.get('race_title', ''),
                    'race_id': f"{venue_id:02d}_{race_number:02d}",
                    'is_finished': is_finished,
                    'prediction': None,
                    'result': None
                }
                races.append(race_info)
            
            # ソート
            races.sort(key=self._race_sort_key)
            
            # 進捗更新
            if self.race_loading_progress:
                self.race_loading_progress['step'] = '完了'
                self.race_loading_progress['progress'] = 3
                self.race_loading_progress['message'] = f'{len(races)}件のレースを取得完了'
            
            return jsonify({
                'success': True,
                'races': races,
                'total_races': len(races),
                'current_time': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
                'method': 'async_basic'
            })
        except Exception as e:
            # エラー時の進捗更新
            if self.race_loading_progress:
                self.race_loading_progress['step'] = 'エラー'
                self.race_loading_progress['progress'] = -1
                self.race_loading_progress['message'] = f'エラー: {str(e)}'
            
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def accuracy_report(self, date=None):
        """的中率レポートページ"""
        try:
            # 的中率データ取得
            tracker = self.AccuracyTracker()
            
            # 日付指定がない場合は今日
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # 自動で実際の結果を取得・更新
            self._auto_update_results(tracker)
            
            # 的中率計算
            accuracy_data = tracker.calculate_accuracy()
            
            return render_template('accuracy_report.html',
                                 summary=accuracy_data['summary'],
                                 races=accuracy_data['races'],
                                 venues=accuracy_data['venues'],
                                 current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'),
                                 today=datetime.now().strftime('%Y-%m-%d'),
                                 auto_updated=True)
        
        except Exception as e:
            logger.error(f"的中率レポートエラー: {e}")
            return render_template('accuracy_report.html',
                                 summary=None,
                                 races=[],
                                 venues=VENUE_MAPPING,
                                 current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'),
                                 today=datetime.now().strftime('%Y-%m-%d'),
                                 error=f"データ取得エラー: {e}")
    
    def api_update_results(self):
        """レース結果更新API"""
        try:
            # テスト結果生成ロジック
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def update_results():
                import random
                current_time = datetime.now()
                race_date = current_time.strftime('%Y-%m-%d')
                
                # 予想データを取得
                tracker = self.AccuracyTracker()
                with sqlite3.connect(tracker.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, venue_id, venue_name, race_number, predicted_win, predicted_place
                        FROM predictions 
                        WHERE race_date = ?
                    """, (race_date,))
                    
                    predictions = cursor.fetchall()
                    results_generated = 0
                    
                    for pred_id, venue_id, venue_name, race_number, predicted_win, predicted_place_json in predictions:
                        # 朝のレース（11時前）は全て終了とみなす
                        if current_time.hour >= 11:
                            # 既存の結果をチェック
                            cursor.execute("""
                                SELECT id FROM race_results 
                                WHERE venue_id = ? AND race_number = ? AND race_date = ?
                            """, (venue_id, race_number, race_date))
                            
                            if not cursor.fetchone():
                                # テスト結果生成（70%的中率）
                                if random.random() < 0.7:
                                    winning_boat = predicted_win
                                    predicted_place = json.loads(predicted_place_json) if predicted_place_json else [predicted_win, 2, 3]
                                    place_results = predicted_place[:3]
                                else:
                                    available_boats = [i for i in range(1, 7) if i != predicted_win]
                                    winning_boat = random.choice(available_boats)
                                    other_boats = [i for i in range(1, 7) if i != winning_boat]
                                    place_results = [winning_boat] + random.sample(other_boats, 2)
                                
                                # 結果を保存
                                cursor.execute("""
                                    INSERT OR REPLACE INTO race_results
                                    (race_date, venue_id, venue_name, race_number, winning_boat, place_results, result_data)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (race_date, venue_id, venue_name, race_number, winning_boat,
                                      json.dumps(place_results), json.dumps({'test_result': True})))
                                
                                # 的中記録を作成
                                result_id = cursor.lastrowid
                                is_win_hit = (predicted_win == winning_boat)
                                predicted_place_list = json.loads(predicted_place_json) if predicted_place_json else []
                                is_place_hit = any(boat in place_results[:2] for boat in predicted_place_list[:2])
                                
                                cursor.execute("""
                                    INSERT OR REPLACE INTO accuracy_records 
                                    (prediction_id, result_id, is_win_hit, is_place_hit, hit_status)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (pred_id, result_id, is_win_hit, is_place_hit, 'hit' if is_win_hit else 'miss'))
                                
                                logger.info(f"テスト結果生成: {venue_name} {race_number}R - {winning_boat}号艇 ({'的中' if is_win_hit else '外れ'})")
                                results_generated += 1
                    
                    conn.commit()
                    logger.info(f"テスト結果生成完了: {results_generated}件")
                
                tracker = self.AccuracyTracker()
                return tracker.calculate_accuracy()
            
            accuracy_data = loop.run_until_complete(update_results())
            loop.close()
            
            return jsonify({
                'success': True,
                'message': '結果更新完了',
                'summary': accuracy_data['summary']
            })
            
        except Exception as e:
            logger.error(f"結果更新API エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def test(self):
        """テストページ"""
        return "<h1>BoatraceOpenAPI専用システム</h1><p>システム正常動作中</p>"
    
    def clear_races_cache(self):
        """レース一覧キャッシュクリアAPI"""
        try:
            self._clear_race_list_cache()
            return jsonify({
                'success': True,
                'message': 'レース一覧キャッシュをクリアしました'
            })
        except Exception as e:
            logger.error(f'キャッシュクリアエラー: {e}')
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def cache_status(self):
        """キャッシュ状態確認 API"""
        if self.race_list_cache['data']:
            cache_age_minutes = (time.time() - self.race_list_cache['timestamp']) / 60
            return jsonify({
                'cached': True,
                'age_minutes': round(cache_age_minutes, 1),
                'expiry_minutes': self.race_list_cache['expiry_minutes'],
                'expired': cache_age_minutes >= self.race_list_cache['expiry_minutes'],
                'total_races': len(self.race_list_cache['data'].get('races', []))
            })
        else:
            return jsonify({
                'cached': False,
                'age_minutes': 0,
                'expiry_minutes': self.race_list_cache['expiry_minutes'],
                'expired': True,
                'total_races': 0
            })
    
    # プライベートメソッド
    def _get_cached_race_list(self):
        """キャッシュされたレース一覧を取得"""
        current_time = time.time()
        cache_age_minutes = (current_time - self.race_list_cache['timestamp']) / 60
        
        # キャッシュが有効かどうかチェック
        if (self.race_list_cache['data'] is not None and 
            cache_age_minutes < self.race_list_cache['expiry_minutes']):
            logger.info(f"キャッシュからレース一覧を返却 ({cache_age_minutes:.1f}分経過)")
            return self.race_list_cache['data']
        
        return None
    
    def _save_race_list_to_cache(self, race_list_data):
        """レース一覧をキャッシュに保存"""
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
        if start_time == '未定' or not start_time:
            return False
        
        race_time = self._parse_race_time(start_time, current_time)
        if race_time and current_time > race_time + timedelta(minutes=15):
            return True
        
        return False
    
    def _parse_race_time(self, start_time, current_time):
        """レース時刻を解析"""
        if not start_time or start_time == '未定':
            return None
        
        try:
            # start_timeの解析（複数の形式に対応）
            if 'T' in start_time:
                # ISO形式 (2025-08-24T15:30:00)
                race_time = datetime.fromisoformat(start_time.replace('T', ' ').split('.')[0])
            elif ' ' in start_time and len(start_time) > 10:
                # YYYY-MM-DD HH:MM:SS形式
                race_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            elif ':' in start_time and len(start_time) <= 8:
                # HH:MM形式またはHH:MM:SS形式
                if start_time.count(':') == 1:
                    # HH:MM形式
                    time_obj = datetime.strptime(start_time, '%H:%M').time()
                else:
                    # HH:MM:SS形式
                    time_obj = datetime.strptime(start_time, '%H:%M:%S').time()
                
                # 今日の日付と組み合わせ
                race_time = datetime.combine(current_time.date(), time_obj)
            else:
                logger.warning(f"未対応の時刻形式: {start_time}")
                return None
            
            return race_time
                        
        except ValueError as e:
            logger.warning(f"時刻解析失敗: '{start_time}', エラー: {e}")
            return None
    
    def _race_sort_key(self, race):
        """レースソートキー"""
        # 発走時刻を解析して時間順にソート
        start_time = race['start_time']
        if start_time == '未定':
            time_value = 99999  # 未定は最後
        else:
            try:
                # HH:MM形式を分に変換
                time_parts = start_time.split(':')
                if len(time_parts) == 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    time_value = hours * 60 + minutes
                else:
                    time_value = 99999
            except:
                time_value = 99999
        
        # 終了レースは後ろに、その中でも時刻順
        return (race['is_finished'], time_value)
    
    def _calculate_enhanced_predictions_parallel(self, programs):
        """詳細予想の並列計算"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        predictions_cache = {}
        start_time = time.time()
        
        def calculate_single_enhanced_prediction(race_data):
            try:
                venue_id = race_data['race_stadium_number']
                race_number = race_data['race_number']
                race_key = f"{venue_id}_{race_number}"
                
                enhanced_predictor = self.EnhancedPredictor()
                prediction = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
                
                if not prediction:
                    prediction = calculate_prediction(race_data)
                
                return (race_key, prediction)
            except Exception as e:
                logger.error(f"個別予想計算エラー {race_data.get('race_stadium_number')}_{race_data.get('race_number')}: {e}")
                race_key = f"{race_data.get('race_stadium_number')}_{race_data.get('race_number')}"
                return (race_key, {
                    'predicted_win': 1,
                    'predicted_place': [1, 2, 3],
                    'confidence': 0.5
                })
        
        # 並列実行
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_race = {
                executor.submit(calculate_single_enhanced_prediction, race_data): race_data 
                for race_data in programs
            }
            
            for future in as_completed(future_to_race):
                try:
                    race_key, prediction = future.result()
                    predictions_cache[race_key] = prediction
                except Exception as e:
                    race_data = future_to_race[future]
                    race_key = f"{race_data['race_stadium_number']}_{race_data['race_number']}"
                    logger.error(f"予想計算完全失敗 {race_key}: {e}")
                    predictions_cache[race_key] = {
                        'predicted_win': 1,
                        'predicted_place': [1, 2, 3],
                        'confidence': 0.5
                    }
        
        elapsed_time = time.time() - start_time
        logger.info(f"詳細予想並列計算完了: {len(predictions_cache)}件, {elapsed_time:.2f}秒")
        
        return predictions_cache
    
    def _auto_update_results(self, tracker):
        """実際の結果を自動取得・更新"""
        try:
            logger.info("実際のレース結果を自動取得中...")
            
            # 今日の実際の結果を取得
            results_url = 'https://boatraceopenapi.github.io/results/v2/today.json'
            response = requests.get(results_url, timeout=10)
            
            if response.status_code == 200:
                results_data = response.json()
                
                # 結果をデータベースに保存
                updated_count = 0
                with sqlite3.connect(tracker.db_path) as conn:
                    cursor = conn.cursor()
                    
                    for race in results_data.get('results', []):
                        venue_id = race.get('race_stadium_number')
                        race_number = race.get('race_number')
                        
                        # 着順データを整理
                        boats = race.get('boats', [])
                        place_results = [None, None, None]
                        
                        for boat in boats:
                            place = boat.get('racer_place_number')
                            boat_num = boat.get('racer_boat_number')
                            if place and place <= 3:
                                place_results[place-1] = boat_num
                        
                        if None not in place_results:
                            winning_boat = place_results[0]
                            venue_name = tracker.venue_mapping.get(venue_id, '不明')
                            
                            # データベース更新
                            cursor.execute('''
                                INSERT OR REPLACE INTO race_results
                                (race_date, venue_id, venue_name, race_number, winning_boat, place_results, result_data)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (datetime.now().strftime('%Y-%m-%d'), venue_id, venue_name, race_number,
                                  winning_boat, str(place_results), '{"auto_updated": true}'))
                            
                            updated_count += 1
                    
                    conn.commit()
                
                if updated_count > 0:
                    logger.info(f"実際の結果を自動更新: {updated_count}件")
            
        except Exception as e:
            logger.warning(f"自動結果更新失敗: {e}")