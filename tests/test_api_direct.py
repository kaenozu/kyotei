"""
APIキー直接テスト
"""
import os
import requests
import sys

def test_api_direct():
    """APIキーを直接指定してテスト"""
    api_key = "c7061dec04482c59adac681ec01cc970"
    
    print("=" * 50)
    print("OpenWeatherMap API直接テスト")
    print("=" * 50)
    print(f"APIキー: {api_key[:8]}...")
    
    try:
        # 東京の天気でテスト
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': 35.6762,
            'lon': 139.6503,
            'appid': api_key,
            'units': 'metric',
            'lang': 'ja'
        }
        
        print("\nAPI接続テスト中...")
        response = requests.get(url, params=params, timeout=10)
        
        print(f"HTTPステータス: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[成功] API接続成功!")
            print(f"  都市: {data.get('name', '不明')}")
            print(f"  天気: {data.get('weather', [{}])[0].get('description', '不明')}")
            print(f"  気温: {data.get('main', {}).get('temp', 0):.1f}度C")
            print(f"  風速: {data.get('wind', {}).get('speed', 0):.1f}m/s")
            print(f"  風向: {data.get('wind', {}).get('deg', 0):.0f}度")
            print(f"  湿度: {data.get('main', {}).get('humidity', 0)}%")
            
            # 環境変数に設定
            os.environ['OPENWEATHER_API_KEY'] = api_key
            print(f"\n[設定] 環境変数に一時設定完了")
            
            return True
            
        elif response.status_code == 401:
            print("[失敗] APIキーが無効です")
            print("原因: キーが間違っているか、まだ有効化されていません")
            return False
        else:
            print(f"[失敗] HTTPエラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"[エラー] 接続失敗: {e}")
        return False

def test_kyotei_weather():
    """競艇システムでの気象テスト"""
    print("\n" + "=" * 50)
    print("競艇システム気象データテスト")
    print("=" * 50)
    
    try:
        # 競艇システムの気象モジュールをテスト
        sys.path.append('.')
        from data.weather_fetcher import weather_fetcher
        
        # 江戸川の気象データを取得
        venue_id = "03"  # 江戸川
        weather_info = weather_fetcher.get_weather_info(venue_id)
        
        if weather_info:
            print(f"[成功] {weather_info.venue_name}の気象データ取得")
            print(f"  風速: {weather_info.wind_speed:.1f}m/s")
            print(f"  風向: {weather_info.wind_direction}")
            print(f"  気温: {weather_info.temperature:.1f}度C")
            print(f"  湿度: {weather_info.humidity:.0f}%")
            print(f"  天候: {weather_info.weather_condition}")
            print(f"  風影響度: {weather_info.wind_impact_score:.2f}")
            print(f"  天候影響度: {weather_info.weather_impact_score:.2f}")
            
            print("\n[結果] 競艇システムで気象データが正常に取得できています!")
            return True
        else:
            print("[失敗] 競艇システムでの気象データ取得に失敗")
            return False
            
    except Exception as e:
        print(f"[エラー] 競艇システムテスト失敗: {e}")
        return False

if __name__ == "__main__":
    # APIテスト
    api_success = test_api_direct()
    
    if api_success:
        # 競艇システムテスト
        kyotei_success = test_kyotei_weather()
        
        if kyotei_success:
            print("\n" + "=" * 50)
            print("🎉 API設定完了! 気象データが有効になりました!")
            print("=" * 50)
            print("効果:")
            print("- リアルタイム風速・風向データ")
            print("- 正確な気温・湿度情報")
            print("- 予想精度5-15%向上期待")
            print("- 気象条件を考慮した高精度予想")
            
            print("\n次のステップ:")
            print("1. python test_weather_accuracy.py で全会場テスト")
            print("2. 実際のレース予想で効果確認")
            print("3. 予想精度データ分析")
        else:
            print("\n[警告] APIは動作しますが、システム統合に問題があります")
    else:
        print("\n[失敗] API設定に問題があります")
        print("対策:")
        print("1. APIキーの確認")
        print("2. 2時間待機（新規キーの場合）")
        print("3. ネットワーク接続確認")