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
        self.cache_file = "cache/openapi_cache.json"
        self.cache_expiry = 300  # 5分間キャッシュ
        
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
        """今日のレースデータ取得"""
        # キャッシュ確認
        cached_data = self._load_cache()
        if cached_data:
            return cached_data
        
        # API取得
        try:
            url = f"{self.base_url}/today.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self._save_cache(data)
                logger.info(f"API取得成功: {len(data.get('programs', []))}件")
                return data
            else:
                logger.error(f"API取得失敗: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"API取得エラー: {e}")
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

# グローバルフェッチャー
fetcher = SimpleOpenAPIFetcher()

def calculate_prediction(race_data: Dict) -> Dict:
    """シンプルな予想計算"""
    predictions = {}
    racers = []
    
    try:
        for boat in race_data.get('boats', []):
            boat_number = boat.get('boat_number', len(racers) + 1)
            racer_name = boat.get('racer_name', '不明')
            
            # 勝率から実力値計算
            win_rate = float(boat.get('racer_national_top_1_percent', 0))
            base_strength = min(win_rate / 100.0, 0.6)
            
            # 艇番有利度
            lane_advantages = {1: 0.25, 2: 0.18, 3: 0.15, 4: 0.12, 5: 0.10, 6: 0.08}
            lane_advantage = lane_advantages.get(boat_number, 0.08)
            
            # 最終予想値
            final_prediction = min(base_strength + lane_advantage, 0.85)
            
            predictions[boat_number] = final_prediction
            racers.append({
                'number': boat_number,
                'name': racer_name,
                'win_rate': win_rate,
                'prediction': final_prediction
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
                                 error="レースデータを取得できませんでした")
        
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
    """レース一覧API"""
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