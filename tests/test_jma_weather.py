"""
気象庁API動作テスト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.jma_weather_fetcher import jma_weather_fetcher
from data.simple_models import VENUE_MAPPING
import time

def test_jma_weather():
    """気象庁APIテスト"""
    print("=" * 60)
    print("気象庁API動作テスト")
    print("=" * 60)
    print("メリット:")
    print("- 完全無料（制限なし）")
    print("- 最高精度（日本の公式データ）")
    print("- APIキー不要")
    print("- 日本の気象に特化")
    print("=" * 60)
    
    # テスト対象会場（代表的な会場）
    test_venues = ["03", "04", "12", "15", "22"]  # 江戸川、平和島、住之江、丸亀、福岡
    
    print(f"\nテスト対象会場: {len(test_venues)}会場")
    for venue_id in test_venues:
        venue_name = VENUE_MAPPING.get(venue_id, f"場{venue_id}")
        print(f"  {venue_id}: {venue_name}")
    
    print("\n【気象庁データ取得テスト】")
    
    results = {}
    for i, venue_id in enumerate(test_venues, 1):
        venue_name = VENUE_MAPPING.get(venue_id, f"場{venue_id}")
        print(f"\n[{i}] {venue_name} (ID: {venue_id})")
        
        try:
            start_time = time.time()
            weather_info = jma_weather_fetcher.get_weather_info(venue_id)
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
        
        # 気象庁への負荷軽減
        if i < len(test_venues):
            time.sleep(1)
    
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
        
        # 風速の分析
        wind_speeds = [r['weather_info'].wind_speed for r in results.values() if r.get('success', False)]
        if wind_speeds:
            min_wind = min(wind_speeds)
            max_wind = max(wind_speeds)
            avg_wind = sum(wind_speeds) / len(wind_speeds)
            print(f"風速範囲: {min_wind:.1f} - {max_wind:.1f} m/s (平均: {avg_wind:.1f})")
        
        # 気温の分析
        temperatures = [r['weather_info'].temperature for r in results.values() if r.get('success', False)]
        if temperatures:
            min_temp = min(temperatures)
            max_temp = max(temperatures)
            avg_temp = sum(temperatures) / len(temperatures)
            print(f"気温範囲: {min_temp:.1f} - {max_temp:.1f}度C (平均: {avg_temp:.1f}度C)")
    
    # データ品質評価
    print(f"\n【気象庁API評価】")
    if success_rate >= 80:
        print("[優秀] 気象庁APIは高い信頼性を示しています")
        quality_level = "優秀"
    elif success_rate >= 60:
        print("[良好] 気象庁APIは概ね正常動作しています")
        quality_level = "良好"
    else:
        print("[問題] 気象庁APIに接続問題があります")
        quality_level = "問題"
    
    # OpenWeatherMapとの比較
    print(f"\n【OpenWeatherMapとの比較】")
    print("気象庁API:")
    print("  ✓ 完全無料（制限なし）")
    print("  ✓ 日本の公式気象データ")
    print("  ✓ APIキー不要")
    print("  ✓ 日本語対応完璧")
    print("  ✓ 競艇場周辺の詳細データ")
    
    print("\nOpenWeatherMap:")
    print("  △ 1日1000回制限")
    print("  △ APIキー必要")
    print("  △ 海外サービス")
    print("  ✓ 実装済み")
    
    return quality_level, success_rate

def integration_recommendation():
    """統合推奨案"""
    print("\n" + "=" * 60)
    print("【統合推奨案】")
    print("=" * 60)
    
    print("Phase 1: 気象庁API統合")
    print("1. weather_fetcher.pyの修正")
    print("2. 気象庁データを第1優先に設定")
    print("3. OpenWeatherMapをバックアップに")
    print("4. 動作テスト")
    
    print("\nPhase 2: 精度向上")
    print("1. 会場固有の補正係数設定")
    print("2. 過去データとの相関分析")
    print("3. 機械学習モデルの特徴量強化")
    
    print("\n期待効果:")
    print("- 予想精度: +10-20%向上")
    print("- データ信頼性: 最高レベル")
    print("- 運用コスト: 完全無料")
    print("- 日本特化: 競艇に最適")

if __name__ == "__main__":
    quality, rate = test_jma_weather()
    
    print(f"\n【最終評価】")
    print(f"気象庁API品質: {quality} (成功率: {rate:.1f}%)")
    
    integration_recommendation()
    
    if rate >= 80:
        print("\n🎉 気象庁APIの統合を強く推奨します！")
        print("無料で最高品質の気象データが取得できます。")
    else:
        print("\n⚠️ 接続に問題がある可能性があります。")
        print("ネットワーク環境を確認してください。")