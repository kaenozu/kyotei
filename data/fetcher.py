"""
競艇データ取得システム
"""
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .models import (
    RaceInfo, RaceDetail, BoatRacerInfo, BoatRacerStats, RaceResult,
    BoatRaceGrade, BoatRacerClass, BoatRacingStyle, OddsInfo, BoatRaceLaneInfo
)
from config.settings import SCRAPING_CONFIG, DATA_SOURCES
from utils.cache import cache
from utils.performance import performance_timer


class KyoteiDataFetcher:
    """競艇データ取得クラス"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': SCRAPING_CONFIG['user_agent']
        })
        self.rate_limit = SCRAPING_CONFIG['rate_limit']
        self.timeout = SCRAPING_CONFIG['timeout']
        self.max_retries = SCRAPING_CONFIG['max_retries']
        self.logger = logging.getLogger(__name__)

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

    @performance_timer("get_today_races")
    def get_today_races(self) -> List[RaceInfo]:
        """本日のレース一覧を取得"""
        today = datetime.now().strftime("%Y%m%d")
        cache_key = f"races_{today}"
        
        # キャッシュから取得を試行
        cached_races = cache.get(cache_key)
        if cached_races:
            self.logger.info(f"キャッシュからレース情報を取得: {len(cached_races)}件")
            return cached_races
        
        races = []
        
        # まず実データ取得を試行
        try:
            from .real_fetcher import real_fetcher
            if real_fetcher.test_connection():
                self.logger.info("実データ取得を試行中...")
                races = real_fetcher.get_today_races()
                if races:
                    self.logger.info(f"実データ取得成功: {len(races)}件")
                    cache.set(cache_key, races, "race_info")
                    return races
        except Exception as e:
            self.logger.warning(f"実データ取得失敗: {e}")
        
        # 実データ取得失敗時は既存のソースを試行
        for source_name, base_url in DATA_SOURCES.items():
            if source_name == "api":
                continue  # APIは別途処理
                
            try:
                races = self._fetch_races_from_source(source_name, base_url)
                # 通常のソースでは実データが取得できないので、この部分はスキップ
                # if races:
                #     self.logger.info(f"{source_name}からレース情報を取得成功: {len(races)}件")
                #     cache.set(cache_key, races, "race_info")
                #     return races
            except Exception as e:
                self.logger.warning(f"{source_name}からの取得失敗: {e}")
                continue
        
        # 全てのソースで失敗した場合はサンプルデータを返す
        self.logger.info("全データソースで取得失敗、サンプルデータを使用")
        sample_races = self._get_sample_races()
        cache.set(cache_key, sample_races, "race_info")
        return sample_races

    @performance_timer("get_tomorrow_races")
    def get_tomorrow_races(self) -> List[RaceInfo]:
        """明日のレース一覧を取得"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        cache_key = f"races_{tomorrow}"
        
        # キャッシュから取得を試行
        cached_races = cache.get(cache_key)
        if cached_races:
            self.logger.info(f"キャッシュから明日のレース情報を取得: {len(cached_races)}件")
            return cached_races
        
        races = []
        
        # 複数のソースからデータ取得を試行
        for source_name, base_url in DATA_SOURCES.items():
            if source_name == "api":
                continue
                
            try:
                races = self._fetch_races_from_source_by_date(source_name, base_url, tomorrow)
                if races:
                    self.logger.info(f"{source_name}から明日のレース情報を取得成功: {len(races)}件")
                    cache.set(cache_key, races, "race_info")
                    return races
            except Exception as e:
                self.logger.warning(f"{source_name}からの明日レース取得失敗: {e}")
                continue
        
        # 全てのソースで失敗した場合はサンプルデータを返す
        self.logger.info("全データソースで取得失敗、明日のサンプルデータを使用")
        sample_races = self._get_sample_races_tomorrow()
        cache.set(cache_key, sample_races, "race_info")
        return sample_races

    def get_races_by_venue(self, venue: str) -> List[RaceInfo]:
        """指定開催場のレース一覧を取得"""
        cache_key = f"venue_races_{venue}"
        
        # キャッシュから取得を試行
        cached_races = cache.get(cache_key)
        if cached_races:
            self.logger.info(f"キャッシュから{venue}のレース情報を取得: {len(cached_races)}件")
            return cached_races
        
        # 今日と明日のレースから指定開催場を抽出
        today_races = self.get_today_races()
        tomorrow_races = self.get_tomorrow_races()
        
        venue_races = []
        for race in today_races + tomorrow_races:
            if race.venue == venue:
                venue_races.append(race)
        
        if venue_races:
            cache.set(cache_key, venue_races, "race_info")
        
        return venue_races

    def _get_sample_races_tomorrow(self) -> List[RaceInfo]:
        """明日のサンプルレースデータを生成"""
        races = []
        tomorrow = datetime.now() + timedelta(days=1)
        venues = ["桐生", "戸田", "江戸川", "平和島"]
        
        for i, venue in enumerate(venues):
            for race_num in range(1, 4):
                hour = 10 + i
                minute = 15 + (race_num - 1) * 30
                if minute >= 60:
                    hour += minute // 60
                    minute = minute % 60
                start_time = tomorrow.replace(hour=hour, minute=minute)
                race_id = f"{tomorrow.strftime('%Y%m%d')}_{venue}_{race_num:02d}"
                
                race = RaceInfo(
                    race_id=race_id,
                    venue=venue,
                    race_number=race_num,
                    start_time=start_time,
                    grade=BoatRaceGrade.GENERAL,
                    prize_money=200
                )
                races.append(race)
        
        return races

    def _fetch_races_from_source_by_date(self, source_name: str, base_url: str, date_str: str) -> List[RaceInfo]:
        """日付指定でソースからレース情報を取得"""
        # 実装は_fetch_races_from_sourceと同様だが、日付パラメータを追加
        if source_name == "primary":
            return self._fetch_from_boatrace_jp_by_date(base_url, date_str)
        elif source_name == "secondary":
            return self._fetch_from_boatrace_net_by_date(base_url, date_str)
        elif source_name == "backup":
            return self._fetch_from_oddspark_by_date(base_url, date_str)
        return []

    def _fetch_from_boatrace_jp_by_date(self, base_url: str, date_str: str) -> List[RaceInfo]:
        """指定日の競艇公式サイトからデータ取得"""
        schedule_url = f"{base_url}/owpc/pc/race/{date_str}"
        soup = self._fetch_with_retry(schedule_url)
        
        if not soup:
            return []
        
        race_elements = soup.find_all('tr', class_='race-row') or soup.find_all('div', class_='race-item')
        races = []
        
        for element in race_elements:
            race_info = self._parse_race_schedule_item(element)
            if race_info:
                races.append(race_info)
        
        return races

    def _fetch_from_boatrace_net_by_date(self, base_url: str, date_str: str) -> List[RaceInfo]:
        """指定日のboatrace.netからデータ取得"""
        return []  # 現在は未実装

    def _fetch_from_oddspark_by_date(self, base_url: str, date_str: str) -> List[RaceInfo]:
        """指定日のオッズパークからデータ取得"""
        return []  # 現在は未実装

    def _fetch_races_from_source(self, source_name: str, base_url: str) -> List[RaceInfo]:
        """指定されたソースからレース情報を取得"""
        if source_name == "primary":
            return self._fetch_from_boatrace_jp(base_url)
        elif source_name == "secondary":
            return self._fetch_from_boatrace_net(base_url)
        elif source_name == "backup":
            return self._fetch_from_oddspark(base_url)
        return []

    def _fetch_from_boatrace_jp(self, base_url: str) -> List[RaceInfo]:
        """競艇公式サイトからデータ取得"""
        schedule_url = f"{base_url}/owpc/pc/race"
        soup = self._fetch_with_retry(schedule_url)
        
        if not soup:
            return []
        
        race_elements = soup.find_all('tr', class_='race-row') or soup.find_all('div', class_='race-item')
        races = []
        
        for element in race_elements:
            race_info = self._parse_race_schedule_item(element)
            if race_info:
                races.append(race_info)
        
        return races

    def _fetch_from_boatrace_net(self, base_url: str) -> List[RaceInfo]:
        """boatrace.netからデータ取得"""
        # AJAXエンドポイントを使用してデータ取得を試行
        ajax_url = f"{base_url}/race/ajax_race_voting.html"
        
        try:
            response = self.session.get(ajax_url, timeout=self.timeout)
            if response.status_code == 200:
                # JSONデータの場合
                try:
                    data = response.json()
                    return self._parse_netkeirin_json(data)
                except:
                    # HTMLデータの場合
                    soup = BeautifulSoup(response.content, 'html.parser')
                    return self._parse_netkeirin_html(soup)
        except Exception as e:
            self.logger.debug(f"netkeirin AJAX取得エラー: {e}")
        
        return []

    def _fetch_from_oddspark(self, base_url: str) -> List[RaceInfo]:
        """オッズパークからデータ取得"""
        # オッズパークのAPIエンドポイントを試行
        return []  # 現在は未実装

    def _parse_netkeirin_json(self, data: dict) -> List[RaceInfo]:
        """netkeirinのJSONデータを解析"""
        races = []
        # JSONデータの構造に応じて解析
        # 実装は実際のデータ形式に依存
        return races

    def _parse_netkeirin_html(self, soup: BeautifulSoup) -> List[RaceInfo]:
        """netkeirinのHTMLデータを解析"""
        races = []
        # HTMLデータの構造に応じて解析
        # 実装は実際のHTML構造に依存
        return races

    def _parse_race_schedule_item(self, element) -> Optional[RaceInfo]:
        """レーススケジュール要素を解析"""
        try:
            venue_elem = element.find('span', class_='venue-name')
            time_elem = element.find('span', class_='start-time')
            grade_elem = element.find('span', class_='grade')
            race_num_elem = element.find('span', class_='race-number')
            
            if not all([venue_elem, time_elem, race_num_elem]):
                return None
            
            venue = venue_elem.get_text(strip=True)
            start_time_str = time_elem.get_text(strip=True)
            race_number = int(race_num_elem.get_text(strip=True).replace('R', ''))
            grade_str = grade_elem.get_text(strip=True) if grade_elem else 'F1'
            
            # 時刻解析
            today = datetime.now().date()
            hour, minute = map(int, start_time_str.split(':'))
            start_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
            
            # グレード変換
            grade = self._parse_grade(grade_str)
            
            race_id = f"{today.strftime('%Y%m%d')}_{venue}_{race_number:02d}"
            
            return RaceInfo(
                race_id=race_id,
                venue=venue,
                race_number=race_number,
                start_time=start_time,
                grade=grade,
                prize_money=self._estimate_prize_money(grade)
            )
            
        except Exception as e:
            self.logger.error(f"レース情報解析エラー: {e}")
            return None

    @performance_timer("get_race_details")
    def get_race_details(self, race_id: str) -> Optional[RaceDetail]:
        """特定レースの詳細情報を取得"""
        cache_key = f"race_detail_{race_id}"
        
        # キャッシュから取得を試行
        cached_detail = cache.get(cache_key)
        if cached_detail:
            self.logger.info(f"キャッシュからレース詳細を取得: {race_id}")
            return cached_detail
        
        # race_idから情報を分解
        parts = race_id.split('_')
        if len(parts) < 3:
            self.logger.warning(f"無効なrace_id形式: {race_id}")
            sample_detail = self._get_sample_race_detail(race_id)
            cache.set(cache_key, sample_detail, "race_info")
            return sample_detail
        
        date_str, venue, race_number = parts[0], parts[1], int(parts[2])
        
        # レース詳細ページのURL構築（競艇公式サイト形式）
        detail_url = f"{DATA_SOURCES['primary']}/owpc/pc/race"
        soup = self._fetch_with_retry(detail_url)
        
        if not soup:
            sample_detail = self._get_sample_race_detail(race_id)
            cache.set(cache_key, sample_detail, "race_info")
            return sample_detail
        
        try:
            race_detail = self._parse_race_detail(soup, race_id)
            cache.set(cache_key, race_detail, "race_info")
            return race_detail
        except Exception as e:
            self.logger.error(f"レース詳細解析エラー: {e}")
            sample_detail = self._get_sample_race_detail(race_id)
            cache.set(cache_key, sample_detail, "race_info")
            return sample_detail

    def _parse_race_detail(self, soup: BeautifulSoup, race_id: str) -> RaceDetail:
        """レース詳細ページを解析"""
        # レース基本情報の解析
        race_info = self._parse_race_info_from_detail(soup, race_id)
        
        # 選手情報の解析
        racers = self._parse_racers_from_detail(soup)
        
        # レーン情報の解析
        lanes = self._parse_lanes_from_detail(soup, racers)
        
        # オッズ情報の解析
        odds = self._parse_odds_from_detail(soup)
        
        return RaceDetail(
            race_info=race_info,
            racers=racers,
            lanes=lanes,
            odds=odds
        )

    def _parse_racers_from_detail(self, soup: BeautifulSoup) -> List[BoatRacerInfo]:
        """選手情報を解析"""
        racers = []
        racer_elements = soup.find_all('tr', class_='racer-row')
        
        for i, element in enumerate(racer_elements, 1):
            try:
                name_elem = element.find('td', class_='racer-name')
                age_elem = element.find('td', class_='racer-age')
                class_elem = element.find('td', class_='racer-class')
                
                if not all([name_elem, age_elem, class_elem]):
                    continue
                
                name = name_elem.get_text(strip=True)
                age = int(age_elem.get_text(strip=True))
                class_str = class_elem.get_text(strip=True)
                
                racer = BoatRacerInfo(
                    racer_id=f"racer_{i:03d}",
                    number=i,
                    name=name,
                    age=age,
                    racer_class=self._parse_racer_class(class_str),
                    boat_racing_style=BoatRacingStyle.INNER,  # デフォルト
                    home_venue="",
                    racer_stats=self._get_racer_stats(f"racer_{i:03d}")
                )
                racers.append(racer)
                
            except Exception as e:
                self.logger.error(f"選手情報解析エラー (艇番{i}): {e}")
                continue
        
        return racers

    def get_racer_stats(self, racer_id: str) -> BoatRacerStats:
        """選手の成績データを取得"""
        return self._get_racer_stats(racer_id)

    def _get_racer_stats(self, racer_id: str) -> BoatRacerStats:
        """選手成績を取得（実装用のプレースホルダー）"""
        # 実際の実装では、選手の詳細ページから成績を取得
        import random
        
        win_rate = random.uniform(0.1, 0.25)
        place_rate = win_rate + random.uniform(0.15, 0.25)
        show_rate = place_rate + random.uniform(0.15, 0.3)
        
        return BoatRacerStats(
            racer_id=racer_id,
            win_rate=win_rate,
            place_rate=place_rate,
            show_rate=show_rate,
            total_races=random.randint(50, 300),
            wins=random.randint(5, 75),
            places=random.randint(10, 120),
            shows=random.randint(20, 180)
        )

    def _parse_grade(self, grade_str: str) -> BoatRaceGrade:
        """グレード文字列を変換"""
        grade_map = {
            'SG': BoatRaceGrade.SG,
            'G1': BoatRaceGrade.G1,
            'G2': BoatRaceGrade.G2,
            'G3': BoatRaceGrade.G3,
            '一般': BoatRaceGrade.GENERAL
        }
        return grade_map.get(grade_str, BoatRaceGrade.GENERAL)

    def _parse_racer_class(self, class_str: str) -> BoatRacerClass:
        """級班文字列を変換"""
        class_map = {
            'A1': BoatRacerClass.A1,
            'A2': BoatRacerClass.A2,
            'B1': BoatRacerClass.B1,
            'B2': BoatRacerClass.B2
        }
        return class_map.get(class_str, BoatRacerClass.B1)

    def _estimate_prize_money(self, grade: BoatRaceGrade) -> int:
        """グレードから賞金を推定"""
        prize_map = {
            BoatRaceGrade.SG: 500,
            BoatRaceGrade.G1: 350,
            BoatRaceGrade.G2: 250,
            BoatRaceGrade.G3: 150,
            BoatRaceGrade.GENERAL: 100
        }
        return prize_map.get(grade, 100)

    def _get_sample_races(self) -> List[RaceInfo]:
        """サンプルレースデータを生成"""
        races = []
        now = datetime.now()
        venues = ["桐生", "戸田", "江戸川", "平和島"]
        
        for i, venue in enumerate(venues):
            for race_num in range(1, 4):
                start_time = now + timedelta(hours=i, minutes=race_num * 30)
                race_id = f"{now.strftime('%Y%m%d')}_{venue}_{race_num:02d}"
                
                race = RaceInfo(
                    race_id=race_id,
                    venue=venue,
                    race_number=race_num,
                    start_time=start_time,
                    grade=BoatRaceGrade.GENERAL,
                    prize_money=200
                )
                races.append(race)
        
        return races

    def _get_sample_race_detail(self, race_id: str) -> RaceDetail:
        """サンプルレース詳細データを生成"""
        from .models import create_sample_race
        return create_sample_race()

    def _parse_race_info_from_detail(self, soup: BeautifulSoup, race_id: str) -> RaceInfo:
        """詳細ページからレース基本情報を解析"""
        # プレースホルダー実装
        parts = race_id.split('_')
        if len(parts) < 3:
            # デフォルト値を使用
            date_str, venue, race_number = "20241205", "平塚", 1
        else:
            date_str, venue, race_number = parts[0], parts[1], int(parts[2])
        
        start_time = datetime.strptime(date_str, '%Y%m%d').replace(hour=10, minute=15)
        
        return RaceInfo(
            race_id=race_id,
            venue=venue,
            race_number=race_number,
            start_time=start_time,
            grade=BoatRaceGrade.GENERAL,
            prize_money=200
        )

    def _parse_lanes_from_detail(self, soup: BeautifulSoup, racers: List[BoatRacerInfo]) -> List[BoatRaceLaneInfo]:
        """レーン情報を解析"""
        lanes = []
        for i, racer in enumerate(racers, 1):
            lane = BoatRaceLaneInfo(
                lane_id=f"lane_{i}",
                lane_number=i,
                racer_number=racer.number,
                motor_number=i,
                boat_number=i,
                start_timing=0.0,
                exhibition_time=None,
                strength=0.5,
                strategy="普通"
            )
            lanes.append(lane)
        
        return lanes

    def _parse_odds_from_detail(self, soup: BeautifulSoup) -> Optional[OddsInfo]:
        """オッズ情報を解析"""
        # プレースホルダー実装
        import random
        
        win_odds = {i: random.uniform(1.5, 50.0) for i in range(1, 8)}
        place_odds = {i: random.uniform(1.1, 10.0) for i in range(1, 8)}
        
        return OddsInfo(
            win_odds=win_odds,
            place_odds=place_odds
        )