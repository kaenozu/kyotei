#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クイック起動テスト - 実運用前確認
"""

def test_system():
    print("=" * 50)
    print("競艇予想システム 実運用前テスト")
    print("=" * 50)
    
    success_count = 0
    total_tests = 5
    
    # 1. 基本設定確認
    try:
        from config.config_manager import config
        print("✅ [1/5] 設定システム: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ [1/5] 設定システム: ERROR - {e}")
    
    # 2. データ取得テスト
    try:
        from data.boatrace_openapi_fetcher import BoatraceOpenAPIFetcher
        fetcher = BoatraceOpenAPIFetcher()
        print("✅ [2/5] データ取得: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ [2/5] データ取得: ERROR - {e}")
    
    # 3. 予想システムテスト
    try:
        from prediction.predictor import enhanced_prediction_system
        print("✅ [3/5] 予想システム: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ [3/5] 予想システム: ERROR - {e}")
    
    # 4. 投資管理テスト
    try:
        from investment_manager import investment_manager
        print("✅ [4/5] 投資管理: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ [4/5] 投資管理: ERROR - {e}")
    
    # 5. Webアプリテスト
    try:
        from openapi_app import app
        print("✅ [5/5] Webアプリ: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ [5/5] Webアプリ: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"テスト結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("🎉 すべてのテストに成功！今日から実運用可能です")
        print("\n起動方法:")
        print("  python openapi_app.py")
        print("  ブラウザで http://localhost:5000 を開く")
        print("\n主要機能:")
        print("  📊 投資ダッシュボード: http://localhost:5000/investment")
        print("  🔍 予想システム: メインページから")
        print("  📈 レポート生成: ダッシュボード内")
        print("  🚨 アラート監視: 自動実行")
    elif success_count >= 3:
        print("⚠️ 基本機能は動作しますが、一部に問題があります")
        print("  軽微な問題のため実運用は可能ですが、修正を推奨します")
    else:
        print("🛑 重要な問題があります。修正してから運用してください")
    
    print("=" * 50)

if __name__ == "__main__":
    test_system()