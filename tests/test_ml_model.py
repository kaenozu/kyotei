"""
MLモデル動作テスト
選手成績データ取得とML予想の動作確認
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ml_model():
    """MLモデルとデータ取得の動作テスト"""
    print("=" * 60)
    print("MLモデルとデータ取得動作テスト")
    print("=" * 60)
    
    try:
        from data.teikoku_simple_fetcher import teikoku_simple_fetcher
        
        # 1. 最新レースを1つ取得
        print("1. レース取得テスト")
        races = teikoku_simple_fetcher.get_today_races()
        if not races:
            print("   エラー: レースが取得できません")
            return False
            
        test_race = races[0]  # 最初のレース
        print(f"   テスト対象: {test_race.venue_name} {test_race.race_number}R")
        
        # 2. レース詳細取得
        print("2. レース詳細取得テスト")
        race_detail = teikoku_simple_fetcher.get_race_detail(test_race.race_id)
        if not race_detail:
            print("   エラー: レース詳細が取得できません")
            return False
            
        print(f"   選手数: {len(race_detail.racers)}人")
        
        # 3. 選手成績データ確認
        print("3. 選手成績データ確認")
        stats_count = 0
        for racer in race_detail.racers:
            if racer.stats and racer.stats.total_races > 0:
                stats_count += 1
                print(f"   OK {racer.name}: 勝率{racer.stats.win_rate:.1f}% (出走{racer.stats.total_races}回)")
            else:
                print(f"   NG {racer.name}: 成績データなし")
        
        print(f"   成績データ取得率: {stats_count}/{len(race_detail.racers)} ({stats_count/len(race_detail.racers)*100:.1f}%)")
        
        # 4. 気象データ確認
        print("4. 気象データ確認")
        if race_detail.weather_info:
            weather = race_detail.weather_info
            print(f"   OK 風速: {weather.wind_speed}m/s {weather.wind_direction}")
            print(f"   OK 気温: {weather.temperature}°C")
            print(f"   OK 風影響: {weather.wind_impact_score:.2f}")
        else:
            print("   NG 気象データなし")
        
        # 5. MLモデル予想テスト
        print("5. MLモデル予想テスト")
        try:
            from prediction.simple_predictor import teikoku_predictor
            
            print("   ML予想実行中...")
            prediction = teikoku_predictor.predict_race_ml(race_detail)
            
            if prediction:
                print(f"   OK ML予想成功: 推奨単勝{prediction.recommended_win}号艇")
                print(f"   OK 信頼度: {prediction.confidence:.1%}")
                print("   OK 各艇予想確率:")
                for racer_num, prob in prediction.predictions.items():
                    racer = next((r for r in race_detail.racers if r.number == racer_num), None)
                    racer_name = racer.name if racer else f"{racer_num}号艇"
                    print(f"      {racer_num}号艇 {racer_name}: {prob:.1%}")
                
                return True
            else:
                print("   NG ML予想失敗")
                return False
                
        except Exception as e:
            print(f"   NG ML予想エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ml_model()
    
    print(f"\n" + "=" * 60)
    print("【テスト結果】")
    print("=" * 60)
    
    if success:
        print("OK MLモデルが正常に動作しています")
        print("   - 選手成績データの取得状況を確認してください")
        print("   - ML予想が成功している場合、システムは実データに基づいて動作中")
    else:
        print("NG MLモデルに問題があります")
        print("   - 選手成績データの取得に問題がある可能性")
        print("   - MLモデルの特徴量に不整合がある可能性")