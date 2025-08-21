#!/usr/bin/env python3
"""
BoatraceOpenAPI専用シンプル競艇予想システム
"""

from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import logging
import requests
import json
import os
import time
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 競艇場マッピング
VENUE_MAPPING = {
    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
    7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
    13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
    19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
}

class SimpleOpenAPIFetcher:
    """BoatraceOpenAPI専用データ取得クラス"""
    
    def __init__(self):
        self.base_url = "https://boatraceopenapi.github.io/programs/v2"
        self.cache_file = "cache/boatrace_openapi_cache.json"  # 統合されたキャッシュファイル
        self.cache_expiry = 300  # 5分間キャッシュ
        self.max_retries = 3  # 最大リトライ回数
        self.retry_delay = 1.0  # リトライ間隔（秒）
        
        # キャッシュディレクトリ作成
        os.makedirs("cache", exist_ok=True)
    
    def _load_cache(self) -> Optional[Dict]:
        """キャッシュ読み込み"""
        try:
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 有効期限チェック
            if time.time() - cache_data.get('timestamp', 0) > self.cache_expiry:
                return None
            
            logger.info(f"キャッシュ読み込み成功: {len(cache_data.get('programs', []))}件")
            return cache_data.get('data')
        except Exception as e:
            logger.warning(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_cache(self, data: Dict) -> None:
        """キャッシュ保存"""
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data,
                'programs': data.get('programs', [])
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"キャッシュ保存成功: {len(data.get('programs', []))}件")
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {e}")
    
    def get_today_races(self) -> Optional[Dict]:
        """今日のレースデータ取得（リトライ機能付き）"""
        # キャッシュ確認
        cached_data = self._load_cache()
        if cached_data:
            return cached_data
        
        # API取得（リトライ機能付き）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}/today.json"
                logger.info(f"API取得試行 {attempt + 1}/{self.max_retries}: {url}")
                
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self._save_cache(data)
                    logger.info(f"API取得成功: {len(data.get('programs', []))}件")
                    return data
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    logger.warning(f"API取得失敗 (試行{attempt + 1}): {last_error}")
                    
            except requests.exceptions.ConnectionError as e:
                last_error = f"接続エラー: {str(e)[:100]}"
                logger.warning(f"接続エラー (試行{attempt + 1}): {last_error}")
                
            except requests.exceptions.Timeout as e:
                last_error = f"タイムアウト: {str(e)[:100]}"
                logger.warning(f"タイムアウト (試行{attempt + 1}): {last_error}")
                
            except Exception as e:
                last_error = f"予期しないエラー: {str(e)[:100]}"
                logger.warning(f"予期しないエラー (試行{attempt + 1}): {last_error}")
            
            # 最後の試行でなければ待機
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        logger.error(f"API取得に{self.max_retries}回失敗: {last_error}")
        return None
    
    async def get_today_races_async(self) -> Optional[Dict]:
        """非同期版レースデータ取得"""
        # キャッシュ確認
        cached_data = self._load_cache()
        if cached_data:
            return cached_data
        
        # 非同期API取得
        async with aiohttp.ClientSession() as session:
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    url = f"{self.base_url}/today.json"
                    logger.info(f"非同期API取得試行 {attempt + 1}/{self.max_retries}: {url}")
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            self._save_cache(data)
                            logger.info(f"非同期API取得成功: {len(data.get('programs', []))}件")
                            return data
                        else:
                            last_error = f"HTTP {response.status}"
                            logger.warning(f"非同期API取得失敗 (試行{attempt + 1}): {last_error}")
                            
                except aiohttp.ClientError as e:
                    last_error = f"接続エラー: {str(e)[:100]}"
                    logger.warning(f"非同期接続エラー (試行{attempt + 1}): {last_error}")
                    
                except Exception as e:
                    last_error = f"予期しないエラー: {str(e)[:100]}"
                    logger.warning(f"非同期予期しないエラー (試行{attempt + 1}): {last_error}")
                
                # 最後の試行でなければ待機
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
            
            logger.error(f"非同期API取得に{self.max_retries}回失敗: {last_error}")
            return None
    
    def get_race_detail(self, venue_id: int, race_number: int) -> Optional[Dict]:
        """指定レース詳細取得"""
        data = self.get_today_races()
        if not data:
            return None
        
        for program in data.get('programs', []):
            if (program['race_stadium_number'] == venue_id and 
                program['race_number'] == race_number):
                return program
        
        return None

# グローバルフェッチャーとエグゼキューター
fetcher = SimpleOpenAPIFetcher()
executor = ThreadPoolExecutor(max_workers=4)

def run_async_in_thread(coro):
    """非同期関数をスレッド内で実行"""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    future = executor.submit(run)
    return future.result(timeout=30)  # 30秒タイムアウト

def calculate_prediction(race_data: Dict) -> Dict:
    """高度な予想計算（複数指標統合）"""
    predictions = {}
    racers = []
    
    try:
        # レース距離による補正係数
        distance = race_data.get('race_distance', 1800)
        distance_factor = 1.0
        if distance <= 1200:
            distance_factor = 1.05  # 短距離は技術重視
        elif distance >= 2000:
            distance_factor = 0.98  # 長距離は体力重視
        
        for boat in race_data.get('boats', []):
            boat_number = boat.get('boat_number', len(racers) + 1)
            racer_name = boat.get('racer_name', '不明')
            
            # 複数の統計データを取得
            national_win_rate = float(boat.get('racer_national_top_1_percent', 0))
            local_win_rate = float(boat.get('racer_rate_local', national_win_rate))
            national_place_rate = float(boat.get('racer_national_top_2_percent', 0))
            average_st = float(boat.get('boat_average_start_timing', 0.17))
            
            # 1. 基本実力値（全国勝率ベース）
            base_strength = min(national_win_rate / 100.0, 0.5)
            
            # 2. 当地適性（当地勝率との差異）
            local_adaptation = 0.0
            if local_win_rate > 0:
                adaptation_diff = (local_win_rate - national_win_rate) / 100.0
                local_adaptation = max(-0.1, min(0.1, adaptation_diff))  # -10%〜+10%
            
            # 3. 連対率考慮
            place_bonus = 0.0
            if national_place_rate > 0:
                place_efficiency = national_place_rate / max(national_win_rate, 1)
                if place_efficiency > 2.8:  # 連対率が勝率の2.8倍以上なら安定性ボーナス
                    place_bonus = 0.03
            
            # 4. スタート技術（平均STによる補正）
            st_factor = 1.0
            if average_st > 0:
                if average_st <= 0.15:  # 優秀なST
                    st_factor = 1.08
                elif average_st <= 0.17:  # 標準的なST
                    st_factor = 1.03
                elif average_st >= 0.20:  # 遅いST
                    st_factor = 0.95
            
            # 5. 艇番有利度（従来）
            lane_advantages = {1: 0.22, 2: 0.16, 3: 0.13, 4: 0.10, 5: 0.08, 6: 0.06}
            lane_advantage = lane_advantages.get(boat_number, 0.06)
            
            # 6. モーター・ボート成績（利用可能な場合）
            motor_bonus = 0.0
            if 'motor_rate' in boat and boat['motor_rate']:
                motor_rate = float(boat['motor_rate'])
                if motor_rate > 40:  # 好調なモーター
                    motor_bonus = 0.02
                elif motor_rate < 30:  # 不調なモーター
                    motor_bonus = -0.02
            
            # 総合予想値計算
            final_prediction = (
                (base_strength + local_adaptation + place_bonus) * 
                st_factor * distance_factor + 
                lane_advantage + motor_bonus
            )
            
            # 上限・下限設定
            final_prediction = max(0.05, min(final_prediction, 0.80))
            
            predictions[boat_number] = final_prediction
            racers.append({
                'number': boat_number,
                'name': racer_name,
                'win_rate': national_win_rate,
                'local_win_rate': local_win_rate,
                'place_rate': national_place_rate,
                'average_st': average_st,
                'prediction': final_prediction,
                'analysis': {
                    'base_strength': base_strength,
                    'local_adaptation': local_adaptation,
                    'place_bonus': place_bonus,
                    'st_factor': st_factor,
                    'lane_advantage': lane_advantage,
                    'motor_bonus': motor_bonus
                }
            })
        
        # 推奨艇計算
        if predictions:
            recommended_win = max(predictions.items(), key=lambda x: x[1])[0]
            sorted_boats = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
            recommended_place = [x[0] for x in sorted_boats[:3]]
        else:
            recommended_win = 1
            recommended_place = [1, 2, 3]
        
        return {
            'predictions': predictions,
            'racers': racers,
            'recommended_win': recommended_win,
            'recommended_place': recommended_place,
            'confidence': 0.7
        }
    
    except Exception as e:
        logger.error(f"予想計算エラー: {e}")
        return {
            'predictions': {},
            'racers': [],
            'recommended_win': 1,
            'recommended_place': [1, 2, 3],
            'confidence': 0.0
        }

@app.route('/')
def index():
    """メインページ"""
    try:
        data = fetcher.get_today_races()
        
        if not data or 'programs' not in data:
            return render_template('openapi_index.html', 
                                 races=[],
                                 total_races=0,
                                 error="レースデータを取得できませんでした。インターネット接続を確認してください。")
        
        races = []
        for program in data['programs']:
            venue_name = VENUE_MAPPING.get(program['race_stadium_number'], '不明')
            start_time = program.get('race_closed_at', '未定')
            
            race_info = {
                'venue_id': program['race_stadium_number'],
                'venue_name': venue_name,
                'race_number': program['race_number'],
                'start_time': start_time,
                'race_title': program.get('race_title', ''),
                'race_id': f"{program['race_stadium_number']:02d}_{program['race_number']:02d}"
            }
            races.append(race_info)
        
        # 時刻順でソート
        races.sort(key=lambda x: x['start_time'] if x['start_time'] != '未定' else 'ZZ:ZZ')
        
        return render_template('openapi_index.html',
                             races=races,
                             total_races=len(races),
                             current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'))
    
    except Exception as e:
        logger.error(f"メインページエラー: {e}")
        return render_template('openapi_index.html',
                             races=[],
                             total_races=0,
                             error=f"システムエラー: {e}")

@app.route('/predict/<race_id>')
def predict_race(race_id):
    """レース予想ページ"""
    try:
        # race_id解析 (venue_race)
        parts = race_id.split('_')
        if len(parts) != 2:
            return f"不正なレースID: {race_id}", 400
        
        venue_id = int(parts[0])
        race_number = int(parts[1])
        
        # レース詳細取得
        race_data = fetcher.get_race_detail(venue_id, race_number)
        if not race_data:
            return render_template('openapi_predict.html',
                                 error=f"レースデータが見つかりません: {race_id}")
        
        # 基本情報
        venue_name = VENUE_MAPPING.get(venue_id, '不明')
        start_time = race_data.get('race_closed_at', '未定')
        race_title = race_data.get('race_title', '')
        
        # 予想計算
        prediction_result = calculate_prediction(race_data)
        
        return render_template('openapi_predict.html',
                             venue_name=venue_name,
                             race_number=race_number,
                             start_time=start_time,
                             race_title=race_title,
                             racers=prediction_result['racers'],
                             predictions=prediction_result['predictions'],
                             recommended_win=prediction_result['recommended_win'],
                             recommended_place=prediction_result['recommended_place'],
                             confidence=prediction_result['confidence'])
    
    except Exception as e:
        logger.error(f"予想ページエラー: {e}")
        return render_template('openapi_predict.html',
                             error=f"予想処理エラー: {e}")

@app.route('/api/races')
def api_races():
    """レース一覧API（同期版）"""
    try:
        data = fetcher.get_today_races()
        if data:
            return jsonify({
                'success': True,
                'total_races': len(data.get('programs', [])),
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'データ取得失敗'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/races/async')
def api_races_async():
    """レース一覧API（非同期版・高速）"""
    try:
        # 非同期APIを別スレッドで実行
        data = run_async_in_thread(fetcher.get_today_races_async())
        if data:
            return jsonify({
                'success': True,
                'total_races': len(data.get('programs', [])),
                'data': data,
                'method': 'async'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'データ取得失敗'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test')
def test():
    """テストページ"""
    return "<h1>BoatraceOpenAPI専用システム</h1><p>システム正常動作中</p>"

if __name__ == '__main__':
    print("=" * 50)
    print("BoatraceOpenAPI専用競艇予想システム")
    print("URL: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)