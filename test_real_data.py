#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
実データ取得テストスクリプト
"""
import sys
import os
from pathlib import Path

# Windows環境での文字化け対策
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.real_fetcher import real_fetcher
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_real_data_fetching():
    """実データ取得テスト"""
    print("=== 競艇実データ取得テスト ===")
    
    # 接続テスト
    print("1. 接続テスト中...")
    if real_fetcher.test_connection():
        print("✅ 競艇公式サイトへの接続成功")
    else:
        print("❌ 競艇公式サイトへの接続失敗")
        return
    
    # 実データ取得テスト
    print("\n2. 本日のレース情報取得中...")
    try:
        races = real_fetcher.get_today_races()
        
        if races:
            print(f"✅ 実データ取得成功: {len(races)}件のレース")
            
            print("\n=== 取得されたレース情報 ===")
            for i, race in enumerate(races[:5], 1):  # 最初の5件のみ表示
                print(f"{i}. {race.venue} {race.race_number}R")
                print(f"   発走時刻: {race.start_time.strftime('%H:%M')}")
                print(f"   レースID: {race.race_id}")
                print(f"   状態: {race.status}")
                print()
                
            if len(races) > 5:
                print(f"... 他 {len(races) - 5}件")
                
        else:
            print("❌ レースデータが取得できませんでした")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_data_fetching()