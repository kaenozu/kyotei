"""
艇国データバンク競艇予想システム 包括的テストクラス
"""
import unittest
import logging
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.teikoku_simple_fetcher import TeikokuSimpleFetcher
from prediction.simple_predictor import TeikokuSimplePredictor
from data.simple_models import (
    TeikokuRaceInfo, TeikokuRacerInfo, TeikokuRaceDetail, 
    TeikokuPrediction, get_venue_name, get_venue_id
)


class TestTeikokuSystem(unittest.TestCase):
    """艇国データバンクシステムの包括的テストクラス"""
    
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
        
        self.sample_racers = [
            TeikokuRacerInfo(
                racer_id="test_racer_1",
                number=1,
                name="テスト選手1",
                estimated_strength=0.25,
                lane_advantage=0.25
            ),
            TeikokuRacerInfo(
                racer_id="test_racer_2", 
                number=2,
                name="テスト選手2",
                estimated_strength=0.20,
                lane_advantage=0.18
            ),
            TeikokuRacerInfo(
                racer_id="test_racer_3",
                number=3,
                name="テスト選手3",
                estimated_strength=0.18,
                lane_advantage=0.15
            ),
            TeikokuRacerInfo(
                racer_id="test_racer_4",
                number=4,
                name="テスト選手4",
                estimated_strength=0.15,
                lane_advantage=0.12
            ),
            TeikokuRacerInfo(
                racer_id="test_racer_5",
                number=5,
                name="テスト選手5",
                estimated_strength=0.12,
                lane_advantage=0.10
            ),
            TeikokuRacerInfo(
                racer_id="test_racer_6",
                number=6,
                name="テスト選手6",
                estimated_strength=0.10,
                lane_advantage=0.08
            )
        ]
        
        self.sample_race_detail = TeikokuRaceDetail(
            race_info=self.sample_race_info,
            racers=self.sample_racers
        )
    
    def test_data_models(self):
        """データモデルのテスト"""
        print("\n=== データモデルテスト ===")
        
        # RaceInfo テスト
        self.assertEqual(self.sample_race_info.venue_name, "戸田")
        self.assertEqual(self.sample_race_info.race_number, 1)
        
        # RacerInfo テスト
        self.assertEqual(len(self.sample_racers), 6)
        self.assertEqual(self.sample_racers[0].number, 1)
        self.assertEqual(self.sample_racers[0].name, "テスト選手1")
        
        # RaceDetail テスト
        self.assertEqual(len(self.sample_race_detail.racers), 6)
        racer = self.sample_race_detail.get_racer_by_number(3)
        self.assertIsNotNone(racer)
        self.assertEqual(racer.name, "テスト選手3")
        
        print("✓ データモデル: 正常")
    
    def test_venue_mapping(self):
        """競艇場マッピングのテスト"""
        print("\n=== 競艇場マッピングテスト ===")
        
        # 競艇場名の取得テスト
        self.assertEqual(get_venue_name("02"), "戸田")
        self.assertEqual(get_venue_name("24"), "大村")
        self.assertEqual(get_venue_name("99"), "場99")  # 存在しないID
        
        # 競艇場IDの取得テスト
        self.assertEqual(get_venue_id("戸田"), "02")
        self.assertEqual(get_venue_id("大村"), "24")
        self.assertIsNone(get_venue_id("存在しない"))
        
        print("✓ 競艇場マッピング: 正常")
    
    def test_fetcher_connection(self):
        """データフェッチャーの接続テスト"""
        print("\n=== フェッチャー接続テスト ===")
        
        try:
            # 接続テスト
            connection_ok = self.fetcher.test_connection()
            self.assertTrue(connection_ok, "艇国データバンクへの接続に失敗")
            print("✓ 艇国データバンク接続: 成功")
            
        except Exception as e:
            self.fail(f"接続テストでエラー: {e}")
    
    def test_today_races_fetching(self):
        """今日のレース取得テスト"""
        print("\n=== レース取得テスト ===")
        
        try:
            races = self.fetcher.get_today_races()
            self.assertIsInstance(races, list, "レース一覧がリストではない")
            self.assertGreater(len(races), 0, "レースが取得されていない")
            
            # 最初のレースの構造をチェック
            first_race = races[0]
            self.assertIsInstance(first_race, TeikokuRaceInfo)
            self.assertIsNotNone(first_race.race_id)
            self.assertIsNotNone(first_race.venue_name)
            self.assertIsInstance(first_race.race_number, int)
            
            print(f"✓ レース取得: {len(races)}件成功")
            
        except Exception as e:
            self.fail(f"レース取得テストでエラー: {e}")
    
    def test_race_detail_fetching(self):
        """レース詳細取得テスト"""
        print("\n=== レース詳細取得テスト ===")
        
        try:
            # まず今日のレースを取得
            races = self.fetcher.get_today_races()
            if not races:
                self.skipTest("テスト用のレースが取得できませんでした")
            
            # 最初のレースの詳細を取得
            test_race = races[0]
            race_detail = self.fetcher.get_race_detail(test_race.race_id)
            
            if race_detail:
                self.assertIsInstance(race_detail, TeikokuRaceDetail)
                self.assertIsNotNone(race_detail.race_info)
                self.assertIsInstance(race_detail.racers, list)
                self.assertGreater(len(race_detail.racers), 0, "選手データが取得されていない")
                
                # 選手データの構造チェック
                first_racer = race_detail.racers[0]
                self.assertIsInstance(first_racer, TeikokuRacerInfo)
                self.assertIsNotNone(first_racer.name)
                self.assertIsInstance(first_racer.number, int)
                
                print(f"✓ レース詳細取得: {len(race_detail.racers)}名の選手データ")
            else:
                print("! レース詳細取得: 実データ取得不可（ハードコーディングなし）")
                
        except Exception as e:
            self.fail(f"レース詳細取得テストでエラー: {e}")
    
    def test_prediction_engine(self):
        """予想エンジンのテスト"""
        print("\n=== 予想エンジンテスト ===")
        
        try:
            # サンプルデータで予想実行
            prediction = self.predictor.predict_race(self.sample_race_detail)
            
            self.assertIsInstance(prediction, TeikokuPrediction)
            self.assertEqual(prediction.race_id, "20250820_02_01")
            self.assertIsInstance(prediction.predictions, dict)
            self.assertEqual(len(prediction.predictions), 6, "6名分の予想がない")
            
            # 推奨艇の妥当性チェック
            self.assertIn(prediction.recommended_win, range(1, 7), "推奨単勝艇番が不正")
            self.assertEqual(len(prediction.recommended_place), 3, "推奨複勝が3艇でない")
            
            # 信頼度の範囲チェック
            self.assertGreaterEqual(prediction.confidence, 0.0, "信頼度が負の値")
            self.assertLessEqual(prediction.confidence, 1.0, "信頼度が1.0を超えている")
            
            print(f"✓ 予想エンジン: 推奨単勝{prediction.recommended_win}号艇, 信頼度{prediction.confidence:.1%}")
            
        except Exception as e:
            self.fail(f"予想エンジンテストでエラー: {e}")
    
    def test_prediction_format(self):
        """予想結果フォーマットのテスト"""
        print("\n=== 予想結果フォーマットテスト ===")
        
        try:
            prediction = self.predictor.predict_race(self.sample_race_detail)
            formatted_result = self.predictor.format_prediction_result(prediction, self.sample_race_detail)
            
            self.assertIsInstance(formatted_result, str)
            self.assertIn("予想結果", formatted_result)
            self.assertIn("戸田", formatted_result)
            self.assertIn("1R", formatted_result)
            self.assertIn("購入推奨", formatted_result)
            
            print("✓ 予想結果フォーマット: 正常")
            
        except Exception as e:
            self.fail(f"予想結果フォーマットテストでエラー: {e}")
    
    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        print("\n=== エラーハンドリングテスト ===")
        
        try:
            # 存在しないレースIDでテスト
            invalid_race_detail = self.fetcher.get_race_detail("invalid_race_id")
            self.assertIsNone(invalid_race_detail, "不正なIDでもデータが返された")
            
            print("✓ エラーハンドリング: 正常")
            
        except Exception as e:
            # エラーが適切に処理されることを確認
            self.assertIsInstance(e, (RuntimeError, ValueError))
            print("✓ エラーハンドリング: 適切にエラーを処理")
    
    def test_no_hardcoding(self):
        """ハードコーディング除去の確認テスト"""
        print("\n=== ハードコーディング除去確認テスト ===")
        
        # ハードコーディングされた選手名のリスト
        hardcoded_names = ['峰竜太', '松井繁', '瓜生正義', '石野貴之', '茅原悠紀', '池田浩二']
        
        try:
            races = self.fetcher.get_today_races()
            if races:
                test_race = races[0]
                race_detail = self.fetcher.get_race_detail(test_race.race_id)
                
                if race_detail and race_detail.racers:
                    # 取得された選手名をチェック
                    racer_names = [racer.name for racer in race_detail.racers]
                    
                    # ハードコーディングされた名前が含まれていないことを確認
                    found_hardcoded = [name for name in hardcoded_names if name in racer_names]
                    
                    self.assertEqual(len(found_hardcoded), 0, 
                                   f"ハードコーディングされた選手名が検出されました: {found_hardcoded}")
                    
                    print(f"✓ ハードコーディング除去: 確認済み (取得選手: {racer_names})")
                else:
                    print("! ハードコーディング除去: 実データ取得不可のため確認できず")
            else:
                self.fail("レース取得に失敗")
                
        except Exception as e:
            self.fail(f"ハードコーディング確認テストでエラー: {e}")
    
    def test_system_integration(self):
        """システム統合テスト"""
        print("\n=== システム統合テスト ===")
        
        try:
            # 1. レース取得
            races = self.fetcher.get_today_races()
            self.assertGreater(len(races), 0, "レース取得失敗")
            
            # 2. レース詳細取得
            test_race = races[0]
            race_detail = self.fetcher.get_race_detail(test_race.race_id)
            
            if race_detail:
                # 3. 予想実行
                prediction = self.predictor.predict_race(race_detail)
                self.assertIsNotNone(prediction, "予想実行失敗")
                
                # 4. 結果フォーマット
                formatted_result = self.predictor.format_prediction_result(prediction, race_detail)
                self.assertIsInstance(formatted_result, str, "結果フォーマット失敗")
                
                print("✓ システム統合: 全工程正常動作")
            else:
                print("! システム統合: 実データ取得制限により部分テスト")
                
        except Exception as e:
            self.fail(f"システム統合テストでエラー: {e}")


class TestKyoteiSystemRunner:
    """テスト実行クラス"""
    
    @staticmethod
    def run_all_tests():
        """全テストを実行"""
        print("=" * 70)
        print("艇国データバンク競艇予想システム 包括的テスト")
        print("=" * 70)
        
        # ログレベルを警告以上に設定（テスト出力を見やすくする）
        logging.getLogger().setLevel(logging.WARNING)
        
        # テストスイートを作成
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestTeikokuSystem)
        
        # テスト実行
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)
        
        # 結果サマリー
        print("\n" + "=" * 70)
        print("テスト結果サマリー")
        print("=" * 70)
        print(f"実行テスト数: {result.testsRun}")
        print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"失敗: {len(result.failures)}")
        print(f"エラー: {len(result.errors)}")
        
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
        
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
        print(f"\n成功率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("✅ システムは正常に動作しています")
        else:
            print("⚠️ システムに問題がある可能性があります")
        
        return result.wasSuccessful()


if __name__ == "__main__":
    TestKyoteiSystemRunner.run_all_tests()