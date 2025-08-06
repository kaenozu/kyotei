"""
実データとモックデータを統合したハイブリッドフェッチャー
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from .models import RaceInfo, RaceDetail
from config.settings import get_setting


class HybridDataFetcher:
    """実データとモックデータを組み合わせた統合データフェッチャー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_mode = get_setting("DATA_MODE")
        
        # 実データフェッチャーの初期化
        try:
            from .real_fetcher import RealBoatraceDataFetcher
            self.real_fetcher = RealBoatraceDataFetcher()
            self.logger.info("実データフェッチャーを初期化しました")
        except Exception as e:
            self.logger.warning(f"実データフェッチャーの初期化に失敗: {e}")
            self.real_fetcher = None
            
        # モックデータフェッチャーの初期化
        try:
            from .fetcher import KyoteiDataFetcher
            self.mock_fetcher = KyoteiDataFetcher()
            self.logger.info("モックデータフェッチャーを初期化しました")
        except Exception as e:
            self.logger.error(f"モックデータフェッチャーの初期化に失敗: {e}")
            self.mock_fetcher = None
    
    def _use_real_data(self) -> bool:
        """実データを使用するかどうかを判定"""
        return (
            self.data_mode.get("use_real_data", False) and 
            self.real_fetcher is not None
        )
    
    def _show_data_source_info(self, source: str, success: bool = True):
        """データソース情報をログ出力"""
        if self.data_mode.get("show_data_source", True):
            status = "成功" if success else "失敗"
            self.logger.info(f"データ取得元: {source} ({status})")
    
    def get_today_races(self) -> List[RaceInfo]:
        """今日のレース一覧を取得"""
        if self._use_real_data():
            try:
                self.logger.info("実データで今日のレース一覧を取得中...")
                races = self.real_fetcher.get_today_races()
                self._show_data_source_info("実データ (boatrace.jp)", True)
                return races
            except Exception as e:
                self.logger.warning(f"実データ取得に失敗: {e}")
                self._show_data_source_info("実データ (boatrace.jp)", False)
                
                if self.data_mode.get("fallback_to_mock", True) and self.mock_fetcher:
                    self.logger.info("モックデータにフォールバック中...")
                    races = self.mock_fetcher.get_today_races()
                    self._show_data_source_info("モックデータ", True)
                    return races
                else:
                    raise
        else:
            if self.mock_fetcher:
                self.logger.info("モックデータで今日のレース一覧を取得中...")
                races = self.mock_fetcher.get_today_races()
                self._show_data_source_info("モックデータ", True)
                return races
            else:
                raise RuntimeError("データフェッチャーが利用できません")
    
    def get_races_today(self) -> List[RaceInfo]:
        """今日のレース一覧を取得（互換性のため）"""
        return self.get_today_races()
    
    def get_tomorrow_races(self) -> List[RaceInfo]:
        """明日のレース一覧を取得"""
        if self._use_real_data():
            try:
                self.logger.info("実データで明日のレース一覧を取得中...")
                races = self.real_fetcher.get_tomorrow_races()
                self._show_data_source_info("実データ (boatrace.jp)", True)
                return races
            except Exception as e:
                self.logger.warning(f"実データ取得に失敗: {e}")
                self._show_data_source_info("実データ (boatrace.jp)", False)
                
                if self.data_mode.get("fallback_to_mock", True) and self.mock_fetcher:
                    self.logger.info("モックデータにフォールバック中...")
                    races = self.mock_fetcher.get_tomorrow_races()
                    self._show_data_source_info("モックデータ", True)
                    return races
                else:
                    raise
        else:
            if self.mock_fetcher:
                self.logger.info("モックデータで明日のレース一覧を取得中...")
                races = self.mock_fetcher.get_tomorrow_races()
                self._show_data_source_info("モックデータ", True)
                return races
            else:
                raise RuntimeError("データフェッチャーが利用できません")
    
    def get_races_tomorrow(self) -> List[RaceInfo]:
        """明日のレース一覧を取得（互換性のため）"""
        return self.get_tomorrow_races()
    
    def get_race_detail(self, race_id: str) -> Optional[RaceDetail]:
        """レース詳細情報を取得"""
        if self._use_real_data():
            try:
                self.logger.info(f"実データでレース詳細を取得中: {race_id}")
                detail = self.real_fetcher.get_race_detail(race_id)
                self._show_data_source_info("実データ (boatrace.jp)", True)
                return detail
            except Exception as e:
                self.logger.warning(f"実データ取得に失敗: {e}")
                self._show_data_source_info("実データ (boatrace.jp)", False)
                
                if self.data_mode.get("fallback_to_mock", True) and self.mock_fetcher:
                    self.logger.info("モックデータにフォールバック中...")
                    detail = self.mock_fetcher.get_race_detail(race_id)
                    self._show_data_source_info("モックデータ", True)
                    return detail
                else:
                    raise
        else:
            if self.mock_fetcher:
                self.logger.info(f"モックデータでレース詳細を取得中: {race_id}")
                detail = self.mock_fetcher.get_race_detail(race_id)
                self._show_data_source_info("モックデータ", True)
                return detail
            else:
                raise RuntimeError("データフェッチャーが利用できません")
    
    def search_races_by_venue(self, venue_name: str, date_filter: Optional[datetime] = None) -> List[RaceInfo]:
        """会場名でレースを検索"""
        if self._use_real_data():
            try:
                self.logger.info(f"実データで会場検索中: {venue_name}")
                # 実データフェッチャーに会場検索機能があれば使用
                if hasattr(self.real_fetcher, 'search_races_by_venue'):
                    races = self.real_fetcher.search_races_by_venue(venue_name, date_filter)
                    self._show_data_source_info("実データ (boatrace.jp)", True)
                    return races
                else:
                    # 今日・明日のレースから会場でフィルタ
                    today_races = self.get_races_today()
                    tomorrow_races = self.get_races_tomorrow()
                    all_races = today_races + tomorrow_races
                    
                    filtered_races = [
                        race for race in all_races
                        if venue_name in race.venue or race.venue in venue_name
                    ]
                    
                    if date_filter:
                        filtered_races = [
                            race for race in filtered_races
                            if race.start_time.date() == date_filter.date()
                        ]
                    
                    return filtered_races
            except Exception as e:
                self.logger.warning(f"実データ取得に失敗: {e}")
                self._show_data_source_info("実データ (boatrace.jp)", False)
                
                if self.data_mode.get("fallback_to_mock", True) and self.mock_fetcher:
                    self.logger.info("モックデータにフォールバック中...")
                    races = self.mock_fetcher.search_races_by_venue(venue_name, date_filter)
                    self._show_data_source_info("モックデータ", True)
                    return races
                else:
                    raise
        else:
            if self.mock_fetcher:
                self.logger.info(f"モックデータで会場検索中: {venue_name}")
                races = self.mock_fetcher.search_races_by_venue(venue_name, date_filter)
                self._show_data_source_info("モックデータ", True)
                return races
            else:
                raise RuntimeError("データフェッチャーが利用できません")
    
    def get_data_source_status(self) -> dict:
        """現在のデータソース状態を取得"""
        return {
            "real_fetcher_available": self.real_fetcher is not None,
            "mock_fetcher_available": self.mock_fetcher is not None,
            "using_real_data": self._use_real_data(),
            "fallback_enabled": self.data_mode.get("fallback_to_mock", True),
            "show_source": self.data_mode.get("show_data_source", True),
            "error_handling": self.data_mode.get("mock_on_error", True)
        }