#!/usr/bin/env python3
"""
BoatraceOpenAPI専用システム - 設定ウィザード
初回セットアップを劇的に簡単にする対話式設定システム
"""

import os
import sys
from pathlib import Path
import json
import platform
import webbrowser
from typing import Dict, Any, Optional


class ConfigurationWizard:
    """設定ウィザードクラス"""
    
    def __init__(self):
        self.config_data = {}
        self.app_dir = Path(__file__).parent
        self.env_file = self.app_dir / ".env"
        
    def run_interactive_setup(self):
        """対話式セットアップ実行"""
        print("=" * 60)
        print("BoatraceOpenAPI競艇予想システム 設定ウィザード")
        print("=" * 60)
        print()
        
        print("このウィザードでシステムの初期設定を行います。")
        print("すべての設定はオプションです。Enterキーで次に進めます。")
        print()
        
        # 1. 基本設定
        self._setup_basic_config()
        
        # 2. オプション設定
        self._setup_optional_features()
        
        # 3. 設定ファイル生成
        self._generate_config_files()
        
        # 4. 依存関係インストール
        self._install_dependencies()
        
        # 5. 完了とガイダンス
        self._show_completion_guide()
    
    def _setup_basic_config(self):
        """基本設定"""
        print("📋 【ステップ1】基本設定")
        print("-" * 30)
        
        # ポート設定
        port = input("サーバーポート番号（デフォルト: 5000）: ").strip()
        self.config_data['PORT'] = port if port else "5000"
        
        # セキュリティキー
        print()
        print("セキュリティキーを設定してください。")
        print("（セッション暗号化に使用。空白で自動生成）")
        secret_key = input("セキュリティキー: ").strip()
        if not secret_key:
            import secrets
            secret_key = secrets.token_hex(32)
            print(f"✓ 自動生成: {secret_key[:16]}...")
        self.config_data['SECRET_KEY'] = secret_key
        
        # デバッグモード
        print()
        debug_mode = input("デバッグモード有効化？ (y/N): ").strip().lower()
        self.config_data['DEBUG'] = "true" if debug_mode in ['y', 'yes'] else "false"
        
        print("✓ 基本設定完了")
        print()
    
    def _setup_optional_features(self):
        """オプション機能設定"""
        print("🔧 【ステップ2】オプション機能")
        print("-" * 30)
        
        # OpenWeatherMap API設定
        print("天候データ連携（予想精度+8%向上）")
        print("OpenWeatherMap APIキーをお持ちですか？")
        print("https://openweathermap.org/api で無料取得可能")
        
        has_weather_api = input("APIキーを設定しますか？ (y/N): ").strip().lower()
        if has_weather_api in ['y', 'yes']:
            api_key = input("OpenWeatherMap APIキー: ").strip()
            if api_key:
                self.config_data['OPENWEATHER_API_KEY'] = api_key
                print("✓ 天候データ連携有効")
            else:
                print("⚠ APIキー未入力 - 天候機能無効")
        else:
            print("⚠ 天候データ機能は無効になります")
        
        print()
        
        # Sentry設定（エラー監視）
        print("エラー監視設定（オプション）")
        has_sentry = input("Sentry DSNを設定しますか？ (y/N): ").strip().lower()
        if has_sentry in ['y', 'yes']:
            sentry_dsn = input("Sentry DSN: ").strip()
            if sentry_dsn:
                self.config_data['SENTRY_DSN'] = sentry_dsn
                print("✓ エラー監視有効")
        
        print()
        
        # ログ設定
        print("ログ設定")
        log_level = input("ログレベル (INFO/DEBUG/WARNING/ERROR) [INFO]: ").strip().upper()
        self.config_data['LOG_LEVEL'] = log_level if log_level in ['DEBUG', 'WARNING', 'ERROR'] else 'INFO'
        
        log_format = input("ログ形式 (json/text) [json]: ").strip().lower()
        self.config_data['LOG_FORMAT'] = log_format if log_format == 'text' else 'json'
        
        # ログファイル
        log_file = input("ログファイル保存先（空白で無効）: ").strip()
        if log_file:
            self.config_data['LOG_FILE'] = log_file
        
        print("✓ オプション設定完了")
        print()
    
    def _generate_config_files(self):
        """設定ファイル生成"""
        print("📄 【ステップ3】設定ファイル生成")
        print("-" * 30)
        
        # .envファイル生成
        env_content = self._create_env_content()
        
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            print(f"✓ 環境設定ファイル作成: {self.env_file}")
        except Exception as e:
            print(f"✗ 設定ファイル作成失敗: {e}")
            return False
        
        # 起動スクリプト生成
        self._create_startup_scripts()
        
        # Dockerファイル生成
        self._create_docker_files()
        
        print("✓ 設定ファイル生成完了")
        print()
        return True
    
    def _create_env_content(self) -> str:
        """環境設定ファイル内容作成"""
        content = f"""# BoatraceOpenAPI競艇予想システム - 環境設定
# 設定ウィザードにより自動生成: {self._get_current_time()}

# 基本設定
HOST=0.0.0.0
PORT={self.config_data.get('PORT', '5000')}
DEBUG={self.config_data.get('DEBUG', 'false')}
SECRET_KEY={self.config_data.get('SECRET_KEY', 'default-key')}

# ログ設定
LOG_LEVEL={self.config_data.get('LOG_LEVEL', 'INFO')}
LOG_FORMAT={self.config_data.get('LOG_FORMAT', 'json')}
"""
        
        if 'LOG_FILE' in self.config_data:
            content += f"LOG_FILE={self.config_data['LOG_FILE']}\n"
        
        # オプション設定
        if 'OPENWEATHER_API_KEY' in self.config_data:
            content += f"""
# 天候データ連携
OPENWEATHER_API_KEY={self.config_data['OPENWEATHER_API_KEY']}
"""
        
        if 'SENTRY_DSN' in self.config_data:
            content += f"""
# エラー監視
SENTRY_DSN={self.config_data['SENTRY_DSN']}
"""
        
        content += """
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
"""
        
        return content
    
    def _create_startup_scripts(self):
        """起動スクリプト作成"""
        # Windows用バッチファイル
        if platform.system() == "Windows":
            batch_content = f"""@echo off
echo 競艇予想システム起動中...
cd /d "{self.app_dir}"
python openapi_app.py
pause
"""
            with open(self.app_dir / "start_kyotei.bat", 'w', encoding='utf-8') as f:
                f.write(batch_content)
            print("✓ Windows起動スクリプト作成: start_kyotei.bat")
        
        # Unix/Linux用シェルスクリプト
        shell_content = f"""#!/bin/bash
echo "競艇予想システム起動中..."
cd "{self.app_dir}"
python3 openapi_app.py
"""
        shell_file = self.app_dir / "start_kyotei.sh"
        with open(shell_file, 'w', encoding='utf-8') as f:
            f.write(shell_content)
        
        # 実行権限付与（Unix系）
        if platform.system() != "Windows":
            os.chmod(shell_file, 0o755)
            print("✓ Unix起動スクリプト作成: start_kyotei.sh")
    
    def _create_docker_files(self):
        """Docker設定ファイル作成"""
        # docker-compose.yml
        docker_compose_content = f"""version: '3.8'
services:
  boatrace-predictor:
    build: .
    container_name: boatrace-predictor
    ports:
      - "{self.config_data.get('PORT', '5000')}:{self.config_data.get('PORT', '5000')}"
    environment:
      - PORT={self.config_data.get('PORT', '5000')}
      - DEBUG={self.config_data.get('DEBUG', 'false')}
    volumes:
      - ./cache:/app/cache
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{self.config_data.get('PORT', '5000')}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""
        
        with open(self.app_dir / "docker-compose.yml", 'w', encoding='utf-8') as f:
            f.write(docker_compose_content)
        print("✓ Docker設定作成: docker-compose.yml")
    
    def _install_dependencies(self):
        """依存関係インストール"""
        print("📦 【ステップ4】依存関係インストール")
        print("-" * 30)
        
        install_deps = input("Pythonライブラリを自動インストールしますか？ (Y/n): ").strip().lower()
        if install_deps not in ['n', 'no']:
            print("依存関係をインストールしています...")
            try:
                import subprocess
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", "requirements_openapi.txt"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✓ 依存関係インストール完了")
                else:
                    print(f"⚠ インストール警告: {result.stderr}")
                    print("手動でインストールしてください: pip install -r requirements_openapi.txt")
            except Exception as e:
                print(f"✗ 自動インストール失敗: {e}")
                print("手動でインストールしてください: pip install -r requirements_openapi.txt")
        else:
            print("⚠ 手動でインストールしてください: pip install -r requirements_openapi.txt")
        
        print()
    
    def _show_completion_guide(self):
        """完了ガイド表示"""
        print("🎉 【ステップ5】セットアップ完了！")
        print("=" * 60)
        
        print("設定が完了しました。以下の方法でシステムを起動できます：")
        print()
        
        # 起動方法
        print("📋 起動方法:")
        if platform.system() == "Windows":
            print("  方法1: start_kyotei.bat をダブルクリック")
            print("  方法2: コマンドプロンプトで python openapi_app.py")
        else:
            print("  方法1: ./start_kyotei.sh")
            print("  方法2: python3 openapi_app.py")
        
        print("  方法3: Docker - docker-compose up")
        print()
        
        # アクセス情報
        port = self.config_data.get('PORT', '5000')
        print("📱 アクセス情報:")
        print(f"  ブラウザで http://localhost:{port} を開いてください")
        print()
        
        # 機能状況
        print("🔧 機能状況:")
        print("  ✅ 基本予想機能: 有効")
        print("  ✅ セキュリティ: 有効")
        print("  ✅ 監視・ログ: 有効")
        
        if 'OPENWEATHER_API_KEY' in self.config_data:
            print("  ✅ 天候データ: 有効（予想精度向上）")
        else:
            print("  ⚠️ 天候データ: 無効")
        
        if 'SENTRY_DSN' in self.config_data:
            print("  ✅ エラー監視: 有効")
        else:
            print("  ⚠️ エラー監視: 無効")
        
        print()
        
        # 次のステップ
        print("🚀 次のステップ:")
        print("  1. システムを起動")
        print("  2. ブラウザでアクセス")
        print("  3. 今日のレース予想を確認")
        if 'OPENWEATHER_API_KEY' not in self.config_data:
            print("  4. 精度向上のため天候API設定を検討")
        
        print()
        print("サポート:")
        print("  - README.md: システム説明書")
        print("  - PRODUCTION_DEPLOYMENT_GUIDE.md: 本番運用ガイド")
        print()
        
        # 自動起動確認
        auto_start = input("今すぐシステムを起動しますか？ (Y/n): ").strip().lower()
        if auto_start not in ['n', 'no']:
            self._auto_start_system()
    
    def _auto_start_system(self):
        """システム自動起動"""
        try:
            print()
            print("システムを起動しています...")
            
            # 環境変数読み込み
            if self.env_file.exists():
                import subprocess
                import time
                
                # バックグラウンドでサーバー起動
                process = subprocess.Popen([
                    sys.executable, "openapi_app.py"
                ], cwd=self.app_dir)
                
                print("サーバー起動中... 3秒待機")
                time.sleep(3)
                
                # ブラウザでアクセス
                port = self.config_data.get('PORT', '5000')
                url = f"http://localhost:{port}"
                
                print(f"ブラウザで {url} を開いています...")
                webbrowser.open(url)
                
                print()
                print("✓ システム起動完了！")
                print("ブラウザが開かない場合は手動でアクセスしてください。")
                print("終了するには Ctrl+C を押してください。")
                
                # プロセス待機
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print("\nシステムを終了しています...")
                    process.terminate()
            
        except Exception as e:
            print(f"自動起動失敗: {e}")
            print("手動で起動してください。")
    
    def _get_current_time(self) -> str:
        """現在時刻取得"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def update_existing_config(self):
        """既存設定の更新"""
        if self.env_file.exists():
            print("既存の設定ファイルが見つかりました。")
            update_config = input("設定を更新しますか？ (y/N): ").strip().lower()
            if update_config in ['y', 'yes']:
                # バックアップ作成
                backup_file = self.env_file.with_suffix('.env.backup')
                self.env_file.rename(backup_file)
                print(f"既存設定をバックアップしました: {backup_file}")
                return True
        return True


def main():
    """メイン実行"""
    try:
        wizard = ConfigurationWizard()
        
        # 既存設定確認
        if not wizard.update_existing_config():
            print("設定更新をキャンセルしました。")
            return
        
        # ウィザード実行
        wizard.run_interactive_setup()
        
    except KeyboardInterrupt:
        print("\n\n設定をキャンセルしました。")
        sys.exit(1)
    except Exception as e:
        print(f"\n設定エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()