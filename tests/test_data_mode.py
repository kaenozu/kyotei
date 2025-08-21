#!/usr/bin/env python3
"""
データモード機能のテストスクリプト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.factory import create_data_fetcher, get_data_source_status
from config.settings import get_setting, set_setting
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_mode_settings():
    """データモード設定のテスト"""
    print("=== データモード設定テスト ===")
    
    # 現在の設定を表示
    data_mode = get_setting("DATA_MODE")
    print(f"現在のDATA_MODE設定: {data_mode}")
    
    # データソース状態を表示
    status = get_data_source_status()
    print(f"データソース状態: {status}")
    
    return True

def test_factory_creation():
    """ファクトリーによるフェッチャー作成テスト"""
    print("\n=== ファクトリーテスト ===")
    
    try:
        fetcher = create_data_fetcher()
        print(f"フェッチャー作成成功: {type(fetcher).__name__}")
        
        # ハイブリッドフェッチャーの場合、状態情報を取得
        if hasattr(fetcher, 'get_data_source_status'):
            status = fetcher.get_data_source_status()
            print(f"フェッチャー状態: {status}")
        
        return True
    except Exception as e:
        print(f"フェッチャー作成失敗: {e}")
        return False

def test_mock_mode():
    """モックモードテスト"""
    print("\n=== モックモードテスト ===")
    
    # モックモードに設定
    original_setting = get_setting("DATA_MODE")
    test_setting = original_setting.copy()
    test_setting["use_real_data"] = False
    set_setting("DATA_MODE", test_setting)
    
    try:
        fetcher = create_data_fetcher()
        print(f"モックモード フェッチャー: {type(fetcher).__name__}")
        
        # 簡単なデータ取得テスト
        if hasattr(fetcher, 'get_races_today'):
            races = fetcher.get_races_today()
            print(f"今日のレース数: {len(races)}")
            if races:
                print(f"最初のレース: {races[0].venue} {races[0].race_number}R")
        
        return True
    except Exception as e:
        print(f"モックモードテスト失敗: {e}")
        return False
    finally:
        # 設定を元に戻す
        set_setting("DATA_MODE", original_setting)

def test_real_mode():
    """実データモードテスト"""
    print("\n=== 実データモードテスト ===")
    
    # 実データモードに設定
    original_setting = get_setting("DATA_MODE")
    test_setting = original_setting.copy()
    test_setting["use_real_data"] = True
    set_setting("DATA_MODE", test_setting)
    
    try:
        fetcher = create_data_fetcher()
        print(f"実データモード フェッチャー: {type(fetcher).__name__}")
        
        # 実際のデータ取得は時間がかかるので、フェッチャーが正しく初期化されたかのみ確認
        if hasattr(fetcher, 'get_data_source_status'):
            status = fetcher.get_data_source_status()
            print(f"実データモード状態: {status}")
        
        return True
    except Exception as e:
        print(f"実データモードテスト失敗: {e}")
        return False
    finally:
        # 設定を元に戻す
        set_setting("DATA_MODE", original_setting)

def main():
    """メインテスト実行"""
    print("データモード機能テスト開始")
    
    tests = [
        test_data_mode_settings,
        test_factory_creation,
        test_mock_mode,
        test_real_mode
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("OK テスト成功")
            else:
                failed += 1
                print("NG テスト失敗")
        except Exception as e:
            failed += 1
            print(f"NG テスト例外: {e}")
        print("-" * 50)
    
    print(f"\n=== テスト結果 ===")
    print(f"成功: {passed}")
    print(f"失敗: {failed}")
    print(f"合計: {passed + failed}")
    
    if failed == 0:
        print("すべてのテストが成功しました！")
    else:
        print(f"{failed}個のテストが失敗しました")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)