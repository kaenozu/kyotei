# 競艇予想システム - モジュール化版 v4.1

モジュール化された高性能・高品質な競艇予想システムです。

## 🚀 特徴

- **モジュール化アーキテクチャ**: 保守性・拡張性を重視した設計
- **高速起動**: 最適化された起動時間
- **シンプルな操作**: 直感的なインターフェース
- **三連単対応**: 単勝・複勝・三連単の的中率追跡
- **Web UI対応**: ブラウザからの操作が可能
- **自動スケジューリング**: AM6:00データ取得・結果更新の自動化

## 📦 必要な環境

- Python 3.8以上
- 必要なライブラリ: `pip install requests flask schedule aiohttp numpy`

## 🎯 使用方法

### モジュール化版（推奨）

```bash
# モジュール化版Webサーバー起動
python scripts/web_app_modular.py

# 直接実行
cd scripts && python -m modules.main_app
```

### Windows での使用（モジュール化版）

```cmd
# モジュール化版起動
cd scripts
start_modular.bat

# レガシー版起動
start_modular.bat legacy
```

### レガシー版（統一システム）

```bash
# Webサーバー起動
python start_kyotei.py web

# 予想テスト実行
python start_kyotei.py test

# 的中率分析
python start_kyotei.py accuracy
```

## 📊 機能一覧

### 1. 予想機能
- BoatraceOpenAPIからのデータ取得
- 統計ベース予想アルゴリズム
- 信頼度付き予想結果

### 2. 的中率追跡
- 単勝的中率の計算
- 複勝的中率の計算
- 三連単的中率の計算
- 履歴データの自動保存

### 3. Web UI
- ブラウザでの操作
- リアルタイム予想
- 的中率レポート表示

## 🌐 Web API

Webサーバー起動後、以下のAPIが利用できます：

- `http://localhost:5000/` - システム情報
- `http://localhost:5000/predict/12/1` - レース予想（住之江1R）
- `http://localhost:5000/accuracy` - 的中率サマリー
- `http://localhost:5000/status` - システム状態

## 📁 ファイル構成

```
kyotei/
├── scripts/
│   ├── modules/            # モジュール化システム（v4.1・推奨）
│   │   ├── api_fetcher.py     # APIデータ取得・ユーティリティ
│   │   ├── route_handlers.py  # Flaskルートハンドラー
│   │   ├── scheduler_service.py # スケジューラーサービス
│   │   ├── main_app.py        # メインアプリ統合
│   │   └── __init__.py        # パッケージ定義
│   ├── web_app_modular.py  # モジュール版エントリーポイント
│   ├── web_app.py          # レガシー大型ファイル（段階的廃止）
│   └── start_modular.bat   # モジュール版起動スクリプト
├── accuracy_tracker.py    # 統一版システム（レガシー）
├── start_kyotei.py         # レガシー起動スクリプト
├── enhanced_predictor.py   # 強化予想システム
├── src/core/               # 共通コンポーネント
│   └── accuracy_tracker.py   # 的中率追跡クラス
├── cache/                  # データベース・キャッシュ
├── logs/                   # ログファイル
├── archive/                # 旧バージョンファイル
├── templates/              # HTMLテンプレート
├── static/                 # 静的ファイル
└── README.md              # このファイル
```

## 🎯 予想アルゴリズム

以下の要素を統合して予想を行います：

- **全国勝率** (18%): 選手の全国成績
- **当地勝率** (12%): 当該競艇場での成績  
- **モーター性能** (12%): 割り当てモーターの性能
- **ボート性能** (8%): 割り当てボートの性能
- **スタートタイミング** (10%): 平均スタート時間
- **その他要素** (40%): 展示・天候・コース等

## 📈 的中率実績

現在の的中率（参考値）：
- **単勝的中率**: 約30-35%
- **複勝的中率**: 約70-75%
- **三連単的中率**: 約3-5%

## 🛠️ トラブルシューティング

### よくある問題

**Q: APIデータが取得できない**
- A: インターネット接続を確認してください
- A: BoatraceOpenAPIの稼働状況を確認してください

**Q: Webサーバーが起動しない**
- A: ポート5000が使用中でないか確認してください
- A: `flask`ライブラリがインストールされているか確認してください

**Q: 文字化けが発生する**
- A: コマンドプロンプトで `chcp 65001` を実行してください

---

**競艇予想システム v4.1 - モジュール化版**  
モジュール化・高品質・拡張性を追求した最新版