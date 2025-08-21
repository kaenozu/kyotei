#!/usr/bin/env python3
"""
システムエラー修正のテストスクリプト
"""
import sys
import asyncio
import logging

# UTF-8エンコーディング設定
sys.stdout.reconfigure(encoding='utf-8')

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_async_fetcher_import():
    """非同期フェッチャーのインポートテスト"""
    try:
        from data.teikoku_async_fetcher import teikoku_async_fetcher
        logger.info("✅ 非同期フェッチャーインポート成功")
        return True
    except Exception as e:
        logger.error(f"❌ 非同期フェッチャーインポート失敗: {e}")
        return False

def test_session_management():
    """セッション管理のテスト"""
    try:
        from data.teikoku_async_fetcher import TeikokuAsyncFetcher
        
        async def session_test():
            fetcher = TeikokuAsyncFetcher()
            try:
                # セッション取得テスト
                session = await fetcher._get_session()
                logger.info("✅ セッション取得成功")
                
                # クリーンアップ
                await fetcher.close()
                logger.info("✅ セッションクローズ成功")
                return True
            except Exception as e:
                logger.error(f"❌ セッション管理テスト失敗: {e}")
                return False
        
        # 非同期テストの実行
        result = asyncio.run(session_test())
        return result
        
    except Exception as e:
        logger.error(f"❌ セッション管理テスト失敗: {e}")
        return False

def test_event_loop_handling():
    """イベントループハンドリングのテスト"""
    try:
        # 既存のイベントループチェック
        try:
            loop = asyncio.get_running_loop()
            logger.info("⚠️ 既存のイベントループが検出されました")
            return False
        except RuntimeError:
            logger.info("✅ イベントループが実行されていません（正常）")
            return True
            
    except Exception as e:
        logger.error(f"❌ イベントループハンドリングテスト失敗: {e}")
        return False

def test_race_selection():
    """レース選択機能のテスト"""
    print("=" * 60)
    print("レース選択機能テスト")
    print("=" * 60)
    
    try:
        # レース一覧取得
        print("1. レース一覧取得中...")
        races = teikoku_simple_fetcher.get_today_races()
        print(f"取得成功: {len(races)}件のレース")
        
        # 最初のレースで予想テスト
        if races:
            test_race = races[0]
            print(f"\n2. テスト対象: {test_race.venue_name} {test_race.race_number}R")
            
            # レース詳細取得
            race_detail = teikoku_simple_fetcher.get_race_detail(test_race.race_id)
            
            if race_detail:
                print("レース詳細取得成功")
                print(f"選手数: {len(race_detail.racers)}名")
                
                # 予想実行
                prediction = teikoku_predictor.predict_race(race_detail)
                print("予想実行成功")
                
                # 簡易結果表示
                print(f"\n=== 予想結果 ===")
                print(f"レース: {race_detail.race_info.venue_name} {race_detail.race_info.race_number}R")
                print(f"推奨: 単勝{prediction.recommended_win}号艇")
                print(f"信頼度: {prediction.confidence:.1%}")
                
                print("\n全機能が正常に動作しています")
                
            else:
                print("レース詳細取得に失敗")
        else:
            print("レース一覧取得に失敗")
            
    except Exception as e:
        print(f"テストエラー: {e}")
    
    print("\n" + "=" * 60)
    print("修正内容:")
    print("- EOFError (入力中断) のエラーハンドリング追加")
    print("- KeyboardInterrupt (Ctrl+C) のエラーハンドリング追加")  
    print("- より分かりやすいエラーメッセージ")
    print("- 入力エラー時の適切な処理")


def main():
    """メインテスト関数"""
    logger.info("🚀 システムエラー修正テスト開始")
    
    results = []
    
    # 1. インポートテスト
    logger.info("1. インポートテスト")
    results.append(test_async_fetcher_import())
    
    # 2. イベントループハンドリングテスト
    logger.info("2. イベントループハンドリングテスト")
    results.append(test_event_loop_handling())
    
    # 3. セッション管理テスト
    logger.info("3. セッション管理テスト")
    results.append(test_session_management())
    
    # 結果集計
    success_count = sum(results)
    total_count = len(results)
    
    logger.info(f"📊 テスト結果: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        logger.info("🎉 すべてのテストが成功しました！")
        return True
    else:
        logger.warning("⚠️ 一部のテストが失敗しました")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ テスト実行中にエラーが発生: {e}")
        sys.exit(1)