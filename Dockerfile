# 競艇予想システム Docker設定
FROM python:3.11-slim

# 作業ディレクトリ設定
WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係インストール
RUN pip install --no-cache-dir requests flask schedule aiohttp numpy gunicorn

# アプリケーションファイルコピー
COPY scripts/ ./scripts/
COPY src/ ./src/
COPY templates/ ./templates/
COPY cache/ ./cache/
COPY logs/ ./logs/

# 必要なディレクトリ作成
RUN mkdir -p cache logs

# 非root ユーザー作成・切り替え
RUN adduser --disabled-password --gecos '' --uid 1000 kyotei
RUN chown -R kyotei:kyotei /app
USER kyotei

# ポート公開
EXPOSE 5001

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001/status || exit 1

# アプリケーション起動
CMD ["python", "scripts/web_app_modular.py"]