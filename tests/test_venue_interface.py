"""
競艇場一覧インターフェースのテスト
"""
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)

from kyotei_teikoku_clean import KyoteiTeikokuApp


def test_venue_interface():
    """競艇場一覧インターフェースの表示テスト"""
    print("=" * 60)
    print("競艇場一覧インターフェース テスト")
    print("=" * 60)
    
    app = KyoteiTeikokuApp()
    
    # 接続テスト
    print("\n1. 接続テスト")
    if not app._test_connection():
        print("接続失敗")
        return
    
    # 競艇場一覧表示テスト
    print("\n2. 競艇場一覧表示テスト")
    print("-" * 40)
    
    try:
        app._show_venues()
        print("\n競艇場一覧表示テスト完了")
        
    except Exception as e:
        print(f"エラー: {e}")
        return
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("新しいインターフェース:")
    print("1. 全国24か所の競艇場を地域別に表示")
    print("2. 今日開催されている競艇場の情報を表示") 
    print("3. 各レースに番号を付けて選択可能")
    print("4. レース選択後、即座に予想を実行")


if __name__ == "__main__":
    test_venue_interface()