#!/usr/bin/env python3
"""
予想根拠透明性システムのテスト
計算過程可視化機能の動作確認
"""

import json
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_transparency_basic():
    """基本的な透明性機能テスト"""
    print("=== 基本透明性機能テスト ===")
    
    try:
        from prediction_transparency import prediction_transparency
        
        # サンプルレースデータ
        sample_race = {
            'race_stadium_number': 3,  # 江戸川
            'boats': [
                {
                    'boat_number': 1,
                    'racer_name': 'テスト選手A',
                    'racer_national_top_1_percent': 35.5,
                    'racer_rate_local': 38.2,
                    'racer_national_top_2_percent': 58.3,
                    'boat_average_start_timing': 0.14
                },
                {
                    'boat_number': 2,
                    'racer_name': 'テスト選手B',
                    'racer_national_top_1_percent': 28.9,
                    'racer_rate_local': 31.5,
                    'racer_national_top_2_percent': 52.1,
                    'boat_average_start_timing': 0.16
                }
            ]
        }
        
        # サンプル予想結果
        sample_predictions = {
            'predictions': [
                {
                    'boat_number': 1,
                    'racer_name': 'テスト選手A',
                    'final_prediction': 0.342,
                    'base_strength': 0.355,
                    'venue_adjustment': 0.024,
                    'weather_adjustment': 0.012,
                    'recent_form': 0.0,
                    'st_factor': 1.15,
                    'lane_advantage': 0.22,
                    'equipment_bonus': 0.015
                },
                {
                    'boat_number': 2,
                    'racer_name': 'テスト選手B',
                    'final_prediction': 0.267,
                    'base_strength': 0.289,
                    'venue_adjustment': 0.018,
                    'weather_adjustment': -0.008,
                    'recent_form': 0.0,
                    'st_factor': 1.10,
                    'lane_advantage': 0.16,
                    'equipment_bonus': 0.008
                }
            ],
            'weather_data_available': True,
            'ml_enabled': False
        }
        
        # 透明性レポート生成
        report = prediction_transparency.create_transparency_report(
            sample_race, sample_predictions
        )
        
        print("✓ 透明性レポート生成成功")
        print(f"  会場: {report.venue_name}")
        print(f"  分析艇数: {len(report.breakdowns)}")
        print(f"  データソース数: {len(report.data_sources)}")
        print(f"  予想精度: {report.accuracy_estimate:.1%}")
        
        # 各艇の詳細表示
        for breakdown in report.breakdowns:
            print(f"\n  {breakdown.boat_number}号艇 - {breakdown.racer_name}")
            print(f"    最終予想: {breakdown.final_prediction:.3f}")
            print(f"    信頼度: {breakdown.confidence_score:.1%}")
            print(f"    構成要素数: {len(breakdown.components)}")
            
            # 主要構成要素表示
            for comp in breakdown.components[:3]:  # 上位3要素
                print(f"      {comp.name}: {comp.value:.3f} (寄与度: {comp.contribution:+.3f})")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_html_generation():
    """HTMLレポート生成テスト"""
    print("\n=== HTMLレポート生成テスト ===")
    
    try:
        from prediction_transparency import prediction_transparency
        
        # サンプルデータで透明性レポート作成
        sample_race = {
            'race_stadium_number': 11,  # びわこ
            'boats': [
                {
                    'boat_number': i,
                    'racer_name': f'選手{i}',
                    'racer_national_top_1_percent': 30 + i * 2,
                    'racer_rate_local': 32 + i * 1.5,
                    'racer_national_top_2_percent': 55 + i * 1,
                    'boat_average_start_timing': 0.14 + i * 0.01
                } for i in range(1, 7)
            ]
        }
        
        sample_predictions = {
            'predictions': [
                {
                    'boat_number': i,
                    'racer_name': f'選手{i}',
                    'final_prediction': 0.4 - i * 0.04,
                    'base_strength': 0.35 - i * 0.03,
                    'venue_adjustment': 0.02,
                    'weather_adjustment': 0.01 if i <= 3 else -0.01,
                    'recent_form': 0.0,
                    'st_factor': 1.2 - i * 0.02,
                    'lane_advantage': [0.22, 0.16, 0.13, 0.10, 0.08, 0.06][i-1],
                    'equipment_bonus': 0.01
                } for i in range(1, 7)
            ],
            'weather_data_available': True,
            'ml_enabled': False
        }
        
        # レポート生成
        report = prediction_transparency.create_transparency_report(
            sample_race, sample_predictions
        )
        
        # HTMLレポート生成
        html_report = prediction_transparency.generate_html_report(report)
        
        # ファイル保存
        output_file = "transparency_report_sample.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        print(f"✓ HTMLレポート生成成功")
        print(f"  ファイル: {output_file}")
        print(f"  サイズ: {len(html_report):,} 文字")
        print(f"  艇数: {len(report.breakdowns)}")
        
        # HTMLの基本構造確認
        if all(tag in html_report for tag in ['<html>', '<head>', '<body>', '<style>']):
            print("  ✓ HTML構造正常")
        else:
            print("  ✗ HTML構造に問題あり")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_json_generation():
    """JSONレポート生成テスト"""
    print("\n=== JSONレポート生成テスト ===")
    
    try:
        from prediction_transparency import prediction_transparency
        
        # 簡単なテストケース
        test_race = {
            'race_stadium_number': 24,  # 大村
            'boats': [
                {
                    'boat_number': 1,
                    'racer_name': 'テスト太郎',
                    'racer_national_top_1_percent': 40.2,
                    'racer_rate_local': 42.8,
                    'racer_national_top_2_percent': 65.1,
                    'boat_average_start_timing': 0.13
                }
            ]
        }
        
        test_predictions = {
            'predictions': [
                {
                    'boat_number': 1,
                    'racer_name': 'テスト太郎',
                    'final_prediction': 0.456,
                    'base_strength': 0.402,
                    'venue_adjustment': 0.035,
                    'weather_adjustment': 0.018,
                    'recent_form': 0.0,
                    'st_factor': 1.18,
                    'lane_advantage': 0.25,
                    'equipment_bonus': 0.021
                }
            ],
            'weather_data_available': True,
            'ml_enabled': True
        }
        
        # レポート生成
        report = prediction_transparency.create_transparency_report(
            test_race, test_predictions
        )
        
        # JSON生成
        json_report = prediction_transparency.generate_json_report(report)
        
        # JSON解析テスト
        parsed_json = json.loads(json_report)
        
        print("✓ JSONレポート生成成功")
        print(f"  JSONサイズ: {len(json_report):,} 文字")
        print(f"  会場名: {parsed_json['venue_name']}")
        print(f"  精度推定: {parsed_json['accuracy_estimate']:.1%}")
        print(f"  データソース: {len(parsed_json['data_sources'])}種類")
        
        # ファイル保存
        with open("transparency_report_sample.json", 'w', encoding='utf-8') as f:
            f.write(json_report)
        print("  ✓ JSONファイル保存完了")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_confidence_calculation():
    """信頼度計算テスト"""
    print("\n=== 信頼度計算テスト ===")
    
    try:
        from prediction_transparency import PredictionComponent, PredictionTransparencyEngine
        
        engine = PredictionTransparencyEngine()
        
        # テスト用構成要素
        test_components = [
            PredictionComponent(
                name="基本実力", value=0.35, weight=0.4, 
                contribution=0.14, description="テスト", 
                data_source="BoatraceOpenAPI", confidence=0.9
            ),
            PredictionComponent(
                name="天候補正", value=0.02, weight=0.2, 
                contribution=0.004, description="テスト", 
                data_source="OpenWeatherMap", confidence=0.8
            ),
            PredictionComponent(
                name="直近調子", value=0.0, weight=0.1, 
                contribution=0.0, description="テスト", 
                data_source="データなし", confidence=0.0
            )
        ]
        
        # 信頼度計算
        confidence = engine._calculate_confidence_score(test_components)
        
        print(f"✓ 信頼度計算成功: {confidence:.1%}")
        
        # 期待値計算（手動）
        expected = (0.9 * 0.4 + 0.8 * 0.2 + 0.0 * 0.1) / (0.4 + 0.2 + 0.1)
        print(f"  期待値: {expected:.1%}")
        print(f"  差異: {abs(confidence - expected):.3f}")
        
        if abs(confidence - expected) < 0.001:
            print("  ✓ 計算正確")
            return True
        else:
            print("  ✗ 計算に誤差あり")
            return False
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def main():
    """メインテスト実行"""
    print("予想根拠透明性システム テスト開始")
    print("=" * 60)
    
    results = []
    
    # 各テスト実行
    results.append(test_transparency_basic())
    results.append(test_html_generation())
    results.append(test_json_generation())
    results.append(test_confidence_calculation())
    
    # 結果集計
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"テスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("✅ すべてのテストが成功しました！")
        print("\n📝 次のステップ:")
        print("1. Webサーバーを起動")
        print("2. /api/prediction/{venue_id}/{race_number}?format=html でHTMLレポート確認")
        print("3. /api/transparency/{venue_id}/{race_number} でJSONレポート確認")
    else:
        print("❌ 一部テストが失敗しました")
    
    print("\n🎯 透明性機能概要:")
    print("- 予想構成要素の詳細分析")
    print("- データソース明示")
    print("- 信頼度スコア計算")
    print("- HTML/JSON両形式対応")
    print("- 計算過程の完全可視化")


if __name__ == "__main__":
    main()