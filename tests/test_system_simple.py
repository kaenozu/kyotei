"""
艇国データバンク競艇予想システム 簡易テストクラス
絵文字・特殊文字を使用しない版
"""
import unittest
import logging
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.teikoku_simple_fetcher import TeikokuSimpleFetcher
from prediction.simple_predictor import TeikokuSimplePredictor
from data.simple_models import (
    TeikokuRaceInfo, TeikokuRacerInfo, TeikokuRaceDetail, 
    TeikokuPrediction, get_venue_name, get_venue_id
)


class TestKyoteiSystem(unittest.TestCase):
    """艇国データバンクシステムのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.fetcher = TeikokuSimpleFetcher()
        self.predictor = TeikokuSimplePredictor()
        
        # テスト用のサンプルデータを作成
        self.sample_race_info = TeikokuRaceInfo(
            race_id="20250820_02_01",
            date="20250820", 
            venue_id="02",
            venue_name="戸田",
            race_number=1,
            status="発売中",
            start_time=datetime.now()
        )
        
        self.sample_racers = []
        for i in range(1, 7):
            racer = TeikokuRacerInfo(
                racer_id=f"test_racer_{i}",
                number=i,
                name=f"テスト選手{i}",
                estimated_strength=0.30 - (i * 0.02),
                lane_advantage=0.25 - (i * 0.03)
            )
            self.sample_racers.append(racer)
        
        self.sample_race_detail = TeikokuRaceDetail(
            race_info=self.sample_race_info,
            racers=self.sample_racers
        )
    
    def test_01_data_models(self):
        """01. データモデルのテスト"""
        print("\n[01] データモデルテスト開始")
        
        # RaceInfo テスト
        self.assertEqual(self.sample_race_info.venue_name, "戸田")
        self.assertEqual(self.sample_race_info.race_number, 1)
        
        # RacerInfo テスト
        self.assertEqual(len(self.sample_racers), 6)
        self.assertEqual(self.sample_racers[0].number, 1)
        
        # RaceDetail テスト
        self.assertEqual(len(self.sample_race_detail.racers), 6)
        racer = self.sample_race_detail.get_racer_by_number(3)
        self.assertIsNotNone(racer)
        
        print("[01] データモデル: 正常")
    
    def test_02_venue_mapping(self):
        """02. 競艇場マッピングのテスト"""
        print("\n[02] 競艇場マッピングテスト開始")
        
        # 競艇場名の取得テスト
        self.assertEqual(get_venue_name("02"), "戸田")
        self.assertEqual(get_venue_name("24"), "大村")
        
        # 競艇場IDの取得テスト
        self.assertEqual(get_venue_id("戸田"), "02")
        self.assertEqual(get_venue_id("大村"), "24")
        
        print("[02] 競艇場マッピング: 正常")
    
    def test_03_fetcher_connection(self):
        """03. データフェッチャーの接続テスト"""
        print("\n[03] フェッチャー接続テスト開始")
        
        try:
            connection_ok = self.fetcher.test_connection()
            self.assertTrue(connection_ok, "艇国データバンクへの接続に失敗")
            print("[03] 艇国データバンク接続: 成功")
            
        except Exception as e:
            print(f"[03] 接続テストエラー: {e}")
            self.fail(f"接続テストでエラー: {e}")
    
    def test_04_today_races_fetching(self):
        """04. 今日のレース取得テスト"""
        print("\n[04] レース取得テスト開始")
        
        try:
            races = self.fetcher.get_today_races()
            self.assertIsInstance(races, list)
            self.assertGreater(len(races), 0)
            
            # 最初のレースの構造をチェック
            first_race = races[0]
            self.assertIsInstance(first_race, TeikokuRaceInfo)
            self.assertIsNotNone(first_race.race_id)
            self.assertIsNotNone(first_race.venue_name)
            
            print(f"[04] レース取得: {len(races)}件成功")
            
        except Exception as e:
            print(f"[04] レース取得エラー: {e}")
            self.fail(f"レース取得テストでエラー: {e}")
    
    def test_05_prediction_engine(self):
        """05. 予想エンジンのテスト"""
        print("\n[05] 予想エンジンテスト開始")
        
        try:
            prediction = self.predictor.predict_race(self.sample_race_detail)
            
            self.assertIsInstance(prediction, TeikokuPrediction)
            self.assertEqual(prediction.race_id, "20250820_02_01")
            self.assertIsInstance(prediction.predictions, dict)
            self.assertEqual(len(prediction.predictions), 6)
            
            # 推奨艇の妥当性チェック
            self.assertIn(prediction.recommended_win, range(1, 7))
            self.assertEqual(len(prediction.recommended_place), 3)
            
            # 信頼度の範囲チェック
            self.assertGreaterEqual(prediction.confidence, 0.0)
            self.assertLessEqual(prediction.confidence, 1.0)
            
            print(f"[05] 予想エンジン: 推奨単勝{prediction.recommended_win}号艇")
            
        except Exception as e:
            print(f"[05] 予想エンジンエラー: {e}")
            self.fail(f"予想エンジンテストでエラー: {e}")
    
    def test_06_prediction_format(self):
        """06. 予想結果フォーマットのテスト"""
        print("\n[06] 予想結果フォーマットテスト開始")
        
        try:
            prediction = self.predictor.predict_race(self.sample_race_detail)
            formatted_result = self.predictor.format_prediction_result(prediction, self.sample_race_detail)
            
            self.assertIsInstance(formatted_result, str)
            self.assertIn("予想結果", formatted_result)
            self.assertIn("戸田", formatted_result)
            self.assertIn("購入推奨", formatted_result)
            
            print("[06] 予想結果フォーマット: 正常")
            
        except Exception as e:
            print(f"[06] フォーマットエラー: {e}")
            self.fail(f"予想結果フォーマットテストでエラー: {e}")
    
    def test_07_no_hardcoding(self):
        """07. ハードコーディング除去の確認テスト"""
        print("\n[07] ハードコーディング除去確認テスト開始")
        
        hardcoded_names = ['峰竜太', '松井繁', '瓜生正義', '石野貴之', '茅原悠紀', '池田浩二']
        
        try:
            races = self.fetcher.get_today_races()
            if races:
                test_race = races[0]
                race_detail = self.fetcher.get_race_detail(test_race.race_id)
                
                if race_detail and race_detail.racers:
                    racer_names = [racer.name for racer in race_detail.racers]
                    found_hardcoded = [name for name in hardcoded_names if name in racer_names]
                    
                    self.assertEqual(len(found_hardcoded), 0, 
                                   f"ハードコーディングされた選手名が検出: {found_hardcoded}")
                    
                    print(f"[07] ハードコーディング除去: 確認済み")
                    print(f"     取得選手: {racer_names}")
                else:
                    print("[07] ハードコーディング除去: 実データ取得不可のため確認できず")
            else:
                self.fail("レース取得に失敗")
                
        except Exception as e:
            print(f"[07] ハードコーディング確認エラー: {e}")
            self.fail(f"ハードコーディング確認テストでエラー: {e}")
    
    def test_08_system_integration(self):
        """08. システム統合テスト"""
        print("\n[08] システム統合テスト開始")
        
        try:
            # 1. レース取得
            races = self.fetcher.get_today_races()
            self.assertGreater(len(races), 0)
            print(f"     レース取得: {len(races)}件")
            
            # 2. レース詳細取得
            test_race = races[0]
            race_detail = self.fetcher.get_race_detail(test_race.race_id)
            
            if race_detail:
                print(f"     レース詳細取得: 成功 ({len(race_detail.racers)}名)")
                
                # 3. 予想実行
                prediction = self.predictor.predict_race(race_detail)
                self.assertIsNotNone(prediction)
                print(f"     予想実行: 成功")
                
                # 4. 結果フォーマット
                formatted_result = self.predictor.format_prediction_result(prediction, race_detail)
                self.assertIsInstance(formatted_result, str)
                print(f"     結果フォーマット: 成功")
                
                print("[08] システム統合: 全工程正常動作")
            else:
                print("[08] システム統合: 実データ取得制限により部分テスト")
                
        except Exception as e:
            print(f"[08] システム統合エラー: {e}")
            self.fail(f"システム統合テストでエラー: {e}")


def run_simple_tests():
    """簡易テスト実行"""
    print("=" * 60)
    print("艇国データバンク競艇予想システム 簡易テスト")
    print("=" * 60)
    
    # ログレベルを警告以上に設定
    logging.getLogger().setLevel(logging.WARNING)
    
    # テスト実行
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestKyoteiSystem)
    
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n成功率: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("システムは正常に動作しています")
    else:
        print("システムに問題がある可能性があります")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    run_simple_tests()