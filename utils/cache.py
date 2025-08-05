"""
キャッシュ管理システム
"""
import sqlite3
import pickle
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict

from config.settings import CACHE_DURATION, BASE_DIR


class CacheManager:
    """最適化されたキャッシュ管理クラス"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or BASE_DIR / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self.logger = logging.getLogger(__name__)
        
        # L1キャッシュ（メモリ）
        self.memory_cache: Dict[str, tuple] = {}
        self.memory_cache_size = 100  # メモリキャッシュ最大サイズ
        self.lock = threading.RLock()
        
        # ヒット率追跡
        self.cache_hits = 0
        self.cache_misses = 0
        
        self._init_database()

    def _init_database(self):
        """キャッシュデータベースを初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        data BLOB,
                        category TEXT,
                        created_at TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """)
                # パフォーマンス最適化のインデックス
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON cache(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)")
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"キャッシュDB初期化エラー: {e}")

    def get(self, key: str) -> Optional[Any]:
        """最適化されたキャッシュからデータを取得"""
        # L1キャッシュ（メモリ）をチェック
        with self.lock:
            if key in self.memory_cache:
                value, expires_at = self.memory_cache[key]
                if expires_at is None or datetime.now() < expires_at:
                    self.cache_hits += 1
                    self.logger.debug(f"L1キャッシュヒット: {key}")
                    return value
                else:
                    # 期限切れなので削除
                    del self.memory_cache[key]
        
        # L2キャッシュ（SQLite）をチェック
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data, expires_at FROM cache WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                    (key, datetime.now().isoformat())
                )
                row = cursor.fetchone()
                
                if row:
                    data_blob, expires_at_str = row
                    expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
                    
                    # データをデシリアライズ
                    data = pickle.loads(data_blob)
                    
                    # L1キャッシュに保存（LRU実装）
                    with self.lock:
                        if len(self.memory_cache) >= self.memory_cache_size:
                            # 最も古いエントリを削除
                            oldest_key = min(self.memory_cache.keys())
                            del self.memory_cache[oldest_key]
                        
                        self.memory_cache[key] = (data, expires_at)
                    
                    self.cache_hits += 1
                    self.logger.debug(f"L2キャッシュヒット: {key}")
                    return data
                else:
                    self.cache_misses += 1
                    return None
                
        except Exception as e:
            self.logger.error(f"キャッシュ取得エラー: {e}")
            self.cache_misses += 1
            return None

    def set(self, key: str, data: Any, cache_type: str = "default", expires_in: int = None):
        """最適化されたデータキャッシュ保存"""
        try:
            # 有効期限を設定
            if expires_in:
                expires_at = datetime.now() + timedelta(seconds=expires_in)
            else:
                duration_minutes = CACHE_DURATION.get(cache_type, 30)
                expires_at = datetime.now() + timedelta(minutes=duration_minutes)
            
            # L1キャッシュに保存
            with self.lock:
                if len(self.memory_cache) >= self.memory_cache_size:
                    # LRU: 最も古いエントリを削除
                    oldest_key = min(self.memory_cache.keys())
                    del self.memory_cache[oldest_key]
                
                self.memory_cache[key] = (data, expires_at)
            
            # L2キャッシュに非同期保存
            threading.Thread(
                target=self._async_db_save,
                args=(key, data, cache_type, expires_at),
                daemon=True
            ).start()
            
            self.logger.debug(f"キャッシュ保存: {key} (期限: {expires_at})")
            
        except Exception as e:
            self.logger.error(f"キャッシュ保存エラー: {e}")
    
    def _async_db_save(self, key: str, data: Any, category: str, expires_at: datetime):
        """非同期でのDB保存"""
        try:
            data_blob = pickle.dumps(data)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache 
                    (key, data, category, created_at, expires_at) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, data_blob, category, datetime.now().isoformat(), expires_at.isoformat())
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"非同期キャッシュ保存エラー: {e}")

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
        """詳細なキャッシュ情報を取得"""
        try:
            # L1キャッシュ情報
            with self.lock:
                l1_count = len(self.memory_cache)
                l1_valid = sum(1 for _, expires_at in self.memory_cache.values() 
                              if expires_at is None or datetime.now() < expires_at)
            
            # L2キャッシュ情報
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total_count = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at > ?",
                    (datetime.now().isoformat(),)
                )
                valid_count = cursor.fetchone()[0]
                
                # カテゴリ別統計
                cursor = conn.execute(
                    "SELECT category, COUNT(*) FROM cache GROUP BY category"
                )
                category_stats = dict(cursor.fetchall())
            
            # ヒット率計算
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "total_entries": total_count,
                "valid_entries": valid_count,
                "expired_entries": total_count - valid_count,
                "l1_cache_entries": l1_count,
                "l1_valid_entries": l1_valid,
                "category_stats": category_stats,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate": hit_rate
            }
        except sqlite3.Error as e:
            self.logger.error(f"キャッシュ情報取得エラー: {e}")
            return {}


# グローバルキャッシュインスタンス
cache = CacheManager()