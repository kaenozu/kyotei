#!/usr/bin/env python3
"""
設定モジュール
アプリケーション設定とログ設定を管理
"""

from .app_config import AppConfig, initialize_app_config
from .logging_config import (
    LoggingConfig, 
    setup_logging, 
    get_logger, 
    log_system_info,
    log_error_with_context,
    create_module_logger
)

__version__ = "1.0.0"
__author__ = "競艇予想システム開発チーム"

# パッケージレベルでの公開API
__all__ = [
    # アプリケーション設定
    'AppConfig',
    'initialize_app_config',
    
    # ログ設定
    'LoggingConfig',
    'setup_logging',
    'get_logger',
    'log_system_info',
    'log_error_with_context',
    'create_module_logger'
]

def get_version():
    """バージョン情報を取得"""
    return __version__

def initialize_all_configs():
    """全設定の初期化"""
    try:
        # アプリケーション設定の初期化
        app_config = initialize_app_config()
        
        # ログ設定の初期化
        logger = setup_logging()
        log_system_info(logger)
        
        logger.info("設定モジュール初期化完了")
        return {
            'app_config': app_config,
            'logger': logger,
            'version': __version__
        }
        
    except Exception as e:
        print(f"[ERROR] 設定初期化エラー: {e}")
        raise