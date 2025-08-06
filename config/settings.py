"""
競艇予想アプリケーション設定ファイル
"""
from pathlib import Path
from typing import Dict, Any

from config.config_manager import config_manager
from config.paths import BASE_DIR, DATA_DIR, CACHE_DIR, LOG_DIR

# アプリケーション基本設定
APP_NAME = "Kyotei Predictor CLI"
APP_VERSION = "1.0.0"

# データ取得設定 (デフォルト値)
DATA_SOURCES: Dict[str, str] = {
    "primary": "https://boatrace.jp",
    "secondary": "https://boatrace.net",
    "backup": "https://www.oddspark.com/boatrace/",
    "api": "https://api.oddspark.com"
}

# スクレイピング設定 (デフォルト値)
SCRAPING_CONFIG: Dict[str, Any] = {
    "rate_limit": 2,  # 秒間隔
    "timeout": 10,    # タイムアウト秒数
    "max_retries": 3, # 最大リトライ回数
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# キャッシュ設定（分単位） (デフォルト値)
CACHE_DURATION: Dict[str, int] = {
    "race_info": 30,      # レース情報
    "racer_stats": 1440,  # 選手成績（24時間）
    "odds": 5,            # オッズ情報
    "venue_data": 10080   # 競艇場データ（7日間）
}

# 予想アルゴリズム重み設定 (デフォルト値)
PREDICTION_WEIGHTS: Dict[str, float] = {
    "racer_ability": 0.35,
    "recent_form": 0.25,
    "track_compatibility": 0.20,
    "lane_strategy": 0.15,
    "external_factors": 0.05
}

# 級班ポイント設定 (デフォルト値)
CLASS_POINTS: Dict[str, int] = {
    "A1": 100,
    "A2": 80,
    "B1": 60,
    "B2": 40
}

# 表示設定 (デフォルト値)
DISPLAY_CONFIG: Dict[str, Any] = {
    "max_races_per_page": 20,
    "recommendation_levels": ["S", "A", "B", "C", "D"],
    "star_ratings": True,
    "color_coding": True
}

# ログ設定 (デフォルト値)
LOG_CONFIG: Dict[str, Any] = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
    "error_log_file": "kyotei_error.log", # エラーログ専用ファイル
    "debug_mode": False # デバッグモードの有効/無効
}

# パフォーマンス監視設定 (デフォルト値)
PERFORMANCE_CONFIG: Dict[str, Any] = {
    "monitor_interval": 10, # 監視間隔（秒）
    "cpu_warning_threshold": 70, # CPU使用率警告閾値 (%)
    "cpu_critical_threshold": 90, # CPU使用率危険閾値 (%)
    "memory_warning_threshold_mb": 512, # メモリ使用量警告閾値 (MB)
    "memory_critical_threshold_mb": 1024, # メモリ使用量危険閾値 (MB)
    "cache_hit_rate_warning_threshold": 0.5, # キャッシュヒット率警告閾値 (0.0-1.0)
    "cache_hit_rate_critical_threshold": 0.3 # キャッシュヒット率危険閾値 (0.0-1.0)
}

# 競艇場設定 (これは永続化の対象外とする)
VENUES: Dict[str, Dict[str, Any]] = {
    "桐生": {"code": "01", "distance": 1800, "water_quality": "淡水", "wind_effect": "強い", "tide_effect": "無"},
    "戸田": {"code": "02", "distance": 1800, "water_quality": "淡水", "wind_effect": "普通", "tide_effect": "無"},
    "江戸川": {"code": "03", "distance": 1800, "water_quality": "汽水", "wind_effect": "非常に強い", "tide_effect": "大"},
    "平和島": {"code": "04", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "多摩川": {"code": "05", "distance": 1800, "water_quality": "淡水", "wind_effect": "弱い", "tide_effect": "無"},
    "浜名湖": {"code": "06", "distance": 1800, "water_quality": "汽水", "wind_effect": "普通", "tide_effect": "小"},
    "蒲郡": {"code": "07", "distance": 1800, "water_quality": "海水", "wind_effect": "強い", "tide_effect": "中"},
    "常滑": {"code": "08", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "津": {"code": "09", "distance": 1800, "water_quality": "淡水", "wind_effect": "弱い", "tide_effect": "無"},
    "三国": {"code": "10", "distance": 1800, "water_quality": "淡水", "wind_effect": "普通", "tide_effect": "無"},
    "びわこ": {"code": "11", "distance": 1800, "water_quality": "淡水", "wind_effect": "普通", "tide_effect": "無"},
    "住之江": {"code": "12", "distance": 1800, "water_quality": "淡水", "wind_effect": "弱い", "tide_effect": "無"},
    "尼崎": {"code": "13", "distance": 1800, "water_quality": "淡水", "wind_effect": "普通", "tide_effect": "無"},
    "鳴門": {"code": "14", "distance": 1800, "water_quality": "海水", "wind_effect": "強い", "tide_effect": "大"},
    "丸亀": {"code": "15", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "児島": {"code": "16", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "宮島": {"code": "17", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "大"},
    "徳山": {"code": "18", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "下関": {"code": "19", "distance": 1800, "water_quality": "海水", "wind_effect": "強い", "tide_effect": "中"},
    "若松": {"code": "20", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "芦屋": {"code": "21", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "福岡": {"code": "22", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"},
    "唐津": {"code": "23", "distance": 1800, "water_quality": "海水", "wind_effect": "強い", "tide_effect": "中"},
    "大村": {"code": "24", "distance": 1800, "water_quality": "海水", "wind_effect": "普通", "tide_effect": "中"}
}

def ensure_directories():
    """必要なディレクトリを作成"""
    for directory in [CACHE_DIR, LOG_DIR]:
        directory.mkdir(exist_ok=True)

def get_venue_info(venue_name: str) -> dict:
    """開催場情報を取得"""
    return VENUES.get(venue_name, {})

def load_settings():
    """ConfigManagerから設定を読み込み、グローバル設定を更新する"""
    global DATA_SOURCES, SCRAPING_CONFIG, CACHE_DURATION, PREDICTION_WEIGHTS, CLASS_POINTS, DISPLAY_CONFIG, LOG_CONFIG, PERFORMANCE_CONFIG

    # 各設定カテゴリをConfigManagerから読み込み、デフォルト値とマージ
    DATA_SOURCES.update(config_manager.get("DATA_SOURCES", {}))
    SCRAPING_CONFIG.update(config_manager.get("SCRAPING_CONFIG", {}))
    CACHE_DURATION.update(config_manager.get("CACHE_DURATION", {}))
    PREDICTION_WEIGHTS.update(config_manager.get("PREDICTION_WEIGHTS", {}))
    CLASS_POINTS.update(config_manager.get("CLASS_POINTS", {}))
    DISPLAY_CONFIG.update(config_manager.get("DISPLAY_CONFIG", {}))
    LOG_CONFIG.update(config_manager.get("LOG_CONFIG", {}))
    PERFORMANCE_CONFIG.update(config_manager.get("PERFORMANCE_CONFIG", {}))

def save_settings():
    """現在のグローバル設定をConfigManagerに保存する"""
    config_manager.set("DATA_SOURCES", DATA_SOURCES)
    config_manager.set("SCRAPING_CONFIG", SCRAPING_CONFIG)
    config_manager.set("CACHE_DURATION", CACHE_DURATION)
    config_manager.set("PREDICTION_WEIGHTS", PREDICTION_WEIGHTS)
    config_manager.set("CLASS_POINTS", CLASS_POINTS)
    config_manager.set("DISPLAY_CONFIG", DISPLAY_CONFIG)
    config_manager.set("LOG_CONFIG", LOG_CONFIG)
    config_manager.set("PERFORMANCE_CONFIG", PERFORMANCE_CONFIG)

# アプリケーション起動時に設定を読み込む
load_settings()
