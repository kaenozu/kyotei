"""
競輪予想アプリケーション設定ファイル
"""
import os
from pathlib import Path

# アプリケーション基本設定
APP_NAME = "Keirin Predictor CLI"
APP_VERSION = "1.0.0"

# ディレクトリ設定
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"

# データ取得設定
DATA_SOURCES = {
    "primary": "https://keirin.kdreams.jp",
    "secondary": "https://keirin.jp",
    "backup": "https://www.oddspark.com/keirin/"
}

# スクレイピング設定
SCRAPING_CONFIG = {
    "rate_limit": 2,  # 秒間隔
    "timeout": 10,    # タイムアウト秒数
    "max_retries": 3, # 最大リトライ回数
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# キャッシュ設定（分単位）
CACHE_DURATION = {
    "race_info": 30,      # レース情報
    "rider_stats": 1440,  # 選手成績（24時間）
    "odds": 5,            # オッズ情報
    "venue_data": 10080   # 開催場データ（7日間）
}

# 予想アルゴリズム重み設定
PREDICTION_WEIGHTS = {
    "rider_ability": 0.35,
    "recent_form": 0.25,
    "track_compatibility": 0.20,
    "line_strategy": 0.15,
    "external_factors": 0.05
}

# 級班ポイント設定
CLASS_POINTS = {
    "S1": 100,
    "S2": 90,
    "A1": 80,
    "A2": 70,
    "A3": 60
}

# 表示設定
DISPLAY_CONFIG = {
    "max_races_per_page": 20,
    "recommendation_levels": ["S", "A", "B", "C", "D"],
    "star_ratings": True,
    "color_coding": True
}

# ログ設定
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# 開催場設定
VENUES = {
    "函館": {"code": "01", "distance": 400, "banking": 31.5},
    "青森": {"code": "02", "distance": 400, "banking": 31.5},
    "いわき平": {"code": "03", "distance": 400, "banking": 31.7},
    "弥彦": {"code": "04", "distance": 400, "banking": 31.5},
    "前橋": {"code": "05", "distance": 400, "banking": 31.5},
    "取手": {"code": "06", "distance": 400, "banking": 31.5},
    "宇都宮": {"code": "07", "distance": 400, "banking": 31.5},
    "大宮": {"code": "08", "distance": 400, "banking": 31.5},
    "西武園": {"code": "09", "distance": 400, "banking": 31.5},
    "京王閣": {"code": "10", "distance": 400, "banking": 31.5},
    "立川": {"code": "11", "distance": 400, "banking": 31.5},
    "松戸": {"code": "12", "distance": 333, "banking": 31.5},
    "千葉": {"code": "13", "distance": 333, "banking": 31.5},
    "川崎": {"code": "14", "distance": 333, "banking": 31.5},
    "平塚": {"code": "15", "distance": 400, "banking": 31.5},
    "小田原": {"code": "16", "distance": 333, "banking": 31.5},
    "伊東温泉": {"code": "17", "distance": 333, "banking": 31.5},
    "静岡": {"code": "18", "distance": 400, "banking": 31.5},
    "名古屋": {"code": "19", "distance": 400, "banking": 31.5},
    "岐阜": {"code": "20", "distance": 400, "banking": 31.5},
    "大垣": {"code": "21", "distance": 400, "banking": 31.5},
    "豊橋": {"code": "22", "distance": 400, "banking": 31.5},
    "富山": {"code": "23", "distance": 333, "banking": 31.5},
    "松阪": {"code": "24", "distance": 400, "banking": 31.5},
    "四日市": {"code": "25", "distance": 400, "banking": 31.5},
    "福井": {"code": "26", "distance": 400, "banking": 31.5},
    "奈良": {"code": "27", "distance": 333, "banking": 31.5},
    "向日町": {"code": "28", "distance": 400, "banking": 31.5},
    "和歌山": {"code": "29", "distance": 400, "banking": 31.5},
    "岸和田": {"code": "30", "distance": 400, "banking": 31.5}
}

def ensure_directories():
    """必要なディレクトリを作成"""
    for directory in [CACHE_DIR, LOG_DIR]:
        directory.mkdir(exist_ok=True)

def get_venue_info(venue_name: str) -> dict:
    """開催場情報を取得"""
    return VENUES.get(venue_name, {})