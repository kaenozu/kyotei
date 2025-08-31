#!/usr/bin/env python3
"""
メインアプリケーション（リファクタリング版）
Flaskアプリケーションの初期化と起動を管理
"""

import sys
import logging
from datetime import datetime

# 設定とコア機能のインポート
from config.app_config import AppConfig
from config.logging_config import setup_logging, get_logger
from core.component_initializer import initialize_components

def create_application():
    """Flaskアプリケーションを作成"""
    try:
        # ログ設定の初期化
        setup_logging()
        logger = get_logger(__name__)
        
        # Flaskアプリケーションの作成
        app = AppConfig.create_flask_app()
        
        # システムコンポーネントの初期化
        components = initialize_components(app, logger)
        
        
        # システム情報の出力
        _print_system_info()
        
        logger.info("アプリケーション作成完了")
        return app, components
        
    except Exception as e:
        print(f"[ERROR] アプリケーション作成失敗: {e}")
        sys.exit(1)

def _print_system_info():
    """システム起動情報を表示"""
    config = AppConfig.get_server_config()
    
    print("=" * 50)
    print("競艇予想システム")
    print("リファクタリング版 v1.0")
    print(f"URL: http://{config['host']}:{config['port']}")
    print("=" * 50)

def run_application():
    """アプリケーションを実行"""
    try:
        # アプリケーションの作成
        app, components = create_application()
        
        # サーバー設定の取得
        config = AppConfig.get_server_config()
        
        # スケジューラーの開始
        if components.get('scheduler'):
            components['scheduler'].start()
            print("統合スケジューラー開始: AM6時データ取得, 毎時結果更新")
        
        # Flaskアプリケーションの実行
        app.run(
            host=config['host'],
            port=config['port'],
            debug=config['debug']
        )
        
    except KeyboardInterrupt:
        print("\n[INFO] システム終了")
    except Exception as e:
        print(f"[ERROR] 実行エラー: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_application()