# 競艇予想システム起動ガイド

## 🚀 基本起動方法

### Step 1: ターミナル/コマンドプロンプトを開く
1. **Windows**: `Win + R` → `cmd` → Enter
2. **または**: スタートメニュー → 「コマンドプロンプト」検索

### Step 2: プロジェクトディレクトリに移動
```bash
cd "C:\Users\neoen\OneDrive\gemini\kyotei"
```

### Step 3: システム起動
```bash
python openapi_app.py
```

### Step 4: ブラウザでアクセス
- **メイン画面**: http://localhost:5000
- **投資ダッシュボード**: http://localhost:5000/investment

---

## 🖥️ 起動後の画面

### メイン画面 (http://localhost:5000)
- 今日のレース一覧
- 各レースの予想リンク
- システム状態表示

### 投資ダッシュボード (http://localhost:5000/investment)
- 投資統計・収支分析
- リスク分析・パフォーマンス指標
- レポート生成・アラート履歴
- 戦略設定・最適化推奨

---

## ⚙️ 起動オプション

### デバッグモード（開発用）
```bash
python openapi_app.py --debug
```

### カスタムポート指定
```bash
set PORT=8080
python openapi_app.py
```

### バックグラウンド実行（Windows）
```bash
start /min python openapi_app.py
```

---

## 🛑 システム停止方法

### 通常停止
- ターミナルで `Ctrl + C`

### 強制停止
- タスクマネージャーでPythonプロセス終了

---

## 🔧 トラブルシューティング

### エラー: "ModuleNotFoundError"
```bash
pip install -r requirements_kyotei.txt
```

### エラー: "Port 5000 already in use"
```bash
# 他のアプリ（Skypeなど）がポート使用中
# ポート変更で回避:
set PORT=8080
python openapi_app.py
```

### エラー: "Permission denied"
```bash
# 管理者権限でコマンドプロンプト実行
```

---

## 🎯 初回使用時の推奨手順

1. **システム起動確認**
   - `python openapi_app.py` でエラーなく起動
   - ブラウザで http://localhost:5000 アクセス確認

2. **今日のレースデータ確認**
   - メイン画面でレース一覧表示確認
   - 1つのレースをクリックして予想詳細確認

3. **投資ダッシュボード確認**
   - /investment でダッシュボード表示確認
   - 各種統計・分析機能の動作確認

4. **設定調整**
   - 投資戦略設定（上限金額・リスクレベル）
   - アラート設定確認

5. **テスト運用**
   - 少額での実際の投資テスト
   - 結果記録・分析機能の確認

---

## 📱 利用可能な機能一覧

### 予想システム
- `/` - 今日のレース一覧
- `/predict/{venue_id}_{race_number}` - レース予想詳細
- `/api/prediction/{venue_id}/{race_number}?format=html` - 予想根拠レポート

### 投資管理
- `/investment` - 投資ダッシュボード
- `/api/investment/stats` - 投資統計API
- `/api/investment/optimal-stake` - 最適賭け金API
- `/api/investment/analytics` - 高度分析API

### レポート・アラート
- `/api/investment/reports/generate` - レポート生成API
- `/api/investment/alerts` - アラート履歴API
- `/api/investment/alerts/check` - アラートチェックAPI

---

## 🔄 自動起動設定（オプション）

### Windows起動時の自動実行
1. `Win + R` → `shell:startup`
2. 以下のバッチファイルを作成:

**startup_kyotei.bat**
```batch
@echo off
cd "C:\Users\neoen\OneDrive\gemini\kyotei"
python openapi_app.py
```

3. ファイルをstartupフォルダに配置

---

## 📞 サポート情報

### ログの確認
- システムログ: `kyotei.log`
- エラー詳細: コンソール出力確認

### 設定ファイル
- 基本設定: `.env`
- キャッシュ: `cache/` フォルダ
- レポート: `reports/` フォルダ

### バックアップ推奨ファイル
- 投資記録: `cache/investment_records.db`
- アラート履歴: `cache/investment_alerts.db`
- 設定ファイル: `.env`