#!/usr/bin/env python3
"""
レース結果取得テスト
"""

import logging
from scripts.modules.api_fetcher import SimpleOpenAPIFetcher

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_result_fetching():
    """結果取得テスト"""
    
    # 今日のレース例でテスト（結果確定済み）
    test_cases = [
        (2, 1, "2025-08-22"),   # 戸田1R
        (3, 1, "2025-08-22"),   # 江戸川1R  
        (12, 1, "2025-08-22"),   # 住之江1R
    ]
    
    for venue_id, race_number, race_date in test_cases:
        print(f"\n{'='*50}")
        print(f"テスト: {venue_id}会場 {race_number}R ({race_date})")
        print(f"{'='*50}")
        
        try:
            result = race_result_fetcher.get_race_result(venue_id, race_number, race_date)
            
            if result:
                print(f"[OK] 結果取得成功!")
                print(f"   着順: {result.finish_order}")
                print(f"   出典: {result.source}")
                print(f"   勝ち時間: {result.win_time}")
                print(f"   天候: {result.weather}")
            else:
                print(f"[NG] 結果取得失敗")
                
        except Exception as e:
            print(f"[ERR] エラー: {e}")

if __name__ == "__main__":
    test_result_fetching()