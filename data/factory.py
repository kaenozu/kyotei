"""
データフェッチャーのファクトリーパターン実装
"""
import logging
from typing import Union
from config.settings import get_setting


class DataFetcherFactory:
    """データフェッチャーの作成を管理するファクトリークラス"""
    
    @staticmethod
    def create_fetcher() -> 'HybridDataFetcher':
        """設定に基づいて適切なデータフェッチャーを作成"""
        logger = logging.getLogger(__name__)
        
        try:
            from .hybrid_fetcher import HybridDataFetcher
            logger.info("ハイブリッドデータフェッチャーを作成します")
            return HybridDataFetcher()
        except ImportError as e:
            logger.error(f"ハイブリッドフェッチャーのインポートに失敗: {e}")
            # フォールバックとして従来のモックフェッチャーを使用
            from .fetcher import KyoteiDataFetcher
            logger.info("フォールバック: モックデータフェッチャーを使用します")
            return KyoteiDataFetcher()
    
    @staticmethod
    def get_data_source_info() -> dict:
        """現在のデータソース情報を取得"""
        data_mode = get_setting("DATA_MODE")
        return {
            "is_real_data": data_mode.get("use_real_data", False),
            "fallback_enabled": data_mode.get("fallback_to_mock", True),
            "error_handling": data_mode.get("mock_on_error", True),
            "show_source": data_mode.get("show_data_source", True)
        }


def create_data_fetcher():
    """データフェッチャーを作成する便利関数"""
    return DataFetcherFactory.create_fetcher()


def get_data_source_status():
    """データソース状態を取得する便利関数"""
    return DataFetcherFactory.get_data_source_info()