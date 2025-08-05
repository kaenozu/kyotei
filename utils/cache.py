"""
キャッシュ管理システム
"""
import sqlite3
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from config.settings import CACHE_DURATION, BASE_DIR


class CacheManager:
    """キャッシュ管理クラス"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or BASE_DIR / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self):
        """キャッシュデータベースを初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        data BLOB,
                        created_at TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at 
                    ON cache(expires_at)
                """)
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"キャッシュDB初期化エラー: {e}")

    def get(self, key: str) -> Optional[Any]:
        """キャッシュからデータを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data, expires_at FROM cache WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                data_blob, expires_at_str = row
                expires_at = datetime.fromisoformat(expires_at_str)
                
                # 期限切れチェック
                if datetime.now() > expires_at:
                    self.delete(key)
                    return None
                
                # データをデシリアライズ
                data = pickle.loads(data_blob)
                self.logger.debug(f"キャッシュヒット: {key}")
                return data
                
        except Exception as e:
            self.logger.error(f"キャッシュ取得エラー: {e}")
            return None

    def set(self, key: str, data: Any, cache_type: str = "default"):
        """データをキャッシュに保存"""
        try:
            # 有効期限を設定
            duration_minutes = CACHE_DURATION.get(cache_type, 30)
            expires_at = datetime.now() + timedelta(minutes=duration_minutes)
            
            # データをシリアライズ
            data_blob = pickle.dumps(data)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache 
                    (key, data, created_at, expires_at) 
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, data_blob, datetime.now().isoformat(), expires_at.isoformat())
                )
                conn.commit()
            
            self.logger.debug(f"キャッシュ保存: {key} (期限: {expires_at})")
            
        except Exception as e:
            self.logger.error(f"キャッシュ保存エラー: {e}")

    def delete(self, key: str):
        """指定キーのキャッシュを削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
            self.logger.debug(f"キャッシュ削除: {key}")
        except sqlite3.Error as e:
            self.logger.error(f"キャッシュ削除エラー: {e}")

    def clear_expired(self):
        """期限切れキャッシュを一括削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                )
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"期限切れキャッシュを削除: {deleted_count}件")
                
        except sqlite3.Error as e:
            self.logger.error(f"期限切れキャッシュ削除エラー: {e}")

    def clear_all(self):
        """全キャッシュを削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
            self.logger.info("全キャッシュを削除")
        except sqlite3.Error as e:
            self.logger.error(f"全キャッシュ削除エラー: {e}")

    def get_cache_info(self) -> dict:
        """キャッシュ情報を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total_count = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at > ?",
                    (datetime.now().isoformat(),)
                )
                valid_count = cursor.fetchone()[0]
                
            return {
                "total_entries": total_count,
                "valid_entries": valid_count,
                "expired_entries": total_count - valid_count
            }
        except sqlite3.Error as e:
            self.logger.error(f"キャッシュ情報取得エラー: {e}")
            return {}


# グローバルキャッシュインスタンス
cache = CacheManager()