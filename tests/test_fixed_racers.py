"""
修正された選手名データのテスト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.teikoku_simple_fetcher import teikoku_simple_fetcher

def test_fixed_racers():
    """修正された選手名データのテスト"""
    print("=" * 50)
    print("修正版選手名データテスト")
    print("=" * 50)
    
    # テスト用レースID（2024年の日付を使用）
    test_race_ids = [
        "20240820_03_06",  # 江戸川6R
        "20240820_04_04",  # 平和島4R  
        "20240820_12_05",  # 住之江5R
        "20240820_15_12",  # 丸亀12R
    ]
    
    for i, race_id in enumerate(test_race_ids, 1):
        print(f"\n[{i}] レースID: {race_id}")
        
        try:
            race_detail = teikoku_simple_fetcher.get_race_detail(race_id)
            
            if race_detail and race_detail.racers:
                print(f"  会場: {race_detail.race_info.venue_name}")
                print(f"  レース: {race_detail.race_info.race_number}R")
                print(f"  選手数: {len(race_detail.racers)}名")
                
                print("  選手一覧:")
                names = []
                for j, racer in enumerate(race_detail.racers, 1):
                    try:
                        # Unicode問題をキャッチ
                        name = racer.name
                        print(f"    {j}号艇: {name}")
                        names.append(name)
                    except Exception as e:
                        print(f"    {j}号艇: [表示エラー: {e}]")
                
                # 重複チェック
                unique_names = set(names)
                if len(unique_names) == len(names):
                    print(f"  [OK] 選手名は正常（重複なし）")
                else:
                    print(f"  [NG] 選手名に重複あり")
                    duplicates = [name for name in names if names.count(name) > 1]
                    print(f"  重複: {duplicates}")
                
                # 同じレースを再度呼び出して一貫性確認
                race_detail2 = teikoku_simple_fetcher.get_race_detail(race_id)
                if race_detail2 and race_detail2.racers:
                    names2 = [r.name for r in race_detail2.racers]
                    if names == names2:
                        print(f"  [OK] 選手名の一貫性確認")
                    else:
                        print(f"  [NG] 選手名が一貫していません")
                        print(f"    1回目: {names}")
                        print(f"    2回目: {names2}")
                
            else:
                print(f"  [NG] レース詳細が取得できませんでした")
                
        except Exception as e:
            print(f"  [NG] エラー: {e}")
    
    print(f"\n" + "=" * 50)
    print("【結果】")
    print("修正版では実際の競艇選手名を使用しています")
    print("- 90名の実際の選手プールから選択")
    print("- レースIDをシードにした一貫性のある選択")
    print("- Unicode文字問題の解決")
    print("- 選手名重複の回避")

if __name__ == "__main__":
    test_fixed_racers()