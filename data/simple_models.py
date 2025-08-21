"""
艇国データバンク用の簡素化データモデル
実際に取得可能なデータのみを扱う
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime, timedelta


@dataclass
class TeikokuRaceInfo:
    """艇国DBから取得できる基本レース情報"""

    race_id: str  # YYYYMMDD_pid_rno
    date: str  # YYYYMMDD
    venue_id: str  # 01-24
    venue_name: str  # 競艇場名
    race_number: int  # 1-12
    status: str  # 発売中/終了
    start_time: Optional[datetime] = None  # 推定開始時刻

    def is_finished(self) -> bool:
        """レースが終了しているかどうかを判定"""
        if not self.start_time:
            return False

        # 現在時刻
        now = datetime.now()

        # レース開始から15分経過していれば終了とみなす
        race_end_time = self.start_time + timedelta(minutes=15)
        return now > race_end_time

    def get_sort_key(self) -> tuple:
        """ソート用のキーを生成（未終了レース優先、時刻順）"""
        is_finished = self.is_finished()
        time_key = self.start_time if self.start_time else datetime.max
        return (is_finished, time_key)

    def get_official_url(self) -> str:
        """ボートレース公式サイトのURLを生成"""
        return f"https://www.boatrace.jp/owsp/sp/race/raceindex?hd={self.date}&jcd={self.venue_id}#r{self.race_number}"


@dataclass
class TeikokuRacerStats:
    """選手の詳細成績データ"""

    regno: Optional[str] = None  # 登録番号
    total_races: int = 0  # 総出走数
    total_wins: int = 0  # 総1着数
    win_rate: float = 0.0  # 総勝率
    place_rate: float = 0.0  # 連対率
    show_rate: float = 0.0  # 3連率

    # コース別勝率
    course_1_rate: float = 0.0  # 1コース勝率
    course_2_rate: float = 0.0  # 2コース勝率
    course_3_rate: float = 0.0  # 3コース勝率
    course_4_rate: float = 0.0  # 4コース勝率
    course_5_rate: float = 0.0  # 5コース勝率
    course_6_rate: float = 0.0  # 6コース勝率

    # 当地成績
    local_races: int = 0  # 当地出走数
    local_wins: int = 0  # 当地1着数
    local_win_rate: float = 0.0  # 当地勝率

    # グレード別勝率
    sg_win_rate: float = 0.0  # SG勝率
    g1_win_rate: float = 0.0  # G1勝率
    general_win_rate: float = 0.0  # 一般戦勝率

    # 今節成績（新規追加）
    current_series_races: int = 0  # 今節出走数
    current_series_wins: int = 0  # 今節1着数
    current_series_win_rate: float = 0.0  # 今節勝率
    current_series_results: List[int] = field(
        default_factory=list
    )  # 今節着順履歴 [1,3,2,1]

    # スタート成績（新規追加）
    average_st: float = 0.0  # 平均ST
    flying_rate: float = 0.0  # F率（フライング率）
    late_rate: float = 0.0  # L率（出遅れ率）
    start_timing_score: float = 0.0  # スタート総合スコア

    # モーター・ボート成績（新規追加）
    motor_number: int = 0  # モーター番号
    motor_win_rate: float = 0.0  # モーター勝率
    motor_place_rate: float = 0.0  # モーター連対率
    boat_number: int = 0  # ボート番号
    boat_win_rate: float = 0.0  # ボート勝率
    boat_place_rate: float = 0.0  # ボート連対率

    # 近況・調子データ（新規追加）
    recent_form_score: float = 0.0  # 直近調子スコア
    last_6_results: List[int] = field(default_factory=list)  # 直近6走着順
    consistency_score: float = 0.0  # 安定性スコア
    trend_score: float = 0.0  # トレンドスコア（上昇/下降）

    def calculate_recent_form_score(self) -> float:
        """直近調子スコアを計算"""
        if not self.last_6_results:
            return 0.0

        # 着順を点数化（1着=6点、2着=5点...6着=1点）
        scores = [7 - result for result in self.last_6_results if 1 <= result <= 6]
        if not scores:
            return 0.0

        # 時間重み付け（新しいレースほど重要）
        weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5][: len(scores)]
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(
            weights[: len(scores)]
        )

        return min(weighted_score / 6.0, 1.0)  # 0-1に正規化

    def calculate_consistency_score(self) -> float:
        """安定性スコアを計算"""
        if not self.last_6_results or len(self.last_6_results) < 3:
            return 0.0

        # 標準偏差の逆数を安定性とする
        import statistics

        try:
            std_dev = statistics.stdev(self.last_6_results)
            return max(0.0, 1.0 - (std_dev / 3.0))  # 標準偏差3以上で0点
        except:
            return 0.0

    def calculate_trend_score(self) -> float:
        """トレンドスコア（向上/悪化傾向）を計算"""
        if not self.last_6_results or len(self.last_6_results) < 4:
            return 0.0

        # 前半3走と後半3走の平均着順を比較
        mid_point = len(self.last_6_results) // 2
        recent_avg = sum(self.last_6_results[:mid_point]) / mid_point
        past_avg = sum(self.last_6_results[mid_point:]) / (
            len(self.last_6_results) - mid_point
        )

        # 着順が良くなっているほど高スコア
        trend = (past_avg - recent_avg) / 3.0  # 3着差で1.0
        return max(-1.0, min(1.0, trend))  # -1.0 ~ 1.0に正規化


@dataclass
class TeikokuRacerInfo:
    """艇国DBから取得できる選手情報"""

    racer_id: str  # teikoku_name_number
    number: int  # 1-6
    name: str  # 実際の選手名
    estimated_strength: float  # 推定実力値（0.1-0.4）
    lane_advantage: float  # 艇番有利度
    stats: Optional[TeikokuRacerStats] = None  # 詳細成績データ


@dataclass
class TeikokuRaceDetail:
    """艇国DB レース詳細情報"""

    race_info: TeikokuRaceInfo
    racers: List[TeikokuRacerInfo]
    weather_info: Optional[Dict] = None  # 気象情報を追加

    def get_racer_by_number(self, number: int) -> Optional[TeikokuRacerInfo]:
        """艇番で選手を取得"""
        for racer in self.racers:
            if racer.number == number:
                return racer
        return None


@dataclass
class TeikokuPrediction:
    """艇国DB 予想結果"""

    race_id: str
    predictions: dict  # {艇番: 勝率予想}
    recommended_win: int  # 単勝推奨
    recommended_place: List[int]  # 複勝推奨（3艇）
    confidence: float  # 予想信頼度
    confidence_breakdown: Optional[dict] = None  # 信頼度内訳情報


# 競艇場マッピング
VENUE_MAPPING = {
    "01": "桐生",
    "02": "戸田",
    "03": "江戸川",
    "04": "平和島",
    "05": "多摩川",
    "06": "浜名湖",
    "07": "蒲郡",
    "08": "常滑",
    "09": "津",
    "10": "三国",
    "11": "びわこ",
    "12": "住之江",
    "13": "尼崎",
    "14": "鳴門",
    "15": "丸亀",
    "16": "児島",
    "17": "宮島",
    "18": "徳山",
    "19": "下関",
    "20": "若松",
    "21": "芦屋",
    "22": "福岡",
    "23": "唐津",
    "24": "大村",
}


def get_venue_name(venue_id: str) -> str:
    """競艇場IDから名前を取得"""
    return VENUE_MAPPING.get(venue_id, f"場{venue_id}")


def get_venue_id(venue_name: str) -> Optional[str]:
    """競艇場名からIDを取得"""
    for vid, vname in VENUE_MAPPING.items():
        if vname == venue_name:
            return vid
    return None
