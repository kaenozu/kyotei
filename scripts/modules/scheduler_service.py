#!/usr/bin/env python3
"""
Scheduler Service
統合スケジューラーサービス（AM6:00自動データ収集・結果更新）
"""

import json
import logging
import sqlite3
import threading
import time
import os
import schedule
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class IntegratedScheduler:
    """Web アプリケーション統合スケジューラー"""
    
    def __init__(self, fetcher, accuracy_tracker_class, enhanced_predictor_class):
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        self.EnhancedPredictor = enhanced_predictor_class
        
        self.is_running = False
        self.thread = None
        
        # ログディレクトリ作成
        os.makedirs("logs", exist_ok=True)
        
        logger.info("統合スケジューラー初期化完了")
    
    def start(self):
        """スケジューラー開始"""
        if self.is_running:
            logger.warning("スケジューラーは既に実行中です")
            return
        
        self.is_running = True
        
        # スケジュール設定
        schedule.clear()
        
        # AM6時に本日分データ取得
        schedule.every().day.at("06:00").do(self.morning_data_collection)
        
        # 毎時間、結果データを確認・更新
        schedule.every().hour.do(self.update_results_if_available)
        
        # 毎日PM11時に的中率レポート更新
        schedule.every().day.at("23:00").do(self.update_accuracy_report)
        
        # バックグラウンドで実行
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("統合スケジューラー開始: AM6時データ取得, 毎時結果更新, PM11時レポート更新")
    
    def stop(self):
        """スケジューラー停止"""
        self.is_running = False
        schedule.clear()
        logger.info("統合スケジューラー停止")
    
    def _run_scheduler(self):
        """スケジューラーメインループ"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
            except Exception as e:
                logger.error(f"スケジューラーエラー: {e}")
                time.sleep(60)
    
    def morning_data_collection(self):
        """AM6時: 本日分データ収集"""
        try:
            logger.info("=== AM6時 自動データ収集開始 ===")
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # ML再学習チェック実行
            self.check_ml_retrain()
            
            # 本日分の予測データを生成・保存
            data = self.fetcher.get_today_races()
            if data and 'programs' in data:
                programs = data['programs']
                logger.info(f"本日のレース数: {len(programs)}件")
                
                prediction_count = 0
                for program in programs:
                    try:
                        venue_id = program['race_stadium_number']
                        race_number = program['race_number']
                        
                        # 強化予想システムで予測
                        enhanced_predictor = self.EnhancedPredictor()
                        prediction = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
                        
                        if prediction:
                            # データベースに保存
                            tracker = self.AccuracyTracker()
                            tracker.save_prediction(program, prediction)
                            tracker.save_race_details(program, prediction)
                            prediction_count += 1
                        
                    except Exception as e:
                        logger.warning(f"予測生成エラー {venue_id}-{race_number}: {e}")
                        continue
                
                logger.info(f"予測データ生成・保存完了: {prediction_count}件")
            
            # 的中率データファイルを更新
            self.update_accuracy_report()
            
            logger.info("=== AM6時 自動データ収集完了 ===")
            
        except Exception as e:
            logger.error(f"AM6時データ収集エラー: {e}")
    
    def update_results_if_available(self):
        """毎時実行: 利用可能な結果データを更新"""
        try:
            current_time = datetime.now()
            
            # 現在時刻が17時以降の場合のみ結果データを取得
            if current_time.hour >= 17:
                logger.info("結果データ更新チェック実行")
                
                # 結果APIから取得
                results_url = 'https://boatraceopenapi.github.io/results/v2/today.json'
                response = requests.get(results_url, timeout=10)
                
                if response.status_code == 200:
                    results_data = response.json()
                    results = results_data.get('results', [])
                    
                    result_count = 0
                    tracker = self.AccuracyTracker()
                    current_date = current_time.strftime('%Y-%m-%d')
                    
                    with sqlite3.connect(tracker.db_path) as conn:
                        cursor = conn.cursor()
                        
                        for race in results:
                            try:
                                venue_id = race.get('race_stadium_number')
                                race_number = race.get('race_number')
                                venue_name = tracker.venue_mapping.get(venue_id, '不明')
                                
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
                                    
                                    # データベースに結果を保存
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO race_results
                                        (race_date, venue_id, venue_name, race_number, winning_boat, place_results, result_data)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', (current_date, venue_id, venue_name, race_number, winning_boat,
                                          json.dumps(place_results), json.dumps(race)))
                                    
                                    # 対応する予測データがあれば的中記録を作成
                                    cursor.execute('''
                                        SELECT id, predicted_win, predicted_place FROM predictions
                                        WHERE race_date = ? AND venue_id = ? AND race_number = ?
                                    ''', (current_date, venue_id, race_number))
                                    
                                    pred_row = cursor.fetchone()
                                    if pred_row:
                                        pred_id, predicted_win, predicted_place_json = pred_row
                                        result_id = cursor.lastrowid
                                        
                                        is_win_hit = (predicted_win == winning_boat)
                                        predicted_place_list = json.loads(predicted_place_json) if predicted_place_json else []
                                        is_place_hit = any(boat in place_results[:2] for boat in predicted_place_list[:2])
                                        
                                        cursor.execute('''
                                            INSERT OR REPLACE INTO accuracy_records 
                                            (prediction_id, result_id, is_win_hit, is_place_hit, hit_status, calculated_at)
                                            VALUES (?, ?, ?, ?, ?, ?)
                                        ''', (pred_id, result_id, is_win_hit, is_place_hit,
                                              'hit' if is_win_hit else 'miss', datetime.now().isoformat()))
                                    
                                    result_count += 1
                            
                            except Exception as e:
                                logger.warning(f"結果処理エラー {venue_id}-{race_number}: {e}")
                                continue
                        
                        conn.commit()
                    
                    if result_count > 0:
                        logger.info(f"結果データ更新完了: {result_count}件")
            else:
                logger.debug("結果データ更新スキップ（17時前）")
                
        except Exception as e:
            logger.error(f"結果データ更新エラー: {e}")
    
    def check_ml_retrain(self):
        """ML再学習チェック"""
        try:
            logger.info("ML再学習チェック実行")
            
            # EnhancedPredictorを初期化し、ML再学習チェック実行
            enhanced_predictor = self.EnhancedPredictor()
            
            # MLPredictorがある場合は再学習チェック
            if hasattr(enhanced_predictor, 'ml_predictor') and enhanced_predictor.ml_predictor:
                enhanced_predictor.ml_predictor.retrain_if_needed()
                logger.info("ML再学習チェック完了")
            else:
                logger.info("ML予想システム無効のため、再学習チェックをスキップ")
                
        except Exception as e:
            logger.error(f"ML再学習チェックエラー: {e}")
    
    def update_accuracy_report(self):
        """PM11時: 的中率レポート更新"""
        try:
            logger.info("的中率レポート更新実行")
            
            # 的中率統計を更新
            tracker = self.AccuracyTracker()
            accuracy_data = tracker.calculate_accuracy()
            
            summary = accuracy_data['summary']
            logger.info(f"的中率統計: 予想数={summary['total_predictions']}, "
                       f"的中数={summary['win_hits']}, 的中率={summary['win_accuracy']}%")
            
            # 的中率データをファイルに保存（予測システムでの活用のため）
            accuracy_file = 'cache/latest_accuracy.json'
            with open(accuracy_file, 'w', encoding='utf-8') as f:
                json.dump(accuracy_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"的中率データ保存: {accuracy_file}")
            
        except Exception as e:
            logger.error(f"的中率レポート更新エラー: {e}")

def create_scheduler_routes(app, scheduler):
    """スケジューラー関連のAPIルートを作成"""
    from flask import jsonify
    
    @app.route('/api/scheduler/start')
    def api_scheduler_start():
        """スケジューラー開始API"""
        try:
            scheduler.start()
            return jsonify({
                'success': True,
                'message': 'スケジューラーを開始しました'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })

    @app.route('/api/scheduler/stop')
    def api_scheduler_stop():
        """スケジューラー停止API"""
        try:
            scheduler.stop()
            return jsonify({
                'success': True,
                'message': 'スケジューラーを停止しました'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })

    @app.route('/api/scheduler/status')
    def api_scheduler_status():
        """スケジューラー状態確認API"""
        try:
            next_run = None
            if schedule.jobs:
                next_run = min(job.next_run for job in schedule.jobs).isoformat() if schedule.jobs else None
            
            return jsonify({
                'success': True,
                'is_running': scheduler.is_running,
                'total_jobs': len(schedule.jobs),
                'next_run': next_run
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })