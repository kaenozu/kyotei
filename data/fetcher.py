"""
競輪データ取得システム
"""
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .models import (
    RaceInfo, RaceDetail, RiderInfo, RiderStats, RaceResult,
    RaceGrade, RiderClass, RacingStyle, OddsInfo, LineInfo
)
from config.settings import SCRAPING_CONFIG, DATA_SOURCES


class KeirinDataFetcher:
    """競輪データ取得クラス"""

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

    def get_today_races(self) -> List[RaceInfo]:
        """本日のレース一覧を取得"""
        races = []
        today = datetime.now().strftime("%Y%m%d")
        
        # Kドリームスのスケジュールページから取得
        schedule_url = f"{DATA_SOURCES['primary']}/schedule/{today}"
        soup = self._fetch_with_retry(schedule_url)
        
        if not soup:
            self.logger.warning("レーススケジュールの取得に失敗")
            return self._get_sample_races()  # サンプルデータを返す
        
        try:
            race_elements = soup.find_all('div', class_='race-schedule-item')
            
            for element in race_elements:
                race_info = self._parse_race_schedule_item(element)
                if race_info:
                    races.append(race_info)
                    
        except Exception as e:
            self.logger.error(f"レーススケジュール解析エラー: {e}")
            return self._get_sample_races()
        
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

    def get_race_details(self, race_id: str) -> Optional[RaceDetail]:
        """特定レースの詳細情報を取得"""
        # race_idから情報を分解
        parts = race_id.split('_')
        if len(parts) < 3:
            self.logger.warning(f"無効なrace_id形式: {race_id}")
            return self._get_sample_race_detail(race_id)
        
        date_str, venue, race_number = parts[0], parts[1], int(parts[2])
        
        # レース詳細ページのURL構築
        detail_url = f"{DATA_SOURCES['primary']}/race-detail/{date_str}/{venue}/{race_number:02d}"
        soup = self._fetch_with_retry(detail_url)
        
        if not soup:
            return self._get_sample_race_detail(race_id)
        
        try:
            return self._parse_race_detail(soup, race_id)
        except Exception as e:
            self.logger.error(f"レース詳細解析エラー: {e}")
            return self._get_sample_race_detail(race_id)

    def _parse_race_detail(self, soup: BeautifulSoup, race_id: str) -> RaceDetail:
        """レース詳細ページを解析"""
        # レース基本情報の解析
        race_info = self._parse_race_info_from_detail(soup, race_id)
        
        # 選手情報の解析
        riders = self._parse_riders_from_detail(soup)
        
        # ライン情報の解析
        lines = self._parse_lines_from_detail(soup, riders)
        
        # オッズ情報の解析
        odds = self._parse_odds_from_detail(soup)
        
        return RaceDetail(
            race_info=race_info,
            riders=riders,
            lines=lines,
            odds=odds
        )

    def _parse_riders_from_detail(self, soup: BeautifulSoup) -> List[RiderInfo]:
        """選手情報を解析"""
        riders = []
        rider_elements = soup.find_all('tr', class_='rider-row')
        
        for i, element in enumerate(rider_elements, 1):
            try:
                name_elem = element.find('td', class_='rider-name')
                age_elem = element.find('td', class_='rider-age')
                class_elem = element.find('td', class_='rider-class')
                
                if not all([name_elem, age_elem, class_elem]):
                    continue
                
                name = name_elem.get_text(strip=True)
                age = int(age_elem.get_text(strip=True))
                class_str = class_elem.get_text(strip=True)
                
                rider = RiderInfo(
                    rider_id=f"rider_{i:03d}",
                    number=i,
                    name=name,
                    age=age,
                    class_rank=self._parse_rider_class(class_str),
                    racing_style=RacingStyle.SPRINTER,  # デフォルト
                    home_venue="",
                    stats=self._get_rider_stats(f"rider_{i:03d}")
                )
                riders.append(rider)
                
            except Exception as e:
                self.logger.error(f"選手情報解析エラー (車番{i}): {e}")
                continue
        
        return riders

    def get_rider_stats(self, rider_id: str) -> RiderStats:
        """選手の成績データを取得"""
        return self._get_rider_stats(rider_id)

    def _get_rider_stats(self, rider_id: str) -> RiderStats:
        """選手成績を取得（実装用のプレースホルダー）"""
        # 実際の実装では、選手の詳細ページから成績を取得
        import random
        
        win_rate = random.uniform(0.1, 0.3)
        place_rate = win_rate + random.uniform(0.1, 0.2)
        show_rate = place_rate + random.uniform(0.1, 0.3)
        
        return RiderStats(
            rider_id=rider_id,
            win_rate=win_rate,
            place_rate=place_rate,
            show_rate=show_rate,
            total_races=random.randint(50, 200),
            wins=random.randint(5, 50),
            places=random.randint(10, 80),
            shows=random.randint(20, 120)
        )

    def _parse_grade(self, grade_str: str) -> RaceGrade:
        """グレード文字列を変換"""
        grade_map = {
            'GP': RaceGrade.GP,
            'G1': RaceGrade.G1,
            'G2': RaceGrade.G2,
            'G3': RaceGrade.G3,
            'F1': RaceGrade.F1,
            'F2': RaceGrade.F2
        }
        return grade_map.get(grade_str, RaceGrade.F1)

    def _parse_rider_class(self, class_str: str) -> RiderClass:
        """級班文字列を変換"""
        class_map = {
            'S1': RiderClass.S1,
            'S2': RiderClass.S2,
            'A1': RiderClass.A1,
            'A2': RiderClass.A2,
            'A3': RiderClass.A3
        }
        return class_map.get(class_str, RiderClass.A1)

    def _estimate_prize_money(self, grade: RaceGrade) -> int:
        """グレードから賞金を推定"""
        prize_map = {
            RaceGrade.GP: 1000,
            RaceGrade.G1: 700,
            RaceGrade.G2: 500,
            RaceGrade.G3: 300,
            RaceGrade.F1: 100,
            RaceGrade.F2: 80
        }
        return prize_map.get(grade, 100)

    def _get_sample_races(self) -> List[RaceInfo]:
        """サンプルレースデータを生成"""
        races = []
        now = datetime.now()
        venues = ["平塚", "川崎", "小田原", "静岡"]
        
        for i, venue in enumerate(venues):
            for race_num in range(1, 4):
                start_time = now + timedelta(hours=i, minutes=race_num * 30)
                race_id = f"{now.strftime('%Y%m%d')}_{venue}_{race_num:02d}"
                
                race = RaceInfo(
                    race_id=race_id,
                    venue=venue,
                    race_number=race_num,
                    start_time=start_time,
                    grade=RaceGrade.F1,
                    prize_money=100
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
            grade=RaceGrade.F1,
            prize_money=100
        )

    def _parse_lines_from_detail(self, soup: BeautifulSoup, riders: List[RiderInfo]) -> List[LineInfo]:
        """ライン情報を解析"""
        # 簡単なライン形成のシミュレーション
        lines = []
        rider_numbers = [rider.number for rider in riders]
        
        # 3-3-1のライン形成を仮定
        if len(rider_numbers) >= 7:
            lines.append(LineInfo(
                line_id="line_1",
                leader_number=1,
                members=[1, 2, 3],
                strength=0.8
            ))
            lines.append(LineInfo(
                line_id="line_2", 
                leader_number=4,
                members=[4, 5, 6],
                strength=0.7
            ))
            lines.append(LineInfo(
                line_id="line_3",
                leader_number=7,
                members=[7],
                strength=0.6
            ))
        
        return lines

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