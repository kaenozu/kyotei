"""
単一レースのテスト - 問題の特定
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.teikoku_simple_fetcher import teikoku_simple_fetcher
from prediction.simple_predictor import teikoku_predictor

def test_single_race():
    """単一レースのテスト"""
    print("=" * 50)
    print("単一レーステスト - 同期版")
    print("=" * 50)
    
    # テスト対象のレースID
    test_race_id = "20250820_03_04"  # 江戸川4R
    
    try:
        print(f"テスト対象: {test_race_id}")
        
        # 1. 同期版でレース詳細取得
        print("\n【1. 同期版でレース詳細取得】")
        race_detail = teikoku_simple_fetcher.get_race_detail(test_race_id)
        
        if race_detail:
            print(f"[OK] レース詳細取得成功")
            print(f"[INFO] 会場: {race_detail.race_info.venue_name}")
            print(f"[INFO] レース: {race_detail.race_info.race_number}R")
            print(f"[INFO] 選手数: {len(race_detail.racers)}名")
            
            # 選手情報表示
            for i, racer in enumerate(race_detail.racers[:3], 1):
                print(f"[INFO] {i}号艇: {racer.name}")
            
            # 2. 予想実行テスト
            print("\n【2. 予想実行テスト】")
            prediction = teikoku_predictor.predict_race(race_detail)
            
            if prediction:
                print(f"[OK] 予想実行成功")
                print(f"[INFO] 推奨単勝: {prediction.recommended_win}号艇")
                print(f"[INFO] 信頼度: {prediction.confidence:.2f}")
                print(f"[INFO] 推奨複勝: {prediction.recommended_place}")
                
                # 各艇の勝率表示
                print("\n【予想勝率】")
                for number in sorted(prediction.predictions.keys()):
                    prob = prediction.predictions[number]
                    print(f"  {number}号艇: {prob:.3f}")
                
                return True
            else:
                print("[NG] 予想実行失敗")
                return False
        else:
            print("[NG] レース詳細取得失敗")
            
            # デバッグ: 利用可能なレース再確認
            print("\n【デバッグ: 利用可能レース確認】")
            races = teikoku_simple_fetcher.get_today_races()
            
            if races:
                print(f"利用可能なレース数: {len(races)}")
                # 最初の5レースを表示
                for race in races[:5]:
                    print(f"  {race.race_id}: {race.venue_name} {race.race_number}R")
                    
                # 指定したレースIDが存在するかチェック
                target_race = None
                for race in races:
                    if race.race_id == test_race_id:
                        target_race = race
                        break
                
                if target_race:
                    print(f"\n[INFO] 対象レース発見: {target_race.venue_name} {target_race.race_number}R")
                    print(f"[INFO] ステータス: {target_race.status}")
                    print(f"[INFO] 時刻: {target_race.start_time}")
                else:
                    print(f"\n[WARNING] 対象レース({test_race_id})が一覧に存在しません")
            
            return False
            
    except Exception as e:
        print(f"[NG] テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_race()
    
    if success:
        print("\n[結果] 同期版は正常に動作しています")
        print("Web UI URL: http://localhost:5000/predict/20250820_03_04")
    else:
        print("\n[結果] 問題が発生しています。ログを確認してください。")