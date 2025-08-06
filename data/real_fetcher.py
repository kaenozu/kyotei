"""
競艇公式サイトからの実データ取得システム
"""
import requests
import time
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .models import (
    RaceInfo, RaceDetail, BoatRacerInfo, BoatRacerStats, 
    BoatRaceGrade, BoatRacerClass, BoatRacingStyle
)
from config.settings import SCRAPING_CONFIG
from utils.cache import cache
from utils.performance import performance_timer


class RealBoatraceDataFetcher:
    """競艇公式サイトからの実データ取得クラス"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': SCRAPING_CONFIG['user_agent']
        })
        self.rate_limit = SCRAPING_CONFIG['rate_limit']
        self.timeout = SCRAPING_CONFIG['timeout']
        self.max_retries = SCRAPING_CONFIG['max_retries']
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.boatrace.jp"

    def _wait_rate_limit(self):
        """レート制限のための待機"""
        time.sleep(self.rate_limit)

    def _fetch_with_retry(self, url: str) -> Optional[BeautifulSoup]:
        """リトライ機能付きでページを取得"""
        for attempt in range(self.max_retries):
            try:
                self._wait_rate_limit()
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                self.logger.info(f"データ取得成功: {url}")
                return soup
                
            except requests.RequestException as e:
                self.logger.warning(f"取得失敗 (試行{attempt+1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    self.logger.error(f"最終的に取得失敗: {url}")
                    return None
                time.sleep(5)  # 失敗時は5秒待機
        
        return None

    @performance_timer("get_today_races_real")
    def get_today_races(self) -> List[RaceInfo]:
        """本日のレース一覧を取得（実データ）"""
        today = datetime.now().strftime("%Y%m%d")
        cache_key = f"real_races_{today}"
        
        # キャッシュから取得を試行
        cached_races = cache.get(cache_key)
        if cached_races:
            self.logger.info(f"キャッシュから実レース情報を取得: {len(cached_races)}件")
            return cached_races
        
        races = []
        race_url = f"{self.base_url}/owpc/pc/race/index"
        
        soup = self._fetch_with_retry(race_url)
        if not soup:
            self.logger.error("競艇公式サイトからのデータ取得に失敗")
            return []
        
        try:
            races = self._parse_race_list(soup)
            self.logger.info(f"実レース情報を取得成功: {len(races)}件")
            
            # キャッシュに保存
            if races:
                cache.set(cache_key, races, "race_info")
            
            return races
            
        except Exception as e:
            self.logger.error(f"レース情報解析エラー: {e}")
            return []

    def _parse_race_list(self, soup: BeautifulSoup) -> List[RaceInfo]:
        """レース一覧ページを解析"""
        races = []
        
        # テーブル行を探す（実際の構造に基づいて調整が必要）
        race_rows = soup.find_all('tr') or soup.find_all('div', class_=re.compile(r'race|list'))
        
        for row in race_rows:
            try:
                race_info = self._parse_single_race(row)
                if race_info:
                    races.append(race_info)
            except Exception as e:
                self.logger.debug(f"個別レース解析エラー: {e}")
                continue
        
        return races

    def _parse_single_race(self, element) -> Optional[RaceInfo]:
        """単一レース要素を解析"""
        try:
            # 開催場名を取得（logoやテキストから）
            venue = self._extract_venue(element)
            if not venue:
                return None
            
            # レース番号を取得
            race_number = self._extract_race_number(element)
            if not race_number:
                return None
            
            # 発走時刻を取得
            start_time = self._extract_start_time(element)
            if not start_time:
                start_time = datetime.now().replace(hour=10, minute=0)  # デフォルト
            
            # レースIDを生成
            race_id = f"{datetime.now().strftime('%Y%m%d')}_{venue}_{race_number:02d}"
            
            # グレードを推定（デフォルトは一般戦）
            grade = BoatRaceGrade.GENERAL
            
            return RaceInfo(
                race_id=race_id,
                venue=venue,
                race_number=race_number,
                start_time=start_time,
                grade=grade,
                prize_money=200,  # デフォルト賞金
                status="発売中"
            )
            
        except Exception as e:
            self.logger.debug(f"レース解析エラー: {e}")
            return None

    def _extract_venue(self, element) -> Optional[str]:
        """開催場名を抽出"""
        # ロゴ画像から抽出を試行
        logo_img = element.find('img', src=re.compile(r'text_place'))
        if logo_img:
            # ファイル名から開催場を推定
            src = logo_img.get('src', '')
            venue_match = re.search(r'text_place1_(\d+)', src)
            if venue_match:
                venue_code = int(venue_match.group(1))
                return self._venue_code_to_name(venue_code)
        
        # テキストから開催場名を直接抽出
        text_content = element.get_text() if hasattr(element, 'get_text') else str(element)
        for venue_name in ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", 
                          "蒲郡", "常滑", "津", "三国", "びわこ", "住之江", 
                          "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", 
                          "下関", "若松", "芦屋", "福岡", "唐津", "大村"]:
            if venue_name in text_content:
                return venue_name
        
        return None

    def _extract_race_number(self, element) -> Optional[int]:
        """レース番号を抽出"""
        # URLパラメータから抽出 (rno=5 など)
        links = element.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            race_match = re.search(r'rno=(\d+)', href)
            if race_match:
                return int(race_match.group(1))
        
        # テキストから抽出 ("5R" など)
        text_content = element.get_text() if hasattr(element, 'get_text') else str(element)
        race_match = re.search(r'(\d+)R', text_content)
        if race_match:
            return int(race_match.group(1))
        
        return None

    def _extract_start_time(self, element) -> Optional[datetime]:
        """発走時刻を抽出"""
        text_content = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        # 時刻パターンを探す (17:01, 14:30 など)
        time_match = re.search(r'(\d{1,2}):(\d{2})', text_content)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            
            today = datetime.now().date()
            return datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
        
        return None

    def _venue_code_to_name(self, code: int) -> str:
        """開催場コードから名前に変換"""
        venue_map = {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川",
            6: "浜名湖", 7: "蒲郡", 8: "常滑", 9: "津", 10: "三国",
            11: "びわこ", 12: "住之江", 13: "尼崎", 14: "鳴門", 15: "丸亀",
            16: "児島", 17: "宮島", 18: "徳山", 19: "下関", 20: "若松",
            21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
        return venue_map.get(code, f"場{code}")

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            self.logger.info(f"接続テスト開始: {self.base_url}")
            response = self.session.get(self.base_url, timeout=10)
            self.logger.info(f"レスポンス状態: {response.status_code}")
            success = response.status_code == 200
            if success:
                self.logger.info("接続テスト成功")
            else:
                self.logger.warning(f"接続テスト失敗: ステータスコード {response.status_code}")
            return success
        except Exception as e:
            self.logger.error(f"接続テストエラー: {e}")
            return False


# グローバルインスタンス
real_fetcher = RealBoatraceDataFetcher()