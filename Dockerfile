# BoatraceOpenAPI専用システム Docker設定
FROM python:3.11-slim

# 作業ディレクトリ設定
WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係コピー・インストール
COPY requirements_openapi.txt .
RUN pip install --no-cache-dir -r requirements_openapi.txt

# アプリケーションファイルコピー
COPY openapi_app.py .
COPY data/ ./data/
COPY templates/ ./templates/

# キャッシュディレクトリ作成
RUN mkdir -p cache

# 非root ユーザー作成・切り替え
RUN adduser --disabled-password --gecos '' --uid 1000 boatrace
RUN chown -R boatrace:boatrace /app
USER boatrace

# ポート公開
EXPOSE 5000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/test', timeout=10)"

# アプリケーション起動
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "30", "openapi_app:app"]