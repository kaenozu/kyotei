"""
競艇予想アプリケーション設定ファイル
"""
from pathlib import Path
from typing import Dict, Any, List

from config.config_manager import get_config_manager
from config.paths import BASE_DIR, DATA_DIR, CACHE_DIR, LOG_DIR

# アプリケーション基本設定
APP_NAME = "Kyotei Predictor CLI"
APP_VERSION = "1.0.0"

# 設定のデフォルト値を定義
DEFAULT_SETTINGS: Dict[str, Any] = {
    "DATA_SOURCES": {
        "primary": "https://boatrace.jp",
        "secondary": "https://boatrace.net",
        "backup": "https://www.oddspark.com/boatrace/",
        "api": "https://api.oddspark.com"
    },
    "SCRAPING_CONFIG": {
        "rate_limit": 2,  # 秒間隔
        "timeout": 30,    # タイムアウト秒数
        "max_retries": 5, # 最大リトライ回数
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
    "CACHE_DURATION": {
        "race_info": 30,      # レース情報
        "racer_stats": 1440,  # 選手成績（24時間）
        "odds": 5,            # オッズ情報
        "venue_data": 10080   # 競艇場データ（7日間）
    },
    "PREDICTION_WEIGHTS": {
        "racer_ability": 0.35,
        "recent_form": 0.25,
        "track_compatibility": 0.20,
        "lane_strategy": 0.15,
        "external_factors": 0.05
    },
    "CLASS_POINTS": {
        "A1": 100,
        "A2": 80,
        "B1": 60,
        "B2": 40
    },
    "DISPLAY_CONFIG": {
        "max_races_per_page": 20,
        "recommendation_levels": ["S", "A", "B", "C", "D"],
        "star_ratings": True,
        "color_coding": True
    },
    "LOG_CONFIG": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file_size": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5,
        "error_log_file": "kyotei_error.log", # エラーログ専用ファイル
        "debug_mode": False # デバッグモードの有効/無効
    },
    "PERFORMANCE_CONFIG": {
        "monitor_interval": 10, # 監視間隔（秒）
        "cpu_warning_threshold": 70, # CPU使用率警告閾値 (%)
        "cpu_critical_threshold": 90, # CPU使用率危険閾値 (%)
        "memory_warning_threshold_mb": 512, # メモリ使用量警告閾値 (MB)
        "memory_critical_threshold_mb": 1024, # メモリ使用量危険閾値 (MB)
        "cache_hit_rate_warning_threshold": 0.5, # キャッシュヒット率警告閾値 (0.0-1.0)
        "cache_hit_rate_critical_threshold": 0.3 # キャッシュヒット率危険閾値 (0.0-1.0)
    },
    "DATA_MODE": {
        "use_real_data": False,  # True: 実データ, False: モックデータ
        "fallback_to_mock": True,  # 実データ取得失敗時にモックを使用
        "mock_on_error": True,  # エラー時にモックデータで継続
        "show_data_source": True  # データソースをユーザーに表示
    }
}

from config.config_manager import get_config_manager


def get_setting(key: str, default: Any = None) -> Any:
    """指定されたキーの設定値を取得する。config_managerに値がなければデフォルト値を返す。"""
    config_manager = get_config_manager()
    return config_manager.get(key, DEFAULT_SETTINGS.get(key, default))

def set_setting(key: str, value: Any):
    """指定されたキーに設定値を保存する。"""
    config_manager = get_config_manager()
    config_manager.set(key, value)

def ensure_directories():
    """必要なディレクトリを作成"""
    for directory in [CACHE_DIR, LOG_DIR]:
        directory.mkdir(exist_ok=True)

def load_settings():
    """config_managerにデフォルト設定を書き込む（初回起動時など）"""
    config_manager = get_config_manager()
    for key, value in DEFAULT_SETTINGS.items():
        if config_manager.get(key) is None:
            config_manager.set(key, value)



# アプリケーション起動時にデフォルト設定をロード
load_settings()
