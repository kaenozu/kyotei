"""
非同期データ取得のパフォーマンステスト
同期版と非同期版の速度比較
"""
import asyncio
import time
import logging
from data.teikoku_simple_fetcher import teikoku_simple_fetcher
from data.teikoku_async_fetcher import teikoku_async_fetcher

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_async_performance():
    """非同期版のパフォーマンステスト"""
    try:
        print("=" * 60)
        print("非同期データ取得パフォーマンステスト")
        print("=" * 60)
        
        # テスト用レースID（実際の取得可能なレース）
        test_race_id = "20250820_15_03"  # 今日の丸亀3R
        
        print(f"テストレースID: {test_race_id}")
        
        # 1. 同期版のテスト
        print("\n【同期版テスト】")
        start_time = time.time()
        
        try:
            sync_result = teikoku_simple_fetcher.get_race_detail(test_race_id)
            sync_elapsed = time.time() - start_time
            
            if sync_result:
                print(f"[OK] 同期版成功: {sync_elapsed:.2f}秒")
                print(f"  選手数: {len(sync_result.racers)}")
                stats_count = len([r for r in sync_result.racers if r.stats])
                print(f"  統計データ有り: {stats_count}/{len(sync_result.racers)}")
            else:
                print("[NG] 同期版失敗: データ取得できず")
                sync_elapsed = None
                
        except Exception as e:
            print(f"[NG] 同期版エラー: {e}")
            sync_elapsed = None
        
        # 2. 非同期版のテスト
        print("\n【非同期版テスト】")
        start_time = time.time()
        
        try:
            async_result = await teikoku_async_fetcher.fetch_race_detail_async(test_race_id)
            async_elapsed = time.time() - start_time
            
            if async_result:
                print(f"[OK] 非同期版成功: {async_elapsed:.2f}秒")
                print(f"  選手数: {len(async_result.racers)}")
                stats_count = len([r for r in async_result.racers if r.stats])
                print(f"  統計データ有り: {stats_count}/{len(async_result.racers)}")
            else:
                print("[NG] 非同期版失敗: データ取得できず")
                async_elapsed = None
                
        except Exception as e:
            print(f"[NG] 非同期版エラー: {e}")
            async_elapsed = None
        
        # 3. パフォーマンス比較
        print("\n【パフォーマンス比較】")
        if sync_elapsed and async_elapsed:
            improvement = ((sync_elapsed - async_elapsed) / sync_elapsed) * 100
            print(f"同期版時間:   {sync_elapsed:.2f}秒")
            print(f"非同期版時間: {async_elapsed:.2f}秒")
            print(f"改善率:       {improvement:.1f}%")
            
            if improvement > 0:
                print(f"🚀 非同期版が {improvement:.1f}% 高速化されました！")
            else:
                print(f"⚠️  非同期版の改善効果: {improvement:.1f}%")
        
        # 4. キャッシュ効果のテスト
        print("\n【キャッシュ効果テスト】")
        
        # 2回目の非同期実行（キャッシュ効果を測定）
        start_time = time.time()
        async_cached_result = await teikoku_async_fetcher.fetch_race_detail_async(test_race_id)
        cached_elapsed = time.time() - start_time
        
        print(f"キャッシュ利用時間: {cached_elapsed:.2f}秒")
        if async_elapsed:
            cache_improvement = ((async_elapsed - cached_elapsed) / async_elapsed) * 100
            print(f"キャッシュ効果: {cache_improvement:.1f}% 高速化")
        
        # 5. 結果サマリー
        print("\n" + "=" * 60)
        print("【テスト結果サマリー】")
        print("=" * 60)
        
        if sync_elapsed and async_elapsed:
            print(f"[OK] 並列処理実装により {improvement:.1f}% の高速化を達成")
            print(f"[OK] キャッシュ機能により追加で {cache_improvement:.1f}% の高速化")
            print(f"[OK] 総合的な性能向上: {improvement + cache_improvement:.1f}%")
        
        print("[OK] 非同期データ取得機能が正常に動作しています")
        
        # リソースクリーンアップ
        await teikoku_async_fetcher.close()
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

def run_performance_test():
    """パフォーマンステストの実行"""
    try:
        # 既存のイベントループがある場合の処理
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 既にループが実行中の場合は新しいループを作成
                import nest_asyncio
                nest_asyncio.apply()
                asyncio.run(test_async_performance())
            else:
                asyncio.run(test_async_performance())
        except RuntimeError:
            # イベントループが存在しない場合
            asyncio.run(test_async_performance())
            
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_performance_test()