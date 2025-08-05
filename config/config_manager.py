import sqlite3
import json
from pathlib import Path
from typing import Any, Dict

from config.paths import CACHE_DIR # BASE_DIRは不要なのでCACHE_DIRのみインポート

class ConfigManager:
    """
    アプリケーション設定を管理し、SQLiteデータベースに永続化するクラス。
    """
    def __init__(self, db_path: Path = CACHE_DIR / "settings.db"):
        self.db_path = db_path
        self._ensure_db_path()
        self._create_table()

    def _ensure_db_path(self):
        """データベースファイルの親ディレクトリが存在することを確認する"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """SQLiteデータベースへの接続を確立する"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # カラム名でアクセスできるようにする
        return conn

    def _create_table(self):
        """設定を保存するためのテーブルを作成する"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """
        指定されたキーの設定値を取得する。
        値はJSON形式で保存されているため、読み込み時にデコードする。
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value'] # JSONでない場合はそのまま返す
            return default

    def set(self, key: str, value: Any):
        """
        指定されたキーに設定値を保存する。
        値はJSON形式で保存するため、保存時にエンコードする。
        """
        with self._get_connection() as conn:
            json_value = json.dumps(value)
            conn.execute("""
                INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)
            """, (key, json_value))
            conn.commit()

    def get_all(self) -> Dict[str, Any]:
        """
        全ての保存された設定を取得する。
        """
        settings = {}
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM app_settings")
            for row in cursor.fetchall():
                try:
                    settings[row['key']] = json.loads(row['value'])
                except json.JSONDecodeError:
                    settings[row['key']] = row['value']
        return settings

    def delete(self, key: str):
        """
        指定されたキーの設定を削除する。
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
            conn.commit()

# グローバルなConfigManagerインスタンス
config_manager = ConfigManager()
