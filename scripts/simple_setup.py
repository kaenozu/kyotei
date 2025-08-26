#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BoatraceOpenAPI専用システム - 簡単セットアップ（Windows対応）
"""

import os
import sys
import secrets
from pathlib import Path

# Windows用コンソール出力設定
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


def main():
    """簡単セットアップ実行"""
    print("=" * 50)
    print("BoatraceOpenAPI競艇予想システム 簡単セットアップ")
    print("=" * 50)
    print()
    
    # 基本設定
    print("【ステップ1】基本設定")
    print("-" * 20)
    
    port = input("サーバーポート番号（デフォルト: 5000）: ").strip()
    if not port:
        port = "5000"
    
    # セキュリティキー自動生成
    secret_key = secrets.token_hex(32)
    print(f"セキュリティキー自動生成完了")
    
    # デバッグモード
    debug_mode = input("デバッグモード有効化? (y/N): ").strip().lower()
    debug = "true" if debug_mode in ['y', 'yes'] else "false"
    
    print("基本設定完了")
    print()
    
    # オプション設定
    print("【ステップ2】オプション設定")
    print("-" * 20)
    
    print("天候データ連携（予想精度+8%向上）")
    print("OpenWeatherMap APIキーをお持ちですか？")
    print("https://openweathermap.org/api で無料取得可能")
    
    has_weather_api = input("APIキーを設定しますか? (y/N): ").strip().lower()
    weather_api_key = ""
    if has_weather_api in ['y', 'yes']:
        weather_api_key = input("OpenWeatherMap APIキー: ").strip()
        if weather_api_key:
            print("天候データ連携有効")
        else:
            print("APIキー未入力 - 天候機能無効")
    else:
        print("天候データ機能は無効になります")
    
    print("オプション設定完了")
    print()
    
    # .envファイル生成
    print("【ステップ3】設定ファイル生成")
    print("-" * 20)
    
    env_content = f"""# BoatraceOpenAPI競艇予想システム - 環境設定
# 簡単セットアップにより自動生成

# 基本設定
HOST=0.0.0.0
PORT={port}
DEBUG={debug}
SECRET_KEY={secret_key}

# ログ設定
LOG_LEVEL=INFO
LOG_FORMAT=json

"""
    
    if weather_api_key:
        env_content += f"""# 天候データ連携
OPENWEATHER_API_KEY={weather_api_key}

"""
    
    env_content += """# キャッシュ設定
CACHE_EXPIRY=300
CACHE_DIR=cache

# セキュリティ設定
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
ENABLE_CORS=false

# 監視設定
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true
"""
    
    # .envファイル保存
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("環境設定ファイル作成: .env")
    except Exception as e:
        print(f"設定ファイル作成失敗: {e}")
        return
    
    # 起動スクリプト作成
    if sys.platform == "win32":
        batch_content = f"""@echo off
echo 競艇予想システム起動中...
cd /d "{os.getcwd()}"
python openapi_app.py
pause
"""
        with open('start_kyotei.bat', 'w', encoding='utf-8') as f:
            f.write(batch_content)
        print("Windows起動スクリプト作成: start_kyotei.bat")
    
    print("設定ファイル生成完了")
    print()
    
    # 完了ガイド
    print("【ステップ4】セットアップ完了！")
    print("=" * 50)
    
    print("設定が完了しました。以下の方法でシステムを起動できます：")
    print()
    
    print("起動方法:")
    if sys.platform == "win32":
        print("  方法1: start_kyotei.bat をダブルクリック")
        print("  方法2: コマンドプロンプトで python openapi_app.py")
    else:
        print("  方法1: python3 openapi_app.py")
    
    print()
    
    print(f"アクセス情報:")
    print(f"  ブラウザで http://localhost:{port} を開いてください")
    print()
    
    print("機能状況:")
    print("  基本予想機能: 有効")
    print("  セキュリティ: 有効")
    print("  監視・ログ: 有効")
    
    if weather_api_key:
        print("  天候データ: 有効（予想精度向上）")
    else:
        print("  天候データ: 無効")
    
    print()
    
    print("次のステップ:")
    print("  1. システムを起動")
    print("  2. ブラウザでアクセス")
    print("  3. 今日のレース予想を確認")
    if not weather_api_key:
        print("  4. 精度向上のため天候API設定を検討")
    
    print()
    
    # 自動起動確認
    auto_start = input("今すぐシステムを起動しますか? (Y/n): ").strip().lower()
    if auto_start not in ['n', 'no']:
        print()
        print("システムを起動しています...")
        print("ブラウザが自動で開かない場合は手動でアクセスしてください")
        print("終了するには Ctrl+C を押してください")
        print()
        
        # システム起動
        try:
            import subprocess
            if sys.platform == "win32":
                subprocess.run(['python', 'openapi_app.py'])
            else:
                subprocess.run(['python3', 'openapi_app.py'])
        except KeyboardInterrupt:
            print("システムを終了しました")
        except Exception as e:
            print(f"起動エラー: {e}")
            print("手動で起動してください: python openapi_app.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nセットアップをキャンセルしました")
    except Exception as e:
        print(f"\nセットアップエラー: {e}")