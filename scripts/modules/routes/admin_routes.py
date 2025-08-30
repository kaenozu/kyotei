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
        self.app.add_url_rule('/api/update-results', 'api_update_results', self.api_update_results, methods=['POST', 'GET'])
        self.app.add_url_rule('/api/update-results/<date>', 'api_update_results_date', self.api_update_results_for_date, methods=['POST', 'GET'])
        self.app.add_url_rule('/api/clear-test-results', 'api_clear_test_results', self.api_clear_test_results, methods=['POST', 'GET'])
    
    def accuracy_report(self, date=None):
        """的中率レポート（日付別）"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            tracker = self.AccuracyTracker()
            
            # 指定日の的中率を計算
            accuracy_data = tracker.calculate_accuracy(date)
            
            # AccuracyTrackerの結果を直接使用（重複処理を避ける）
            race_list = accuracy_data.get('races', [])
            logger.info(f"デバッグ: race_list長さ={len(race_list)}, 最初のレース={race_list[0] if race_list else 'なし'}")
            
            # 完全なデータ（発走時間+予想+結果）が存在する前日・翌日を検索
            current_date = datetime.strptime(date, '%Y-%m-%d')
            prev_date = self._find_previous_data_date(current_date, tracker)
            next_date = self._find_next_data_date(current_date, tracker)
            today = datetime.now().strftime('%Y-%m-%d')
            
            return render_template('accuracy_report.html',
                                 date=date,
                                 current_date=date,
                                 prev_date=prev_date,
                                 next_date=next_date,
                                 is_today=(date == today),
                                 accuracy_data={
                                     'summary': accuracy_data.get('summary'),
                                     'races': race_list,
                                     'venues': VENUE_MAPPING
                                 },
                                 summary=accuracy_data.get('summary'),
                                 races=race_list,
                                 total_races=len(race_list),
                                 venues=VENUE_MAPPING)
        
        except Exception as e:
            logger.error(f"的中率レポートエラー: {e}")
            error_date = date or datetime.now().strftime('%Y-%m-%d')
            return render_template('accuracy_report.html',
                                 error=f"レポート生成エラー: {str(e)}",
                                 date=error_date,
                                 current_date=error_date,
                                 prev_date=None,
                                 next_date=None,
                                 is_today=False,
                                 accuracy_data={
                                     'summary': {},
                                     'races': [],
                                     'venues': VENUE_MAPPING
                                 },
                                 venues=VENUE_MAPPING)
    
    def api_update_results(self):
        """結果データ更新API"""
        try:
            tracker = self.AccuracyTracker()
            
            # 直接実行（非同期処理を削除）
            try:
                updated_count = self._auto_update_results(tracker)
                return jsonify({
                    'success': True, 
                    'message': f'結果更新完了: {updated_count}件更新されました'
                })
            except Exception as e:
                logger.error(f"結果更新エラー: {e}")
                return jsonify({
                    'success': False, 
                    'error': str(e)
                })
            
        except Exception as e:
            logger.error(f"結果更新APIエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_update_results_for_date(self, date):
        """指定日の結果データ更新API"""
        try:
            tracker = self.AccuracyTracker()
            
            # 日付形式検証
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': '無効な日付形式です (YYYY-MM-DD)'
                })
            
            # 指定日の結果を更新
            updated_count = self._auto_update_results_for_date(tracker, date)
            return jsonify({
                'success': True, 
                'message': f'{date}の結果更新完了: {updated_count}件更新されました'
            })
            
        except Exception as e:
            logger.error(f"日付別結果更新APIエラー: {e}")
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
                    return updated_count
                else:
                    logger.info("更新対象のレース結果がありませんでした")
                    return 0
            else:
                logger.warning(f"結果データAPI失敗: HTTP {response.status_code}")
                return 0
            
        except Exception as e:
            logger.warning(f"自動結果更新失敗: {e}")
            raise e
    
    def api_clear_test_results(self):
        """不適切なテスト結果データを削除するAPI"""
        try:
            tracker = self.AccuracyTracker()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # テストデータまたは全ての結果データを削除
            with sqlite3.connect(tracker.db_path) as conn:
                cursor = conn.cursor()
                
                # race_results テーブルから今日のデータを削除
                cursor.execute('''
                    DELETE FROM race_results 
                    WHERE race_date = ?
                ''', (today,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
            logger.info(f"不適切な結果データを削除: {deleted_count}件")
            
            return jsonify({
                'success': True, 
                'message': f'不適切な結果データを削除しました: {deleted_count}件'
            })
            
        except Exception as e:
            logger.error(f"結果データ削除エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def _auto_update_results_for_date(self, tracker, date):
        """指定日の結果を自動取得・更新"""
        try:
            logger.info(f"{date}の実際のレース結果を自動取得中...")
            
            # 指定日の結果を取得（BoatraceOpenAPIは今日のみ対応のため、別のAPIまたはデータソースを使用する必要がある）
            # 現在はtodayの結果のみ利用可能なため、今日の日付の場合のみ更新
            today = datetime.now().strftime('%Y-%m-%d')
            if date != today:
                logger.warning(f"{date}は今日ではないため、結果データの自動取得はスキップします")
                return 0
            
            # 今日の場合は通常の更新処理を実行
            return self._auto_update_results(tracker)
            
        except Exception as e:
            logger.warning(f"{date}の自動結果更新失敗: {e}")
            return 0
    
    def _find_previous_data_date(self, current_date, tracker):
        """完全なデータ（発走時間+予想+結果）が存在する前の日付を検索"""
        try:
            import sqlite3
            with sqlite3.connect('cache/accuracy_tracker.db') as conn:
                cursor = conn.cursor()
                # race_detailsとrace_resultsの両方にデータがある日付を検索
                cursor.execute('''
                    SELECT rd.race_date 
                    FROM race_details rd
                    INNER JOIN race_results rr ON rd.race_date = rr.race_date
                    WHERE rd.race_date < ? 
                      AND rd.prediction_data IS NOT NULL
                      AND rr.winning_boat IS NOT NULL
                    GROUP BY rd.race_date 
                    HAVING COUNT(DISTINCT rd.race_number) >= 10 
                       AND COUNT(DISTINCT rr.race_number) >= 5
                    ORDER BY rd.race_date DESC 
                    LIMIT 1
                ''', (current_date.strftime('%Y-%m-%d'),))
                
                result = cursor.fetchone()
                return result[0] if result else None
        except:
            return None
    
    def _find_next_data_date(self, current_date, tracker):
        """完全なデータ（発走時間+予想+結果）が存在する次の日付を検索"""
        try:
            import sqlite3
            with sqlite3.connect('cache/accuracy_tracker.db') as conn:
                cursor = conn.cursor()
                # race_detailsとrace_resultsの両方にデータがある日付を検索
                cursor.execute('''
                    SELECT rd.race_date 
                    FROM race_details rd
                    INNER JOIN race_results rr ON rd.race_date = rr.race_date
                    WHERE rd.race_date > ? 
                      AND rd.prediction_data IS NOT NULL
                      AND rr.winning_boat IS NOT NULL
                    GROUP BY rd.race_date 
                    HAVING COUNT(DISTINCT rd.race_number) >= 10 
                       AND COUNT(DISTINCT rr.race_number) >= 5
                    ORDER BY rd.race_date ASC 
                    LIMIT 1
                ''', (current_date.strftime('%Y-%m-%d'),))
                
                result = cursor.fetchone()
                return result[0] if result else None
        except:
            return None