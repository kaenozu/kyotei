"""
BoatraceOpenAPI専用システム モジュール
競艇予想システムのモジュール化されたコンポーネント
"""

from .api_fetcher import SimpleOpenAPIFetcher, VENUE_MAPPING
from .routes import RouteManager
from .scheduler_service import IntegratedScheduler
from .main_app import create_application, run_application

__version__ = "4.0.0"
__author__ = "Kyotei System"
__description__ = "BoatraceOpenAPI専用競艇予想システム（モジュール化版）"

__all__ = [
    'SimpleOpenAPIFetcher',
    'RouteManager', 
    'IntegratedScheduler',
    'create_application',
    'run_application',
    'VENUE_MAPPING'
]