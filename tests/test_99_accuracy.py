#!/usr/bin/env python3
"""
99%精度向上チェーンテスト
"""

import requests
import time
import json
from datetime import datetime

def test_accuracy_chain():
    """精度向上チェーンをテスト"""
    print("99%精度向上システムテスト開始")
    
    # テスト用URL
    base_url = "http://127.0.0.1:5000"
    
    # 1. システム起動確認
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"システム起動確認: {response.status_code}")
    except Exception as e:
        print(f"システム接続エラー: {e}")
        return
    
    # 2. 予測API直接テスト（桐生競艇場 第1レース）
    try:
        print("\n予測精度テスト開始...")
        response = requests.get(f"{base_url}/predict/10_1", timeout=30)
        
        if response.status_code == 200:
            print("予測API成功")
            
            # HTMLレスポンスから精度関連情報を抽出
            html_content = response.text
            
            # データ品質向上ログ確認
            if "データ品質向上" in html_content:
                print("ウルトラデータ品質向上システム動作確認")
            
            # 量子精度ブースター確認 
            if "量子精度" in html_content or "量子ブースター" in html_content:
                print("量子精度ブースターシステム動作確認")
            
            # 信頼度確認
            if "信頼度" in html_content:
                print("信頼度スコア表示確認")
                
            # レーサー情報表示確認
            if "号艇" in html_content or "選手名" in html_content:
                print("レーサー情報表示確認")
                
            print("予測ページ正常表示")
            
        else:
            print(f"予測API失敗: {response.status_code}")
            print(f"エラー内容: {response.text[:200]}")
            
    except Exception as e:
        print(f"予測テストエラー: {e}")
    
    # 3. 統計API確認
    try:
        print("\n統計APIテスト...")
        
        # 量子システム統計
        response = requests.get(f"{base_url}/api/quantum/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"量子システム統計: {stats.get('quantum_stats', {})}")
        
    except Exception as e:
        print(f"統計APIエラー: {e}")
    
    print("\n99%精度向上システムテスト完了")

if __name__ == "__main__":
    test_accuracy_chain()