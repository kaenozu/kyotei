#!/usr/bin/env python3
"""
ROI-Based Evaluation System for Kyotei Prediction
競艇予想システム向け利益重視評価システム

従来の的中率評価から投資収益性（ROI）重視の評価へ転換:
1. オッズを考慮した期待値計算
2. 投資戦略の最適化
3. リスク調整済み収益率
4. Kelly Criterion による賭け金最適化
5. Sharpe Ratio による投資効率評価
"""

import sqlite3
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

class ROIEvaluationSystem:
    """利益重視評価システム"""
    
    def __init__(self, db_path: str = 'cache/accuracy_tracker.db'):
        self.db_path = db_path
        self.evaluation_cache_path = 'cache/roi_evaluation.json'
        
        # 投資戦略パラメータ
        self.strategies = {
            'conservative': {
                'min_confidence': 0.6,
                'max_bet_ratio': 0.05,  # 資金の5%まで
                'target_roi': 1.2
            },
            'moderate': {
                'min_confidence': 0.5,
                'max_bet_ratio': 0.1,   # 資金の10%まで
                'target_roi': 1.5
            },
            'aggressive': {
                'min_confidence': 0.4,
                'max_bet_ratio': 0.2,   # 資金の20%まで
                'target_roi': 2.0
            }
        }
        
        self.evaluation_history = []
        self._load_evaluation_history()
    
    def calculate_roi_metrics(self, predictions: List[Dict], results: List[Dict],
                            strategy: str = 'moderate') -> Dict:
        """ROI指標の計算"""
        try:
            if not predictions or not results:
                return self._empty_roi_metrics()
            
            strategy_params = self.strategies.get(strategy, self.strategies['moderate'])
            
            # 予想と結果をマッチング
            matched_data = self._match_predictions_with_results(predictions, results)
            
            if not matched_data:
                return self._empty_roi_metrics()
            
            # 各レースの投資成果を計算
            investment_results = []
            total_investment = 0
            total_return = 0
            
            for data in matched_data:
                race_result = self._evaluate_single_race(data, strategy_params)
                if race_result:
                    investment_results.append(race_result)
                    total_investment += race_result['bet_amount']
                    total_return += race_result['return_amount']
            
            if total_investment == 0:
                return self._empty_roi_metrics()
            
            # 総合ROI指標計算
            overall_roi = (total_return - total_investment) / total_investment
            win_rate = sum(1 for r in investment_results if r['is_profit']) / len(investment_results)
            
            # リスク調整指標
            returns = [r['roi'] for r in investment_results]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            max_drawdown = self._calculate_max_drawdown([r['cumulative_profit'] for r in self._calculate_cumulative_profits(investment_results)])
            
            # Kelly Criterion による最適賭け金比率
            kelly_ratio = self._calculate_kelly_criterion(investment_results)
            
            roi_metrics = {
                'strategy': strategy,
                'total_races': len(matched_data),
                'invested_races': len(investment_results),
                'total_investment': total_investment,
                'total_return': total_return,
                'net_profit': total_return - total_investment,
                'overall_roi': round(overall_roi * 100, 2),
                'win_rate': round(win_rate * 100, 2),
                'average_roi_per_race': round(np.mean(returns) * 100, 2),
                'sharpe_ratio': round(sharpe_ratio, 3),
                'max_drawdown': round(max_drawdown * 100, 2),
                'kelly_optimal_ratio': round(kelly_ratio * 100, 2),
                'profitability_score': self._calculate_profitability_score(overall_roi, win_rate, sharpe_ratio),
                'risk_level': self._assess_risk_level(sharpe_ratio, max_drawdown),
                'investment_results': investment_results[-10:]  # 最新10件
            }
            
            logger.info(f"ROI計算完了: {strategy}戦略, ROI={roi_metrics['overall_roi']:.2f}%, 勝率={roi_metrics['win_rate']:.1f}%")
            return roi_metrics
            
        except Exception as e:
            logger.error(f"ROI指標計算エラー: {e}")
            return self._empty_roi_metrics()
    
    def _match_predictions_with_results(self, predictions: List[Dict], results: List[Dict]) -> List[Dict]:
        """予想と結果をマッチング"""
        matched = []
        
        # 結果をキーでインデックス化
        results_dict = {}
        for result in results:
            key = f"{result.get('venue_id')}_{result.get('race_number')}_{result.get('race_date')}"
            results_dict[key] = result
        
        # 予想に対応する結果を探す
        for prediction in predictions:
            key = f"{prediction.get('venue_id')}_{prediction.get('race_number')}_{prediction.get('date', prediction.get('race_date'))}"
            if key in results_dict:
                matched.append({
                    'prediction': prediction,
                    'result': results_dict[key]
                })
        
        return matched
    
    def _evaluate_single_race(self, data: Dict, strategy_params: Dict) -> Optional[Dict]:
        """単一レースの投資成果評価"""
        try:
            prediction = data['prediction']
            result = data['result']
            
            # 信頼度チェック
            confidence = prediction.get('confidence', 0.5)
            if confidence < strategy_params['min_confidence']:
                return None  # 信頼度不足で投資しない
            
            # オッズ取得（簡易版）
            predicted_win = prediction.get('predicted_win') or prediction.get('recommended_win')
            actual_win = result.get('winning_boat')
            
            if not predicted_win or not actual_win:
                return None
            
            # オッズ推定（実際のAPIから取得すべき）
            estimated_odds = self._estimate_odds(predicted_win, confidence)
            
            # 期待値計算
            hit_probability = confidence
            expected_value = (hit_probability * estimated_odds) - 1
            
            if expected_value <= 0:
                return None  # 期待値がマイナスなら投資しない
            
            # 賭け金決定（Kelly Criterionベース）
            base_bet = 100  # 基準賭け金（円）
            kelly_fraction = max(0.01, min(strategy_params['max_bet_ratio'], 
                                         (hit_probability * estimated_odds - 1) / (estimated_odds - 1)))
            bet_amount = base_bet * kelly_fraction / strategy_params['max_bet_ratio']
            
            # 結果計算
            is_hit = (predicted_win == actual_win)
            return_amount = bet_amount * estimated_odds if is_hit else 0
            profit = return_amount - bet_amount
            roi = profit / bet_amount
            
            return {
                'venue_id': prediction.get('venue_id'),
                'race_number': prediction.get('race_number'),
                'predicted_win': predicted_win,
                'actual_win': actual_win,
                'confidence': confidence,
                'estimated_odds': estimated_odds,
                'bet_amount': round(bet_amount),
                'return_amount': round(return_amount),
                'profit': round(profit),
                'roi': roi,
                'is_hit': is_hit,
                'is_profit': profit > 0,
                'expected_value': expected_value
            }
            
        except Exception as e:
            logger.warning(f"単一レース評価エラー: {e}")
            return None
    
    def _estimate_odds(self, predicted_win: int, confidence: float) -> float:
        """オッズ推定（簡易版）"""
        # 実際の実装では、オッズAPIから取得すべき
        # ここでは信頼度と艇番から推定
        
        base_odds = {
            1: 2.5, 2: 4.0, 3: 5.5, 4: 8.0, 5: 12.0, 6: 15.0
        }
        
        base = base_odds.get(predicted_win, 6.0)
        
        # 信頼度が高いほどオッズは低め（人気）に調整
        confidence_factor = 1 - (confidence - 0.5) * 0.5
        estimated = base * confidence_factor
        
        return max(1.1, min(50.0, estimated))  # 1.1倍～50倍の範囲
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Sharpe Ratio計算"""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # リスクフリーレート（無リスク収益率）を0と仮定
        return mean_return / std_return
    
    def _calculate_max_drawdown(self, cumulative_profits: List[float]) -> float:
        """最大ドローダウン計算"""
        if not cumulative_profits:
            return 0.0
        
        peak = cumulative_profits[0]
        max_dd = 0.0
        
        for profit in cumulative_profits:
            if profit > peak:
                peak = profit
            
            drawdown = (peak - profit) / max(abs(peak), 1)
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_cumulative_profits(self, investment_results: List[Dict]) -> List[Dict]:
        """累積利益計算"""
        cumulative_profit = 0
        results_with_cumulative = []
        
        for result in investment_results:
            cumulative_profit += result['profit']
            result_copy = result.copy()
            result_copy['cumulative_profit'] = cumulative_profit
            results_with_cumulative.append(result_copy)
        
        return results_with_cumulative
    
    def _calculate_kelly_criterion(self, investment_results: List[Dict]) -> float:
        """Kelly Criterion最適賭け金比率計算"""
        if not investment_results:
            return 0.01
        
        wins = [r for r in investment_results if r['is_hit']]
        losses = [r for r in investment_results if not r['is_hit']]
        
        if not wins:
            return 0.01
        
        win_probability = len(wins) / len(investment_results)
        avg_win_odds = np.mean([r['estimated_odds'] for r in wins])
        
        # Kelly公式: f = (bp - q) / b
        # b = オッズ-1, p = 勝率, q = 負け率
        b = avg_win_odds - 1
        p = win_probability
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # 安全のため、Kelly比率を制限
        return max(0.01, min(0.25, kelly_fraction))
    
    def _calculate_profitability_score(self, roi: float, win_rate: float, sharpe: float) -> float:
        """収益性スコア計算（0-100）"""
        # ROI、勝率、Sharpe比率を総合したスコア
        roi_score = min(50, max(0, roi + 50))  # ROI -50%～+50% を 0～100に変換
        win_rate_score = win_rate  # 勝率はそのまま0-100
        sharpe_score = min(50, max(0, sharpe * 25 + 25))  # Sharpe -1～+1 を 0～50に変換
        
        # 重み付き平均
        composite_score = (roi_score * 0.4 + win_rate_score * 0.4 + sharpe_score * 0.2)
        return round(composite_score, 1)
    
    def _assess_risk_level(self, sharpe: float, max_drawdown: float) -> str:
        """リスクレベル評価"""
        if sharpe > 1.0 and max_drawdown < 10:
            return "低リスク"
        elif sharpe > 0.5 and max_drawdown < 20:
            return "中リスク"
        elif sharpe > 0 and max_drawdown < 40:
            return "高リスク"
        else:
            return "危険"
    
    def _empty_roi_metrics(self) -> Dict:
        """空のROI指標"""
        return {
            'strategy': 'none',
            'total_races': 0,
            'invested_races': 0,
            'total_investment': 0,
            'total_return': 0,
            'net_profit': 0,
            'overall_roi': 0.0,
            'win_rate': 0.0,
            'average_roi_per_race': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'kelly_optimal_ratio': 1.0,
            'profitability_score': 0.0,
            'risk_level': '不明',
            'investment_results': []
        }
    
    def _load_evaluation_history(self) -> None:
        """評価履歴をロード"""
        try:
            import os
            if os.path.exists(self.evaluation_cache_path):
                with open(self.evaluation_cache_path, 'r', encoding='utf-8') as f:
                    self.evaluation_history = json.load(f)
        except Exception as e:
            logger.warning(f"評価履歴ロードエラー: {e}")
            self.evaluation_history = []
    
    def save_evaluation_result(self, roi_metrics: Dict) -> None:
        """評価結果を保存"""
        try:
            import os
            
            # 現在時刻を追加
            roi_metrics['evaluated_at'] = datetime.now().isoformat()
            
            # 履歴に追加
            self.evaluation_history.append(roi_metrics)
            
            # 最新100件のみ保持
            if len(self.evaluation_history) > 100:
                self.evaluation_history = self.evaluation_history[-100:]
            
            # ファイルに保存
            os.makedirs('cache', exist_ok=True)
            with open(self.evaluation_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"評価結果保存エラー: {e}")
    
    def get_roi_report(self, days: int = 7) -> Dict:
        """ROIレポート生成"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 予想データ取得
            cursor.execute('''
                SELECT venue_id, race_number, predicted_win, confidence, race_date,
                       prediction_data
                FROM predictions 
                WHERE race_date >= date('now', '-{} days')
                ORDER BY race_date DESC
            '''.format(days))
            
            predictions = []
            for row in cursor.fetchall():
                venue_id, race_number, predicted_win, confidence, race_date, prediction_data_json = row
                
                prediction_data = {}
                if prediction_data_json:
                    try:
                        prediction_data = json.loads(prediction_data_json)
                    except:
                        pass
                
                predictions.append({
                    'venue_id': venue_id,
                    'race_number': race_number,
                    'predicted_win': predicted_win,
                    'confidence': confidence or 0.5,
                    'race_date': race_date,
                    'prediction_data': prediction_data
                })
            
            # 結果データ取得
            cursor.execute('''
                SELECT venue_id, race_number, winning_boat, race_date
                FROM race_results 
                WHERE race_date >= date('now', '-{} days')
            '''.format(days))
            
            results = []
            for row in cursor.fetchall():
                venue_id, race_number, winning_boat, race_date = row
                results.append({
                    'venue_id': venue_id,
                    'race_number': race_number,
                    'winning_boat': winning_boat,
                    'race_date': race_date
                })
            
            conn.close()
            
            # 各戦略でROI計算
            roi_report = {}
            for strategy in self.strategies.keys():
                roi_metrics = self.calculate_roi_metrics(predictions, results, strategy)
                roi_report[strategy] = roi_metrics
                
                # 評価結果を保存
                self.save_evaluation_result(roi_metrics)
            
            # 最適戦略選択
            best_strategy = max(roi_report.keys(), 
                              key=lambda x: roi_report[x]['profitability_score'])
            
            roi_report['recommended_strategy'] = best_strategy
            roi_report['evaluation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            logger.info(f"ROIレポート生成完了: 推奨戦略={best_strategy}")
            return roi_report
            
        except Exception as e:
            logger.error(f"ROIレポート生成エラー: {e}")
            return {'error': str(e)}

if __name__ == "__main__":
    # テスト実行
    system = ROIEvaluationSystem()
    report = system.get_roi_report(days=7)
    
    print("=== ROI評価レポート ===")
    for strategy, metrics in report.items():
        if strategy not in ['recommended_strategy', 'evaluation_date']:
            print(f"\n【{strategy}戦略】")
            print(f"ROI: {metrics['overall_roi']:.2f}%")
            print(f"勝率: {metrics['win_rate']:.1f}%")
            print(f"収益性スコア: {metrics['profitability_score']:.1f}")
            print(f"リスクレベル: {metrics['risk_level']}")
    
    if 'recommended_strategy' in report:
        print(f"\n🏆 推奨戦略: {report['recommended_strategy']}")