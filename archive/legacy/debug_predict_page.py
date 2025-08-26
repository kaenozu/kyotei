#!/usr/bin/env python3
"""
予測ページ表示問題デバッグ
ページが表示されない原因特定
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def test_predict_page():
    """予測ページテスト"""
    print("=== 予測ページ表示問題デバッグ ===")
    
    base_url = "http://127.0.0.1:5000"
    
    print(f"\n[1] メインページアクセステスト")
    try:
        response = requests.get(f"{base_url}/", timeout=30)
        print(f"メインページステータス: {response.status_code}")
        print(f"レスポンス長: {len(response.text)}")
        
        # HTMLからrace-cardクラスの有無を確認
        if "race-card" in response.text:
            print("レースカードが存在します")
            
            # race_idを抽出
            import re
            # ボタンのonclick属性からrace_idを抽出
            race_ids = re.findall(r'onclick[^>]*predict/([^"\']+)', response.text)
            print(f"利用可能なrace_id: {race_ids[:10]}")  # 最初の10個
            
            # 終了したレースの確認
            finished_count = response.text.count("race-card") - len(race_ids)
            print(f"総レース数: {response.text.count('race-card')}, 予想可能: {len(race_ids)}, 終了: {finished_count}")
            
            if race_ids:
                # 最初のrace_idで予想テスト
                test_race_id = race_ids[0]
                print(f"\n[2] 予想ページテスト: {test_race_id}")
                
                predict_response = requests.get(f"{base_url}/predict/{test_race_id}", timeout=60)
                print(f"予想ページステータス: {predict_response.status_code}")
                print(f"予想ページサイズ: {len(predict_response.text)}")
                
                if predict_response.status_code == 200:
                    if "レーサー" in predict_response.text or "予想" in predict_response.text:
                        print("[SUCCESS] 予想ページが正常に表示されています")
                    else:
                        print("[ERROR] 予想ページの内容が不完全です")
                        print("最初の1000文字:")
                        print(predict_response.text[:1000])
                elif predict_response.status_code == 500:
                    print("[ERROR] サーバーエラーが発生しています")
                    print("エラー内容:")
                    print(predict_response.text[:1000])
                else:
                    print(f"[ERROR] 予期しないステータス: {predict_response.status_code}")
            else:
                print("[ERROR] 予想可能なレースIDが見つかりません（全て終了?）")
                # 終了判定時刻を確認
                time_matches = re.findall(r'開始時刻[^0-9]*(\d{1,2}:\d{2})', response.text)
                print(f"開始時刻リスト: {time_matches[:5]}")
                current_time = datetime.now().strftime("%H:%M")
                print(f"現在時刻: {current_time}")
        else:
            print("[ERROR] メインページにレースカードがありません")
            print("ページの最初の1000文字:")
            print(response.text[:1000].encode('ascii', 'ignore').decode('ascii'))
    
    except requests.exceptions.Timeout:
        print("[ERROR] リクエストタイムアウト - サーバーが応答しません")
    except requests.exceptions.ConnectionError:
        print("[ERROR] 接続エラー - サーバーが起動していない可能性があります")
    except Exception as e:
        print(f"[ERROR] 予期しないエラー: {e}")
    
    print(f"\n[3] APIエンドポイントテスト")
    try:
        # システム状態確認（存在しないAPIなので省略）
        pass
    
    except Exception as e:
        print(f"[ERROR] API テストエラー: {e}")

def test_template_files():
    """テンプレートファイル確認"""
    print(f"\n[4] テンプレートファイル確認")
    
    template_files = [
        "templates/openapi_index.html",
        "templates/openapi_predict.html"
    ]
    
    for template_file in template_files:
        if os.path.exists(template_file):
            file_size = os.path.getsize(template_file)
            print(f"OK {template_file}: {file_size} bytes")
            
            # 基本的な内容チェック
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'openapi_predict.html' in template_file:
                    if '{{ racers }}' in content:
                        print("  OK racers変数テンプレート存在")
                    if '{{ predictions }}' in content:
                        print("  OK predictions変数テンプレート存在")
                    if '{{ confidence }}' in content:
                        print("  OK confidence変数テンプレート存在")
                
            except Exception as e:
                print(f"  [ERROR] {template_file} 読み込みエラー: {e}")
        else:
            print(f"NG {template_file}: ファイルが存在しません")

def main():
    """メイン実行"""
    print("競艇予想システム - 予測ページ表示問題デバッグ")
    print("=" * 60)
    
    test_predict_page()
    test_template_files()
    
    print("\n" + "=" * 60)
    print("デバッグ完了")
    
    print("\n--- 解決方法 ---")
    print("1. サーバーが正常に動作していることを確認")
    print("2. テンプレートファイルの存在確認")
    print("3. 予想処理でエラーが発生していないか確認")
    print("4. ブラウザのキャッシュをクリア")

if __name__ == "__main__":
    main()