#!/usr/bin/env python3
"""
API Fetcher - 互換性レイヤー（簡略版）
直接実装を含む互換性レイヤー
"""

# 既存の実装をここに直接配置

import requests
import json
import logging
import time
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

# 競艇場マッピング
VENUE_MAPPING = {
    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
    7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
    13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
    19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
}

class SimpleOpenAPIFetcher:
    """競艇公式データAPI専用データ取得クラス"""
    
    def __init__(self):
        self.programs_base_url = "https://boatraceopenapi.github.io/programs/v2"
        self.results_base_url = "https://boatraceopenapi.github.io/results/v2"
        self.cache_file = "cache/boatrace_openapi_cache.json"
        self.results_cache_file = "cache/boatrace_results_cache.json"
        self.cache_expiry = 300
        self.max_retries = 3
        self.retry_delay = 1.0
        os.makedirs("cache", exist_ok=True)
    
    def get_programs_for_date(self, date: str) -> Optional[List[Dict]]:
        """指定日のプログラムデータを取得"""
        try:
            # 今日の場合はtoday.jsonを使用
            today = datetime.now().strftime('%Y-%m-%d')
            if date == today:
                url = f"{self.programs_base_url}/today.json"
            else:
                # 日付から年を動的に取得してURLを生成
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                url = f"{self.programs_base_url}/{date_obj.year}/{date_obj.strftime('%Y%m%d')}.json"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                programs = data.get('programs', [])
                logger.info(f"{date}のプログラムデータ取得完了: {len(programs)}レース")
                return programs
            else:
                logger.warning(f"{date}のプログラムデータ取得失敗: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"{date}のプログラムデータ取得エラー: {e}")
            return []

    def get_today_races(self) -> Optional[Dict]:
        """今日のレース一覧を取得"""
        cached_data = self._load_cache()
        if cached_data:
            logger.info("キャッシュから今日のレースを取得")
            return cached_data
        
        try:
            url = f"{self.programs_base_url}/today.json"
            response = self._make_request(url)
            if response and response.status_code == 200:
                data = response.json()
                self._save_cache(data)
                logger.info(f"今日のレース取得成功: {len(data.get('programs', []))}件")
                return data
        except Exception as e:
            logger.error(f"今日のレース取得エラー: {e}")
        
        return None
    
    def get_race_detail(self, venue_id: int, race_number: int) -> Optional[Dict]:
        """特定レースの詳細情報を取得"""
        try:
            today_races = self.get_today_races()
            if not today_races or 'programs' not in today_races:
                return None
            
            for program in today_races['programs']:
                if (program.get('race_stadium_number') == venue_id and 
                    program.get('race_number') == race_number):
                    return program
            
            return None
        except Exception as e:
            logger.error(f"レース詳細取得エラー: {e}")
            return None
    
    def get_results_for_date(self, date: str) -> Optional[List[Dict]]:
        """指定日の結果データを取得"""
        try:
            # 今日の場合はtoday.jsonを使用
            today = datetime.now().strftime('%Y-%m-%d')
            if date == today:
                url = f"{self.results_base_url}/today.json"
            else:
                # 日付から年を動的に取得してURLを生成
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                url = f"{self.results_base_url}/{date_obj.year}/{date_obj.strftime('%Y%m%d')}.json"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                logger.info(f"{date}の結果データ取得完了: {len(results)}レース")
                return results
            else:
                logger.warning(f"{date}の結果データ取得失敗: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"{date}の結果データ取得エラー: {e}")
            return []

    def get_today_results(self) -> Optional[Dict]:
        """今日の結果一覧を取得"""
        cached_data = self._load_results_cache()
        if cached_data:
            logger.info("キャッシュから今日の結果を取得")
            return cached_data
        
        try:
            url = f"{self.results_base_url}/today.json"
            response = self._make_request(url)
            if response and response.status_code == 200:
                data = response.json()
                self._save_results_cache(data)
                logger.info(f"今日の結果取得成功: {len(data.get('results', []))}件")
                return data
        except Exception as e:
            logger.error(f"今日の結果取得エラー: {e}")
        
        return None

    def _load_results_cache(self) -> Optional[Dict]:
        """結果キャッシュ読み込み"""
        try:
            if not os.path.exists(self.results_cache_file):
                return None
            
            with open(self.results_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if 'timestamp' not in cache_data:
                return None
            
            if time.time() - cache_data['timestamp'] > self.cache_expiry:
                return None
            
            if cache_data.get('date') != datetime.now().strftime('%Y-%m-%d'):
                return None
            
            return cache_data.get('data')
        except Exception as e:
            logger.warning(f"結果キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_results_cache(self, data: Dict) -> None:
        """結果キャッシュ保存"""
        try:
            cache_data = {
                'timestamp': time.time(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'data': data
            }
            
            with open(self.results_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"結果キャッシュ保存エラー: {e}")
    
    def _load_cache(self) -> Optional[Dict]:
        """キャッシュ読み込み"""
        try:
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if 'timestamp' not in cache_data:
                return None
            
            if time.time() - cache_data['timestamp'] > self.cache_expiry:
                return None
            
            if cache_data.get('date') != datetime.now().strftime('%Y-%m-%d'):
                return None
            
            return cache_data.get('data')
        except Exception as e:
            logger.warning(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_cache(self, data: Dict) -> None:
        """キャッシュ保存"""
        try:
            cache_data = {
                'timestamp': time.time(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'data': data
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """HTTPリクエスト実行（リトライ付き）"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return response
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        return None

def calculate_prediction(race_data: Dict) -> Dict:
    """レースデータから予想を計算（改善版統合システム使用）"""
    try:
        if not race_data or 'racers' not in race_data:
            raise ValueError("レースデータが不正です")
        
        # 改善された統合予想システムを使用
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))
            
            from integrated_prediction_system import IntegratedPredictionSystem
            
            # 統合予想システム初期化
            prediction_system = IntegratedPredictionSystem()
            
            # レースデータから基本情報を抽出
            race_date = race_data.get('race_date', datetime.now().strftime('%Y-%m-%d'))
            venue_id = race_data.get('venue_id')
            race_number = race_data.get('race_number')
            
            if venue_id and race_number:
                # 統合システムで予想実行
                result = prediction_system.predict_race(race_date, venue_id, race_number)
                
                if result and 'boat_scores' in result:
                    # 統合システムの結果を旧形式に変換
                    predictions = {}
                    racer_info = []
                    
                    for boat_score in result['boat_scores']:
                        boat_number = boat_score['boat_number']
                        score = boat_score['score']
                        details = boat_score['details']
                        
                        predictions[boat_number] = score
                        racer_info.append({
                            'boat_number': boat_number,
                            'name': boat_score['racer_name'],
                            'prediction': round(score, 3),
                            'win_rate': details.get('nationwide_win_rate', 0),
                            'confidence': min(1.0, score)
                        })
                    
                    return {
                        'predictions': predictions,
                        'racers': racer_info,
                        'recommended_win': result['predicted_win'],
                        'recommended_place': result['predicted_place'],
                        'confidence': result['confidence']  # 改善された動的信頼度
                    }
        except Exception as integration_error:
            logger.warning(f"統合予想システム使用失敗、フォールバック実行: {integration_error}")
        
        # フォールバック: 改善された簡易システム
        racers = race_data['racers']
        predictions = {}
        racer_info = []
        
        for racer in racers:
            boat_number = racer.get('boat_number', 0)
            if boat_number == 0:
                continue
                
            # 改善された簡易予想計算
            score = 0.0
            
            # 全国勝率（重視）
            overall_win_rate = racer.get('win_rate', {}).get('overall', 0)
            score += overall_win_rate * 0.25
            
            # 当地勝率
            local_win_rate = racer.get('win_rate', {}).get('local', 0) 
            score += local_win_rate * 0.20
            
            # モーター勝率
            motor_win_rate = racer.get('motor_win_rate', 0)
            score += motor_win_rate * 0.18
            
            # 艇番優位性（軽減）
            position_bonus = (7 - boat_number) * 0.02  # 削減
            score += position_bonus
            
            # 年齢による経験値
            age = racer.get('racer_age', 30)
            age_factor = min(1.0, (age - 20) / 15.0) * 0.05
            score += age_factor
            
            predictions[boat_number] = score
            racer_info.append({
                'boat_number': boat_number,
                'name': racer.get('racer_name', '不明'),
                'prediction': round(score, 3),
                'win_rate': overall_win_rate
            })
        
        if predictions:
            sorted_boats = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
            recommended_win = sorted_boats[0][0] if sorted_boats else 1
            recommended_place = [x[0] for x in sorted_boats[:3]]
            
            # 動的信頼度計算
            top_score = sorted_boats[0][1] if sorted_boats else 0
            second_score = sorted_boats[1][1] if len(sorted_boats) > 1 else 0
            score_gap = top_score - second_score
            
            base_confidence = min(0.90, top_score * 0.8)
            gap_bonus = min(0.15, score_gap * 3)
            confidence = max(0.35, base_confidence + gap_bonus)
        else:
            recommended_win = 1
            recommended_place = [1, 2, 3]
            confidence = 0.5
        
        return {
            'predictions': predictions,
            'racers': racer_info,
            'recommended_win': recommended_win,
            'recommended_place': recommended_place,
            'confidence': confidence
        }
    
    except Exception as e:
        logger.error(f"予想計算エラー: {e}")
        return None

def normalize_prediction_data(prediction: Dict) -> Optional[Dict]:
    """予想データをテンプレート用に正規化（ダミーデータ生成禁止）"""
    if not prediction or not isinstance(prediction, dict):
        logger.warning("予想データが無効です。ダミーデータは生成しません。")
        return None
    
    # 必須データの存在確認
    if 'recommended_win' not in prediction and 'predicted_win' not in prediction:
        logger.warning("推奨勝者データがありません。正規化を中止します。")
        return None
    
    normalized = {
        'predicted_win': prediction.get('recommended_win') or prediction.get('predicted_win'),
        'predicted_place': prediction.get('recommended_place') or prediction.get('predicted_place'),
        'confidence': prediction.get('confidence', 0.0),
        'is_quick_prediction': False
    }
    
    # データ型検証（エラー時はNoneを返す）
    try:
        normalized['predicted_win'] = int(normalized['predicted_win'])
    except (ValueError, TypeError):
        logger.warning("推奨勝者データが無効です。")
        return None
    
    if not isinstance(normalized['predicted_place'], list) or len(normalized['predicted_place']) == 0:
        logger.warning("推奨複勝データが無効です。")
        return None
    
    try:
        normalized['confidence'] = float(normalized['confidence'])
    except (ValueError, TypeError):
        normalized['confidence'] = 0.0
    
    return normalized

def run_async_in_thread(coro):
    """非同期コルーチンを別スレッドで実行"""
    def run_in_thread():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(run_in_thread)
    return future.result()

# キャッシュ関数
race_list_cache = {'data': None, 'timestamp': 0}

def get_cached_race_list():
    """キャッシュされたレース一覧を取得"""
    current_time = time.time()
    cache_age_minutes = (current_time - race_list_cache['timestamp']) / 60
    
    if race_list_cache['data'] is not None and cache_age_minutes < 5:
        return race_list_cache['data']
    return None

def save_race_list_to_cache(race_list_data):
    """レース一覧をキャッシュに保存"""
    race_list_cache['data'] = race_list_data
    race_list_cache['timestamp'] = time.time()

def clear_race_list_cache():
    """レース一覧キャッシュをクリア"""
    race_list_cache['data'] = None
    race_list_cache['timestamp'] = 0