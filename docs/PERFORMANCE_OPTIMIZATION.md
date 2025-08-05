# 競輪予想システム - パフォーマンス最適化ガイド

## 📋 目次
1. [概要](#概要)
2. [現在のパフォーマンス状況](#現在のパフォーマンス状況)
3. [キャッシュシステム最適化](#キャッシュシステム最適化)
4. [データ取得最適化](#データ取得最適化)
5. [予想処理最適化](#予想処理最適化)
6. [メモリ使用量最適化](#メモリ使用量最適化)
7. [並列処理の活用](#並列処理の活用)
8. [監視・プロファイリング](#監視プロファイリング)
9. [最適化の実装例](#最適化の実装例)

---

## 概要

競輪予想システムのパフォーマンス最適化に関する包括的なガイドです。システムの各コンポーネントの最適化手法と実装方法を詳細に説明します。

### 🎯 最適化目標
- **応答時間**: レース一覧表示 < 1秒、予想計算 < 3秒
- **スループット**: 同時10レース以上の予想処理
- **メモリ効率**: 使用メモリ < 256MB
- **キャッシュ効率**: ヒット率 > 85%

---

## 現在のパフォーマンス状況

### ⚡ 測定結果（v1.0.0基準）

| 処理項目 | 現在値 | 目標値 | 状態 |
|---------|--------|--------|------|
| システム起動時間 | 0.8秒 | < 1秒 | ✅ 良好 |
| レース一覧取得 | 2.1秒 | < 1秒 | ⚠️ 改善要 |
| レース詳細取得 | 1.5秒 | < 1秒 | ⚠️ 改善要 |
| 予想計算処理 | 0.4秒 | < 3秒 | ✅ 良好 |
| キャッシュヒット率 | 78% | > 85% | ⚠️ 改善要 |
| メモリ使用量 | 145MB | < 256MB | ✅ 良好 |

### 🔍 ボトルネック分析

パフォーマンスの閾値は `config/settings.py` の `PERFORMANCE_CONFIG` で設定可能です。

```python
# パフォーマンス測定用のデコレータ
import time
import functools
from typing import Callable

def performance_monitor(func: Callable) -> Callable:
    """パフォーマンス測定デコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        print(f"⏱️  {func.__name__}: {end_time - start_time:.3f}秒")
        return result
    return wrapper
```

---

## キャッシュシステム最適化

### 🚀 現在のキャッシュ実装

```python
# utils/cache.py の最適化版
import sqlite3
import pickle
import threading
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging

class OptimizedCacheManager:
    """最適化されたキャッシュマネージャー"""
    
    def __init__(self, db_path: str = "cache/cache.db"):
        self.db_path = db_path
        self.memory_cache = {}  # L1キャッシュ（メモリ）
        self.memory_cache_size = 1000  # メモリキャッシュ最大サイズ
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        self._init_db()
    
    def _init_db(self):
        """データベース初期化（インデックス追加）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    category TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            # パフォーマンス向上のためのインデックス
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON cache(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)")
    
    def get(self, key: str) -> Optional[Any]:
        """最適化されたデータ取得"""
        # L1キャッシュ（メモリ）をチェック
        with self.lock:
            if key in self.memory_cache:
                value, expires_at = self.memory_cache[key]
                if expires_at is None or datetime.now() < expires_at:
                    return value
                else:
                    # 期限切れなので削除
                    del self.memory_cache[key]
        
        # L2キャッシュ（SQLite）をチェック
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                (key, datetime.now())
            )
            row = cursor.fetchone()
            
            if row:
                value = pickle.loads(row[0])
                expires_at = datetime.fromisoformat(row[1]) if row[1] else None
                
                # L1キャッシュに保存（LRU実装）
                with self.lock:
                    if len(self.memory_cache) >= self.memory_cache_size:
                        # 最も古いエントリを削除
                        oldest_key = min(self.memory_cache.keys())
                        del self.memory_cache[oldest_key]
                    
                    self.memory_cache[key] = (value, expires_at)
                
                return value
        
        return None
    
    def set(self, key: str, value: Any, category: str = "default", expires_in: int = None):
        """最適化されたデータ保存"""
        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None
        
        # L1キャッシュに保存
        with self.lock:
            if len(self.memory_cache) >= self.memory_cache_size:
                # LRU: 最も古いエントリを削除
                oldest_key = min(self.memory_cache.keys())
                del self.memory_cache[oldest_key]
            
            self.memory_cache[key] = (value, expires_at)
        
        # L2キャッシュに非同期保存
        threading.Thread(
            target=self._async_db_save,
            args=(key, value, category, expires_at),
            daemon=True
        ).start()
    
    def _async_db_save(self, key: str, value: Any, category: str, expires_at: Optional[datetime]):
        """非同期でのDB保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, category, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                    (key, pickle.dumps(value), category, datetime.now(), expires_at)
                )
        except Exception as e:
            self.logger.error(f"非同期キャッシュ保存エラー: {e}")
```

### 📊 キャッシュ戦略の最適化

```python
# 効率的なキャッシュキー設計
class CacheKeyGenerator:
    """効率的なキャッシュキー生成"""
    
    @staticmethod
    def race_list_key(date: str) -> str:
        """レース一覧のキー"""
        return f"races_{date}"
    
    @staticmethod
    def race_detail_key(race_id: str) -> str:
        """レース詳細のキー"""
        return f"race_detail_{race_id}"
    
    @staticmethod
    def rider_stats_key(rider_id: str, period: str = "recent") -> str:
        """選手成績のキー"""
        return f"rider_stats_{rider_id}_{period}"
    
    @staticmethod
    def prediction_key(race_id: str, algorithm_version: str = "v1") -> str:
        """予想結果のキー"""
        return f"prediction_{race_id}_{algorithm_version}"

# キャッシュ有効期限の最適化
CACHE_DURATIONS = {
    "race_info": 1800,      # 30分（レース情報）
    "race_detail": 3600,    # 1時間（レース詳細）
    "rider_stats": 86400,   # 24時間（選手成績）
    "prediction": 1800,     # 30分（予想結果）
    "system_config": 3600   # 1時間（システム設定）
}
```

---

## データ取得最適化

### 🌐 並列データ取得

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List

class OptimizedDataFetcher:
    """最適化されたデータ取得クラス"""
    
    def __init__(self):
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def get_multiple_races_async(self, race_ids: List[str]) -> List[Optional[RaceDetail]]:
        """複数レースの並列取得"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_race_detail_async(session, race_id)
                for race_id in race_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 例外処理
            race_details = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"レース取得エラー {race_ids[i]}: {result}")
                    race_details.append(None)
                else:
                    race_details.append(result)
            
            return race_details
    
    async def _fetch_race_detail_async(self, session: aiohttp.ClientSession, race_id: str) -> Optional[RaceDetail]:
        """非同期レース詳細取得"""
        try:
            # キャッシュ確認
            cached = cache.get(f"race_detail_{race_id}")
            if cached:
                return cached
            
            # 非同期HTTP取得
            url = self._build_race_detail_url(race_id)
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    race_detail = self._parse_race_detail_html(html, race_id)
                    
                    # キャッシュに保存
                    cache.set(f"race_detail_{race_id}", race_detail, "race_detail", 3600)
                    return race_detail
        
        except Exception as e:
            self.logger.error(f"非同期取得エラー {race_id}: {e}")
            return None
```

### 🔄 接続プール最適化

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedHTTPSession:
    """最適化されたHTTPセッション"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # 接続プール設定
        adapter = HTTPAdapter(
            pool_connections=10,    # 接続プールサイズ
            pool_maxsize=20,        # 最大プールサイズ
            max_retries=Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 504]
            )
        )
        
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # ヘッダー最適化
        self.session.headers.update({
            'User-Agent': 'KeirinPredictor/1.0',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def get(self, url: str, **kwargs):
        """最適化されたGETリクエスト"""
        return self.session.get(url, timeout=10, **kwargs)
```

---

## 予想処理最適化

### ⚡ 計算処理の最適化

```python
import numpy as np
from numba import jit
from typing import Dict, List, Tuple

class OptimizedPredictor:
    """最適化された予想エンジン"""
    
    @staticmethod
    @jit(nopython=True)
    def calculate_rider_scores_vectorized(
        rider_abilities: np.ndarray,
        recent_forms: np.ndarray,
        track_compatibilities: np.ndarray,
        weights: np.ndarray
    ) -> np.ndarray:
        """ベクトル化された選手スコア計算"""
        # NumPyを使った高速な行列演算
        feature_matrix = np.column_stack((
            rider_abilities,
            recent_forms,
            track_compatibilities
        ))
        
        # 重み付き合計をベクトル化計算
        scores = np.dot(feature_matrix, weights)
        
        # 非線形変換（シグモイド関数）
        return 100 / (1 + np.exp(-scores / 10))
    
    def predict_race_optimized(self, race_detail: RaceDetail) -> PredictionResult:
        """最適化された予想実行"""
        riders = race_detail.riders
        n_riders = len(riders)
        
        # データをNumPy配列に変換
        rider_abilities = np.zeros(n_riders)
        recent_forms = np.zeros(n_riders)
        track_compatibilities = np.zeros(n_riders)
        
        for i, rider in enumerate(riders):
            rider_abilities[i] = self._calculate_rider_ability(rider)
            recent_forms[i] = self._calculate_recent_form(rider)
            track_compatibilities[i] = self._calculate_track_compatibility(rider)
        
        # 重みベクトル
        weights = np.array([
            PREDICTION_WEIGHTS['rider_ability'],
            PREDICTION_WEIGHTS['recent_form'],
            PREDICTION_WEIGHTS['track_compatibility']
        ])
        
        # ベクトル化計算実行
        scores = self.calculate_rider_scores_vectorized(
            rider_abilities, recent_forms, track_compatibilities, weights
        )
        
        # 結果の構築
        rider_scores = {}
        for i, rider in enumerate(riders):
            rider_scores[rider.number] = RiderScore(
                rider_number=rider.number,
                ability_score=rider_abilities[i],
                form_score=recent_forms[i],
                track_score=track_compatibilities[i],
                line_score=70.0,  # デフォルト値
                external_score=50.0,  # デフォルト値
                total_score=scores[i],
                confidence=0.8
            )
        
        # ランキング作成
        rankings = sorted(riders, key=lambda r: scores[r.number-1], reverse=True)
        rankings = [r.number for r in rankings]
        
        # 信頼度計算
        confidence = self._calculate_confidence(scores)
        
        return PredictionResult(
            race_id=race_detail.race_info.race_id,
            rankings=rankings,
            scores=rider_scores,
            confidence=confidence,
            betting_recommendations=[]
        )
```

### 📊 メモリ効率の改善

```python
import gc
from memory_profiler import profile

class MemoryOptimizedPredictor:
    """メモリ最適化された予想エンジン"""
    
    def __init__(self):
        self.cache_limit = 100  # キャッシュサイズ制限
        self._prediction_cache = {}
    
    @profile
    def predict_with_memory_management(self, race_detail: RaceDetail) -> PredictionResult:
        """メモリ管理付き予想実行"""
        race_id = race_detail.race_info.race_id
        
        # メモリキャッシュ確認
        if race_id in self._prediction_cache:
            return self._prediction_cache[race_id]
        
        try:
            # 予想実行
            result = self._execute_prediction(race_detail)
            
            # キャッシュサイズ管理
            if len(self._prediction_cache) >= self.cache_limit:
                # 古いエントリを削除
                oldest_key = min(self._prediction_cache.keys())
                del self._prediction_cache[oldest_key]
            
            # 結果をキャッシュ
            self._prediction_cache[race_id] = result
            
            return result
        
        finally:
            # 明示的なガベージ収集
            gc.collect()
    
    def _execute_prediction(self, race_detail: RaceDetail) -> PredictionResult:
        """実際の予想処理（メモリ効率重視）"""
        # 一時変数の使用を最小限に
        riders = race_detail.riders
        scores = {}
        
        for rider in riders:
            # インライン計算でメモリ使用量削減
            total_score = (
                self._calc_ability(rider) * 0.35 +
                self._calc_form(rider) * 0.30 +
                self._calc_track(rider) * 0.20 +
                self._calc_line(rider) * 0.10 +
                self._calc_external(rider) * 0.05
            )
            
            scores[rider.number] = RiderScore(
                rider_number=rider.number,
                total_score=total_score,
                # 他のフィールドは計算済みの値を再利用
                ability_score=0.0,  # 必要に応じて計算
                form_score=0.0,
                track_score=0.0,
                line_score=0.0,
                external_score=0.0,
                confidence=0.8
            )
        
        # ソートして順位決定
        rankings = sorted(riders, key=lambda r: scores[r.number].total_score, reverse=True)
        rankings = [r.number for r in rankings]
        
        return PredictionResult(
            race_id=race_detail.race_info.race_id,
            rankings=rankings,
            scores=scores,
            confidence=0.82,
            betting_recommendations=[]
        )
```

---

## 並列処理の活用

### 🔄 マルチプロセッシング

```python
from multiprocessing import Pool, cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

class ParallelPredictor:
    """並列処理対応予想エンジン"""
    
    def __init__(self):
        self.max_workers = min(cpu_count(), 8)  # CPU数に応じて調整
    
    def predict_multiple_races(self, race_details: List[RaceDetail]) -> List[PredictionResult]:
        """複数レースの並列予想"""
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 並列タスクを投入
            future_to_race = {
                executor.submit(self._predict_single_race, race): race
                for race in race_details
            }
            
            results = []
            for future in as_completed(future_to_race):
                race = future_to_race[future]
                try:
                    result = future.result(timeout=30)  # 30秒タイムアウト
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"並列予想エラー {race.race_info.race_id}: {e}")
                    results.append(None)
        
        end_time = time.time()
        self.logger.info(f"並列予想完了: {len(race_details)}レース, {end_time - start_time:.2f}秒")
        
        return results
    
    def _predict_single_race(self, race_detail: RaceDetail) -> PredictionResult:
        """単一レースの予想（プロセス内実行）"""
        # 各プロセスで独立して実行される
        predictor = KeirinPredictor()
        return predictor.predict_race(race_detail)

# 使用例
async def batch_prediction_example():
    """バッチ予想の実行例"""
    fetcher = OptimizedDataFetcher()
    predictor = ParallelPredictor()
    
    # 本日の全レース取得
    races = await fetcher.get_today_races()
    race_ids = [race.race_id for race in races[:10]]  # 最初の10レース
    
    # 並列でレース詳細取得
    race_details = await fetcher.get_multiple_races_async(race_ids)
    
    # 並列で予想実行
    valid_details = [detail for detail in race_details if detail is not None]
    predictions = predictor.predict_multiple_races(valid_details)
    
    return predictions
```

---

## 監視・プロファイリング

### 📊 パフォーマンス監視

アプリケーションのパフォーマンスは、`config/settings.py` で定義された `PERFORMANCE_CONFIG` に基づいて監視されます。この設定により、監視間隔や各種リソース使用率の閾値を柔軟に調整できます。

#### `PERFORMANCE_CONFIG` の主要設定項目

```python
PERFORMANCE_CONFIG: Dict[str, Any] = {
    "monitor_interval": 10, # 監視間隔（秒）
    "cpu_warning_threshold": 70, # CPU使用率警告閾値 (%)
    "cpu_critical_threshold": 90, # CPU使用率危険閾値 (%)
    "memory_warning_threshold_mb": 512, # メモリ使用量警告閾値 (MB)
    "memory_critical_threshold_mb": 1024, # メモリ使用量危険閾値 (MB)
    "cache_hit_rate_warning_threshold": 0.5, # キャッシュヒット率警告閾値 (0.0-1.0)
    "cache_hit_rate_critical_threshold": 0.3 # キャッシュヒット率危険閾値 (0.0-1.0)
}
```

これらの設定は、CLIの「設定・管理」メニューから「設定変更」を選択し、「パフォーマンス監視設定」を編集することで、実行中に変更し永続化することが可能です。

#### `PerformanceMonitor` クラス

システムリソース（CPU、メモリ）、キャッシュヒット率、アクティブスレッド数、応答時間などを定期的に収集し、履歴として保持します。収集されたデータは `logs/performance_metrics.json` に保存されます。

##### `start_monitoring(interval: int = PERFORMANCE_CONFIG['monitor_interval'])`
パフォーマンス監視を開始します。`interval` はメトリクス収集の間隔を秒単位で指定します。デフォルトは `PERFORMANCE_CONFIG` から読み込まれます。

##### `stop_monitoring()`
パフォーマンス監視を停止します。

##### `get_performance_report(minutes: int = 10) -> Dict`
指定された期間（分）のパフォーマンスレポートを生成します。CPU使用率、メモリ使用量、キャッシュヒット率、応答時間などの統計情報が含まれます。システムの状態（`healthy`, `warning`, `critical`, `unknown`）も判定されます。

#### `performance_timer` デコレータ

任意の関数の実行時間を計測し、`PerformanceMonitor` に記録するためのデコレータです。これにより、アプリケーション内の特定の処理のパフォーマンスを詳細に追跡できます。

```python
from utils.performance import performance_timer

@performance_timer("data_fetch_operation")
def fetch_data_from_api():
    # データ取得処理
    pass
```

### 🔍 プロファイリングツール

```python
import cProfile
import pstats
from functools import wraps
import io

class ProfileManager:
    """プロファイリング管理"""
    
    @staticmethod
    def profile_function(func):
        """関数プロファイリングデコレータ"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            pr = cProfile.Profile()
            pr.enable()
            
            result = func(*args, **kwargs)
            
            pr.disable()
            
            # プロファイル結果を文字列として取得
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)  # 上位20件表示
            
            profile_output = s.getvalue()
            print(f"\n📊 プロファイル結果 - {func.__name__}:")
            print(profile_output)
            
            return result
        return wrapper
    
    @staticmethod
    def profile_race_prediction():
        """レース予想のプロファイリング実行"""
        from data.models import create_sample_race
        
        @ProfileManager.profile_function
        def run_prediction():
            race_detail = create_sample_race()
            predictor = KeirinPredictor()
            return predictor.predict_race(race_detail)
        
        return run_prediction()

# 使用例
if __name__ == "__main__":
    # パフォーマンス監視開始
    performance_monitor.start_monitoring()
    
    try:
        # プロファイリング実行
        result = ProfileManager.profile_race_prediction()
        
        # パフォーマンスレポート表示
        time.sleep(30)  # 30秒間のメトリクス収集
        report = performance_monitor.get_performance_report()
        print("\n📈 パフォーマンスレポート:")
        print(f"平均CPU使用率: {report.get('avg_cpu_percent', 0):.1f}%")
        print(f"平均メモリ使用量: {report.get('avg_memory_mb', 0):.1f}MB")
        print(f"キャッシュヒット率: {report.get('avg_cache_hit_rate', 0):.1%}")
        
    finally:
        performance_monitor.stop_monitoring()
```

---

## 最適化の実装例

### 🚀 統合最適化システム

```python
class OptimizedKeirinSystem:
    """最適化された競輪予想システム"""
    
    def __init__(self):
        self.fetcher = OptimizedDataFetcher()
        self.predictor = OptimizedPredictor()
        self.cache = OptimizedCacheManager()
        self.monitor = PerformanceMonitor()
        
        # 最適化設定
        self.config = {
            "enable_parallel_processing": True,
            "max_concurrent_predictions": 5,
            "cache_preload_enabled": True,
            "memory_optimization": True
        }
    
    async def initialize(self):
        """システム初期化"""
        # パフォーマンス監視開始
        self.monitor.start_monitoring()
        
        # キャッシュの事前読み込み
        if self.config["cache_preload_enabled"]:
            await self._preload_cache()
    
    async def _preload_cache(self):
        """キャッシュ事前読み込み"""
        try:
            # よく使用されるデータを事前にキャッシュ
            today_races = await self.fetcher.get_today_races()
            self.cache.set("today_races_preloaded", today_races, "race_info", 1800)
            
            # 人気競輪場のデータも事前取得
            popular_venues = ["平塚", "川崎", "大宮", "西武園"]
            for venue in popular_venues:
                venue_races = await self.fetcher.get_races_by_venue(venue)
                self.cache.set(f"venue_races_{venue}", venue_races, "race_info", 3600)
                
        except Exception as e:
            self.logger.error(f"キャッシュ事前読み込みエラー: {e}")
    
    @performance_timer
    async def predict_optimized(self, race_id: str) -> PredictionResult:
        """最適化された予想実行"""
        # 1. キャッシュ確認
        cached_prediction = self.cache.get(f"prediction_{race_id}")
        if cached_prediction:
            return cached_prediction
        
        # 2. レース詳細取得（キャッシュ付き）
        race_detail = await self.fetcher.get_race_detail_cached(race_id)
        if not race_detail:
            raise ValueError(f"レース詳細が取得できません: {race_id}")
        
        # 3. 予想実行（最適化版）
        prediction = self.predictor.predict_race_optimized(race_detail)
        
        # 4. 結果をキャッシュ
        self.cache.set(f"prediction_{race_id}", prediction, "prediction", 1800)
        
        return prediction
    
    async def batch_predict_optimized(self, race_ids: List[str]) -> List[PredictionResult]:
        """最適化されたバッチ予想"""
        if self.config["enable_parallel_processing"]:
            return await self._parallel_batch_predict(race_ids)
        else:
            return await self._sequential_batch_predict(race_ids)
    
    async def _parallel_batch_predict(self, race_ids: List[str]) -> List[PredictionResult]:
        """並列バッチ予想"""
        semaphore = asyncio.Semaphore(self.config["max_concurrent_predictions"])
        
        async def predict_with_semaphore(race_id):
            async with semaphore:
                return await self.predict_optimized(race_id)
        
        tasks = [predict_with_semaphore(race_id) for race_id in race_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外処理
        predictions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"予想エラー {race_ids[i]}: {result}")
                predictions.append(None)
            else:
                predictions.append(result)
        
        return predictions
    
    def get_optimization_stats(self) -> Dict:
        """最適化統計情報"""
        performance_report = self.monitor.get_performance_report()
        cache_info = self.cache.get_cache_info()
        
        return {
            "performance": performance_report,
            "cache": cache_info,
            "optimization_config": self.config,
            "system_status": "optimal" if performance_report.get("avg_cpu_percent", 100) < 80 else "high_load"
        }

# 使用例
async def main():
    system = OptimizedKeirinSystem()
    await system.initialize()
    
    try:
        # 単一予想
        prediction = await system.predict_optimized("20241205_平塚_01")
        print(f"予想完了: {prediction.rankings[0]}番が1位")
        
        # バッチ予想
        race_ids = ["20241205_平塚_01", "20241205_平塚_02", "20241205_川崎_01"]
        predictions = await system.batch_predict_optimized(race_ids)
        print(f"バッチ予想完了: {len([p for p in predictions if p])}件成功")
        
        # 最適化統計表示
        stats = system.get_optimization_stats()
        print(f"システム状態: {stats['system_status']}")
        print(f"キャッシュヒット率: {stats['cache'].get('hit_rate', 0):.1%}")
        
    finally:
        system.monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 今後の最適化計画

### Phase 1: 基本最適化（実装済み）
- ✅ L1/L2キャッシュシステム
- ✅ データベースインデックス
- ✅ 接続プール最適化

### Phase 2: 高度最適化（計画中）
- 🔄 機械学習モデルの最適化
- 🔄 分散キャッシュシステム
- 🔄 CDN活用

### Phase 3: スケール最適化（将来）
- 📅 水平スケーリング対応
- 📅 マイクロサービス化
- 📅 リアルタイムストリーミング

---

*最終更新: 2025年8月5日*
*バージョン: v1.0.0*
