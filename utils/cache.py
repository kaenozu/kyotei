"""
キャッシュ管理システム
"""
import sqlite3
import json
import logging
import threading
from dataclasses import is_dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict
from collections import OrderedDict

from enum import Enum
from config.settings import get_setting
from config.paths import BASE_DIR
from data.models import RaceInfo, BoatRaceGrade # RaceInfoとBoatRaceGradeをインポート


class CacheManager:
    """最適化されたキャッシュ管理クラス"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or BASE_DIR / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self.logger = logging.getLogger(__name__)
        
        # L1キャッシュ（メモリ）
        self.memory_cache: OrderedDict[str, tuple] = OrderedDict() # OrderedDictを使用
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
                        data TEXT,
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

    def _json_serialize(self, obj):
        """カスタムJSONシリアライザ：datetimeオブジェクトをISOフォーマット文字列に変換"""
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Enumオブジェクトをその値に変換
        if isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def _json_deserialize(self, obj):
        """カスタムJSONデシリアライザ：ISOフォーマット文字列をdatetimeオブジェクトに変換"""
        # ISOフォーマットのdatetime文字列を検出して変換
        if isinstance(obj, str):
            try:
                # 年-月-日T時間:分:秒.マイクロ秒の形式を試す
                return datetime.fromisoformat(obj)
            except ValueError:
                pass
        # RaceInfoオブジェクトの再構築を試みる
        if isinstance(obj, dict) and all(k in obj for k in ['race_id', 'venue', 'race_number', 'start_time', 'grade', 'prize_money']):
            try:
                obj['start_time'] = datetime.fromisoformat(obj['start_time'])
                obj['grade'] = BoatRaceGrade(obj['grade'])
                return RaceInfo(**obj)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"RaceInfoのデシリアライズに失敗しました: {e}, データ: {obj}")
        return obj

    def get(self, key: str) -> Optional[Any]:
        """最適化されたキャッシュからデータを取得"""
        # L1キャッシュ（メモリ）をチェック
        with self.lock:
            if key in self.memory_cache:
                value, expires_at = self.memory_cache[key]
                if expires_at is None or datetime.now() < expires_at:
                    self.cache_hits += 1
                    self.logger.debug(f"L1キャッシュヒット: {key}")
                    # LRUのため、アクセスされたキーを更新
                    self.memory_cache.move_to_end(key)
                    return value
                else:
                    # 期限切れなので削除
                    del self.memory_cache[key]
                    self.memory_cache.pop(key) # OrderedDictからも削除
        
        # L2キャッシュ（SQLite）をチェック
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data, expires_at FROM cache WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                    (key, datetime.now().isoformat())
                )
                row = cursor.fetchone()
                
                if row:
                    data_str, expires_at_str = row
                    expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
                    
                    # データをデシリアライズ
                    data = json.loads(data_str, object_hook=self._json_deserialize)
                    
                    # L1キャッシュに保存（LRU実装）
                    with self.lock:
                        if len(self.memory_cache) >= self.memory_cache_size:
                            self.memory_cache.popitem(last=False) # 最も古いエントリを削除
                        
                        self.memory_cache[key] = (data, expires_at)
                        self.memory_cache.move_to_end(key) # 最新に移動
                    
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
                duration_minutes = get_setting("CACHE_DURATION").get(cache_type, 30)
                expires_at = datetime.now() + timedelta(minutes=duration_minutes)
            
            # L1キャッシュに保存
            with self.lock:
                if len(self.memory_cache) >= self.memory_cache_size:
                    self.memory_cache.popitem(last=False) # 最も古いエントリを削除
                
                self.memory_cache[key] = (data, expires_at)
                self.memory_cache.move_to_end(key) # 最新に移動
            
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
            # json.dumpsのdefault引数にカスタムシリアライザを渡す
            data_str = json.dumps(data, default=self._json_serialize)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache 
                    (key, data, category, created_at, expires_at) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, data_str, category, datetime.now().isoformat(), expires_at.isoformat())
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"非同期キャッシュ保存エラー: {e}")

    def delete(self, key: str):
        """指定キーのキャッシュを削除"""
        try:
            with self.lock:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
            self.logger.debug(f"キャッシュ削除: {key}")
        except sqlite3.Error as e:
            self.logger.error(f"キャッシュ削除エラー: {e}")

    def clear_expired(self):
        """期限切れキャッシュを一括削除"""
        try:
            # L1キャッシュの期限切れを削除
            with self.lock:
                keys_to_delete = [k for k, v in self.memory_cache.items() if v[1] is not None and datetime.now() > v[1]]
                for k in keys_to_delete:
                    del self.memory_cache[k]

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
            with self.lock:
                self.memory_cache.clear()

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