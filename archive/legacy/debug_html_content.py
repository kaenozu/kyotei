#!/usr/bin/env python3
"""
HTMLコンテンツ詳細デバッグ
race_idリンクが生成されているか確認
"""

import requests
import re

def debug_html_content():
    """HTMLコンテンツ詳細確認"""
    print("=== HTMLコンテンツ詳細デバッグ ===")
    
    try:
        response = requests.get("http://127.0.0.1:5000/", timeout=30)
        html_content = response.text
        
        print(f"レスポンスサイズ: {len(html_content)} bytes")
        
        # race-cardクラスの数
        race_cards = re.findall(r'<div class="race-card[^>]*>', html_content)
        print(f"race-cardの数: {len(race_cards)}")
        
        # finishedクラス付きの数
        finished_cards = re.findall(r'<div class="race-card[^>]*finished[^>]*>', html_content)
        print(f"finishedクラス付き: {len(finished_cards)}")
        
        # predict-btnの数
        predict_buttons = re.findall(r'<button[^>]*class="predict-btn"[^>]*>', html_content)
        print(f"predict-btnの数: {len(predict_buttons)}")
        
        # predictリンクを全て抽出
        predict_links = re.findall(r'href="/predict/([^"]+)"', html_content)
        print(f"predictリンク: {predict_links[:10]}")  # 最初の10個
        
        # レース情報の一部を抽出
        venues = re.findall(r'<div class="race-venue">([^<]+)</div>', html_content)
        print(f"会場リスト: {venues[:10]}")
        
        # race_idが含まれるボタンのHTMLを検索
        button_pattern = r'<button[^>]*onclick[^>]*predict/([^"\']+)[^>]*>'
        button_matches = re.findall(button_pattern, html_content)
        print(f"ボタン内race_id: {button_matches[:10]}")
        
        # 最初のrace-cardを詳細表示
        first_card_match = re.search(r'<div class="race-card[^>]*>.*?</div>\s*</div>', html_content, re.DOTALL)
        if first_card_match:
            print(f"\n最初のレースカードHTML（500文字）:")
            print(first_card_match.group(0)[:500])
        
        # 終了ステータスバッジの数
        status_badges = html_content.count('<div class="status-badge">終了</div>')
        print(f"\n終了バッジ数: {status_badges}")
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    debug_html_content()