# コードベース リファクタリング計画

## 現状の問題点
- **ファイル数過多**: 100+個のPythonファイルが乱雑に配置
- **重複コード**: 類似機能が複数ファイルに分散
- **命名規則**: 一貫性のないファイル・変数命名
- **構造不明**: ディレクトリ構造が不明確
- **テストファイル混在**: 本番コードとテストが混在

## リファクタリング目標
1. **クリーンな構造**: 機能別ディレクトリ分割
2. **重複排除**: 共通機能の統合
3. **命名統一**: 一貫したネーミング規則
4. **保守性向上**: 理解しやすいコード構造
5. **テスト分離**: テストコードの適切な配置

## 新しいディレクトリ構造
```
kyotei/
├── src/                    # メインソースコード
│   ├── core/              # 核心機能
│   ├── prediction/        # 予測機能
│   ├── data/             # データ処理
│   ├── monitoring/       # 監視・分析
│   └── utils/            # ユーティリティ
├── tests/                 # テストコード
├── docs/                  # ドキュメント
├── scripts/              # 実行スクリプト
├── configs/              # 設定ファイル
└── cache/                # キャッシュデータ
```

## 統合対象ファイル
### 予測システム
- production_deployment.py (メイン)
- enhanced_prediction_system.py
- simple_production_test.py
- realtime_prediction_system.py

### データ処理
- data_monitoring_system.py (メイン)
- data/boatrace_openapi_fetcher.py
- weather_fetcher.py
- race_result_fetcher.py

### 最適化・調整
- hyperparameter_optimizer.py (メイン)
- quick_hyperparameter_tune.py
- system_optimizer.py
- simple_parameter_tune.py

### テスト・検証
- test_* ファイル群を tests/ に移動
- 重複テストの統合