"""
競輪データモデル定義
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class RaceGrade(Enum):
    """レースグレード"""
    GP = "GP"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    F1 = "F1"
    F2 = "F2"


class RiderClass(Enum):
    """選手級班"""
    S1 = "S1"
    S2 = "S2"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"


class RacingStyle(Enum):
    """脚質"""
    SPRINTER = "逃げ"
    LEADER = "先行"
    TRACKER = "差し"
    SWEEPER = "追込"


@dataclass
class RaceResult:
    """レース結果"""
    race_id: str
    finish_position: int
    race_time: Optional[float] = None
    race_date: Optional[datetime] = None
    venue: Optional[str] = None
    grade: Optional[str] = None


@dataclass
class RiderStats:
    """選手成績データ"""
    rider_id: str
    win_rate: float = 0.0
    place_rate: float = 0.0
    show_rate: float = 0.0
    recent_results: List[RaceResult] = field(default_factory=list)
    venue_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    total_races: int = 0
    wins: int = 0
    places: int = 0
    shows: int = 0


@dataclass
class RiderInfo:
    """選手基本情報"""
    rider_id: str
    number: int
    name: str
    age: int
    class_rank: RiderClass
    racing_style: RacingStyle
    home_venue: str
    stats: Optional[RiderStats] = None
    recent_form: str = ""
    weight: Optional[float] = None
    height: Optional[float] = None


@dataclass
class LineInfo:
    """ライン情報"""
    line_id: str
    leader_number: int
    members: List[int]
    strength: float = 0.0
    strategy: str = ""


@dataclass
class OddsInfo:
    """オッズ情報"""
    win_odds: Dict[int, float] = field(default_factory=dict)
    place_odds: Dict[int, float] = field(default_factory=dict)
    quinella_odds: Dict[str, float] = field(default_factory=dict)
    exacta_odds: Dict[str, float] = field(default_factory=dict)
    trifecta_odds: Dict[str, float] = field(default_factory=dict)
    trio_odds: Dict[str, float] = field(default_factory=dict)


@dataclass
class RaceInfo:
    """レース基本情報"""
    race_id: str
    venue: str
    race_number: int
    start_time: datetime
    grade: RaceGrade
    prize_money: int
    distance: int = 2000
    laps: int = 5
    status: str = "発売中"


@dataclass
class RaceDetail:
    """レース詳細情報"""
    race_info: RaceInfo
    riders: List[RiderInfo]
    lines: List[LineInfo] = field(default_factory=list)
    odds: Optional[OddsInfo] = None
    weather: str = "晴"
    wind_speed: float = 0.0
    temperature: float = 20.0
    track_condition: str = "良"

    def get_rider_by_number(self, number: int) -> Optional[RiderInfo]:
        """車番で選手を検索"""
        for rider in self.riders:
            if rider.number == number:
                return rider
        return None

    def get_line_by_rider(self, rider_number: int) -> Optional[LineInfo]:
        """選手車番からラインを検索"""
        for line in self.lines:
            if rider_number in line.members:
                return line
        return None


@dataclass
class PredictionScore:
    """予想スコア詳細"""
    rider_number: int
    total_score: float
    ability_score: float
    form_score: float
    track_score: float
    line_score: float
    external_score: float
    confidence: float


@dataclass
class BetRecommendation:
    """買い目推奨"""
    bet_type: str
    combination: str
    expected_odds: float
    confidence: str
    expected_value: float
    investment_ratio: float = 1.0


@dataclass
class PredictionResult:
    """予想結果"""
    race_id: str
    rankings: List[int]
    scores: Dict[int, PredictionScore]
    confidence: float
    betting_recommendations: List[BetRecommendation] = field(default_factory=list)
    prediction_time: datetime = field(default_factory=datetime.now)


@dataclass
class VenueInfo:
    """開催場情報"""
    name: str
    code: str
    distance: int
    banking: float
    characteristics: Dict[str, bool] = field(default_factory=dict)

    @property
    def is_sprint_favorable(self) -> bool:
        """スプリント有利バンクかどうか"""
        return self.characteristics.get('sprint_favorable', False)

    @property
    def is_endurance_favorable(self) -> bool:
        """持久力有利バンクかどうか"""
        return self.characteristics.get('endurance_favorable', False)


@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    key: str
    data: any
    created_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """キャッシュが期限切れかどうか"""
        return datetime.now() > self.expires_at


def create_sample_race() -> RaceDetail:
    """サンプルレースデータを作成（テスト用）"""
    race_info = RaceInfo(
        race_id="20241205_15_01",
        venue="平塚",
        race_number=1,
        start_time=datetime(2024, 12, 5, 10, 15),
        grade=RaceGrade.F1,
        prize_money=100
    )

    riders = []
    for i in range(1, 8):
        rider = RiderInfo(
            rider_id=f"rider_{i:03d}",
            number=i,
            name=f"選手{i}",
            age=25 + i,
            class_rank=RiderClass.A1,
            racing_style=RacingStyle.SPRINTER,
            home_venue="平塚",
            stats=RiderStats(
                rider_id=f"rider_{i:03d}",
                win_rate=0.15 + i * 0.02,
                place_rate=0.35 + i * 0.03,
                show_rate=0.55 + i * 0.04
            )
        )
        riders.append(rider)

    return RaceDetail(
        race_info=race_info,
        riders=riders
    )