#!/usr/bin/env python3
"""
アプリケーション設定モジュール
Flask設定、サーバー設定、環境変数管理
"""

import os
from flask import Flask
from typing import Dict, Any

class AppConfig:
    """アプリケーション設定クラス"""
    
    # デフォルト設定
    DEFAULT_CONFIG = {
        'server': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False
        },
        'flask': {
            'SECRET_KEY': 'kyotei-prediction-system-2024',
            'JSON_AS_ASCII': False,
            'JSONIFY_PRETTYPRINT_REGULAR': True
        },
        'database': {
            'path': 'cache/comprehensive_kyotei.db'
        },
        'api': {
            'programs_base_url': 'https://boatraceopenapi.github.io/programs/v2',
            'results_base_url': 'https://boatraceopenapi.github.io/results/v2',
            'cache_expiry': 300,
            'max_retries': 3,
            'retry_delay': 1.0
        },
        'cache': {
            'directory': 'cache',
            'programs_file': 'boatrace_openapi_cache.json',
            'results_file': 'boatrace_results_cache.json'
        },
        'logs': {
            'directory': 'logs',
            'level': 'INFO'
        }
    }
    
    @classmethod
    def get_server_config(cls) -> Dict[str, Any]:
        """サーバー設定を取得"""
        config = cls.DEFAULT_CONFIG['server'].copy()
        
        # 環境変数からの設定上書き
        if os.getenv('HOST'):
            config['host'] = os.getenv('HOST')
        if os.getenv('PORT'):
            try:
                config['port'] = int(os.getenv('PORT'))
            except ValueError:
                pass
        if os.getenv('DEBUG'):
            config['debug'] = os.getenv('DEBUG', '0') == '1'
            
        return config
    
    @classmethod
    def get_flask_config(cls) -> Dict[str, Any]:
        """Flask設定を取得"""
        config = cls.DEFAULT_CONFIG['flask'].copy()
        
        # 環境変数からの設定上書き
        if os.getenv('SECRET_KEY'):
            config['SECRET_KEY'] = os.getenv('SECRET_KEY')
            
        return config
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """データベース設定を取得"""
        config = cls.DEFAULT_CONFIG['database'].copy()
        
        # 環境変数からの設定上書き
        if os.getenv('DATABASE_PATH'):
            config['path'] = os.getenv('DATABASE_PATH')
            
        return config
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """API設定を取得"""
        config = cls.DEFAULT_CONFIG['api'].copy()
        
        # 環境変数からの設定上書き
        if os.getenv('API_CACHE_EXPIRY'):
            try:
                config['cache_expiry'] = int(os.getenv('API_CACHE_EXPIRY'))
            except ValueError:
                pass
                
        return config
    
    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """キャッシュ設定を取得"""
        config = cls.DEFAULT_CONFIG['cache'].copy()
        
        # 環境変数からの設定上書き
        if os.getenv('CACHE_DIRECTORY'):
            config['directory'] = os.getenv('CACHE_DIRECTORY')
            
        return config
    
    @classmethod
    def create_flask_app(cls) -> Flask:
        """Flaskアプリケーションを作成"""
        app = Flask(__name__)
        
        # Flask設定の適用
        flask_config = cls.get_flask_config()
        for key, value in flask_config.items():
            app.config[key] = value
            
        # 静的ファイルとテンプレートの設定
        app.static_folder = '../../../templates/static'
        app.template_folder = '../../../templates'
        
        return app
    
    @classmethod
    def ensure_directories(cls):
        """必要なディレクトリを作成"""
        cache_config = cls.get_cache_config()
        logs_config = cls.DEFAULT_CONFIG['logs']
        
        directories = [
            cache_config['directory'],
            logs_config['directory']
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """全設定を取得（デバッグ用）"""
        return {
            'server': cls.get_server_config(),
            'flask': cls.get_flask_config(),
            'database': cls.get_database_config(),
            'api': cls.get_api_config(),
            'cache': cls.get_cache_config(),
            'logs': cls.DEFAULT_CONFIG['logs']
        }

# 設定の初期化
def initialize_app_config():
    """アプリケーション設定の初期化"""
    AppConfig.ensure_directories()
    return AppConfig.get_all_config()

if __name__ == '__main__':
    # 設定テスト
    config = initialize_app_config()
    print("アプリケーション設定:")
    for section, values in config.items():
        print(f"  {section}: {values}")