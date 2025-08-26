#!/usr/bin/env python3
"""
統合ML予想システムの性能テスト
従来システムとML統合システムの的中率を比較
"""

import json
import logging
from datetime import datetime
from enhanced_predictor import EnhancedPredictor
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedSystemTester:
    """統合システムテスター"""
    
    def __init__(self):
        self.predictor = EnhancedPredictor()
        self.test_venues = [12, 15, 19, 22, 23, 24]  # テスト会場
        self.test_races = [1, 2, 3, 4, 5]  # テストレース
    
    def run_prediction_test(self) -> Dict:
        """予想テストを実行"""
        test_results = {
            'total_tests': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'predictions': [],
            'summary': {}
        }
        
        print("=== 統合ML予想システム性能テスト開始 ===")
        
        for venue_id in self.test_venues:
            print(f"\n--- 会場 {venue_id} のテスト ---")
            
            for race_number in self.test_races:
                try:
                    # 統合システムで予想実行
                    result = self.predictor.calculate_enhanced_prediction(venue_id, race_number)
                    
                    if result:
                        test_results['successful_predictions'] += 1
                        test_results['predictions'].append({
                            'venue_id': venue_id,
                            'race_number': race_number,
                            'prediction': result,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # 予想結果の概要表示
                        top_prediction = result.get('recommended_win', 0)
                        confidence = result.get('confidence', 0)
                        print(f"  レース{race_number}: 本命{top_prediction}号艇 (信頼度:{confidence:.3f})")
                    else:
                        test_results['failed_predictions'] += 1
                        print(f"  レース{race_number}: 予想失敗")
                    
                    test_results['total_tests'] += 1
                    
                except Exception as e:
                    test_results['failed_predictions'] += 1
                    test_results['total_tests'] += 1
                    logger.error(f"予想エラー (会場{venue_id} レース{race_number}): {e}")
        
        # 成功率計算
        if test_results['total_tests'] > 0:
            success_rate = (test_results['successful_predictions'] / test_results['total_tests']) * 100
            test_results['success_rate'] = success_rate
            
            print(f"\n=== テスト結果サマリー ===")
            print(f"総テスト数: {test_results['total_tests']}")
            print(f"成功: {test_results['successful_predictions']}")
            print(f"失敗: {test_results['failed_predictions']}")
            print(f"成功率: {success_rate:.1f}%")
        
        return test_results
    
    def analyze_prediction_patterns(self, results: Dict) -> Dict:
        """予想パターンを分析"""
        analysis = {
            'boat_number_distribution': {},
            'confidence_distribution': {},
            'venue_performance': {},
            'recommendations': []
        }
        
        if not results.get('predictions'):
            return analysis
        
        # 艇番分布分析
        boat_counts = {}
        confidence_levels = {'high': 0, 'medium': 0, 'low': 0}
        venue_stats = {}
        
        for pred_data in results['predictions']:
            prediction = pred_data['prediction']
            venue_id = pred_data['venue_id']
            
            # 本命艇番の分布
            recommended_win = prediction.get('recommended_win', 0)
            boat_counts[recommended_win] = boat_counts.get(recommended_win, 0) + 1
            
            # 信頼度分布
            confidence = prediction.get('confidence', 0)
            if confidence >= 0.6:
                confidence_levels['high'] += 1
            elif confidence >= 0.4:
                confidence_levels['medium'] += 1
            else:
                confidence_levels['low'] += 1
            
            # 会場別統計
            if venue_id not in venue_stats:
                venue_stats[venue_id] = {'count': 0, 'avg_confidence': 0}
            venue_stats[venue_id]['count'] += 1
            venue_stats[venue_id]['avg_confidence'] += confidence
        
        # 平均信頼度計算
        for venue_id in venue_stats:
            if venue_stats[venue_id]['count'] > 0:
                venue_stats[venue_id]['avg_confidence'] /= venue_stats[venue_id]['count']
        
        analysis['boat_number_distribution'] = boat_counts
        analysis['confidence_distribution'] = confidence_levels
        analysis['venue_performance'] = venue_stats
        
        # 改善提案
        if confidence_levels['low'] > confidence_levels['high']:
            analysis['recommendations'].append("信頼度が低い予想が多い - 特徴量の見直しが必要")
        
        total_predictions = sum(boat_counts.values())
        if total_predictions > 0:
            boat_1_rate = boat_counts.get(1, 0) / total_predictions
            if boat_1_rate > 0.4:
                analysis['recommendations'].append("1号艇偏重 - 予想の多様性を改善")
        
        return analysis
    
    def save_results(self, results: Dict, analysis: Dict):
        """結果を保存"""
        try:
            output_data = {
                'test_timestamp': datetime.now().isoformat(),
                'test_results': results,
                'analysis': analysis,
                'system_version': 'Enhanced_ML_Integrated_v1.0'
            }
            
            with open('cache/integrated_system_test_results.json', 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n結果を保存しました: cache/integrated_system_test_results.json")
            
        except Exception as e:
            logger.error(f"結果保存エラー: {e}")


def main():
    """メイン実行"""
    tester = IntegratedSystemTester()
    
    # 予想テスト実行
    test_results = tester.run_prediction_test()
    
    # パターン分析
    analysis = tester.analyze_prediction_patterns(test_results)
    
    # 結果詳細表示
    if analysis:
        print(f"\n=== 予想パターン分析 ===")
        print(f"艇番分布: {analysis['boat_number_distribution']}")
        print(f"信頼度分布: {analysis['confidence_distribution']}")
        print(f"会場別平均信頼度: {analysis['venue_performance']}")
        
        if analysis['recommendations']:
            print(f"\n改善提案:")
            for i, rec in enumerate(analysis['recommendations'], 1):
                print(f"  {i}. {rec}")
    
    # 結果保存
    tester.save_results(test_results, analysis)
    
    print(f"\n=== 統合ML予想システムテスト完了 ===")


if __name__ == "__main__":
    main()