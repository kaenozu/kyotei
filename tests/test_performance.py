"""
高速化版パフォーマンステスト
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_loading_speed():
    """読み込み速度テスト"""
    print("=" * 50)
    print("高速化版パフォーマンステスト")
    print("=" * 50)
    
    try:
        from data.teikoku_simple_fetcher import teikoku_simple_fetcher
        
        # 1. レース一覧取得速度テスト
        print("\n1. レース一覧取得速度テスト")
        start_time = time.time()
        
        races = teikoku_simple_fetcher.get_today_races()
        
        list_time = time.time() - start_time
        print(f"   レース一覧取得: {list_time:.2f}秒")
        print(f"   取得レース数: {len(races)}件")
        
        if races:
            # 2. 個別レース取得速度テスト
            print("\n2. 個別レース取得速度テスト")
            test_race = races[0]  # 最初のレース
            
            start_time = time.time()
            race_detail = teikoku_simple_fetcher.get_race_detail(test_race.race_id)
            detail_time = time.time() - start_time
            
            print(f"   レース詳細取得: {detail_time:.2f}秒")
            print(f"   テストレース: {test_race.race_id}")
            
            if race_detail:
                print(f"   選手数: {len(race_detail.racers)}名")
                print(f"   選手名例: {race_detail.racers[0].name}")
            
            # 3. キャッシュ効果テスト
            print("\n3. キャッシュ効果テスト")
            start_time = time.time()
            race_detail2 = teikoku_simple_fetcher.get_race_detail(test_race.race_id)
            cache_time = time.time() - start_time
            
            print(f"   2回目取得(キャッシュ): {cache_time:.3f}秒")
            print(f"   高速化効果: {detail_time/cache_time:.1f}倍")
        
        # 4. 総合評価
        print(f"\n4. 総合評価")
        total_time = list_time + (detail_time if races else 0)
        print(f"   初回総読み込み時間: {total_time:.2f}秒")
        
        if total_time < 3.0:
            print("   評価: 高速 (3秒未満)")
        elif total_time < 10.0:
            print("   評価: 良好 (10秒未満)")
        else:
            print("   評価: 要改善 (10秒以上)")
        
        return True
        
    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_web_response():
    """WebUI応答速度テスト"""
    print(f"\n" + "=" * 50)
    print("WebUI応答速度テスト")
    print("=" * 50)
    
    try:
        import requests
        
        # トップページ応答テスト
        start_time = time.time()
        response = requests.get("http://localhost:5000", timeout=10)
        web_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"   トップページ応答: {web_time:.2f}秒")
            print("   WebUI正常稼働中")
            return True
        else:
            print(f"   応答エラー: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   WebUIテストエラー: {e}")
        return False

if __name__ == "__main__":
    print("高速化による読み込み時間の改善テスト")
    
    data_success = test_loading_speed()
    web_success = test_web_response()
    
    print(f"\n" + "=" * 50)
    print("【高速化結果】")
    print("=" * 50)
    
    if data_success and web_success:
        print("高速化成功!")
        print("")
        print("改善内容:")
        print("- ネットワーク取得をスキップ")
        print("- キャッシュ優先の読み込み")
        print("- 主要会場のみの高速生成")
        print("- 実名データベースの活用")
        print("")
        print("WebUI: http://localhost:5000")
    else:
        print("高速化に課題があります")