# BoatraceOpenAPI専用競艇予想システム

## 概要

このシステムは**BoatraceOpenAPI**のみを使用したシンプルな競艇予想システムです。複雑な機械学習や多数のデータソースを排除し、OpenAPIから取得できる実際のデータのみを使用して予想を行います。

## 特徴

- ✅ **BoatraceOpenAPI専用**: 実際のデータのみ使用、推測データ一切なし
- ✅ **シンプル設計**: 最小限の依存関係、軽量動作
- ✅ **レスポンシブUI**: スマートフォン・タブレット対応
- ✅ **キャッシュ機能**: API負荷軽減のため5分間キャッシュ
- ✅ **リアルタイムデータ**: 今日のレース情報を自動取得

## システム構成

```
├── openapi_app.py                # メインアプリケーション
├── templates/
│   ├── openapi_index.html        # レース一覧ページ
│   └── openapi_predict.html      # 予想詳細ページ
├── cache/                        # キャッシュディレクトリ
├── requirements_openapi.txt      # 依存関係
├── test_openapi_simple.py        # テストスクリプト
└── README_OPENAPI.md            # このファイル
```

## 動作要件

- Python 3.7+
- インターネット接続（BoatraceOpenAPI取得用）
- ブラウザ（Chrome, Firefox, Safari, Edge対応）

## インストール・起動

### 1. 依存関係インストール

```bash
pip install -r requirements_openapi.txt
```

### 2. システム起動

```bash
python openapi_app.py
```

### 3. ブラウザアクセス

```
http://localhost:5000
```

## 機能詳細

### メインページ (/)

- 今日開催の全レースを一覧表示
- 会場名、レース番号、発走時刻を表示
- レース数の統計情報を表示
- 5分間隔で自動リロード

### 予想ページ (/predict/{race_id})

- 各選手の詳細情報を表示
- 全国勝率に基づく予想勝率計算
- 艇番有利度を考慮した推奨艇表示
- 単勝・複勝の推奨を表示

### API エンドポイント

#### GET /api/races
今日のレース一覧をJSON形式で取得

```json
{
  "success": true,
  "total_races": 144,
  "data": {
    "programs": [...]
  }
}
```

## 予想アルゴリズム

### 基本実力値計算
```python
base_strength = min(全国勝率 / 100.0, 0.6)
```

### 艇番有利度
```python
lane_advantages = {
    1: 0.25,  # 1号艇: 25%
    2: 0.18,  # 2号艇: 18%
    3: 0.15,  # 3号艇: 15%
    4: 0.12,  # 4号艇: 12%
    5: 0.10,  # 5号艇: 10%
    6: 0.08   # 6号艇: 8%
}
```

### 最終予想値
```python
final_prediction = min(base_strength + lane_advantage, 0.85)
```

## データソース

- **唯一のデータソース**: [BoatraceOpenAPI](https://boatraceopenapi.github.io/)
- **取得データ**: 
  - 選手情報（名前、登録番号）
  - 成績データ（全国勝率、当地勝率）
  - レース情報（会場、番号、発走時刻）
  - ボート情報（平均ST）

## テスト

### 基本テスト（OpenAPI接続確認）
```bash
python test_openapi_simple.py
```

### フルテスト（アプリ動作確認）
```bash
# 別ターミナルでアプリ起動
python openapi_app.py

# テスト実行
python test_openapi_simple.py --app
```

## ファイル説明

### openapi_app.py
- Flask Webアプリケーションのメイン
- SimpleOpenAPIFetcherクラス：OpenAPIデータ取得・キャッシュ管理
- 予想計算ロジック
- ルーティング定義

### templates/openapi_index.html
- レース一覧表示ページ
- Bootstrap風のレスポンシブデザイン
- レースカードのホバー効果
- 統計情報表示

### templates/openapi_predict.html
- レース予想詳細ページ
- 各選手の詳細情報表示
- 予想バーグラフ
- 推奨艇のハイライト

### test_openapi_simple.py
- OpenAPI接続テスト
- アプリケーション動作テスト
- システム準備確認

## 注意事項

- このシステムは**実際のデータのみ**を使用します
- 推測・憶測による情報は一切表示しません
- OpenAPIからデータが取得できない場合は「データなし」を表示します
- 投資の判断は自己責任で行ってください

## システムの制限

- OpenAPIの更新頻度に依存
- インターネット接続が必要
- 過去のレース結果は保存しない（リアルタイムのみ）
- 気象情報は含まない（OpenAPIに気象データが含まれていないため）

## トラブルシューティング

### OpenAPI接続エラー
```bash
# 接続確認
python test_openapi_simple.py
```

### アプリ起動エラー
```bash
# ポート確認
netstat -an | findstr :5000

# 依存関係再インストール
pip install -r requirements_openapi.txt --force-reinstall
```

### キャッシュクリア
```bash
# キャッシュファイル削除
del cache\openapi_cache.json
```

## ライセンス

このプロジェクトはMITライセンスの下で提供されています。

---

**BoatraceOpenAPI専用システム v1.0**  
最終更新: 2025-08-21