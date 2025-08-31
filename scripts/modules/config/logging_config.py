#!/usr/bin/env python3
"""
ログ設定モジュール
ログレベル、フォーマット、出力先の管理
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

class LoggingConfig:
    """ログ設定クラス"""
    
    # ログレベルマッピング
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # デフォルト設定
    DEFAULT_SETTINGS = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'log_directory': 'logs',
        'console_output': True,
        'file_output': True,
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    @classmethod
    def get_log_level(cls) -> int:
        """ログレベルを取得"""
        level_str = os.getenv('LOG_LEVEL', cls.DEFAULT_SETTINGS['level']).upper()
        return cls.LOG_LEVELS.get(level_str, logging.INFO)
    
    @classmethod
    def get_log_directory(cls) -> str:
        """ログディレクトリを取得"""
        return os.getenv('LOG_DIRECTORY', cls.DEFAULT_SETTINGS['log_directory'])
    
    @classmethod
    def get_log_format(cls) -> str:
        """ログフォーマットを取得"""
        return os.getenv('LOG_FORMAT', cls.DEFAULT_SETTINGS['format'])
    
    @classmethod
    def ensure_log_directory(cls):
        """ログディレクトリを作成"""
        log_dir = cls.get_log_directory()
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

def setup_logging(logger_name: Optional[str] = None) -> logging.Logger:
    """ログ設定をセットアップ"""
    
    # ログディレクトリの作成
    log_dir = LoggingConfig.ensure_log_directory()
    
    # ロガーの取得
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    # 既存ハンドラーをクリア
    logger.handlers.clear()
    
    # ログレベル設定
    log_level = LoggingConfig.get_log_level()
    logger.setLevel(log_level)
    
    # フォーマッター作成
    formatter = logging.Formatter(
        fmt=LoggingConfig.get_log_format(),
        datefmt=LoggingConfig.DEFAULT_SETTINGS['date_format']
    )
    
    # コンソールハンドラー
    if LoggingConfig.DEFAULT_SETTINGS['console_output']:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ファイルハンドラー
    if LoggingConfig.DEFAULT_SETTINGS['file_output']:
        # メインログファイル
        log_file = os.path.join(log_dir, 'kyotei_system.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LoggingConfig.DEFAULT_SETTINGS['max_bytes'],
            backupCount=LoggingConfig.DEFAULT_SETTINGS['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # エラーログファイル（WARNING以上のみ）
        error_log_file = os.path.join(log_dir, 'kyotei_errors.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=LoggingConfig.DEFAULT_SETTINGS['max_bytes'],
            backupCount=LoggingConfig.DEFAULT_SETTINGS['backup_count'],
            encoding='utf-8'
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """指定された名前のロガーを取得"""
    logger = logging.getLogger(name)
    
    # ロガーが未設定の場合は設定
    if not logger.handlers:
        setup_logging(name)
    
    return logger

def log_system_info(logger: logging.Logger):
    """システム情報をログ出力"""
    logger.info("=" * 50)
    logger.info("競艇予想システム起動")
    logger.info(f"起動時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"ログレベル: {logging.getLevelName(logger.level)}")
    logger.info(f"ログディレクトリ: {LoggingConfig.get_log_directory()}")
    logger.info("=" * 50)

def log_error_with_context(logger: logging.Logger, error: Exception, context: str = ""):
    """コンテキスト付きエラーログ"""
    error_msg = f"エラー発生"
    if context:
        error_msg += f" [{context}]"
    error_msg += f": {type(error).__name__}: {error}"
    
    logger.error(error_msg)
    logger.debug(f"詳細情報: {error}", exc_info=True)

# 便利関数
def create_module_logger(module_name: str) -> logging.Logger:
    """モジュール用ロガーを作成"""
    logger = get_logger(module_name)
    logger.debug(f"ロガー初期化: {module_name}")
    return logger

if __name__ == '__main__':
    # ログ設定テスト
    print("ログ設定テスト開始...")
    
    # メインロガーの設定
    main_logger = setup_logging()
    log_system_info(main_logger)
    
    # 各レベルのテスト
    main_logger.debug("デバッグメッセージ")
    main_logger.info("情報メッセージ")
    main_logger.warning("警告メッセージ")
    main_logger.error("エラーメッセージ")
    
    # モジュール別ロガーのテスト
    test_logger = create_module_logger('test_module')
    test_logger.info("モジュール別ログテスト")
    
    print("ログ設定テスト完了")