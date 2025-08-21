#!/bin/bash
# BoatraceOpenAPI専用システム デプロイスクリプト

set -e  # エラーで停止

echo "=== BoatraceOpenAPI専用システム デプロイ開始 ==="

# 現在の時刻
DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "デプロイ時刻: $DEPLOY_TIME"

# 1. システム動作確認
echo "1. システムテスト実行中..."
python test_openapi_simple.py
if [ $? -ne 0 ]; then
    echo "❌ システムテストに失敗しました"
    exit 1
fi
echo "✅ システムテスト成功"

# 2. Dockerイメージビルド
echo "2. Dockerイメージビルド中..."
docker build -t boatrace-openapi:latest .
if [ $? -ne 0 ]; then
    echo "❌ Dockerビルドに失敗しました"
    exit 1
fi
echo "✅ Dockerイメージビルド成功"

# 3. イメージテスト
echo "3. Dockerイメージテスト中..."
docker run --rm -d --name boatrace-test -p 5001:5000 boatrace-openapi:latest
sleep 10

# ヘルスチェック
curl -f http://localhost:5001/test > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Dockerコンテナのヘルスチェックに失敗しました"
    docker stop boatrace-test || true
    exit 1
fi

docker stop boatrace-test
echo "✅ Dockerイメージテスト成功"

# 4. 本番デプロイ
echo "4. 本番デプロイ中..."
if [ "$1" = "--production" ]; then
    echo "本番環境にデプロイします..."
    docker-compose -f docker-compose.yml --profile production up -d
    echo "✅ 本番デプロイ完了"
else
    echo "開発環境にデプロイします..."
    docker-compose up -d boatrace-openapi
    echo "✅ 開発デプロイ完了"
fi

# 5. デプロイ後確認
echo "5. デプロイ後確認中..."
sleep 15

curl -f http://localhost:5000/test > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ デプロイ後のヘルスチェックに失敗しました"
    exit 1
fi

echo "✅ デプロイ後確認成功"

echo ""
echo "=== デプロイ完了 ==="
echo "URL: http://localhost:5000"
echo "API: http://localhost:5000/api/races"
echo "ヘルスチェック: http://localhost:5000/test"
echo ""
echo "ログ確認: docker-compose logs -f"
echo "停止: docker-compose down"
echo "==========================="