"""
ログ管理ユーティリティ
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

from config.settings import LOG_CONFIG, LOG_DIR


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """専用ロガーを設定"""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_CONFIG['level']))
    
    # フォーマッター作成
    formatter = logging.Formatter(LOG_CONFIG['format'])
    
    # ファイルハンドラー
    if log_file:
        log_path = LOG_DIR / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=LOG_CONFIG['file_size'],
            backupCount=LOG_CONFIG['backup_count'],
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_performance(func):
    """パフォーマンス計測デコレータ"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"{func.__name__} 実行時間: {elapsed:.2f}秒")
            return result
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} エラー (実行時間: {elapsed:.2f}秒): {e}")
            raise
    
    return wrapper