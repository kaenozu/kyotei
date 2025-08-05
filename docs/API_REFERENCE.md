# 競輪予想システム - API リファレンス

## 📋 目次
1. [概要](#概要)
2. [データ取得API](#データ取得api)
3. [予想エンジンAPI](#予想エンジンapi)
4. [キャッシュシステムAPI](#キャッシュシステムapi)
5. [設定管理API](#設定管理api)
6. [エラーハンドリング](#エラーハンドリング)
7. [使用例](#使用例)

---

## 概要

競輪予想システムの内部APIリファレンスです。各モジュールの主要クラスとメソッドの詳細仕様を記載しています。

---

## データ取得API

### KeirinDataFetcher

競輪データの取得を担当するメインクラスです。

#### クラス初期化

```python
from data.fetcher import KeirinDataFetcher

fetcher = KeirinDataFetcher()
```

#### メソッド一覧

##### `get_today_races() -> List[RaceInfo]`
本日のレース一覧を取得します。

**戻り値:**
- `List[RaceInfo]`: 本日のレース情報リスト

**例:**
```python
races = fetcher.get_today_races()
for race in races:
    print(f"{race.venue} {race.race_number}R - {race.start_time}")
```

##### `get_tomorrow_races() -> List[RaceInfo]`
明日のレース一覧を取得します。

**戻り値:**
- `List[RaceInfo]`: 明日のレース情報リスト

##### `get_races_by_venue(venue: str) -> List[RaceInfo]`
指定開催場のレース一覧を取得します。

**パラメータ:**
- `venue` (str): 競輪場名（例: "平塚", "川崎"）

**戻り値:**
- `List[RaceInfo]`: 指定開催場のレース情報リスト

##### `get_race_details(race_id: str) -> Optional[RaceDetail]`
特定レースの詳細情報を取得します。

**パラメータ:**
- `race_id` (str): レースID（例: "20241205_平塚_01"）

**戻り値:**
- `Optional[RaceDetail]`: レース詳細情報、取得失敗時はNone

**例:**
```python
detail = fetcher.get_race_details("20241205_平塚_01")
if detail:
    print(f"選手数: {len(detail.riders)}")
    for rider in detail.riders:
        print(f"{rider.number}番 {rider.name} ({rider.class_rank.value})")
```

##### `get_rider_stats(rider_id: str) -> RiderStats`
選手の成績データを取得します。

**パラメータ:**
- `rider_id` (str): 選手ID

**戻り値:**
- `RiderStats`: 選手成績データ

---

## 予想エンジンAPI

### KeirinPredictor

レース予想を実行するメインクラスです。

#### クラス初期化

```python
from prediction.predictor import KeirinPredictor

predictor = KeirinPredictor()
```

#### メソッド一覧

##### `predict_race(race_detail: RaceDetail) -> PredictionResult`
レースの予想を実行します。

**パラメータ:**
- `race_detail` (RaceDetail): レース詳細情報

**戻り値:**
- `PredictionResult`: 予想結果

**例:**
```python
prediction = predictor.predict_race(race_detail)
print(f"1位予想: {prediction.rankings[0]}番")
print(f"信頼度: {prediction.confidence:.1%}")

# 各選手のスコア確認
for rank, rider_num in enumerate(prediction.rankings, 1):
    score = prediction.scores[rider_num]
    print(f"{rank}位: {rider_num}番 (スコア: {score.total_score:.1f})")
```

##### スコア計算の詳細

**RiderScore構造:**
```python
@dataclass
class RiderScore:
    rider_number: int
    ability_score: float      # 選手能力スコア (0-100)
    form_score: float         # 近況フォームスコア (0-100)
    track_score: float        # バンク相性スコア (0-100)
    line_score: float         # ライン戦略スコア (0-100)
    external_score: float     # 外部要因スコア (0-100)
    total_score: float        # 総合スコア (0-100)
    confidence: float         # 信頼度 (0-1)
```

---

## キャッシュシステムAPI

### CacheManager

SQLiteベースのキャッシュシステムです。

#### クラス初期化

```python
from utils.cache import cache  # シングルトンインスタンス
```

#### メソッド一覧

##### `get(key: str) -> Any`
キーに対応するデータを取得します。

**パラメータ:**
- `key` (str): キャッシュキー

**戻り値:**
- `Any`: キャッシュされたデータ、存在しない場合はNone

##### `set(key: str, value: Any, category: str, expires_in: int = None)`
データをキャッシュに保存します。

**パラメータ:**
- `key` (str): キャッシュキー
- `value` (Any): 保存するデータ
- `category` (str): カテゴリ（"race_info", "race_detail", "rider_stats"）
- `expires_in` (int, optional): 有効期限（秒）

##### `clear_all()`
全キャッシュをクリアします。

##### `clear_expired()`
期限切れキャッシュのみクリアします。

##### `get_cache_info() -> Dict[str, int]`
キャッシュ統計情報を取得します。

**戻り値:**
```python
{
    "total_entries": 150,
    "valid_entries": 140,
    "expired_entries": 10
}
```

---

## 設定管理API

### ConfigManager

アプリケーションの設定をSQLiteデータベースに永続化して管理するクラスです。`config/settings.py` から設定を読み書きする際に内部的に使用されます。

#### クラス初期化

`ConfigManager` はシングルトンとして `config/config_manager.py` でインスタンス化されており、通常は直接インスタンスを作成する必要はありません。`config.config_manager` からインポートして使用します。

```python
from config.config_manager import config_manager

# config_manager インスタンスを直接使用
current_log_level = config_manager.get("LOG_CONFIG")["level"]
```

#### メソッド一覧

##### `get(key: str, default: Any = None) -> Any`
指定されたキーの設定値を取得します。値はJSON形式で保存されているため、読み込み時にデコードされます。

**パラメータ:**
- `key` (str): 設定のキー（例: "LOG_CONFIG", "SCRAPING_CONFIG"）
- `default` (Any, optional): キーが存在しない場合に返されるデフォルト値。デフォルトは `None`。

**戻り値:**
- `Any`: キーに対応する設定値。キーが存在しない場合は `default` 値。

**例:**
```python
log_config = config_manager.get("LOG_CONFIG", {})
print(f"現在のログレベル: {log_config.get("level")}")
```

##### `set(key: str, value: Any)`
指定されたキーに設定値を保存します。値はJSON形式で保存するため、保存時にエンコードされます。

**パラメータ:**
- `key` (str): 設定のキー
- `value` (Any): 保存する設定値

**例:**
```python
# ログレベルをDEBUGに設定して保存
log_config = config_manager.get("LOG_CONFIG", {})
log_config["level"] = "DEBUG"
config_manager.set("LOG_CONFIG", log_config)
```

##### `get_all() -> Dict[str, Any]`
全ての保存された設定を取得します。

**戻り値:**
- `Dict[str, Any]`: 全ての設定をキーと値の辞書として返します。

**例:**
```python
all_settings = config_manager.get_all()
for key, value in all_settings.items():
    print(f"{key}: {value}")
```

##### `delete(key: str)`
指定されたキーの設定をデータベースから削除します。

**パラメータ:**
- `key` (str): 削除する設定のキー

**例:**
```python
config_manager.delete("OLD_SETTING")
```

### `config/settings.py` の設定ロード・保存関数

`config/settings.py` は、アプリケーション起動時に `ConfigManager` から設定をロードし、アプリケーション終了時（または明示的に呼び出された時）に設定を保存するためのヘルパー関数を提供します。

##### `load_settings()`
`ConfigManager` から最新の設定を読み込み、グローバルな設定変数（`LOG_CONFIG`, `SCRAPING_CONFIG` など）を更新します。アプリケーションの起動時に自動的に呼び出されます。

##### `save_settings()`
現在のグローバルな設定変数（`LOG_CONFIG`, `SCRAPING_CONFIG` など）の値を `ConfigManager` を介してデータベースに保存します。CLIの「設定変更」メニューなどで設定が変更された後に呼び出されます。

---

## エラーハンドリング

### 例外クラス

```python
class KeirinDataError(Exception):
    """データ取得関連エラー"""
    pass

class KeirinPredictionError(Exception):
    """予想処理関連エラー"""
    pass

class KeirinCacheError(Exception):
    """キャッシュ関連エラー"""
    pass
```

### エラー処理パターン

```python
try:
    races = fetcher.get_today_races()
except KeirinDataError as e:
    logger.error(f"データ取得エラー: {e}")
    # フォールバック処理
    races = fetcher._get_sample_races()
```

---

## 使用例

### 完全な予想実行例

```python
#!/usr/bin/env python3
"""競輪予想システム使用例"""

from data.fetcher import KeirinDataFetcher
from prediction.predictor import KeirinPredictor
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)

def main():
    # システム初期化
    fetcher = KeirinDataFetcher()
    predictor = KeirinPredictor()
    
    try:
        # 1. 本日のレース一覧取得
        print("📅 本日のレース一覧取得中...")
        races = fetcher.get_today_races()
        print(f"取得成功: {len(races)}レース")
        
        # 2. 最初のレースを選択
        if races:
            target_race = races[0]
            print(f"🎯 対象レース: {target_race.venue} {target_race.race_number}R")
            
            # 3. レース詳細取得
            print("📊 レース詳細取得中...")
            race_detail = fetcher.get_race_details(target_race.race_id)
            
            if race_detail:
                print(f"選手数: {len(race_detail.riders)}人")
                
                # 4. 予想実行
                print("🔮 予想計算中...")
                prediction = predictor.predict_race(race_detail)
                
                # 5. 結果表示
                print("\n🏆 予想結果:")
                print(f"信頼度: {prediction.confidence:.1%}")
                
                for rank, rider_num in enumerate(prediction.rankings[:3], 1):
                    rider = race_detail.get_rider_by_number(rider_num)
                    score = prediction.scores[rider_num]
                    print(f"{rank}位: {rider_num}番 {rider.name} "
                          f"(スコア: {score.total_score:.1f})")
                
                # 6. 買い目推奨
                if prediction.betting_recommendations:
                    print("\n💡 おすすめ買い目:")
                    for rec in prediction.betting_recommendations[:3]:
                        print(f"{rec.bet_type}: {rec.combination} "
                              f"({rec.expected_odds:.1f}倍, 信頼度{rec.confidence})")
            
            else:
                print("❌ レース詳細の取得に失敗しました")
        
        else:
            print("❌ レース情報の取得に失敗しました")
    
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
```

### バッチ処理例

```python
def batch_prediction():
    """全レースの一括予想処理"""
    fetcher = KeirinDataFetcher()
    predictor = KeirinPredictor()
    
    # 本日の全レース取得
    races = fetcher.get_today_races()
    results = []
    
    for race in races:
        try:
            # レース詳細取得
            detail = fetcher.get_race_details(race.race_id)
            if detail:
                # 予想実行
                prediction = predictor.predict_race(detail)
                
                results.append({
                    "race_id": race.race_id,
                    "venue": race.venue,
                    "race_number": race.race_number,
                    "prediction": prediction.rankings[0],  # 1位予想
                    "confidence": prediction.confidence
                })
        
        except Exception as e:
            print(f"予想エラー ({race.race_id}): {e}")
    
    return results
```

### キャッシュ活用例

```python
def optimized_data_fetch():
    """キャッシュを活用した効率的なデータ取得"""
    from utils.cache import cache
    
    # キャッシュ確認
    cache_key = "today_races"
    races = cache.get(cache_key)
    
    if races:
        print("📦 キャッシュからデータ取得")
        return races
    
    # キャッシュにない場合は新規取得
    print("🌐 新規データ取得")
    fetcher = KeirinDataFetcher()
    races = fetcher.get_today_races()
    
    # キャッシュに保存（30分間有効）
    cache.set(cache_key, races, "race_info", expires_in=1800)
    
    return races
```

---

## パフォーマンスチューニング

### 高速化のポイント

1. **キャッシュ活用**: 頻繁にアクセスするデータはキャッシュ化
2. **並列処理**: 複数レースの予想は並列実行可能
3. **メモリ管理**: 大量データ処理時はメモリ使用量に注意
4. **データベース最適化**: SQLiteインデックスの活用

### 推奨使用パターン

```python
# ✅ 推奨: キャッシュを活用
races = fetcher.get_today_races()  # 自動でキャッシュ確認

# ❌ 非推奨: 頻繁な詳細取得
for race in races:
    detail = fetcher.get_race_details(race.race_id)  # 毎回通信発生

# ✅ 推奨: バッチ取得 + キャッシュ
details = []
for race in races:
    detail = fetcher.get_race_details(race.race_id)  # キャッシュ確認済み
    if detail:
        details.append(detail)
```

---

*最終更新: 2025年8月5日*
*バージョン: v1.0.0*