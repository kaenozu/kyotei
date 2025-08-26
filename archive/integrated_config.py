#!/usr/bin/env python3
"""
統合設定管理システム
既存設定と最適化設定を統合管理（環境変数による制御）
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IntegratedConfig:
    """統合設定管理クラス"""
    
    def __init__(self, config_file: str = "integrated_config.json"):
        self.config_file = config_file
        self.settings = {}
        
        # デフォルト設定
        self._setup_defaults()
        
        # 設定ファイルの読み込み
        self._load_config_file()
        
        # 環境変数による上書き
        self._apply_environment_overrides()
        
        logger.info("統合設定管理初期化完了")
    
    def _setup_defaults(self):
        """デフォルト設定"""
        self.settings = {
            # システム全般
            "system": {
                "name": "競艇予想システム",
                "version": "3.0-Integrated",
                "debug": False
            },
            
            # 最適化設定
            "optimization": {
                "enabled": True,
                "fast_startup": True,
                "lazy_loading": True,
                "cache_enabled": True,
                "cache_timeout": 300,
                "async_operations": True
            },
            
            # データベース設定
            "database": {
                "accuracy_tracker_path": "cache/accuracy_tracker.db",
                "backup_enabled": True,
                "connection_pool_size": 5
            },
            
            # API設定
            "api": {
                "base_urls": {
                    "programs": "https://boatraceopenapi.github.io/programs/v2",
                    "previews": "https://boatraceopenapi.github.io/previews/v2",
                    "results": "https://boatraceopenapi.github.io/results/v2"
                },
                "timeout": 30,
                "retry_count": 3,
                "request_delay_min": 2.0,
                "request_delay_max": 5.0,
                "cache_responses": True
            },
            
            # ML設定
            "ml": {
                "use_lightweight": True,
                "use_statistical_fallback": True,
                "model_cache_dir": "cache/ml_models",
                "feature_columns": [
                    "national_win_rate", "local_win_rate", "motor_performance",
                    "boat_performance", "start_timing", "age", "boat_number"
                ]
            },
            
            # Web設定
            "web": {
                "host": "0.0.0.0",
                "port": 5000,
                "threaded": True,
                "auto_reload": False
            },
            
            # ログ設定
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_enabled": True,
                "file_path": "logs/integrated_system.log"
            },
            
            # 会場マッピング
            "venues": {
                1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
                7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
                13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
                19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
            }
        }
    
    def _load_config_file(self):
        """設定ファイルの読み込み"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # 設定をマージ（ファイルの設定で上書き）
                self._merge_config(self.settings, file_config)
                logger.info(f"設定ファイル読み込み完了: {self.config_file}")
            else:
                logger.info("設定ファイルが存在しません。デフォルト設定を使用します。")
                
        except Exception as e:
            logger.warning(f"設定ファイル読み込みエラー: {e}")
    
    def _apply_environment_overrides(self):
        """環境変数による設定上書き"""
        
        # 最適化設定
        if os.getenv('OPTIMIZATION_ENABLED') is not None:
            self.settings['optimization']['enabled'] = os.getenv('OPTIMIZATION_ENABLED', '1') == '1'
        
        if os.getenv('FAST_STARTUP') is not None:
            self.settings['optimization']['fast_startup'] = os.getenv('FAST_STARTUP', '1') == '1'
        
        if os.getenv('USE_CACHE') is not None:
            self.settings['optimization']['cache_enabled'] = os.getenv('USE_CACHE', '1') == '1'
        
        # Web設定
        if os.getenv('WEB_PORT') is not None:
            try:
                self.settings['web']['port'] = int(os.getenv('WEB_PORT'))
            except ValueError:
                pass
        
        if os.getenv('WEB_HOST') is not None:
            self.settings['web']['host'] = os.getenv('WEB_HOST')
        
        # デバッグ設定
        if os.getenv('DEBUG') is not None:
            self.settings['system']['debug'] = os.getenv('DEBUG', '0') == '1'
        
        # ログレベル
        if os.getenv('LOG_LEVEL') is not None:
            self.settings['logging']['level'] = os.getenv('LOG_LEVEL', 'INFO')
        
        logger.info("環境変数による設定上書き完了")
    
    def _merge_config(self, base_config: Dict, override_config: Dict):
        """設定のマージ（再帰的）"""
        for key, value in override_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_config(base_config[key], value)
            else:
                base_config[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """設定値取得（ドット記法対応）"""
        try:
            keys = key_path.split('.')
            value = self.settings
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key_path: str, value: Any):
        """設定値設定（ドット記法対応）"""
        try:
            keys = key_path.split('.')
            config = self.settings
            
            # 最後のキーまで辿る
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 値を設定
            config[keys[-1]] = value
            
        except Exception as e:
            logger.error(f"設定値設定エラー: {e}")
    
    def save_config(self):
        """設定をファイルに保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            
            logger.info(f"設定ファイル保存完了: {self.config_file}")
            
        except Exception as e:
            logger.error(f"設定ファイル保存エラー: {e}")
    
    def get_database_path(self, db_name: str = 'accuracy_tracker') -> str:
        """データベースパス取得"""
        if db_name == 'accuracy_tracker':
            return self.get('database.accuracy_tracker_path', 'cache/accuracy_tracker.db')
        else:
            return f"cache/{db_name}.db"
    
    def get_venue_name(self, venue_id: int) -> str:
        """会場名取得"""
        venues = self.get('venues', {})
        return venues.get(str(venue_id), venues.get(venue_id, f"会場{venue_id}"))
    
    def is_optimization_enabled(self) -> bool:
        """最適化機能有効チェック"""
        return self.get('optimization.enabled', True)
    
    def is_fast_startup_enabled(self) -> bool:
        """高速起動有効チェック"""
        return self.get('optimization.fast_startup', True)
    
    def get_api_config(self) -> Dict:
        """API設定取得"""
        return self.get('api', {})
    
    def get_ml_config(self) -> Dict:
        """ML設定取得"""
        return self.get('ml', {})
    
    def get_web_config(self) -> Dict:
        """Web設定取得"""
        return self.get('web', {})
    
    def setup_directories(self):
        """必要ディレクトリの作成"""
        directories = [
            'cache',
            'logs',
            self.get('ml.model_cache_dir', 'cache/ml_models')
        ]
        
        for dir_path in directories:
            Path(dir_path).mkdir(exist_ok=True, parents=True)
        
        logger.info("必要ディレクトリ作成完了")
    
    def get_status(self) -> Dict:
        """設定状態取得"""
        return {
            'config_file': self.config_file,
            'config_file_exists': Path(self.config_file).exists(),
            'optimization_enabled': self.is_optimization_enabled(),
            'fast_startup_enabled': self.is_fast_startup_enabled(),
            'debug_mode': self.get('system.debug', False),
            'log_level': self.get('logging.level', 'INFO'),
            'web_port': self.get('web.port', 5000)
        }


# グローバル統合設定インスタンス
integrated_config = IntegratedConfig()

# 既存コードとの互換性
def get_config():
    """統合設定取得"""
    return integrated_config

# 便利関数
def get_venue_name(venue_id: int) -> str:
    """会場名取得"""
    return integrated_config.get_venue_name(venue_id)

def get_database_path(db_name: str = 'accuracy_tracker') -> str:
    """データベースパス取得"""
    return integrated_config.get_database_path(db_name)

def is_optimization_enabled() -> bool:
    """最適化有効チェック"""
    return integrated_config.is_optimization_enabled()


if __name__ == "__main__":
    """テスト実行"""
    print("=" * 60)
    print("統合設定管理 テスト")
    print("=" * 60)
    
    config = IntegratedConfig()
    
    print("\n[INFO] 設定状態:")
    status = config.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print(f"\n[TEST] 設定値取得テスト:")
    print(f"  システム名: {config.get('system.name')}")
    print(f"  最適化有効: {config.is_optimization_enabled()}")
    print(f"  高速起動有効: {config.is_fast_startup_enabled()}")
    print(f"  データベースパス: {config.get_database_path()}")
    print(f"  住之江会場名: {config.get_venue_name(12)}")
    
    print(f"\n[TEST] 必要ディレクトリ作成:")
    config.setup_directories()
    
    print(f"\n[SUCCESS] 統合設定管理テスト完了")