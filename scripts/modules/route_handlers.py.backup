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

# 信頼度統一システム
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from confidence_unifier import confidence_unifier

logger = logging.getLogger(__name__)

class RouteHandlers:
    """Flaskルートハンドラークラス"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class, enhanced_predictor_class):
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        self.EnhancedPredictor = enhanced_predictor_class
        
        # EnhancedPredictor単一インスタンス（重い初期化を1回のみ）
        self._enhanced_predictor_instance = None
        
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
        self.app.add_url_rule('/api/races/enhanced-prediction/<race_key>', 'get_enhanced_prediction', self.get_enhanced_prediction)
        
        # 新しいUI/UX APIエンドポイント
        self.app.add_url_rule('/api/investment/dashboard', 'investment_dashboard', self.api_investment_dashboard)
        self.app.add_url_rule('/api/confidence/<race_key>', 'confidence_visualization', self.api_confidence_visualization)
        self.app.add_url_rule('/api/bet-recommendation/<race_key>', 'bet_recommendation', self.api_bet_recommendation)
        self.app.add_url_rule('/api/alerts', 'realtime_alerts', self.api_realtime_alerts)
        self.app.add_url_rule('/dashboard', 'enhanced_dashboard', self.enhanced_dashboard)
        # self.app.add_url_rule('/api/debug/confidence/<race_key>', 'debug_confidence', self.debug_confidence)
    
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
                # Refererヘッダーから戟り元を取得
                from flask import request
                referer = request.headers.get('Referer', '')
                back_url = '/accuracy' if 'accuracy' in referer else '/'
                
                return render_template('openapi_predict.html',
                                     error=f"レースデータが見つかりません: {race_id}",
                                     race_id=race_id,
                                     venue_name=venue_name,
                                     race_number=race_number,
                                     back_url=back_url,
                                     show_back_button=True)
            
            # 基本情報
            start_time = race_data.get('race_closed_at', '未定')
            race_title = race_data.get('race_title', '')
            
            # 予想計算（常に最新の予想を計算し、古いデータベース予想は参考程度に）
            enhanced_predictor = self.EnhancedPredictor()
            new_prediction = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
            
            logger.info(f"予想詳細 {venue_name} {race_number}R - DB予想:{prediction_result is not None}, 新予想:{new_prediction is not None}")
            
            if new_prediction:
                prediction_result = new_prediction
                logger.info(f"新しい予想使用 {venue_name} {race_number}R: 推奨={new_prediction.get('recommended_win')}, 複勝={new_prediction.get('recommended_place')}, 信頼度={new_prediction.get('confidence', 0):.6f}")
                # 新しい予想をデータベースに保存/更新
                if not is_from_database:
                    try:
                        tracker = self.AccuracyTracker()
                        tracker.save_race_details(race_data, prediction_result)
                        logger.info(f"新しい予想をデータベースに保存: {venue_name} {race_number}R")
                    except Exception as e:
                        logger.warning(f"予想保存エラー: {e}")
            elif not prediction_result:
                # 新しい計算も失敗し、データベース予想もない場合のフォールバック
                logger.warning("強化予想システム失敗、従来システムを使用")
                prediction_result = calculate_prediction(race_data)
            else:
                logger.info(f"データベース予想使用: 推奨={prediction_result.get('recommended_win')}, 信頼度={prediction_result.get('confidence', 0):.6f}")
                
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
            
            # Refererヘッダーから戟り元を取得
            from flask import request
            referer = request.headers.get('Referer', '')
            back_url = '/accuracy' if 'accuracy' in referer else '/'
            
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
                                 confidence=prediction_result['confidence'],
                                 betting_recommendations=prediction_result.get('betting_recommendations'),
                                 back_url=back_url,
                                 show_back_button=True)
        
        except Exception as e:
            logger.error(f"予想ページエラー: {e}")
            # Refererヘッダーから戟り元を取得
            from flask import request
            referer = request.headers.get('Referer', '')
            back_url = '/accuracy' if 'accuracy' in referer else '/'
            
            return render_template('openapi_predict.html',
                                 error=f"予想処理エラー: {e}",
                                 back_url=back_url,
                                 show_back_button=True)
    
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
            # enhanced_predictions = self._calculate_enhanced_predictions_parallel(data['programs'])
            # logger.info(f"並列計算結果: {len(enhanced_predictions)}件の予想を取得")
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
                
                # 詳細予想システムの結果を優先使用（データベース予想より新しい並行処理予想を優先）
                if race_key in enhanced_predictions:
                    raw_prediction = enhanced_predictions[race_key]
                    logger.info(f"並列計算予想使用 {venue_name} {race_number}R: 推奨={raw_prediction.get('recommended_win')}, 複勝={raw_prediction.get('recommended_place')}")
                    prediction = normalize_prediction_data(raw_prediction)
                    
                    # 新しく計算した予想をデータベースに保存
                    try:
                        tracker = self.AccuracyTracker()
                        tracker.save_race_details(program, raw_prediction)
                        logger.debug(f"新しい予想をデータベースに保存: {venue_name} {race_number}R")
                    except Exception as e:
                        logger.warning(f"予想保存エラー {venue_name} {race_number}R: {e}")
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
            
            # 統一信頼度システムで信頼度を統一化
            try:
                for race in races:
                    venue_id = race.get('venue_id')
                    race_number = race.get('race_number')
                    
                    if venue_id and race_number:
                        # プログラムデータを検索
                        race_data = None
                        for program in data.get('programs', []):
                            if (program['race_stadium_number'] == venue_id and 
                                program['race_number'] == race_number):
                                race_data = program
                                break
                        
                        # 統一信頼度を取得
                        unified_confidence = confidence_unifier.get_unified_confidence(
                            venue_id, race_number, race_data
                        )
                        
                        # 信頼度を設定（0-1を0-100に変換）
                        race['confidence'] = unified_confidence * 100
                        race['unified_confidence'] = unified_confidence
                        
                        # race['prediction']['confidence']にも統一信頼度を反映
                        if race.get('prediction'):
                            race['prediction']['confidence'] = unified_confidence
                
                logger.info(f"信頼度統一化完了: {len(races)}件")
            except Exception as e:
                logger.warning(f"信頼度統一化エラー: {e}")
                # エラー時はデフォルト信頼度を設定
                for race in races:
                    race['confidence'] = 50.0
                    race['unified_confidence'] = 0.5
            
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
            
            # 進捗更新（信頼度統一化）
            if self.race_loading_progress:
                self.race_loading_progress['step'] = '信頼度統一化'
                self.race_loading_progress['progress'] = 3
                self.race_loading_progress['message'] = '信頼度を統一化中...'
            
            # 統一信頼度システムで信頼度を統一
            try:
                # レースデータを取得（統一信頼度計算に必要）
                for race in races:
                    venue_id = race.get('venue_id')
                    race_number = race.get('race_number')
                    
                    if venue_id and race_number:
                        # プログラムデータを検索
                        race_data = None
                        for program in data.get('programs', []):
                            if (program['race_stadium_number'] == venue_id and 
                                program['race_number'] == race_number):
                                race_data = program
                                break
                        
                        # 統一信頼度を取得
                        unified_confidence = confidence_unifier.get_unified_confidence(
                            venue_id, race_number, race_data
                        )
                        
                        # 信頼度を設定（0-1を0-100に変換）
                        race['confidence'] = unified_confidence * 100
                        race['unified_confidence'] = unified_confidence
                        
                        # race['prediction']['confidence']にも統一信頼度を反映
                        if race.get('prediction'):
                            race['prediction']['confidence'] = unified_confidence
                
                logger.info(f"信頼度統一化完了: {len(races)}件")
            except Exception as e:
                logger.warning(f"信頼度統一化エラー: {e}")
                # エラー時はデフォルト信頼度を設定
                for race in races:
                    race['confidence'] = 50.0
                    race['unified_confidence'] = 0.5
            
            # 進捗更新（完了）
            if self.race_loading_progress:
                self.race_loading_progress['step'] = '完了'
                self.race_loading_progress['progress'] = 4
                self.race_loading_progress['message'] = f'{len(races)}件のレース処理完了'
            
            return jsonify({
                'success': True,
                'races': races,
                'total_races': len(races),
                'current_time': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
                'method': 'async_unified'
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
        """的中率レポートページ（ROI評価統合版）"""
        try:
            # 的中率データ取得
            tracker = self.AccuracyTracker()
            
            # 日付指定がない場合は今日
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # 自動で実際の結果を取得・更新
            self._auto_update_results(tracker)
            
            # 的中率計算（日付指定対応）
            accuracy_data = tracker.calculate_accuracy(target_date=date)
            
            # ROI評価を追加
            roi_data = None
            try:
                from roi_evaluation_system import ROIEvaluationSystem
                roi_system = ROIEvaluationSystem()
                roi_data = roi_system.get_roi_report(days=7)
            except Exception as e:
                logger.warning(f"ROI評価エラー: {e}")
                roi_data = None
            
            # 日付フォーマット
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            current_date_formatted = date_obj.strftime('%Y年%m月%d日')
            
            return render_template('accuracy_report.html',
                                 summary=accuracy_data['summary'],
                                 races=accuracy_data['races'],
                                 venues=accuracy_data['venues'],
                                 roi_data=roi_data,
                                 current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'),
                                 current_date=date,
                                 current_date_formatted=current_date_formatted,
                                 today=datetime.now().strftime('%Y-%m-%d'),
                                 auto_updated=True)
        
        except Exception as e:
            logger.error(f"的中率レポートエラー: {e}")
            return render_template('accuracy_report.html',
                                 summary=None,
                                 races=[],
                                 venues=VENUE_MAPPING,
                                 roi_data=None,
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
                        # レースが実際に終了しているかを判定（発走時間＋15分後）
                        race_finished = False
                        
                        # データベースからrace_dataを取得してstart_timeをチェック
                        cursor.execute("""
                            SELECT race_data FROM race_details 
                            WHERE venue_id = ? AND race_number = ? AND race_date = ?
                        """, (venue_id, race_number, race_date))
                        
                        race_data_row = cursor.fetchone()
                        if race_data_row and race_data_row[0]:
                            try:
                                race_data = json.loads(race_data_row[0])
                                start_time_str = race_data.get('race_closed_at')
                                
                                if start_time_str:
                                    # start_time_strは "2025-08-25 15:19:00" 形式
                                    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                                    # 15分のマージンを追加（レース終了まで）
                                    race_end_time = start_time + timedelta(minutes=15)
                                    race_finished = current_time >= race_end_time
                            except (json.JSONDecodeError, ValueError, TypeError):
                                race_finished = False
                        
                        if race_finished:
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
        """レースソートキー（完全タイムスタンプ対応版）"""
        # 発走時刻を解析して時間順にソート
        start_time = race['start_time']
        if start_time == '未定' or not start_time:
            time_value = 99999  # 未定は最後
        else:
            try:
                # 完全なタイムスタンプ形式（YYYY-MM-DD HH:MM:SS）に対応
                if ' ' in start_time:
                    # "2025-08-25 15:19:00" 形式
                    time_part = start_time.split(' ')[1]  # "15:19:00"
                    time_parts = time_part.split(':')
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    time_value = hours * 60 + minutes
                elif ':' in start_time:
                    # "HH:MM" または "HH:MM:SS" 形式
                    time_parts = start_time.split(':')
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
                
                # 単一インスタンス再利用（初期化コスト削減）
                if self._enhanced_predictor_instance is None:
                    self._enhanced_predictor_instance = self.EnhancedPredictor()
                
                prediction = self._enhanced_predictor_instance.calculate_enhanced_prediction(venue_id, race_number, 'today')
                
                if not prediction:
                    logger.warning(f"並列計算でEnhancedPredictor失敗、フォールバック使用: {venue_id}_{race_number}")
                    prediction = calculate_prediction(race_data)
                elif race_key == '14_9':  # 鳴門9Rのデバッグ
                    logger.info(f"並列計算 鳴門9R: 推奨={prediction.get('recommended_win')}, 複勝={prediction.get('recommended_place')}, 信頼度={prediction.get('confidence', 0):.6f}")
                elif race_key == '22_1':  # 福岡1Rのデバッグ
                    logger.info(f"並列計算 福岡1R: 推奨={prediction.get('recommended_win')}, 複勝={prediction.get('recommended_place')}, 信頼度={prediction.get('confidence', 0):.6f}")
                elif race_key == '6_3':  # 浜名湖3Rのデバッグ
                    logger.info(f"並列計算 浜名湖3R: 推奨={prediction.get('recommended_win')}, 複勝={prediction.get('recommended_place')}, 信頼度={prediction.get('confidence', 0):.6f}")
                
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
    
    def get_enhanced_prediction(self, race_key):
        """個別レースの詳細予想を遅延ロードで取得"""
        try:
            parts = race_key.split('_')
            if len(parts) != 2:
                return jsonify({'success': False, 'error': '不正なレースキー'})
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            
            # EnhancedPredictorの単一インスタンスを使用
            if self._enhanced_predictor_instance is None:
                self._enhanced_predictor_instance = self.EnhancedPredictor()
            
            prediction = self._enhanced_predictor_instance.calculate_enhanced_prediction(
                venue_id, race_number, 'today'
            )
            
            if not prediction:
                # フォールバック予想
                prediction = {
                    'predicted_win': 1,
                    'predicted_place': [1, 2, 3],
                    'confidence': 0.5
                }
            
            return jsonify({
                'success': True,
                'race_key': race_key,
                'prediction': normalize_prediction_data(prediction)
            })
            
        except Exception as e:
            logger.error(f"詳細予想遅延ロードエラー {race_key}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
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
    
    def api_investment_dashboard(self):
        """投資ダッシュボードAPI"""
        try:
            from advanced_investment_strategy import AdvancedInvestmentStrategy
            
            strategy = AdvancedInvestmentStrategy()
            
            # 現在の投資状況
            investment_status = {
                'current_bankroll': strategy.current_bankroll,
                'daily_spent': strategy.daily_spent,
                'win_streak': strategy.win_streak,
                'loss_streak': strategy.consecutive_loss_count,
                'daily_limit': strategy.current_bankroll * strategy.daily_limit,
                'performance_metrics': strategy.performance_metrics,
                'recommended_strategy': strategy.get_strategy_recommendation()
            }
            
            # 過去7日間の収支データ
            conn = sqlite3.connect(strategy.db_path)
            cursor = conn.cursor()
            
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT date_str, SUM(profit_loss) as daily_profit,
                       COUNT(*) as daily_bets, AVG(roi) as daily_roi
                FROM investment_history 
                WHERE date_str >= ?
                GROUP BY date_str
                ORDER BY date_str
            ''', (seven_days_ago,))
            
            daily_data = cursor.fetchall()
            conn.close()
            
            investment_status['daily_performance'] = [
                {
                    'date': row[0],
                    'profit': row[1] or 0,
                    'bets': row[2] or 0,
                    'roi': row[3] or 0.0
                } for row in daily_data
            ]
            
            return jsonify({
                'success': True,
                'investment_data': investment_status
            })
            
        except Exception as e:
            logger.error(f"投資ダッシュボードエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_confidence_visualization(self, race_key):
        """予想信頼度可視化API"""
        try:
            parts = race_key.split('_')
            if len(parts) != 2:
                return jsonify({'success': False, 'error': '不正なレースキー'})
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            
            # 高度予想システムの統合
            from advanced_ensemble_system import AdvancedEnsembleSystem
            from realtime_data_integration import RealtimeDataIntegration
            
            ensemble = AdvancedEnsembleSystem()
            realtime = RealtimeDataIntegration()
            
            # レースデータ取得
            data = run_async_in_thread(self.fetcher.get_today_races_async())
            race_data = None
            
            for program in data.get('programs', []):
                if (program['race_stadium_number'] == venue_id and 
                    program['race_number'] == race_number):
                    race_data = program
                    break
            
            if not race_data:
                return jsonify({'success': False, 'error': 'レースデータが見つかりません'})
            
            # 複数予想手法の結果を取得
            predictions = {}
            
            # 統一信頼度を取得
            unified_confidence = confidence_unifier.get_unified_confidence(
                venue_id, race_number, race_data
            )
            
            # 1. 統一基本予想（統一信頼度を使用）
            basic_prediction = calculate_prediction(race_data)
            predictions['basic'] = {
                'win': basic_prediction.get('predicted_win', 1),
                'confidence': unified_confidence * 100,  # 統一信頼度を使用
                'method': 'Unified Basic Statistics'
            }
            
            # 2. アンサンブル予想
            try:
                ensemble_prediction = ensemble.predict(race_data)
                predictions['ensemble'] = {
                    'win': ensemble_prediction.get('win', 1),
                    'confidence': ensemble_prediction.get('confidence', 50.0),
                    'method': ensemble_prediction.get('method', 'Ensemble'),
                    'model_weights': ensemble_prediction.get('model_weights', {})
                }
            except:
                predictions['ensemble'] = predictions['basic'].copy()
                predictions['ensemble']['method'] = 'Ensemble (Fallback)'
            
            # 3. リアルタイム統合予想（統一信頼度ベース）
            try:
                realtime_data = run_async_in_thread(
                    realtime.get_integrated_data(venue_id, race_number)
                )
                confidence_boost = realtime_data.get('confidence_boost', 1.0)
                
                # 統一信頼度にリアルタイム補正を適用
                boosted_confidence = min(95.0, unified_confidence * 100 * confidence_boost)
                
                predictions['realtime'] = {
                    'win': predictions['basic']['win'],
                    'confidence': boosted_confidence,
                    'method': 'Unified Realtime Enhanced',
                    'boost_factor': confidence_boost,
                    'base_confidence': unified_confidence * 100,
                    'weather_impact': realtime_data.get('weather', {}).get('racing_impact', {}),
                    'recommendations': realtime_data.get('recommendations', {})
                }
            except:
                predictions['realtime'] = predictions['basic'].copy()
                predictions['realtime']['method'] = 'Unified Realtime (Fallback)'
            
            # 信頼度レベル分類
            def get_confidence_level(confidence):
                if confidence >= 80:
                    return {'level': 'very_high', 'color': '#4CAF50', 'label': '非常に高い'}
                elif confidence >= 65:
                    return {'level': 'high', 'color': '#8BC34A', 'label': '高い'}
                elif confidence >= 50:
                    return {'level': 'medium', 'color': '#FFC107', 'label': '普通'}
                elif confidence >= 35:
                    return {'level': 'low', 'color': '#FF9800', 'label': '低い'}
                else:
                    return {'level': 'very_low', 'color': '#F44336', 'label': '非常に低い'}
            
            # 可視化データ構築
            visualization_data = {
                'race_key': race_key,
                'venue_name': VENUE_MAPPING.get(venue_id, '不明'),
                'race_number': race_number,
                'predictions': []
            }
            
            for method, pred_data in predictions.items():
                confidence_info = get_confidence_level(pred_data['confidence'])
                visualization_data['predictions'].append({
                    'method': pred_data['method'],
                    'win_prediction': pred_data['win'],
                    'confidence': pred_data['confidence'],
                    'confidence_level': confidence_info,
                    'additional_data': pred_data.get('model_weights') or pred_data.get('boost_factor') or {}
                })
            
            # 総合推奨（統一信頼度ベース）
            # 統一信頼度を基準として、各手法の補正値を加味
            base_confidence = unified_confidence * 100
            
            # 最も高い信頼度を持つ手法を特定
            most_confident = max(predictions.values(), key=lambda x: x['confidence'])
            
            # 統一信頼度を使用した総合判定
            visualization_data['summary'] = {
                'recommended_win': most_confident['win'],
                'average_confidence': base_confidence,  # 統一信頼度をベースに
                'confidence_level': get_confidence_level(base_confidence),
                'best_method': most_confident['method'],
                'consensus': len(set(p['win'] for p in predictions.values())) == 1,
                'unified_base': unified_confidence,
                'prediction_variants': {
                    method: pred['confidence'] for method, pred in predictions.items()
                }
            }
            
            return jsonify({
                'success': True,
                'visualization': visualization_data
            })
            
        except Exception as e:
            logger.error(f"信頼度可視化エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_bet_recommendation(self, race_key):
        """推奨ベット金額API"""
        try:
            parts = race_key.split('_')
            if len(parts) != 2:
                return jsonify({'success': False, 'error': '不正なレースキー'})
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            
            # 予想データ取得
            confidence_data = self.api_confidence_visualization(race_key)
            if not confidence_data.json.get('success'):
                return jsonify({'success': False, 'error': '予想データ取得失敗'})
            
            visualization = confidence_data.json['visualization']
            summary = visualization['summary']
            
            # 投資戦略システム
            from advanced_investment_strategy import AdvancedInvestmentStrategy
            
            strategy_system = AdvancedInvestmentStrategy()
            
            # 予想データを投資システム用に変換
            race_prediction = {
                'win': summary['recommended_win'],
                'place': [summary['recommended_win'], summary['recommended_win'] % 6 + 1],
                'trifecta': [summary['recommended_win'], summary['recommended_win'] % 6 + 1, (summary['recommended_win'] + 1) % 6 + 1],
                'confidence': summary['average_confidence'],
                'estimated_odds': 5.0 - (summary['average_confidence'] / 25.0)  # 信頼度からオッズ推定
            }
            
            # 各戦略での推奨ベット額計算
            strategies = ['conservative', 'moderate', 'aggressive']
            recommendations = {}
            
            for strategy_name in strategies:
                bet_result = strategy_system.calculate_optimal_bet(race_prediction, strategy_name)
                
                recommendations[strategy_name] = {
                    'total_bet': bet_result['total_bet'],
                    'diversified_bets': bet_result['diversified_bets'],
                    'expected_roi': bet_result['estimated_roi'],
                    'risk_level': bet_result['risk_level'],
                    'kelly_fraction': bet_result['kelly_fraction']
                }
            
            # 現在の推奨戦略
            recommended_strategy_name = strategy_system.get_strategy_recommendation()
            recommended_bet = recommendations[recommended_strategy_name]
            
            return jsonify({
                'success': True,
                'race_key': race_key,
                'current_bankroll': strategy_system.current_bankroll,
                'recommended_strategy': recommended_strategy_name,
                'recommended_bet': recommended_bet,
                'all_strategies': recommendations,
                'risk_warnings': self._generate_risk_warnings(strategy_system, summary['average_confidence'])
            })
            
        except Exception as e:
            logger.error(f"ベット推奨エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def _generate_risk_warnings(self, strategy_system, confidence):
        """リスク警告生成"""
        warnings = []
        
        if strategy_system.consecutive_loss_count >= 3:
            warnings.append(f"注意: 現在{strategy_system.consecutive_loss_count}連敗中です。慎重な投資を推奨します。")
        
        if strategy_system.current_bankroll < 5000:
            warnings.append("警告: 資金が少なくなっています。投資額を控えめにしてください。")
        
        if confidence < 60:
            warnings.append("注意: 予想信頼度が低めです。リスクを考慮した投資を行ってください。")
        
        daily_usage = strategy_system.daily_spent / (strategy_system.current_bankroll * strategy_system.daily_limit)
        if daily_usage > 0.8:
            warnings.append("警告: 本日の投資限度額の80%を超過しています。")
        
        return warnings
    
    def api_realtime_alerts(self):
        """リアルタイムアラートAPI"""
        try:
            from realtime_data_integration import RealtimeDataIntegration
            
            realtime = RealtimeDataIntegration()
            alerts = []
            
            # 今日のレース一覧を取得
            data = run_async_in_thread(self.fetcher.get_today_races_async())
            current_time = datetime.now()
            
            for program in data.get('programs', []):
                venue_id = program['race_stadium_number']
                race_number = program['race_number']
                start_time = program.get('race_closed_at', '')
                
                # 30分以内に開始するレースをチェック
                race_time = self._parse_race_time(start_time, current_time)
                if not race_time:
                    continue
                
                time_diff = (race_time - current_time).total_seconds() / 60
                if 5 <= time_diff <= 30:  # 5-30分前
                    # 高信頼度予想をチェック
                    confidence_data = self.api_confidence_visualization(f"{venue_id}_{race_number}")
                    if confidence_data.json.get('success'):
                        visualization = confidence_data.json['visualization']
                        avg_confidence = visualization['summary']['average_confidence']
                        
                        if avg_confidence >= 75:  # 高信頼度
                            venue_name = VENUE_MAPPING.get(venue_id, '不明')
                            alerts.append({
                                'type': 'high_confidence',
                                'title': f'高信頼度レース発見',
                                'message': f'{venue_name} {race_number}R - 信頼度{avg_confidence:.1f}%',
                                'race_key': f"{venue_id}_{race_number}",
                                'venue_name': venue_name,
                                'race_number': race_number,
                                'confidence': avg_confidence,
                                'start_time': start_time,
                                'minutes_until_start': int(time_diff),
                                'recommended_win': visualization['summary']['recommended_win']
                            })
            
            # 投資状況アラート
            from advanced_investment_strategy import AdvancedInvestmentStrategy
            strategy = AdvancedInvestmentStrategy()
            
            if strategy.consecutive_loss_count >= 5:
                alerts.append({
                    'type': 'loss_streak_warning',
                    'title': '連敗注意報',
                    'message': f'現在{strategy.consecutive_loss_count}連敗中です。投資戦略の見直しを検討してください。',
                    'severity': 'high'
                })
            
            if strategy.current_bankroll < 3000:
                alerts.append({
                    'type': 'low_bankroll_warning',
                    'title': '資金不足警告',
                    'message': f'残り資金が{strategy.current_bankroll}円と少なくなっています。',
                    'severity': 'high'
                })
            
            return jsonify({
                'success': True,
                'alerts': alerts,
                'alert_count': len(alerts)
            })
            
        except Exception as e:
            logger.error(f"リアルタイムアラートエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def enhanced_dashboard(self):
        """統合ダッシュボードページ"""
        return render_template('enhanced_dashboard.html')
    
    def debug_confidence(self, race_key):
        """信頼度デバッグAPI"""
        try:
            parts = race_key.split('_')
            if len(parts) != 2:
                return jsonify({'success': False, 'error': '不正なレースキー'})
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            
            # レースデータ取得
            data = run_async_in_thread(self.fetcher.get_today_races_async())
            race_data = None
            
            for program in data.get('programs', []):
                if (program['race_stadium_number'] == venue_id and 
                    program['race_number'] == race_number):
                    race_data = program
                    break
            
            # 詳細信頼度分析
            analysis = confidence_unifier.get_detailed_confidence_analysis(
                venue_id, race_number, race_data
            )
            
            # 従来システムの信頼度も取得
            legacy_confidence = None
            if race_data:
                legacy_prediction = calculate_prediction(race_data)
                legacy_confidence = legacy_prediction.get('confidence', 0.5)
            
            debug_info = {
                'race_key': race_key,
                'venue_name': VENUE_MAPPING.get(venue_id, '不明'),
                'race_number': race_number,
                'unified_analysis': analysis,
                'legacy_confidence': legacy_confidence,
                'comparison': {
                    'unified_vs_legacy': {
                        'unified': analysis['unified_confidence'],
                        'legacy': legacy_confidence,
                        'difference': abs(analysis['unified_confidence'] - (legacy_confidence or 0.5)),
                        'match': abs(analysis['unified_confidence'] - (legacy_confidence or 0.5)) < 0.01
                    }
                },
                'confidence_sources': {
                    source: confidence for source, confidence in analysis['sources'].items()
                },
                'primary_source': analysis['primary_source'],
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify({
                'success': True,
                'debug_info': debug_info
            })
            
        except Exception as e:
            logger.error(f"信頼度デバッグエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })