#!/usr/bin/env python3
"""
的中率詳細分析ツール
予想精度の問題点を特定し、改善案を提示
"""

import sqlite3
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccuracyAnalyzer:
    """的中率詳細分析クラス"""
    
    def __init__(self, db_path: str = "cache/accuracy_tracker.db"):
        self.db_path = db_path
        self.venue_mapping = {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
    
    def analyze_accuracy_issues(self) -> Dict:
        """的中率の問題を詳細分析"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 予想と結果の詳細データを取得
                cursor.execute("""
                    SELECT p.venue_id, p.venue_name, p.race_number,
                           p.predicted_win, p.predicted_place, p.confidence,
                           r.winning_boat, r.place_results,
                           p.race_date, p.race_time
                    FROM predictions p
                    LEFT JOIN race_results r ON p.race_date = r.race_date 
                                              AND p.venue_id = r.venue_id 
                                              AND p.race_number = r.race_number
                    WHERE r.winning_boat IS NOT NULL
                    ORDER BY p.race_date DESC, p.venue_id, p.race_number
                """)
                
                results = cursor.fetchall()
                
                # 分析データ構造
                analysis = {
                    'total_races': len(results),
                    'win_accuracy': 0,
                    'place_accuracy': 0,
                    'trifecta_accuracy': 0,  # 3連単的中率
                    'venue_analysis': defaultdict(lambda: {'total': 0, 'hits': 0}),
                    'confidence_analysis': defaultdict(lambda: {'total': 0, 'hits': 0}),
                    'boat_number_analysis': defaultdict(lambda: {'predicted': 0, 'actual': 0, 'hits': 0}),
                    'prediction_distribution': defaultdict(int),
                    'actual_distribution': defaultdict(int),
                    'miss_patterns': [],
                    'best_predictions': [],
                    'worst_predictions': []
                }
                
                win_hits = 0
                place_hits = 0
                trifecta_hits = 0
                
                for row in results:
                    venue_id, venue_name, race_number, predicted_win, predicted_place_json, confidence, winning_boat, place_results_json, race_date, race_time = row
                    
                    try:
                        predicted_place = json.loads(predicted_place_json) if predicted_place_json else []
                        place_results = json.loads(place_results_json) if place_results_json else []
                    except:
                        predicted_place = []
                        place_results = []
                    
                    # 基本統計
                    is_win_hit = (predicted_win == winning_boat)
                    is_place_hit = (predicted_win in place_results[:2])  # 複勝は1位・2位のみ
                    
                    # 3連単の計算（予想上位3艇が着順通りか）
                    is_trifecta_hit = False
                    if len(predicted_place) >= 3 and len(place_results) >= 3:
                        is_trifecta_hit = (predicted_place[:3] == place_results[:3])
                    
                    if is_win_hit:
                        win_hits += 1
                    if is_place_hit:
                        place_hits += 1
                    if is_trifecta_hit:
                        trifecta_hits += 1
                    
                    # 会場別分析
                    analysis['venue_analysis'][venue_name]['total'] += 1
                    if is_win_hit:
                        analysis['venue_analysis'][venue_name]['hits'] += 1
                    
                    # 信頼度別分析
                    conf_range = self._get_confidence_range(confidence)
                    analysis['confidence_analysis'][conf_range]['total'] += 1
                    if is_win_hit:
                        analysis['confidence_analysis'][conf_range]['hits'] += 1
                    
                    # 艇番分析
                    analysis['boat_number_analysis'][predicted_win]['predicted'] += 1
                    analysis['boat_number_analysis'][winning_boat]['actual'] += 1
                    if is_win_hit:
                        analysis['boat_number_analysis'][predicted_win]['hits'] += 1
                    
                    # 分布分析
                    analysis['prediction_distribution'][predicted_win] += 1
                    analysis['actual_distribution'][winning_boat] += 1
                    
                    # ミスパターン記録
                    if not is_win_hit:
                        analysis['miss_patterns'].append({
                            'venue': venue_name,
                            'race': race_number,
                            'predicted': predicted_win,
                            'actual': winning_boat,
                            'confidence': confidence,
                            'date': race_date
                        })
                    
                    # 成功例記録
                    if is_win_hit and confidence > 0.7:
                        analysis['best_predictions'].append({
                            'venue': venue_name,
                            'race': race_number,
                            'boat': predicted_win,
                            'confidence': confidence,
                            'date': race_date
                        })
                
                # 基本的中率
                analysis['win_accuracy'] = (win_hits / len(results)) * 100 if results else 0
                analysis['place_accuracy'] = (place_hits / len(results)) * 100 if results else 0
                analysis['trifecta_accuracy'] = (trifecta_hits / len(results)) * 100 if results else 0
                
                return analysis
                
        except Exception as e:
            logger.error(f"精度分析エラー: {e}")
            return {}
    
    def _get_confidence_range(self, confidence: float) -> str:
        """信頼度を範囲に分類"""
        if confidence >= 0.8:
            return "高信頼度(80%+)"
        elif confidence >= 0.6:
            return "中信頼度(60-80%)"
        elif confidence >= 0.4:
            return "低信頼度(40-60%)"
        else:
            return "超低信頼度(-40%)"
    
    def generate_improvement_suggestions(self, analysis: Dict) -> List[str]:
        """改善提案を生成"""
        suggestions = []
        
        # 1. 全体的中率の問題
        if analysis['win_accuracy'] < 20:
            suggestions.append("🚨 緊急: 単勝的中率が20%以下です。予想アルゴリズムの根本的見直しが必要")
        
        # 2. 艇番偏重の問題
        pred_dist = analysis['prediction_distribution']
        actual_dist = analysis['actual_distribution']
        
        # 1号艇偏重チェック
        if pred_dist.get(1, 0) / sum(pred_dist.values()) > 0.4:
            suggestions.append("⚠️  1号艇を予想しすぎています。他の艇番の可能性も考慮してください")
        
        # 実際の勝率との乖離
        for boat_num in range(1, 7):
            pred_rate = pred_dist.get(boat_num, 0) / sum(pred_dist.values()) if pred_dist else 0
            actual_rate = actual_dist.get(boat_num, 0) / sum(actual_dist.values()) if actual_dist else 0
            
            if abs(pred_rate - actual_rate) > 0.15:
                suggestions.append(f"📊 {boat_num}号艇: 予想率{pred_rate:.1%} vs 実際{actual_rate:.1%} - 大きな偏りあり")
        
        # 3. 会場別問題
        venue_issues = []
        for venue, data in analysis['venue_analysis'].items():
            if data['total'] > 5:  # 十分なサンプル数
                accuracy = (data['hits'] / data['total']) * 100
                if accuracy < 10:
                    venue_issues.append(f"{venue}({accuracy:.1f}%)")
        
        if venue_issues:
            suggestions.append(f"🏟️  特に苦手な会場: {', '.join(venue_issues)}")
        
        # 4. 信頼度の問題
        for conf_range, data in analysis['confidence_analysis'].items():
            if data['total'] > 3:
                accuracy = (data['hits'] / data['total']) * 100
                if "高信頼度" in conf_range and accuracy < 30:
                    suggestions.append(f"🎯 {conf_range}でも的中率{accuracy:.1f}% - 信頼度計算に問題あり")
        
        # 5. 改善案
        suggestions.extend([
            "💡 改善案1: 展示航走データの活用（現在未使用の可能性）",
            "💡 改善案2: モーター・ボート成績の重み見直し",
            "💡 改善案3: 気象条件の影響をより詳細に考慮",
            "💡 改善案4: 過去の成績データの時系列分析",
            "💡 改善案5: 機械学習アルゴリズムの導入検討"
        ])
        
        return suggestions
    
    def print_detailed_report(self):
        """詳細レポート出力"""
        print("=" * 60)
        print("競艇予想精度詳細分析レポート")
        print("=" * 60)
        
        analysis = self.analyze_accuracy_issues()
        
        if not analysis:
            print("分析データが取得できませんでした")
            return
        
        # 基本統計
        print(f"\n[基本統計]")
        print(f"  総レース数: {analysis['total_races']}件")
        print(f"  単勝的中率: {analysis['win_accuracy']:.2f}%")
        print(f"  複勝的中率: {analysis['place_accuracy']:.2f}%")
        print(f"  3連単的中率: {analysis['trifecta_accuracy']:.2f}%")
        
        # 艇番分析
        print(f"\n[艇番別分析]")
        for boat_num in range(1, 7):
            data = analysis['boat_number_analysis'][boat_num]
            pred_rate = (data['predicted'] / analysis['total_races']) * 100 if analysis['total_races'] else 0
            actual_rate = (data['actual'] / analysis['total_races']) * 100 if analysis['total_races'] else 0
            hit_rate = (data['hits'] / data['predicted']) * 100 if data['predicted'] else 0
            
            print(f"  {boat_num}号艇: 予想{pred_rate:5.1f}% | 実際{actual_rate:5.1f}% | 的中{hit_rate:5.1f}%")
        
        # 会場別分析
        print(f"\n[会場別的中率 (上位5会場)]")
        venue_accuracy = []
        for venue, data in analysis['venue_analysis'].items():
            if data['total'] >= 3:
                accuracy = (data['hits'] / data['total']) * 100
                venue_accuracy.append((venue, accuracy, data['total'], data['hits']))
        
        venue_accuracy.sort(key=lambda x: x[1], reverse=True)
        for venue, accuracy, total, hits in venue_accuracy[:5]:
            print(f"  {venue:8}: {accuracy:5.1f}% ({hits}/{total})")
        
        # 信頼度分析
        print(f"\n[信頼度別的中率]")
        for conf_range, data in analysis['confidence_analysis'].items():
            if data['total'] > 0:
                accuracy = (data['hits'] / data['total']) * 100
                print(f"  {conf_range:15}: {accuracy:5.1f}% ({data['hits']}/{data['total']})")
        
        # 改善提案
        suggestions = self.generate_improvement_suggestions(analysis)
        print(f"\n[改善提案]")
        for i, suggestion in enumerate(suggestions, 1):
            # 絵文字を除去
            clean_suggestion = suggestion
            for emoji in ['🚨', '⚠️', '📊', '🏟️', '🎯', '💡']:
                clean_suggestion = clean_suggestion.replace(emoji, '')
            print(f"  {i:2d}. {clean_suggestion.strip()}")
        
        print(f"\n{'=' * 60}")


if __name__ == "__main__":
    analyzer = AccuracyAnalyzer()
    analyzer.print_detailed_report()