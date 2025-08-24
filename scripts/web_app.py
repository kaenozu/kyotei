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
import sys
import time
import asyncio
import aiohttp
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any
import threading
import schedule

# accuracy_tracker.pyと強化予想システムをインポートするためのパス追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src.core.accuracy_tracker import AccuracyTracker
except ImportError:
    # フォールバック: シンプルなダミークラスを作成
    class AccuracyTracker:
        def __init__(self):
            self.db_path = 'cache/accuracy_tracker.db'
        def save_prediction(self, race_data, prediction_result):
            pass
        def save_race_details(self, race_data, prediction_result):
            pass
        def get_race_details(self, venue_id, race_number, race_date):
            return None

try:
    from enhanced_predictor import EnhancedPredictor
except ImportError:
    # フォールバック: シンプルなダミークラスを作成
    class EnhancedPredictor:
        def calculate_enhanced_prediction(self, venue_id, race_number, date):
            return None

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# テンプレートとスタティックファイルのパスを設定
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# レース一覧キャッシュ用グローバル変数
race_list_cache = {
    'data': None,
    'timestamp': 0,
    'expiry_minutes': 5  # 5分間キャッシュ
}

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
            national_win_rate = float(boat.get('racer_national_top_1_percent') or 0)
            local_win_rate = float(boat.get('racer_rate_local') or national_win_rate)
            national_place_rate = float(boat.get('racer_national_top_2_percent') or 0)
            average_st = float(boat.get('boat_average_start_timing') or 0.17)
            
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
                try:
                    motor_rate = float(boat['motor_rate'])
                    if motor_rate > 40:  # 好調なモーター
                        motor_bonus = 0.02
                    elif motor_rate < 30:  # 不調なモーター
                        motor_bonus = -0.02
                except (ValueError, TypeError):
                    motor_bonus = 0.0
            
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

def calculate_enhanced_predictions_parallel(races_data: List[Dict]) -> Dict[str, Dict]:
    """レース一覧用の並列詳細予想計算"""
    predictions_cache = {}
    
    def calculate_single_prediction(race_data):
        try:
            venue_id = race_data['race_stadium_number']
            race_number = race_data['race_number']
            race_key = f"{venue_id}_{race_number}"
            
            # 強化予想システムで計算
            enhanced_predictor = EnhancedPredictor()
            prediction = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
            
            if prediction:
                # データベースに保存（的中率レポート用）
                try:
                    tracker = AccuracyTracker()
                    tracker.save_prediction(race_data, prediction)
                    logger.debug(f"予想データ保存成功: {race_key}")
                except Exception as e:
                    logger.warning(f"予想データ保存失敗 {race_key}: {e}")
                
                return race_key, prediction
            else:
                # 強化予想失敗時は従来予想にフォールバック
                fallback_prediction = calculate_prediction(race_data)
                return race_key, fallback_prediction
                
        except Exception as e:
            logger.warning(f"詳細予想計算エラー {race_key}: {e}")
            # エラー時は従来予想にフォールバック
            fallback_prediction = calculate_prediction(race_data)
            return race_key, fallback_prediction
    
    # 並列実行
    logger.info(f"詳細予想並列計算開始: {len(races_data)}件")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 全レースの詳細予想を並列実行
        future_to_race = {executor.submit(calculate_single_prediction, race): race for race in races_data}
        
        for future in as_completed(future_to_race):
            try:
                race_key, prediction = future.result()
                predictions_cache[race_key] = prediction
            except Exception as e:
                race_data = future_to_race[future]
                race_key = f"{race_data['race_stadium_number']}_{race_data['race_number']}"
                logger.error(f"予想計算完全失敗 {race_key}: {e}")
                # 最低限のフォールバック
                predictions_cache[race_key] = {
                    'predicted_win': 1,
                    'predicted_place': [1, 2, 3],
                    'confidence': 0.5
                }
    
    elapsed_time = time.time() - start_time
    logger.info(f"詳細予想並列計算完了: {len(predictions_cache)}件, {elapsed_time:.2f}秒")
    
    # デバッグ: 最初の数件の予想結果を確認
    debug_count = 0
    for key, prediction in predictions_cache.items():
        if debug_count < 3:
            logger.info(f"詳細予想結果 {key}: {prediction}")
        debug_count += 1
        if debug_count >= 3:
            break
    
    return predictions_cache

def get_cached_race_list():
    """\u30ad\u30e3\u30c3\u30b7\u30e5\u3055\u308c\u305f\u30ec\u30fc\u30b9\u4e00\u89a7\u3092\u53d6\u5f97"""
    global race_list_cache
    
    current_time = time.time()
    cache_age_minutes = (current_time - race_list_cache['timestamp']) / 60
    
    # \u30ad\u30e3\u30c3\u30b7\u30e5\u304c\u6709\u52b9\u304b\u3069\u3046\u304b\u30c1\u30a7\u30c3\u30af
    if (race_list_cache['data'] is not None and 
        cache_age_minutes < race_list_cache['expiry_minutes']):
        logger.info(f"\u30ad\u30e3\u30c3\u30b7\u30e5\u304b\u3089\u30ec\u30fc\u30b9\u4e00\u89a7\u3092\u8fd4\u5374 ({cache_age_minutes:.1f}\u5206\u7d4c\u904e)")
        return race_list_cache['data']
    
    return None

def save_race_list_to_cache(race_list_data):
    """\u30ec\u30fc\u30b9\u4e00\u89a7\u3092\u30ad\u30e3\u30c3\u30b7\u30e5\u306b\u4fdd\u5b58"""
    global race_list_cache
    
    race_list_cache['data'] = race_list_data
    race_list_cache['timestamp'] = time.time()
    
    logger.info(f"\u30ec\u30fc\u30b9\u4e00\u89a7\u3092\u30ad\u30e3\u30c3\u30b7\u30e5\u306b\u4fdd\u5b58: {len(race_list_data.get('races', []))}\u4ef6")

def clear_race_list_cache():
    """\u30ec\u30fc\u30b9\u4e00\u89a7\u30ad\u30e3\u30c3\u30b7\u30e5\u3092\u30af\u30ea\u30a2"""
    global race_list_cache
    
    race_list_cache['data'] = None
    race_list_cache['timestamp'] = 0
    
    logger.info("\u30ec\u30fc\u30b9\u4e00\u89a7\u30ad\u30e3\u30c3\u30b7\u30e5\u3092\u30af\u30ea\u30a2\u3057\u307e\u3057\u305f")


def normalize_prediction_data(prediction: Dict) -> Dict:
    """予想データをテンプレート用に正規化"""
    if not prediction or not isinstance(prediction, dict):
        return None
    
    # 詳細予想システムの出力を統一形式に変換
    normalized = {
        'predicted_win': prediction.get('recommended_win') or prediction.get('predicted_win', 1),
        'predicted_place': prediction.get('recommended_place') or prediction.get('predicted_place', [1, 2, 3]),
        'confidence': prediction.get('confidence', 0.5),
        'is_quick_prediction': False  # 詳細予想のみ使用
    }
    
    # データ型の検証と修正
    try:
        normalized['predicted_win'] = int(normalized['predicted_win'])
    except (ValueError, TypeError):
        normalized['predicted_win'] = 1
    
    if not isinstance(normalized['predicted_place'], list):
        normalized['predicted_place'] = [1, 2, 3]
    
    try:
        normalized['confidence'] = float(normalized['confidence'])
    except (ValueError, TypeError):
        normalized['confidence'] = 0.5
    
    return normalized


@app.route('/')
def index():
    """メインページ（軽量化版）"""
    return render_template('openapi_index.html',
                         races=[],
                         total_races=0,
                         loading=True,
                         current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'))

@app.route('/predict/<race_id>')
def predict_race(race_id):
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
            race_data = fetcher.get_race_detail(venue_id, race_number)
        
        # APIデータがない場合、データベースから取得
        if not race_data:
            try:
                tracker = AccuracyTracker()
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
            enhanced_predictor = EnhancedPredictor()
            prediction_result = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
            
            if not prediction_result:
                logger.warning("強化予想システム失敗、従来システムを使用")
                prediction_result = calculate_prediction(race_data)
            
            # 予想データとレース詳細データを保存
            if not is_from_database:
                try:
                    tracker = AccuracyTracker()
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
                             racers=sorted_racers,  # ソート済みレーサー
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
    """レース一覧API（キャッシュ機能付き）"""
    try:
        # キャッシュからデータを取得してみる
        cached_result = get_cached_race_list()
        if cached_result:
            return jsonify(cached_result)
        
        # キャッシュがない場合、新しいデータを取得
        logger.info("キャッシュなし、新規データ取得を開始")
        data = fetcher.get_today_races()
        
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
            import sqlite3
            tracker = AccuracyTracker()
            with sqlite3.connect(tracker.db_path) as conn:
                cursor = conn.cursor()
                
                # 今日の予想データを取得
                cursor.execute("""
                    SELECT venue_id, race_number, predicted_win, predicted_place, confidence
                    FROM predictions 
                    WHERE race_date = ?
                """, (race_date,))
                
                for row in cursor.fetchall():
                    venue_id, race_number, predicted_win, predicted_place_json, confidence = row
                    key = f"{venue_id}_{race_number}"
                    try:
                        import json
                        predicted_place = json.loads(predicted_place_json) if predicted_place_json else []
                    except:
                        predicted_place = []
                    
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
        enhanced_predictions = calculate_enhanced_predictions_parallel(data['programs'])
        
        for program in data['programs']:
            venue_name = VENUE_MAPPING.get(program['race_stadium_number'], '不明')
            start_time = program.get('race_closed_at', '未定')
            venue_id = program['race_stadium_number']
            race_number = program['race_number']
            race_key = f"{venue_id}_{race_number}"
            
            # レース状態を判定（修正版）
            is_finished = False
            race_time = None
            
            if start_time != '未定' and start_time:
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
                        race_time = None
                    
                    # レース終了判定（厳密に）
                    if race_time and current_time > race_time + timedelta(minutes=15):
                        is_finished = True
                        logger.debug(f"レース終了判定: {venue_name} {race_number}R, 発走: {race_time}, 現在: {current_time}")
                    elif race_time:
                        logger.debug(f"レース未終了: {venue_name} {race_number}R, 発走: {race_time}, 現在: {current_time}")
                        
                except ValueError as e:
                    # 時刻解析に失敗した場合はデバッグ情報出力
                    logger.warning(f"時刻解析失敗 [{venue_name} {race_number}R]: '{start_time}', エラー: {e}")
                    race_time = None
                    is_finished = False
            
            # 予想データと結果データを追加（修正版）
            prediction = prediction_data.get(race_key)
            # 結果データは終了したレースのみ表示（厳格な条件）
            result = result_data.get(race_key) if is_finished and race_time else None
            
            # デバッグログ
            if result:
                logger.info(f"結果データ表示: {venue_name} {race_number}R (終了済み)")
            elif race_key in result_data:
                logger.info(f"結果データ非表示: {venue_name} {race_number}R (未終了/時刻不明)")
            
            # 詳細予想システムの結果を使用（簡易予想を廃止）
            if not prediction:
                raw_prediction = enhanced_predictions.get(race_key, {
                    'predicted_win': 1,
                    'predicted_place': [1, 2, 3],
                    'confidence': 0.5
                })
                # 強化予想データを取得
                prediction = normalize_prediction_data(raw_prediction)
            else:
                # データベースから取得した予想データも正規化
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
        def sort_key(race):
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
        
        races.sort(key=sort_key)
        
        # 結果をキャッシュに保存
        result = {
            'success': True,
            'races': races,
            'total_races': len(races),
            'current_time': datetime.now().strftime('%Y年%m月%d日 %H:%M')
        }
        save_race_list_to_cache(result)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"レース一覧API エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/races/progress')
def api_races_progress():
    """進捗付きレース一覧API"""
    try:
        # セッションストレージに進捗を記録するため、一意なIDを生成
        import uuid
        progress_id = str(uuid.uuid4())
        
        # 進捗管理用のグローバル変数
        global race_loading_progress
        race_loading_progress = {
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

@app.route('/api/races/status/<progress_id>')
def api_races_status(progress_id):
    """進捗状況取得API"""
    try:
        global race_loading_progress
        if 'race_loading_progress' in globals() and race_loading_progress.get('id') == progress_id:
            return jsonify({
                'success': True,
                'progress': race_loading_progress
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

@app.route('/api/races/async')
def api_races_async():
    """レース一覧API（非同期版・軽量）"""
    try:
        # 進捗更新
        global race_loading_progress
        if 'race_loading_progress' in globals():
            race_loading_progress['step'] = 'データ取得'
            race_loading_progress['progress'] = 1
            race_loading_progress['message'] = 'レースデータを取得中...'
        
        # 非同期APIを別スレッドで実行
        data = run_async_in_thread(fetcher.get_today_races_async())
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'データ取得失敗'
            })
        
        # 進捗更新
        if 'race_loading_progress' in globals():
            race_loading_progress['step'] = '基本処理'
            race_loading_progress['progress'] = 2
            race_loading_progress['message'] = 'レース情報を処理中...'
        
        # 基本的なレース情報のみ処理（予想は後で）
        races = []
        current_time = datetime.now()
        
        for program in data.get('programs', []):
            venue_name = VENUE_MAPPING.get(program['race_stadium_number'], '不明')
            start_time = program.get('race_closed_at', '未定')
            venue_id = program['race_stadium_number']
            race_number = program['race_number']
            
            # レース状態を判定（修正版 - 非同期）
            is_finished = False
            race_time = None
            
            if start_time != '未定' and start_time:
                try:
                    # start_timeの解析（非同期版も同じロジック）
                    if 'T' in start_time:
                        race_time = datetime.fromisoformat(start_time.replace('T', ' ').split('.')[0])
                    elif ' ' in start_time and len(start_time) > 10:
                        race_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    elif ':' in start_time and len(start_time) <= 8:
                        if start_time.count(':') == 1:
                            time_obj = datetime.strptime(start_time, '%H:%M').time()
                        else:
                            time_obj = datetime.strptime(start_time, '%H:%M:%S').time()
                        race_time = datetime.combine(current_time.date(), time_obj)
                    
                    # レース終了判定（異同期では15分で判定）
                    if race_time and current_time > race_time + timedelta(minutes=15):
                        is_finished = True
                        
                except ValueError as e:
                    logger.debug(f"非同期 - 時刻解析失敗: {start_time}, {e}")
                    race_time = None
            
            race_info = {
                'venue_id': venue_id,
                'venue_name': venue_name,
                'race_number': race_number,
                'start_time': start_time,
                'race_title': program.get('race_title', ''),
                'race_id': f"{venue_id:02d}_{race_number:02d}",
                'is_finished': is_finished,
                'prediction': None,  # 後で更新
                'result': None       # 後で更新
            }
            races.append(race_info)
        
        # ソート
        def sort_key(race):
            start_time = race['start_time']
            if start_time == '未定':
                time_value = 99999
            else:
                try:
                    time_parts = start_time.split(':')
                    if len(time_parts) == 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        time_value = hours * 60 + minutes
                    else:
                        time_value = 99999
                except:
                    time_value = 99999
            
            return (race['is_finished'], time_value)
        
        races.sort(key=sort_key)
        
        # 進捗更新
        if 'race_loading_progress' in globals():
            race_loading_progress['step'] = '完了'
            race_loading_progress['progress'] = 3
            race_loading_progress['message'] = f'{len(races)}件のレースを取得完了'
        
        return jsonify({
            'success': True,
            'races': races,
            'total_races': len(races),
            'current_time': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
            'method': 'async_basic'
        })
    except Exception as e:
        # エラー時の進捗更新
        if 'race_loading_progress' in globals():
            race_loading_progress['step'] = 'エラー'
            race_loading_progress['progress'] = -1
            race_loading_progress['message'] = f'エラー: {str(e)}'
        
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/accuracy')
@app.route('/accuracy/<date>')
def accuracy_report(date=None):
    """的中率レポートページ"""
    try:
        # 的中率データ取得
        tracker = AccuracyTracker()
        
        # 日付指定がない場合は今日
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 自動で実際の結果を取得・更新
        try:
            logger.info("実際のレース結果を自動取得中...")
            from enhanced_predictor import EnhancedPredictor
            import requests
            
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

@app.route('/api/update-results')
def api_update_results():
    """レース結果更新API"""
    try:
        # 非同期処理を同期的に実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 結果更新関数を作成
        async def update_results():
            # 暫定：終了したレースに直接テスト結果を生成
            import random
            import json
            current_time = datetime.now()
            race_date = current_time.strftime('%Y-%m-%d')
            
            # 予想データを取得
            tracker = AccuracyTracker()
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
                            is_place_hit = any(boat in place_results[:2] for boat in predicted_place_list[:2])  # 複勝は1位・2位のみ
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO accuracy_records 
                                (prediction_id, result_id, is_win_hit, is_place_hit, hit_status)
                                VALUES (?, ?, ?, ?, ?)
                            """, (pred_id, result_id, is_win_hit, is_place_hit, 'hit' if is_win_hit else 'miss'))
                            
                            logger.info(f"テスト結果生成: {venue_name} {race_number}R - {winning_boat}号艇 ({'的中' if is_win_hit else '外れ'})")
                            results_generated += 1
                
                conn.commit()
                logger.info(f"テスト結果生成完了: {results_generated}件")
            
            tracker = AccuracyTracker()
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


@app.route('/test')
def test():
    """テストページ"""
    return "<h1>BoatraceOpenAPI専用システム</h1><p>システム正常動作中</p>"

@app.route('/api/races/clear-cache')
def clear_races_cache():
    """レース一覧キャッシュクリアAPI"""
    try:
        clear_race_list_cache()
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

@app.route('/api/races/cache-status')
def cache_status():
    """キャッシュ状態確認 API"""
    global race_list_cache
    
    if race_list_cache['data']:
        cache_age_minutes = (time.time() - race_list_cache['timestamp']) / 60
        return jsonify({
            'cached': True,
            'age_minutes': round(cache_age_minutes, 1),
            'expiry_minutes': race_list_cache['expiry_minutes'],
            'expired': cache_age_minutes >= race_list_cache['expiry_minutes'],
            'total_races': len(race_list_cache['data'].get('races', []))
        })
    else:
        return jsonify({
            'cached': False,
            'age_minutes': 0,
            'expiry_minutes': race_list_cache['expiry_minutes'],
            'expired': True,
            'total_races': 0
        })

# スケジューラーサービス統合クラス
class IntegratedScheduler:
    """Web アプリケーション統合スケジューラー"""
    
    def __init__(self):
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
            
            # 本日分の予測データを生成・保存
            data = fetcher.get_today_races()
            if data and 'programs' in data:
                programs = data['programs']
                logger.info(f"本日のレース数: {len(programs)}件")
                
                prediction_count = 0
                for program in programs:
                    try:
                        venue_id = program['race_stadium_number']
                        race_number = program['race_number']
                        
                        # 強化予想システムで予測
                        enhanced_predictor = EnhancedPredictor()
                        prediction = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
                        
                        if prediction:
                            # データベースに保存
                            tracker = AccuracyTracker()
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
                    tracker = AccuracyTracker()
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
                                        (race_date, venue_id, venue_name, race_number, winning_boat, place_results, result_data, timestamp)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (current_date, venue_id, venue_name, race_number, winning_boat,
                                          json.dumps(place_results), json.dumps(race), datetime.now().isoformat()))
                                    
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
                                            (prediction_id, result_id, is_win_hit, is_place_hit, hit_status, timestamp)
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
    
    def update_accuracy_report(self):
        """PM11時: 的中率レポート更新"""
        try:
            logger.info("的中率レポート更新実行")
            
            # 的中率統計を更新
            tracker = AccuracyTracker()
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

# グローバル統合スケジューラー
integrated_scheduler = IntegratedScheduler()

@app.route('/api/scheduler/start')
def api_scheduler_start():
    """スケジューラー開始API"""
    try:
        integrated_scheduler.start()
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
        integrated_scheduler.stop()
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
            'is_running': integrated_scheduler.is_running,
            'total_jobs': len(schedule.jobs),
            'next_run': next_run
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    print("=" * 50)
    print("BoatraceOpenAPI専用競艇予想システム")
    print("統合スケジューラー機能付き")
    print("URL: http://localhost:5001")
    print("=" * 50)
    
    # スケジューラーを自動開始
    integrated_scheduler.start()
    print("統合スケジューラー開始: AM6時データ取得, 毎時結果更新")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5001)
    finally:
        # アプリケーション終了時にスケジューラー停止
        integrated_scheduler.stop()