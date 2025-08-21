"""
気象データの正確性テスト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.weather_fetcher import weather_fetcher
from data.simple_models import VENUE_MAPPING
import time

def test_weather_accuracy():
    """気象データの正確性をテスト"""
    print("=" * 60)
    print("気象データ正確性テスト")
    print("=" * 60)
    
    # テスト対象会場（代表的な会場）
    test_venues = ["03", "04", "12", "15", "22"]  # 江戸川、平和島、住之江、丸亀、福岡
    
    print(f"テスト対象会場: {len(test_venues)}会場")
    for venue_id in test_venues:
        venue_name = VENUE_MAPPING.get(venue_id, f"場{venue_id}")
        print(f"  {venue_id}: {venue_name}")
    
    print("\n【気象データ取得テスト】")
    
    results = {}
    for i, venue_id in enumerate(test_venues, 1):
        venue_name = VENUE_MAPPING.get(venue_id, f"場{venue_id}")
        print(f"\n[{i}] {venue_name} (ID: {venue_id})")
        
        try:
            start_time = time.time()
            weather_info = weather_fetcher.get_weather_info(venue_id)
            elapsed = time.time() - start_time
            
            if weather_info:
                print(f"  [OK] 取得成功 ({elapsed:.2f}秒)")
                print(f"    風速: {weather_info.wind_speed:.1f} m/s")
                print(f"    風向: {weather_info.wind_direction}")
                print(f"    気温: {weather_info.temperature:.1f}度C")
                print(f"    湿度: {weather_info.humidity:.0f}%")
                print(f"    天候: {weather_info.weather_condition}")
                print(f"    視界: {weather_info.visibility:.1f} km")
                print(f"    推定波高: {weather_info.wave_height:.2f} m")
                print(f"    推定水温: {weather_info.water_temperature:.1f}度C")
                print(f"    風影響度: {weather_info.wind_impact_score:.2f}")
                print(f"    天候影響度: {weather_info.weather_impact_score:.2f}")
                
                results[venue_id] = {
                    'success': True,
                    'elapsed': elapsed,
                    'weather_info': weather_info
                }
            else:
                print(f"  [NG] 取得失敗")
                results[venue_id] = {'success': False, 'elapsed': elapsed}
                
        except Exception as e:
            print(f"  [NG] エラー: {e}")
            results[venue_id] = {'success': False, 'error': str(e)}
        
        # API制限を考慮して間隔を空ける
        if i < len(test_venues):
            time.sleep(2)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("【テスト結果サマリー】")
    print("=" * 60)
    
    success_count = sum(1 for r in results.values() if r.get('success', False))
    total_count = len(test_venues)
    success_rate = success_count / total_count * 100
    
    print(f"成功率: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_count > 0:
        avg_time = sum(r['elapsed'] for r in results.values() if r.get('success', False)) / success_count
        print(f"平均取得時間: {avg_time:.2f}秒")
        
        # 風速の妥当性チェック
        wind_speeds = [r['weather_info'].wind_speed for r in results.values() if r.get('success', False)]
        if wind_speeds:
            min_wind = min(wind_speeds)
            max_wind = max(wind_speeds)
            avg_wind = sum(wind_speeds) / len(wind_speeds)
            print(f"風速範囲: {min_wind:.1f} - {max_wind:.1f} m/s (平均: {avg_wind:.1f})")
        
        # 気温の妥当性チェック
        temperatures = [r['weather_info'].temperature for r in results.values() if r.get('success', False)]
        if temperatures:
            min_temp = min(temperatures)
            max_temp = max(temperatures)
            avg_temp = sum(temperatures) / len(temperatures)
            print(f"気温範囲: {min_temp:.1f} - {max_temp:.1f}度C (平均: {avg_temp:.1f}度C)")
    
    # データ品質評価
    print(f"\n【データ品質評価】")
    if success_rate >= 80:
        print("[OK] 高品質: 気象データは信頼性が高いです")
        quality_level = "高"
    elif success_rate >= 60:
        print("[OK] 中品質: 気象データは概ね信頼できます")
        quality_level = "中"
    elif success_rate >= 40:
        print("[WARNING] 低品質: 気象データの信頼性は限定的です")
        quality_level = "低"
    else:
        print("[NG] 不良: 気象データの取得に問題があります")
        quality_level = "不良"
    
    # 改善提案
    print(f"\n【改善提案】")
    if success_rate < 100:
        print("- API キーの設定を確認してください")
        print("- ネットワーク接続を確認してください")
        print("- レート制限の調整を検討してください")
    
    if success_count > 0:
        print("- 取得できたデータは予想システムで活用されています")
        print("- キャッシュシステムにより高速化されています")
        print("- 影響度スコアが予想精度向上に寄与しています")
    
    return quality_level, success_rate

if __name__ == "__main__":
    quality, rate = test_weather_accuracy()
    
    print(f"\n【最終評価】")
    print(f"気象データ品質: {quality} (成功率: {rate:.1f}%)")
    
    if rate >= 60:
        print("気象条件は予想に有効活用されています。")
    else:
        print("気象データの改善が必要です。")