#!/usr/bin/env python3
"""
Admin Routes - 管理・その他ルート
的中率レポート、結果更新、デバッグ機能など
"""

import json
import sqlite3
import requests
import logging
import asyncio
from datetime import datetime, timedelta
from flask import jsonify, render_template, request

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_fetcher import VENUE_MAPPING

logger = logging.getLogger(__name__)

class AdminRoutes:
    """管理・その他ルートハンドラー"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class):
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        
        self._register_routes()
    
    def _register_routes(self):
        """管理関連ルートを登録"""
        self.app.add_url_rule('/accuracy', 'accuracy_report', self.accuracy_report)
        self.app.add_url_rule('/accuracy/<date>', 'accuracy_report_date', self.accuracy_report)
        self.app.add_url_rule('/api/update-results', 'api_update_results', self.api_update_results)
    
    def accuracy_report(self, date=None):
        """的中率レポート（日付別）"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            tracker = self.AccuracyTracker()
            
            # 指定日の的中率を計算
            accuracy_data = tracker.calculate_accuracy(date)
            
            # 指定日のレース一覧を取得
            race_list = []
            with sqlite3.connect(tracker.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT rd.venue_id, rd.venue_name, rd.race_number, rd.prediction_data,
                           rr.winning_boat, rr.place_results, rr.trifecta_result
                    FROM race_details rd
                    LEFT JOIN race_results rr ON rd.venue_id = rr.venue_id 
                        AND rd.race_number = rr.race_number 
                        AND rd.race_date = rr.race_date
                    WHERE rd.race_date = ?
                    ORDER BY rd.venue_id, rd.race_number
                """, (date,))
                
                for row in cursor.fetchall():
                    venue_id, venue_name, race_number, prediction_data_json, winning_boat, place_results_json, trifecta_result = row
                    
                    # 予想データ解析
                    prediction_data = {}
                    if prediction_data_json:
                        try:
                            prediction_data = json.loads(prediction_data_json)
                        except:
                            pass
                    
                    # 結果データ解析
                    place_results = []
                    if place_results_json:
                        try:
                            place_results = json.loads(place_results_json)
                        except:
                            pass
                    
                    # 的中判定
                    predicted_win = prediction_data.get('recommended_win') or prediction_data.get('predicted_win', 0)
                    predicted_place = prediction_data.get('recommended_place') or prediction_data.get('predicted_place', [])
                    predicted_trifecta = prediction_data.get('recommended_trifecta', '')
                    
                    is_win_hit = (winning_boat == predicted_win) if winning_boat else False
                    is_place_hit = False
                    is_trifecta_hit = False
                    
                    if place_results and len(place_results) >= 2:
                        if isinstance(predicted_place, list) and len(predicted_place) >= 2:
                            is_place_hit = (predicted_place[0] in place_results[:2] and 
                                          predicted_place[1] in place_results[:2])
                    
                    if trifecta_result and predicted_trifecta:
                        is_trifecta_hit = (predicted_trifecta == trifecta_result)
                    
                    race_info = {
                        'venue_id': venue_id,
                        'venue_name': venue_name or VENUE_MAPPING.get(venue_id, '不明'),
                        'race_number': race_number,
                        'race_id': f"{venue_id:02d}_{race_number:02d}_{date}",
                        'predicted_win': predicted_win,
                        'predicted_place': predicted_place,
                        'predicted_trifecta': predicted_trifecta,
                        'actual_win': winning_boat,
                        'actual_place': place_results,
                        'actual_trifecta': trifecta_result,
                        'is_win_hit': is_win_hit,
                        'is_place_hit': is_place_hit,
                        'is_trifecta_hit': is_trifecta_hit,
                        'confidence': prediction_data.get('confidence', 0),
                        'has_result': winning_boat is not None
                    }
                    race_list.append(race_info)
            
            # 前日・翌日のナビゲーション
            current_date = datetime.strptime(date, '%Y-%m-%d')
            prev_date = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
            next_date = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            return render_template('accuracy_report.html',
                                 date=date,
                                 prev_date=prev_date,
                                 next_date=next_date,
                                 is_today=(date == today),
                                 accuracy_data=accuracy_data,
                                 race_list=race_list,
                                 total_races=len(race_list))
        
        except Exception as e:
            logger.error(f"的中率レポートエラー: {e}")
            return render_template('accuracy_report.html',
                                 error=f"レポート生成エラー: {str(e)}",
                                 date=date or datetime.now().strftime('%Y-%m-%d'))
    
    def api_update_results(self):
        """結果データ更新API"""
        try:
            tracker = self.AccuracyTracker()
            
            # バックグラウンドで結果更新を実行
            async def update_results():
                try:
                    self._auto_update_results(tracker)
                    return {'success': True, 'message': '結果更新を開始しました'}
                except Exception as e:
                    logger.error(f"結果更新エラー: {e}")
                    return {'success': False, 'error': str(e)}
            
            # 非同期実行
            result = asyncio.run(update_results())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"結果更新APIエラー: {e}")
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
                            venue_name = VENUE_MAPPING.get(venue_id, '不明')
                            
                            # 三連単結果作成
                            trifecta_result = f"{place_results[0]}-{place_results[1]}-{place_results[2]}"
                            
                            # データベース更新
                            cursor.execute('''
                                INSERT OR REPLACE INTO race_results
                                (race_date, venue_id, venue_name, race_number, winning_boat, place_results, trifecta_result, result_data)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (datetime.now().strftime('%Y-%m-%d'), venue_id, venue_name, race_number,
                                  winning_boat, json.dumps(place_results), trifecta_result, '{"auto_updated": true}'))
                            
                            updated_count += 1
                    
                    conn.commit()
                
                if updated_count > 0:
                    logger.info(f"実際の結果を自動更新: {updated_count}件")
            
        except Exception as e:
            logger.warning(f"自動結果更新失敗: {e}")
            raise e