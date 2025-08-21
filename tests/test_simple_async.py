"""
非同期データ取得の簡単なテスト
"""
import asyncio
import time
import sys
import os

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.teikoku_async_fetcher import teikoku_async_fetcher

async def simple_test():
    """簡単な非同期テスト"""
    print("非同期データ取得テスト開始")
    
    # テスト用レースID
    race_id = "20250820_15_03"  # 丸亀3R
    
    print(f"テストレースID: {race_id}")
    
    start_time = time.time()
    
    try:
        # 非同期でレース詳細を取得
        result = await teikoku_async_fetcher.fetch_race_detail_async(race_id)
        
        elapsed = time.time() - start_time
        
        if result:
            print(f"成功: {elapsed:.2f}秒で取得完了")
            print(f"会場: {result.race_info.venue_name}")
            print(f"レース: {result.race_info.race_number}R")
            print(f"選手数: {len(result.racers)}")
            
            for i, racer in enumerate(result.racers, 1):
                stats_status = "統計有" if racer.stats else "統計無"
                print(f"  {i}号艇: {racer.name} ({stats_status})")
        else:
            print("データ取得失敗")
    
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # リソースクリーンアップ
        await teikoku_async_fetcher.close()

def run_test():
    """テスト実行"""
    try:
        asyncio.run(simple_test())
    except Exception as e:
        print(f"テスト実行エラー: {e}")

if __name__ == "__main__":
    run_test()