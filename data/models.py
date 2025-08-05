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
    """サンプルレースデータを作成（テスト用・改善版）"""
    import random
    
    race_info = RaceInfo(
        race_id="20241205_15_01",
        venue="平塚",
        race_number=1,
        start_time=datetime(2024, 12, 5, 10, 15),
        grade=RaceGrade.F1,
        prize_money=100
    )

    riders = []
    rider_profiles = _generate_realistic_rider_profiles()
    
    for i, profile in enumerate(rider_profiles, 1):
        # より現実的な成績データを生成
        recent_results = _generate_recent_results(profile['win_rate'])
        
        rider = RiderInfo(
            rider_id=f"rider_{i:03d}",
            number=i,
            name=profile['name'],
            age=profile['age'],
            class_rank=profile['class_rank'],
            racing_style=profile['racing_style'],
            home_venue=profile['home_venue'],
            stats=RiderStats(
                rider_id=f"rider_{i:03d}",
                win_rate=profile['win_rate'],
                place_rate=profile['place_rate'],
                show_rate=profile['show_rate'],
                total_races=profile['total_races'],
                wins=int(profile['total_races'] * profile['win_rate']),
                places=int(profile['total_races'] * profile['place_rate']),
                shows=int(profile['total_races'] * profile['show_rate']),
                recent_results=recent_results,
                venue_stats={
                    "平塚": {
                        "win_rate": profile['win_rate'] * random.uniform(0.8, 1.3),
                        "place_rate": profile['place_rate'] * random.uniform(0.9, 1.2)
                    }
                }
            )
        )
        riders.append(rider)

    return RaceDetail(
        race_info=race_info,
        riders=riders
    )

def _generate_realistic_rider_profiles():
    """現実的な選手プロフィールを生成"""
    import random
    
    names = ["田中太郎", "佐藤次郎", "鈴木三郎", "高橋四郎", "山田五郎", "中村六郎", "小林七郎"]
    venues = ["平塚", "川崎", "小田原", "静岡", "名古屋", "京都", "大阪"]
    styles = [RacingStyle.SPRINTER, RacingStyle.LEADER, RacingStyle.TRACKER, RacingStyle.SWEEPER]
    classes = [RiderClass.S1, RiderClass.S2, RiderClass.A1, RiderClass.A2, RiderClass.A3]
    
    profiles = []
    for i in range(7):
        # 級班に応じた勝率設定
        class_rank = random.choice(classes)
        base_win_rate = {
            RiderClass.S1: 0.25,
            RiderClass.S2: 0.20,
            RiderClass.A1: 0.15,
            RiderClass.A2: 0.12,
            RiderClass.A3: 0.08
        }[class_rank]
        
        # 個人差を追加
        win_rate = base_win_rate * random.uniform(0.7, 1.4)
        place_rate = win_rate + random.uniform(0.15, 0.25)
        show_rate = place_rate + random.uniform(0.20, 0.35)
        
        # 年齢に応じた調整
        age = random.randint(22, 45)
        if 25 <= age <= 32:  # ピーク年齢
            performance_factor = random.uniform(1.0, 1.2)
        elif age < 25 or age > 38:
            performance_factor = random.uniform(0.8, 1.0)
        else:
            performance_factor = random.uniform(0.9, 1.1)
        
        win_rate *= performance_factor
        place_rate *= performance_factor
        show_rate = min(0.8, show_rate * performance_factor)
        
        profiles.append({
            'name': names[i],
            'age': age,
            'class_rank': class_rank,
            'racing_style': random.choice(styles),
            'home_venue': random.choice(venues),
            'win_rate': round(win_rate, 3),
            'place_rate': round(place_rate, 3),
            'show_rate': round(show_rate, 3),
            'total_races': random.randint(80, 300)
        })
    
    return profiles

def _generate_recent_results(base_win_rate: float) -> List[RaceResult]:
    """選手の直近成績を現実的に生成"""
    import random
    from datetime import datetime, timedelta
    
    results = []
    current_form = random.uniform(0.7, 1.3)  # 現在の調子
    
    for i in range(10):  # 直近10走
        # トレンドを考慮した順位決定
        adjusted_win_rate = base_win_rate * current_form
        
        # 順位を確率的に決定
        rand = random.random()
        if rand < adjusted_win_rate:
            position = 1
        elif rand < adjusted_win_rate + 0.15:
            position = 2
        elif rand < adjusted_win_rate + 0.25:
            position = 3
        elif rand < 0.7:
            position = random.randint(4, 6)
        else:
            position = random.randint(7, 9)
        
        # 日付を生成（過去10戦分）
        race_date = datetime.now() - timedelta(days=random.randint(7, 70))
        
        result = RaceResult(
            race_id=f"past_race_{i}",
            finish_position=position,
            race_date=race_date,
            venue=random.choice(["平塚", "川崎", "小田原"]),
            grade="F1"
        )
        results.append(result)
        
        # 調子の微調整（連続性を持たせる）
        current_form *= random.uniform(0.95, 1.05)
        current_form = max(0.5, min(1.5, current_form))
    
    # 新しい順（最新が最初）にソート
    results.sort(key=lambda x: x.race_date, reverse=True)
    return results