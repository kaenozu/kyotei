#!/usr/bin/env python3
"""
スケジューラーサービス
AM6時の自動データ取得と的中率レポート連携
"""

import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
import requests
import json
import sqlite3
import os
import sys

# 必要なモジュールのパス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from src.core.accuracy_tracker import AccuracyTracker
    from enhanced_predictor import EnhancedPredictor
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SchedulerService:
    """自動データ取得・更新スケジューラー"""
    
    def __init__(self):
        self.tracker = AccuracyTracker()
        self.predictor = EnhancedPredictor()
        self.is_running = False
        self.thread = None
        
        # ログディレクトリ作成
        os.makedirs('logs', exist_ok=True)
        
        logger.info("スケジューラーサービス初期化完了")
    
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
        
        # 毎時間、前日の結果データを確認・更新
        schedule.every().hour.do(self.update_results_if_available)
        
        # 毎日PM11時に的中率レポート更新
        schedule.every().day.at("23:00").do(self.update_accuracy_report)
        
        # バックグラウンドで実行
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("スケジューラー開始: AM6時データ取得, 毎時結果更新, PM11時レポート更新")
    
    def stop(self):
        """スケジューラー停止"""
        self.is_running = False
        schedule.clear()
        logger.info("スケジューラー停止")
    
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
        logger.info("=== AM6時 自動データ収集開始 ===")
        
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # 1. 本日分の予測データを生成・保存
            self._collect_daily_predictions(current_date)
            
            # 2. 前日の結果データを取得・更新（可能な場合）
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            self._collect_results_data(yesterday)
            
            # 3. 的中率レポート更新
            self._update_accuracy_statistics()
            
            logger.info("=== AM6時 自動データ収集完了 ===")
            
        except Exception as e:
            logger.error(f"AM6時データ収集エラー: {e}")
    
    def _collect_daily_predictions(self, target_date: str):
        """本日分の全レース予測データを生成・保存"""
        try:
            # Programs APIから本日のレースデータを取得
            url = "https://boatraceopenapi.github.io/programs/v2/today.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Programs API取得失敗: {response.status_code}")
                return
            
            data = response.json()
            programs = data.get('programs', [])
            
            logger.info(f"本日のレース数: {len(programs)}件")
            
            prediction_count = 0
            for program in programs:
                try:
                    venue_id = program['race_stadium_number']
                    race_number = program['race_number']
                    
                    # 強化予想システムで予測
                    prediction = self.predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
                    
                    if prediction:
                        # データベースに保存
                        self.tracker.save_prediction(program, prediction)
                        self.tracker.save_race_details(program, prediction)
                        prediction_count += 1
                    
                except Exception as e:
                    logger.warning(f"予測生成エラー {venue_id}-{race_number}: {e}")
                    continue
            
            logger.info(f"予測データ生成・保存完了: {prediction_count}件")
            
        except Exception as e:
            logger.error(f"予測データ収集エラー: {e}")
    
    def _collect_results_data(self, target_date: str):
        """指定日の結果データを取得・保存"""
        try:
            # Results APIから結果データを取得
            if target_date == datetime.now().strftime('%Y-%m-%d'):
                url = "https://boatraceopenapi.github.io/results/v2/today.json"
            else:
                # 過去データの場合は todayしか利用できないため、制限あり
                logger.info(f"過去データ({target_date})は今日以外取得できません")
                return
            
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Results API取得失敗: {response.status_code}")
                return
            
            data = response.json()
            results = data.get('results', [])
            
            logger.info(f"結果データ取得: {len(results)}件")
            
            result_count = 0
            with sqlite3.connect(self.tracker.db_path) as conn:
                cursor = conn.cursor()
                
                for race in results:
                    try:
                        venue_id = race.get('race_stadium_number')
                        race_number = race.get('race_number')
                        venue_name = self.tracker.venue_mapping.get(venue_id, '不明')
                        
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
                                (race_date, venue_id, venue_name, race_number, winning_boat, place_results, result_data, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (target_date, venue_id, venue_name, race_number, winning_boat,
                                  json.dumps(place_results), json.dumps(race), datetime.now().isoformat()))
                            
                            # 対応する予測データがあれば的中記録を作成
                            cursor.execute('''
                                SELECT id, predicted_win, predicted_place FROM predictions
                                WHERE race_date = ? AND venue_id = ? AND race_number = ?
                            ''', (target_date, venue_id, race_number))
                            
                            pred_row = cursor.fetchone()
                            if pred_row:
                                pred_id, predicted_win, predicted_place_json = pred_row
                                result_id = cursor.lastrowid
                                
                                is_win_hit = (predicted_win == winning_boat)
                                predicted_place_list = json.loads(predicted_place_json) if predicted_place_json else []
                                is_place_hit = any(boat in place_results[:2] for boat in predicted_place_list[:2])
                                
                                cursor.execute('''
                                    INSERT OR REPLACE INTO accuracy_records 
                                    (prediction_id, result_id, is_win_hit, is_place_hit, hit_status, timestamp)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (pred_id, result_id, is_win_hit, is_place_hit,
                                      'hit' if is_win_hit else 'miss', datetime.now().isoformat()))
                            
                            result_count += 1
                    
                    except Exception as e:
                        logger.warning(f"結果処理エラー {venue_id}-{race_number}: {e}")
                        continue
                
                conn.commit()
            
            logger.info(f"結果データ保存完了: {result_count}件")
            
        except Exception as e:
            logger.error(f"結果データ収集エラー: {e}")
    
    def update_results_if_available(self):
        """毎時実行: 利用可能な結果データを更新"""
        try:
            current_time = datetime.now()
            current_date = current_time.strftime('%Y-%m-%d')
            
            # 現在時刻が17時以降の場合のみ結果データを取得
            if current_time.hour >= 17:
                logger.info("結果データ更新チェック実行")
                self._collect_results_data(current_date)
            else:
                logger.debug("結果データ更新スキップ（17時前）")
                
        except Exception as e:
            logger.error(f"結果データ更新エラー: {e}")
    
    def update_accuracy_report(self):
        """PM11時: 的中率レポート更新"""
        try:
            logger.info("=== PM11時 的中率レポート更新開始 ===")
            
            # 的中率統計を更新
            self._update_accuracy_statistics()
            
            logger.info("=== PM11時 的中率レポート更新完了 ===")
            
        except Exception as e:
            logger.error(f"的中率レポート更新エラー: {e}")
    
    def _update_accuracy_statistics(self):
        """的中率統計を更新・計算"""
        try:
            accuracy_data = self.tracker.calculate_accuracy()
            
            summary = accuracy_data['summary']
            logger.info(f"的中率統計: 予想数={summary['total_predictions']}, "
                       f"的中数={summary['win_hits']}, 的中率={summary['win_accuracy']}%")
            
            # 的中率データをファイルに保存（予測システムでの活用のため）
            accuracy_file = 'cache/latest_accuracy.json'
            with open(accuracy_file, 'w', encoding='utf-8') as f:
                json.dump(accuracy_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"的中率データ保存: {accuracy_file}")
            
        except Exception as e:
            logger.error(f"的中率統計更新エラー: {e}")
    
    def get_status(self) -> dict:
        """スケジューラー状態取得"""
        return {
            'is_running': self.is_running,
            'next_morning_job': schedule.next_run() if schedule.jobs else None,
            'total_jobs': len(schedule.jobs)
        }

# スタンドアロン実行用
if __name__ == '__main__':
    scheduler_service = SchedulerService()
    
    try:
        print("スケジューラーサービス開始...")
        scheduler_service.start()
        
        # メイン処理継続
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("スケジューラーサービス停止中...")
        scheduler_service.stop()
        print("スケジューラーサービス停止完了")