#!/usr/bin/env python3
"""
BoatraceOpenAPI専用システム - 本番デプロイ設定
SSL設定、Nginx設定、環境チェック
"""

import os
import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ProductionDeployer:
    """本番デプロイ管理クラス"""
    
    def __init__(self, domain: str, ssl_email: str):
        self.domain = domain
        self.ssl_email = ssl_email
        self.app_dir = Path(__file__).parent
        self.logs = []
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(log_entry)
        print(log_entry)
    
    def run_command(self, command: str, check: bool = True) -> tuple:
        """コマンド実行"""
        self.log(f"実行: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=check
            )
            if result.stdout:
                self.log(f"出力: {result.stdout.strip()}")
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.log(f"エラー: {e.stderr}", "ERROR")
            return False, e.stderr
    
    def check_system_requirements(self) -> bool:
        """システム要件チェック"""
        self.log("=== システム要件チェック ===")
        
        requirements = [
            ("docker", "Docker"),
            ("docker-compose", "Docker Compose"),
            ("nginx", "Nginx"),
            ("certbot", "Certbot"),
            ("python3", "Python 3"),
        ]
        
        all_ok = True
        for cmd, name in requirements:
            success, output = self.run_command(f"which {cmd}", check=False)
            if success:
                self.log(f"✓ {name} インストール済み")
            else:
                self.log(f"✗ {name} がインストールされていません", "ERROR")
                all_ok = False
        
        return all_ok
    
    def generate_ssl_certificates(self) -> bool:
        """SSL証明書生成（Let's Encrypt）"""
        self.log("=== SSL証明書生成 ===")
        
        # Nginxを一時停止
        self.run_command("sudo nginx -s stop", check=False)
        
        # Certbot実行
        certbot_cmd = (
            f"sudo certbot certonly --standalone "
            f"--email {self.ssl_email} "
            f"--agree-tos "
            f"--no-eff-email "
            f"-d {self.domain}"
        )
        
        success, output = self.run_command(certbot_cmd)
        if success:
            self.log("✓ SSL証明書生成完了")
            return True
        else:
            self.log("✗ SSL証明書生成失敗", "ERROR")
            return False
    
    def create_nginx_ssl_config(self):
        """SSL対応Nginx設定作成"""
        self.log("=== SSL対応Nginx設定作成 ===")
        
        nginx_config = f"""
# BoatraceOpenAPI専用システム - SSL対応Nginx設定
# HTTP -> HTTPS リダイレクト
server {{
    listen 80;
    server_name {self.domain};
    
    # Let's Encrypt認証用
    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}
    
    # その他はHTTPSにリダイレクト
    location / {{
        return 301 https://$server_name$request_uri;
    }}
}}

# HTTPS設定
server {{
    listen 443 ssl http2;
    server_name {self.domain};
    
    # SSL証明書設定
    ssl_certificate /etc/letsencrypt/live/{self.domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{self.domain}/privkey.pem;
    
    # SSL設定（セキュリティ強化）
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS設定
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # セキュリティヘッダー（追加）
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # CSP（Content Security Policy）
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;
    
    # ファイルアップロード制限
    client_max_body_size 1M;
    
    # レート制限
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;
    
    # ログ設定
    access_log /var/log/nginx/boatrace_access.log;
    error_log /var/log/nginx/boatrace_error.log;
    
    # API エンドポイント（レート制限あり）
    location /api/ {{
        limit_req zone=api burst=10 nodelay;
        
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # タイムアウト設定
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }}
    
    # 監視エンドポイント
    location ~ ^/(health|metrics) {{
        limit_req zone=general burst=5 nodelay;
        
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # 静的ファイル
    location /static/ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary Accept-Encoding;
        
        # Gzip圧縮
        gzip on;
        gzip_types text/css application/javascript application/json text/plain;
        
        alias /app/static/;
    }}
    
    # メインアプリケーション
    location / {{
        limit_req zone=general burst=20 nodelay;
        
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # キャッシュ無効化（動的コンテンツ）
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }}
}}
"""
        
        # 設定ファイル保存
        config_path = self.app_dir / "nginx_ssl.conf"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(nginx_config)
        
        self.log(f"✓ SSL対応Nginx設定作成: {config_path}")
        return config_path
    
    def create_production_docker_compose(self):
        """本番用docker-compose.yml作成"""
        self.log("=== 本番用Docker Compose設定作成 ===")
        
        docker_compose = {
            "version": "3.8",
            "services": {
                "boatrace-app": {
                    "build": ".",
                    "container_name": "boatrace-openapi-app",
                    "restart": "unless-stopped",
                    "ports": ["5000:5000"],
                    "environment": {
                        "FLASK_ENV": "production",
                        "LOG_LEVEL": "INFO",
                        "LOG_FORMAT": "json",
                        "LOG_FILE": "/app/logs/app.log",
                        "METRICS_ENABLED": "true",
                        "HEALTH_CHECK_ENABLED": "true",
                        "RATE_LIMIT_ENABLED": "true",
                        "CACHE_EXPIRY": "300",
                        "API_TIMEOUT": "10",
                        "SECRET_KEY": "${SECRET_KEY}",
                        "SENTRY_DSN": "${SENTRY_DSN:-}"
                    },
                    "volumes": [
                        "./logs:/app/logs",
                        "./cache:/app/cache"
                    ],
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:5000/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "30s"
                    },
                    "logging": {
                        "driver": "json-file",
                        "options": {
                            "max-size": "10m",
                            "max-file": "5"
                        }
                    }
                }
            },
            "networks": {
                "default": {
                    "driver": "bridge"
                }
            }
        }
        
        config_path = self.app_dir / "docker-compose.prod.yml"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(docker_compose, f, indent=2, ensure_ascii=False)
        
        self.log(f"✓ 本番用Docker Compose設定作成: {config_path}")
        return config_path
    
    def create_env_template(self):
        """環境変数テンプレート作成"""
        self.log("=== 環境変数テンプレート作成 ===")
        
        env_template = """# BoatraceOpenAPI専用システム - 本番環境設定

# 必須設定
SECRET_KEY=your-secret-key-here-change-this-in-production

# オプション設定
SENTRY_DSN=https://your-sentry-dsn-here
LOG_LEVEL=INFO
LOG_FORMAT=json
CACHE_EXPIRY=300
API_TIMEOUT=10
WORKERS=4
WORKER_TIMEOUT=30

# セキュリティ設定
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
ENABLE_CORS=false

# 監視設定
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# サーバー設定
HOST=0.0.0.0
PORT=5000
DEBUG=false
"""
        
        env_path = self.app_dir / ".env.production"
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_template)
        
        self.log(f"✓ 環境変数テンプレート作成: {env_path}")
        self.log("重要: .env.productionを編集してSECRET_KEYを設定してください")
        return env_path
    
    def create_systemd_service(self):
        """systemdサービス設定作成"""
        self.log("=== systemdサービス設定作成 ===")
        
        service_config = f"""[Unit]
Description=BoatraceOpenAPI System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={self.app_dir}
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
        
        service_path = self.app_dir / "boatrace-openapi.service"
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(service_config)
        
        self.log(f"✓ systemdサービス設定作成: {service_path}")
        self.log("sudo cp boatrace-openapi.service /etc/systemd/system/ で有効化してください")
        return service_path
    
    def deploy(self) -> bool:
        """完全デプロイ実行"""
        self.log("=== BoatraceOpenAPI本番デプロイ開始 ===")
        
        # 1. システム要件チェック
        if not self.check_system_requirements():
            self.log("システム要件が満たされていません", "ERROR")
            return False
        
        # 2. 設定ファイル作成
        self.create_nginx_ssl_config()
        self.create_production_docker_compose()
        self.create_env_template()
        self.create_systemd_service()
        
        # 3. ディレクトリ作成
        os.makedirs(self.app_dir / "logs", exist_ok=True)
        os.makedirs(self.app_dir / "cache", exist_ok=True)
        
        # 4. Docker イメージビルド
        self.log("=== Dockerイメージビルド ===")
        success, _ = self.run_command("docker-compose -f docker-compose.prod.yml build")
        if not success:
            self.log("Dockerビルド失敗", "ERROR")
            return False
        
        # 5. SSL証明書生成（ドメイン指定時のみ）
        if self.domain != "localhost":
            if not self.generate_ssl_certificates():
                self.log("SSL証明書生成失敗 - HTTP版で継続", "WARNING")
        
        self.log("=== デプロイ完了 ===")
        self.log("次の手順を実行してください:")
        self.log("1. .env.productionを編集してSECRET_KEYを設定")
        self.log("2. sudo cp nginx_ssl.conf /etc/nginx/sites-available/boatrace")
        self.log("3. sudo ln -s /etc/nginx/sites-available/boatrace /etc/nginx/sites-enabled/")
        self.log("4. sudo nginx -t && sudo systemctl reload nginx")
        self.log("5. docker-compose -f docker-compose.prod.yml up -d")
        
        return True
    
    def save_deployment_log(self):
        """デプロイログ保存"""
        log_content = "\n".join(self.logs)
        log_path = self.app_dir / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        print(f"\nデプロイログ保存: {log_path}")


def main():
    """メイン実行"""
    if len(sys.argv) < 3:
        print("使用法: python production_deploy.py <domain> <ssl_email>")
        print("例: python production_deploy.py example.com admin@example.com")
        sys.exit(1)
    
    domain = sys.argv[1]
    ssl_email = sys.argv[2]
    
    deployer = ProductionDeployer(domain, ssl_email)
    
    try:
        success = deployer.deploy()
        deployer.save_deployment_log()
        
        if success:
            print("\n🎉 デプロイ準備完了！")
            sys.exit(0)
        else:
            print("\n❌ デプロイ失敗")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ デプロイ中断")
        deployer.save_deployment_log()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 予期しないエラー: {e}")
        deployer.save_deployment_log()
        sys.exit(1)


if __name__ == "__main__":
    main()