#!/usr/bin/env python3
"""
BoatraceOpenAPI専用システム動作テスト
"""

import requests
import sys
import os
from datetime import datetime

def test_openapi_direct():
    """OpenAPI直接アクセステスト"""
    print("=== BoatraceOpenAPI 直接テスト ===")
    
    try:
        api_url = "https://boatraceopenapi.github.io/programs/v2/today.json"
        print(f"API URL: {api_url}")
        
        response = requests.get(api_url, timeout=10)
        print(f"ステータス: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            programs = data.get('programs', [])
            print(f"取得レース数: {len(programs)}")
            
            if programs:
                # 最初のレースの詳細を表示
                first_race = programs[0]
                print(f"\n--- サンプルレース ---")
                print(f"会場: {first_race.get('race_stadium_name')}")
                print(f"レース番号: {first_race.get('race_number')}R")
                print(f"締切時刻: {first_race.get('race_closed_at')}")
                print(f"距離: {first_race.get('race_distance')}m")
                
                boats = first_race.get('boats', [])
                print(f"選手数: {len(boats)}")
                
                for i, boat in enumerate(boats[:3], 1):  # 最初の3艇のみ表示
                    print(f"  {i}号艇: {boat.get('racer_name', '不明')} (勝率: {boat.get('racer_national_top_1_percent', 0):.1f}%)")
                
                print("[OK] OpenAPI正常動作確認")
                return True
            else:
                print("[WARN] プログラムデータが空です")
                return False
        else:
            print(f"[ERROR] API取得失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] エラー発生: {e}")
        return False

def test_local_app():
    """ローカルアプリテスト"""
    print("\n=== ローカルアプリテスト ===")
    
    try:
        # メインページテスト
        response = requests.get("http://localhost:5000/", timeout=5)
        print(f"メインページ: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] メインページ正常動作")
        
        # テストページ
        response = requests.get("http://localhost:5000/test", timeout=5)
        print(f"テストページ: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] テストページ正常動作")
        
        # API テスト
        response = requests.get("http://localhost:5000/api/races", timeout=5)
        print(f"API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"[OK] API正常動作 - {data.get('total_races', 0)}レース")
            else:
                print(f"[WARN] API エラー: {data.get('error')}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("[WARN] ローカルアプリが起動していません")
        print("python openapi_app.py を実行してからテストしてください")
        return False
    except Exception as e:
        print(f"[ERROR] ローカルアプリテストエラー: {e}")
        return False

def show_usage():
    """使用方法表示"""
    print("\n=== BoatraceOpenAPI専用システム ===")
    print("1. 依存関係インストール:")
    print("   pip install -r requirements_openapi.txt")
    print()
    print("2. システム起動:")
    print("   python openapi_app.py")
    print()
    print("3. ブラウザアクセス:")
    print("   http://localhost:5000")
    print()
    print("4. 機能:")
    print("   - 今日のレース一覧表示")
    print("   - レース詳細と予想表示")
    print("   - BoatraceOpenAPIキャッシュ機能")
    print("   - シンプルなレスポンシブデザイン")

if __name__ == "__main__":
    print("=" * 50)
    print("BoatraceOpenAPI専用システム テスト")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # OpenAPI直接テスト
    openapi_ok = test_openapi_direct()
    
    # ローカルアプリテスト（オプション）
    if len(sys.argv) > 1 and sys.argv[1] == "--app":
        app_ok = test_local_app()
    else:
        app_ok = None
        print("\n--- アプリテストをスキップ ---")
        print("アプリテストを実行するには: python test_openapi_simple.py --app")
    
    # 結果まとめ
    print("\n" + "=" * 50)
    print("テスト結果:")
    print(f"OpenAPI接続: {'[OK] 正常' if openapi_ok else '[ERROR] 失敗'}")
    if app_ok is not None:
        print(f"ローカルアプリ: {'[OK] 正常' if app_ok else '[ERROR] 失敗'}")
    
    if openapi_ok:
        print("\n[OK] BoatraceOpenAPI専用システム準備完了!")
        show_usage()
    else:
        print("\n[ERROR] OpenAPI接続に問題があります")
        print("インターネット接続を確認してください")
    
    print("=" * 50)