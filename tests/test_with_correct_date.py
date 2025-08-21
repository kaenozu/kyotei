"""
正しい日付でのテスト
2024年の日付を使用してレースデータ取得をテスト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.teikoku_simple_fetcher import teikoku_simple_fetcher
from datetime import datetime

def test_with_correct_date():
    """正しい日付でのテスト"""
    print("=" * 60)
    print("正しい日付（2024年）でのレースデータテスト")
    print("=" * 60)
    
    # 2024年の実際の競艇開催日をテスト
    test_dates = [
        "20240820",  # 2024年8月20日
        "20240819",  # 2024年8月19日
        "20240821",  # 2024年8月21日
        "20240815",  # 2024年8月15日
    ]
    
    for date_str in test_dates:
        print(f"\n【日付: {date_str}】")
        print(f"年月日: {date_str[:4]}年{date_str[4:6]}月{date_str[6:8]}日")
        
        try:
            # 手動でレースIDを作成
            test_race_ids = [
                f"{date_str}_03_06",  # 江戸川6R
                f"{date_str}_04_04",  # 平和島4R
                f"{date_str}_12_05",  # 住之江5R
            ]
            
            for race_id in test_race_ids:
                print(f"\n  レースID: {race_id}")
                
                # レース詳細取得をテスト
                race_detail = teikoku_simple_fetcher.get_race_detail(race_id)
                
                if race_detail and race_detail.racers:
                    print(f"    [成功] {race_detail.race_info.venue_name} {race_detail.race_info.race_number}R")
                    print(f"    選手数: {len(race_detail.racers)}名")
                    
                    # 選手名をチェック
                    for i, racer in enumerate(race_detail.racers[:3], 1):
                        print(f"      {i}号艇: {racer.name}")
                    
                    # 重複チェック
                    names = [racer.name for racer in race_detail.racers]
                    unique_names = set(names)
                    if len(unique_names) < len(names):
                        print(f"    [警告] 選手名に重複があります")
                    else:
                        print(f"    [OK] 選手名は正常です")
                    
                    return True  # 成功したらテスト終了
                    
                else:
                    print(f"    [失敗] レース詳細が取得できませんでした")
                    
        except Exception as e:
            print(f"    [エラー] {e}")
    
    print(f"\n[結果] 全ての日付でデータ取得に失敗しました")
    return False

def test_direct_url_access():
    """直接URL アクセステスト"""
    print(f"\n" + "=" * 60)
    print("【直接URLアクセステスト】")
    print("=" * 60)
    
    import requests
    from bs4 import BeautifulSoup
    import time
    
    # 2024年の日付でテスト
    date_str = "20240820"
    venue_id = "03"
    race_number = "06"
    
    base_url = "https://boatrace-db.net"
    
    # 複数のURLパターンをテスト
    url_patterns = [
        f"{base_url}/race/races/date/{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}/venue/{venue_id}/number/{race_number}",
        f"{base_url}/owrt/{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}/{venue_id}/{int(race_number):02d}",
        f"{base_url}/race/{date_str}/{venue_id}/{race_number}",
        f"{base_url}/races/{date_str}/{venue_id}/{race_number}",
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    for i, url in enumerate(url_patterns, 1):
        print(f"\nパターン{i}: {url}")
        
        try:
            time.sleep(1)
            response = session.get(url, timeout=10)
            print(f"  ステータス: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  [成功] データ取得")
                
                # HTMLを簡単に解析
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title')
                if title:
                    print(f"  タイトル: {title.get_text()[:50]}...")
                
                # 選手名らしきデータを探す
                import re
                japanese_names = re.findall(r'[一-龯]{2,4}', response.text)
                unique_names = list(set(japanese_names))[:10]
                if unique_names:
                    print(f"  選手名候補: {unique_names[:5]}")
                
                print(f"  [結果] このURLパターンが有効な可能性があります")
                return url
                
            elif response.status_code == 404:
                print(f"  [失敗] 404 Not Found")
            else:
                print(f"  [失敗] HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [エラー] {e}")
    
    return None

def propose_solution():
    """解決策の提案"""
    print(f"\n" + "=" * 60)
    print("【解決策の提案】")
    print("=" * 60)
    
    print("問題:")
    print("1. システム日付が2025年になっている")
    print("2. 艇国データバンクのURLパターンが変更された可能性")
    print("3. アクセス制限やサイト構造変更")
    
    print(f"\n解決策:")
    print("1. 日付を2024年に修正")
    print("2. 有効なURLパターンの特定")
    print("3. モックデータでの一時的対応")
    print("4. 代替データソースの検討")
    
    print(f"\n即座の対応:")
    print("1. テスト用の実在選手名データを使用")
    print("2. システム日付の手動修正")
    print("3. URLパターンの更新")

if __name__ == "__main__":
    success = test_with_correct_date()
    
    if not success:
        working_url = test_direct_url_access()
        if working_url:
            print(f"\n有効なURL発見: {working_url}")
        else:
            print(f"\n有効なURLが見つかりませんでした")
    
    propose_solution()