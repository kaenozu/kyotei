"""
ハードコーディング除去後のシステムテスト
艇国データバンクから実際に取得できるデータのみを使用
"""
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)

from data.teikoku_simple_fetcher import teikoku_simple_fetcher


def test_no_hardcode():
    """ハードコーディングなしのシステムテスト"""
    print("=" * 60)
    print("ハードコーディング除去後テスト")
    print("艇国データバンクから実際に取得できるデータのみを使用")
    print("=" * 60)
    
    # 1. 接続テスト
    print("\n1. 接続テスト")
    print("-" * 30)
    
    if teikoku_simple_fetcher.test_connection():
        print("艇国データバンクへの接続成功")
    else:
        print("接続失敗")
        return
    
    # 2. レース一覧取得テスト
    print("\n2. 今日のレース一覧取得テスト")
    print("-" * 30)
    
    try:
        races = teikoku_simple_fetcher.get_today_races()
        print(f"レース取得成功: {len(races)}件")
        
        if races:
            print("\n取得されたレース:")
            for race in races[:3]:
                print(f"  - {race.venue_name} {race.race_number}R ({race.race_id})")
        else:
            print("レースが取得できませんでした")
            return
            
    except Exception as e:
        print(f"レース取得エラー: {e}")
        return
    
    # 3. 実際のデータ取得テスト（複数のレースで試行）
    print("\n3. 実際の選手データ取得テスト")
    print("-" * 30)
    
    success_count = 0
    total_tests = min(5, len(races))  # 最大5件テスト
    
    for i, test_race in enumerate(races[:total_tests]):
        print(f"\nテスト {i+1}/{total_tests}: {test_race.venue_name} {test_race.race_number}R")
        
        try:
            race_detail = teikoku_simple_fetcher.get_race_detail(test_race.race_id)
            
            if race_detail and race_detail.racers:
                print(f"  成功: {len(race_detail.racers)}名の選手データを取得")
                print(f"  選手名: {[r.name for r in race_detail.racers]}")
                success_count += 1
                
                # ハードコーディングチェック
                hardcoded_names = ['峰竜太', '松井繁', '瓜生正義', '石野貴之', '茅原悠紀', '池田浩二']
                found_hardcoded = [name for name in hardcoded_names 
                                 if any(name in racer.name for racer in race_detail.racers)]
                
                if found_hardcoded:
                    print(f"  ⚠️ ハードコーディングされた名前が検出: {found_hardcoded}")
                else:
                    print("  ✓ ハードコーディングされた名前は検出されませんでした")
                    
            else:
                print("  失敗: 実際のデータが取得できませんでした")
                
        except Exception as e:
            print(f"  エラー: {e}")
    
    # 4. 結果まとめ
    print(f"\n" + "=" * 60)
    print("テスト結果まとめ")
    print("=" * 60)
    print(f"総テスト数: {total_tests}")
    print(f"成功数: {success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    
    if success_count == 0:
        print("\n結論: 現在の艇国データバンクからは実際の選手データが取得できません")
        print("- レース詳細ページへのアクセスに問題がある可能性")
        print("- 選手名抽出ロジックに問題がある可能性")
        print("- サイト構造が変更された可能性")
        print("\n対策: 艇国データバンクのサイト構造を再調査が必要")
    elif success_count < total_tests:
        print(f"\n結論: 部分的に実際のデータが取得できています ({success_count}/{total_tests})")
        print("- 一部のレースでは実データ取得が成功")
        print("- レースによって取得可能性が異なる")
    else:
        print("\n結論: 全てのテストで実際のデータ取得に成功")
        print("- ハードコーディングを完全に除去")
        print("- 艇国データバンクからの実データのみを使用")
    
    print("\nシステムの制約:")
    print("- 実際のデータが取得できない場合、予想は実行できません")
    print("- ハードコーディングされたデータは一切使用しません")
    print("- 艇国データバンクから取得できるデータのみに依存")


if __name__ == "__main__":
    test_no_hardcode()