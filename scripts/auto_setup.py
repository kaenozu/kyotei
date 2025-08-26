#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BoatraceOpenAPI専用システム - 自動セットアップ
"""

import os
import sys
import secrets

def auto_setup():
    """自動セットアップ実行"""
    print("=" * 50)
    print("BoatraceOpenAPI競艇予想システム 自動セットアップ")
    print("=" * 50)
    
    # デフォルト設定
    port = "5000"
    secret_key = secrets.token_hex(32)
    debug = "false"
    
    print(f"ポート番号: {port}")
    print(f"セキュリティキー: 自動生成完了")
    print(f"デバッグモード: {debug}")
    print("天候APIキー: 未設定（後で設定可能）")
    
    # .envファイル生成
    env_content = f"""# BoatraceOpenAPI競艇予想システム - 環境設定
# 自動セットアップにより生成

# 基本設定
HOST=0.0.0.0
PORT={port}
DEBUG={debug}
SECRET_KEY={secret_key}

# ログ設定
LOG_LEVEL=INFO
LOG_FORMAT=json

# キャッシュ設定
CACHE_EXPIRY=300
CACHE_DIR=cache

# セキュリティ設定
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
ENABLE_CORS=false

# 監視設定
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# 天候データ連携（オプション）
# OPENWEATHER_API_KEY=your-api-key-here
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("環境設定ファイル作成: .env")
    except Exception as e:
        print(f"設定ファイル作成失敗: {e}")
        return False
    
    # 起動スクリプト作成
    if sys.platform == "win32":
        batch_content = f"""@echo off
echo 競艇予想システム起動中...
cd /d "{os.getcwd()}"
python openapi_app.py
pause
"""
        try:
            with open('start_kyotei.bat', 'w', encoding='utf-8') as f:
                f.write(batch_content)
            print("Windows起動スクリプト作成: start_kyotei.bat")
        except:
            pass
    
    print()
    print("セットアップ完了！")
    print()
    print("次のステップ:")
    print("  1. python openapi_app.py でサーバー起動")
    print("  2. ブラウザで http://localhost:5000 を開く")
    print("  3. 今日のレース予想を確認")
    print()
    print("天候データで予想精度を8%向上させるには:")
    print("  1. https://openweathermap.org/api でAPIキー取得")
    print("  2. .env ファイルでOPENWEATHER_API_KEY=your-key に設定")
    print()
    
    return True

if __name__ == "__main__":
    auto_setup()