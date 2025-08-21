#!/usr/bin/env python3
"""
BoatraceOpenAPIを使用したデータ取得クラス（キャッシュ対応）
"""

import requests
import logging
import json
import os
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from data.simple_models import TeikokuRaceInfo, TeikokuRacerInfo, TeikokuRaceDetail, get_venue_name

class BoatraceOpenAPIFetcher:
    """BoatraceOpenAPIを使用したデータ取得（キャッシュ対応）"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://boatraceopenapi.github.io/programs/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # キャッシュ設定
        self.cache_dir = "cache"
        self.cache_file = os.path.join(self.cache_dir, "boatrace_openapi_cache.json")
        self.cache_expiry = 300  # 5分間キャッシュ
        
        # キャッシュディレクトリ作成
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _load_cache(self) -> Optional[Dict]:
        """キャッシュからデータを読み込み"""
        try:
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # キャッシュの有効期限をチェック
            cache_time = cache_data.get('timestamp', 0)
            if time.time() - cache_time > self.cache_expiry:
                self.logger.info("キャッシュの有効期限切れ")
                return None
            
            self.logger.info(f"キャッシュからデータ読み込み成功 ({len(cache_data.get('programs', []))}件)")
            return cache_data.get('data')
            
        except Exception as e:
            self.logger.warning(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_cache(self, data: Dict) -> None:
        """データをキャッシュに保存"""
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data,
                'programs': data.get('programs', [])
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"キャッシュ保存成功 ({len(data.get('programs', []))}件)")
            
        except Exception as e:
            self.logger.warning(f"キャッシュ保存エラー: {e}")
    
    def get_today_programs(self) -> Optional[Dict]:
        """今日のプログラムデータを取得（キャッシュ対応）"""
        # まずキャッシュから取得を試行
        cached_data = self._load_cache()
        if cached_data:
            return cached_data
        
        # キャッシュがない場合はAPIから取得
        try:
            url = f"{self.base_url}/today.json"
            self.logger.info(f"BoatraceOpenAPI取得: {url}")
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"API取得成功: {len(data['programs'])}件のレース")
                
                # キャッシュに保存
                self._save_cache(data)
                
                return data
            else:
                self.logger.warning(f"API取得失敗: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"BoatraceOpenAPI取得エラー: {e}")
            return None
    
    def get_race_by_venue_and_number(self, venue_id: str, race_number: int) -> Optional[Dict]:
        """指定された会場・レース番号のデータを取得"""
        try:
            data = self.get_today_programs()
            if not data:
                return None
            
            # 会場IDを数値に変換
            venue_num = int(venue_id)
            
            for program in data['programs']:
                if (program['race_stadium_number'] == venue_num and 
                    program['race_number'] == race_number):
                    return program
            
            self.logger.warning(f"レースが見つかりません: venue={venue_id}, race={race_number}")
            return None
            
        except Exception as e:
            self.logger.error(f"レース検索エラー: {e}")
            return None
    
    def create_race_detail_from_api(self, venue_id: str, race_number: int) -> Optional[TeikokuRaceDetail]:
        """APIデータからTeikokuRaceDetailを作成"""
        try:
            program = self.get_race_by_venue_and_number(venue_id, race_number)
            if not program:
                return None
            
            # レース情報を作成
            today = datetime.now().strftime('%Y%m%d')
            race_id = f"{today}_{venue_id}_{race_number:02d}"
            
            venue_name = get_venue_name(venue_id)
            
            # 締切時刻をパース
            start_time = None
            try:
                if 'race_closed_at' in program and program['race_closed_at']:
                    # 'HH:MM' 形式をパース
                    time_str = program['race_closed_at']
                    hour, minute = map(int, time_str.split(':'))
                    start_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            except:
                pass
            
            race_info = TeikokuRaceInfo(
                race_id=race_id,
                date=today,
                venue_id=venue_id,
                venue_name=venue_name,
                race_number=race_number,
                status="API取得",
                start_time=start_time
            )
            
            # 選手情報を作成
            racers = []
            for boat_data in program['boats']:
                # boat_data自体が選手データ
                boat_number = boat_data.get('racer_boat_number', len(racers) + 1)
                
                # 実力値を成績から計算（全国勝率を使用）
                win_rate = float(boat_data.get('racer_national_top_1_percent', 0))
                estimated_strength = min(win_rate / 100.0, 0.6)  # 勝率を0-1に正規化
                
                # 艇番有利度
                lane_advantages = {1: 0.25, 2: 0.18, 3: 0.15, 4: 0.12, 5: 0.10, 6: 0.08}
                lane_advantage = lane_advantages.get(boat_number, 0.08)
                
                racer = TeikokuRacerInfo(
                    racer_id=f"openapi_{boat_data['racer_number']}_{boat_number}",
                    number=boat_number,
                    name=boat_data['racer_name'],
                    estimated_strength=estimated_strength,
                    lane_advantage=lane_advantage,
                    stats=None  # APIから詳細統計は別途作成可能
                )
                racers.append(racer)
                
                self.logger.info(f"OpenAPI選手取得: {boat_number}号艇 {boat_data['racer_name']} (勝率: {win_rate:.2f}%)")
            
            race_detail = TeikokuRaceDetail(
                race_info=race_info,
                racers=racers,
                weather_info=None  # 気象情報は別APIまたは追加実装
            )
            
            self.logger.info(f"BoatraceOpenAPIからレース詳細作成成功: {race_id}")
            return race_detail
            
        except Exception as e:
            self.logger.error(f"レース詳細作成エラー: {e}")
            return None
    
    def get_available_venues_today(self) -> List[str]:
        """今日開催されている会場一覧を取得"""
        try:
            data = self.get_today_programs()
            if not data:
                return []
            
            venues = set()
            for program in data['programs']:
                venue_id = f"{program['race_stadium_number']:02d}"
                venues.add(venue_id)
            
            return sorted(list(venues))
            
        except Exception as e:
            self.logger.error(f"開催会場取得エラー: {e}")
            return []

# グローバルインスタンス
boatrace_openapi_fetcher = BoatraceOpenAPIFetcher()