"""
競艇データモデル定義
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class BoatRaceGrade(Enum):
    """競艇レースグレード"""
    SG = "SG"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    GENERAL = "一般"


class BoatRacerClass(Enum):
    """選手級別"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"


class BoatRacingStyle(Enum):
    """進入コース/戦法"""
    INNER = "イン"
    NUKI = "抜き"
    SASHI = "差し"
    MAKURI = "まくり"
    MAKURI_ZASHI = "まくり差し"
    OUTSIDE = "アウト"


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
class BoatRacerStats:
    """選手成績データ"""
    racer_id: str
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
class BoatRacerInfo:
    """選手基本情報"""
    racer_id: str
    number: int
    name: str
    age: int
    racer_class: BoatRacerClass
    boat_racing_style: BoatRacingStyle
    home_venue: str
    racer_stats: Optional[BoatRacerStats] = None
    recent_form: str = ""
    weight: Optional[float] = None
    height: Optional[float] = None


@dataclass
class BoatRaceLaneInfo:
    """競艇レーン情報"""
    lane_id: str
    lane_number: int
    racer_number: int
    motor_number: int
    boat_number: int
    start_timing: Optional[float] = None
    exhibition_time: Optional[float] = None
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
    grade: BoatRaceGrade
    prize_money: int
    course_length: int = 1800 # メートル
    status: str = "発売中"


@dataclass
class RaceDetail:
    """レース詳細情報"""
    race_info: RaceInfo
    racers: List[BoatRacerInfo]
    lanes: List[BoatRaceLaneInfo] = field(default_factory=list)
    odds: Optional[OddsInfo] = None
    weather: str = "晴"
    wind_speed: float = 0.0
    temperature: float = 20.0
    track_condition: str = "良"
    
    def get_racer_by_number(self, number: int) -> Optional[BoatRacerInfo]:
        """登録番号で選手を検索"""
        for racer in self.racers:
            if racer.number == number:
                return racer
        return None

    def get_lane_by_racer(self, racer_number: int) -> Optional[BoatRaceLaneInfo]:
        """選手登録番号からレーンを検索"""
        for lane in self.lanes:
            if lane.racer_number == racer_number:
                return lane
        return None


@dataclass
class PredictionScore:
    """予想スコア詳細"""
    racer_number: int
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
class BoatRaceVenueInfo:
    """競艇場情報"""
    name: str
    code: str
    water_quality: str # 淡水, 汽水, 海水
    tide_effect: str # 大, 中, 小
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
        venue="桐生",
        race_number=1,
        start_time=datetime(2024, 12, 5, 10, 15),
        grade=BoatRaceGrade.GENERAL,
        prize_money=300 # 競艇の賞金に合わせて変更
    )

    racers = []
    racer_profiles = _generate_realistic_racer_profiles()
    
    for i, profile in enumerate(racer_profiles, 1):
        # より現実的な成績データを生成
        recent_results = _generate_recent_results(profile['win_rate'])
        
        racer = BoatRacerInfo(
            racer_id=f"racer_{i:03d}",
            number=i,
            name=profile['name'],
            age=profile['age'],
            racer_class=profile['racer_class'],
            boat_racing_style=profile['boat_racing_style'],
            home_venue=profile['home_venue'],
            racer_stats=BoatRacerStats(
                racer_id=f"racer_{i:03d}",
                win_rate=profile['win_rate'],
                place_rate=profile['place_rate'],
                show_rate=profile['show_rate'],
                total_races=profile['total_races'],
                wins=int(profile['total_races'] * profile['win_rate']),
                places=int(profile['total_races'] * profile['place_rate']),
                shows=int(profile['total_races'] * profile['show_rate']),
                recent_results=recent_results,
                venue_stats={
                    "桐生": {
                        "win_rate": profile['win_rate'] * random.uniform(0.8, 1.3),
                        "place_rate": profile['place_rate'] * random.uniform(0.9, 1.2)
                    }
                }
            )
        )
        racers.append(racer)

    return RaceDetail(
        race_info=race_info,
        racers=racers
    )

def _generate_realistic_racer_profiles():
    """現実的な選手プロフィールを生成"""
    import random
    
    names = ["田中太郎", "佐藤次郎", "鈴木三郎", "高橋四郎", "山田五郎", "中村六郎"]
    venues = ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡"]
    styles = [BoatRacingStyle.INNER, BoatRacingStyle.SASHI, BoatRacingStyle.MAKURI, BoatRacingStyle.OUTSIDE]
    classes = [BoatRacerClass.A1, BoatRacerClass.A2, BoatRacerClass.B1, BoatRacerClass.B2]
    
    profiles = []
    for i in range(6):
        # 級班に応じた勝率設定（競艇は競輪より勝率が高い傾向）
        racer_class = random.choice(classes)
        base_win_rate = {
            BoatRacerClass.A1: 0.25,
            BoatRacerClass.A2: 0.18,
            BoatRacerClass.B1: 0.12,
            BoatRacerClass.B2: 0.08
        }[racer_class]
        
        # 個人差を追加
        win_rate = base_win_rate * random.uniform(0.7, 1.4)
        place_rate = win_rate + random.uniform(0.15, 0.25)
        show_rate = place_rate + random.uniform(0.20, 0.35)
        
        # 年齢に応じた調整
        age = random.randint(20, 55)
        if 25 <= age <= 40:  # ピーク年齢
            performance_factor = random.uniform(1.0, 1.2)
        elif age < 25 or age > 50:
            performance_factor = random.uniform(0.8, 1.0)
        else:
            performance_factor = random.uniform(0.9, 1.1)
        
        win_rate *= performance_factor
        place_rate *= performance_factor
        show_rate = min(0.8, show_rate * performance_factor)
        
        profiles.append({
            'name': names[i],
            'age': age,
            'racer_class': racer_class,
            'boat_racing_style': random.choice(styles),
            'home_venue': random.choice(venues),
            'win_rate': round(win_rate, 3),
            'place_rate': round(place_rate, 3),
            'show_rate': round(show_rate, 3),
            'total_races': random.randint(100, 500)
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
            venue=random.choice(["桐生", "戸田", "江戸川", "平和島"]),
            grade="一般"
        )
        results.append(result)
        
        # 調子の微調整（連続性を持たせる）
        current_form *= random.uniform(0.95, 1.05)
        current_form = max(0.5, min(1.5, current_form))
    
    # 新しい順（最新が最初）にソート
    results.sort(key=lambda x: x.race_date, reverse=True)
    return results