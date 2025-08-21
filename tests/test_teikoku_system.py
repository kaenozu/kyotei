"""
艇国データバンクシステムのテスト
"""
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)

from data.teikoku_simple_fetcher import teikoku_simple_fetcher
from prediction.simple_predictor import teikoku_predictor


def test_system():
    """システム全体のテスト"""
    print("=" * 60)
    print("艇国データバンク競艇予想システム テスト")
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
            for race in races[:3]:  # 最初の3件を表示
                print(f"  - {race.venue_name} {race.race_number}R ({race.race_id})")
        else:
            print("レースが取得できませんでした")
            return
            
    except Exception as e:
        print(f"レース取得エラー: {e}")
        return
    
    # 3. レース詳細取得テスト
    print("\n3. レース詳細取得テスト")
    print("-" * 30)
    
    try:
        test_race = races[0]  # 最初のレースでテスト
        print(f"テスト対象: {test_race.venue_name} {test_race.race_number}R")
        
        race_detail = teikoku_simple_fetcher.get_race_detail(test_race.race_id)
        
        if race_detail:
            print("レース詳細取得成功")
            print(f"  会場: {race_detail.race_info.venue_name}")
            print(f"  レース: {race_detail.race_info.race_number}R")
            print(f"  選手数: {len(race_detail.racers)}名")
            
            print("\n  出走選手:")
            for racer in race_detail.racers:
                print(f"    {racer.number}号艇: {racer.name} (実力{racer.estimated_strength:.1%})")
        else:
            print("レース詳細取得失敗")
            return
            
    except Exception as e:
        print(f"レース詳細取得エラー: {e}")
        return
    
    # 4. 予想テスト
    print("\n4. AI予想テスト")
    print("-" * 30)
    
    try:
        prediction = teikoku_predictor.predict_race(race_detail)
        
        print("予想実行成功")
        print(f"  レースID: {prediction.race_id}")
        print(f"  信頼度: {prediction.confidence:.1%}")
        print(f"  単勝推奨: {prediction.recommended_win}号艇")
        print(f"  複勝推奨: {prediction.recommended_place}")
        
        print("\n  選手別予想勝率:")
        for number, prob in prediction.predictions.items():
            racer = race_detail.get_racer_by_number(number)
            name = racer.name if racer else f"選手{number}"
            print(f"    {number}号艇 {name}: {prob:.1%}")
            
    except Exception as e:
        print(f"予想エラー: {e}")
        return
    
    # 5. 予想結果フォーマットテスト
    print("\n5. 予想結果表示テスト")
    print("-" * 30)
    
    try:
        formatted_result = teikoku_predictor.format_prediction_result(prediction, race_detail)
        print(formatted_result)
        print("\n予想結果表示成功")
        
    except Exception as e:
        print(f"予想結果表示エラー: {e}")
        return
    
    # 6. 総合結果
    print("\n" + "=" * 60)
    print("総合テスト結果")
    print("=" * 60)
    print("全ての機能が正常に動作しています")
    print()
    print("システムの特徴:")
    print("- 艇国データバンクから実際の選手名を取得")
    print("- 艇番有利度による基本予想")
    print("- 選手名特徴分析による実力推定")
    print("- 会場・時間帯特性の考慮")
    print()
    print("制限事項:")
    print("- オッズ情報なし")
    print("- 詳細な成績データなし")
    print("- 基本的な傾向分析のみ")
    print()
    print("予想精度: 限定的データによる基本予想レベル")


if __name__ == "__main__":
    test_system()