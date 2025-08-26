"""
高度投資戦略システム v1.0

動的ベット調整、複数レース最適化、リスク分散投資による
ROI最大化投資戦略システム
"""
import numpy as np
import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings
warnings.filterwarnings('ignore')


class AdvancedInvestmentStrategy:
    def __init__(self, db_path='cache/accuracy_tracker.db'):
        """高度投資戦略システム初期化"""
        self.db_path = db_path
        self.strategies = {
            'conservative': {'max_bet_ratio': 0.02, 'kelly_multiplier': 0.25, 'risk_tolerance': 0.1},
            'moderate': {'max_bet_ratio': 0.05, 'kelly_multiplier': 0.5, 'risk_tolerance': 0.2},
            'aggressive': {'max_bet_ratio': 0.1, 'kelly_multiplier': 0.75, 'risk_tolerance': 0.35}
        }
        self.current_bankroll = 10000  # 初期資金
        self.daily_limit = 0.2  # 1日最大リスク
        self.consecutive_loss_count = 0
        self.win_streak = 0
        self.performance_metrics = {}
        self._load_performance_history()
    
    def _load_performance_history(self):
        """投資成績履歴をロード"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 投資履歴テーブル作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS investment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_str TEXT NOT NULL,
                    race_key TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    bet_type TEXT NOT NULL,
                    bet_amount INTEGER,
                    predicted_confidence REAL,
                    actual_odds REAL,
                    result TEXT,
                    profit_loss INTEGER,
                    bankroll_after INTEGER,
                    roi REAL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 過去7日間の成績を取得
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT strategy_name, 
                       AVG(roi) as avg_roi,
                       COUNT(*) as total_bets,
                       SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                       AVG(profit_loss) as avg_profit,
                       MAX(bankroll_after) as peak_bankroll,
                       MIN(bankroll_after) as lowest_bankroll
                FROM investment_history 
                WHERE date_str >= ?
                GROUP BY strategy_name
            ''', (seven_days_ago,))
            
            results = cursor.fetchall()
            for row in results:
                strategy, avg_roi, total_bets, wins, avg_profit, peak, lowest = row
                self.performance_metrics[strategy] = {
                    'avg_roi': avg_roi or 0.0,
                    'win_rate': (wins / total_bets) if total_bets > 0 else 0.0,
                    'total_bets': total_bets,
                    'avg_profit': avg_profit or 0.0,
                    'peak_bankroll': peak or self.current_bankroll,
                    'lowest_bankroll': lowest or self.current_bankroll,
                    'max_drawdown': ((peak or self.current_bankroll) - (lowest or self.current_bankroll)) / (peak or self.current_bankroll) if peak else 0.0
                }
            
            # 現在の資金状況を更新
            cursor.execute('''
                SELECT bankroll_after FROM investment_history 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            latest_bankroll = cursor.fetchone()
            if latest_bankroll:
                self.current_bankroll = latest_bankroll[0]
            
            conn.close()
            print(f"[INFO] 投資履歴ロード完了: 現在資金={self.current_bankroll}円")
        
        except Exception as e:
            print(f"[ERROR] 投資履歴ロードエラー: {e}")
    
    @property
    def daily_spent(self):
        """本日の投資額をリアルタイムでデータベースから計算"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(bet_amount) FROM investment_history 
                WHERE date_str = ?
            ''', (today,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] is not None else 0
            
        except Exception as e:
            print(f"[WARNING] daily_spent計算エラー: {e}")
            return 0
    
    def kelly_criterion(self, win_probability, odds, confidence_multiplier=1.0):
        """ケリー基準によるベット額計算"""
        try:
            if win_probability <= 0 or odds <= 1.0:
                return 0.0
            
            # ケリー基準: f = (bp - q) / b
            # b = オッズ-1, p = 勝率, q = 負率
            b = odds - 1.0
            p = win_probability * confidence_multiplier
            q = 1.0 - p
            
            kelly_fraction = (b * p - q) / b
            
            # 負の値の場合はベットしない
            if kelly_fraction <= 0:
                return 0.0
            
            return min(kelly_fraction, 0.25)  # 最大25%に制限
        
        except Exception as e:
            print(f"[ERROR] ケリー基準計算エラー: {e}")
            return 0.0
    
    def dynamic_bet_adjustment(self, base_bet_amount, strategy_name):
        """動的ベット調整"""
        try:
            adjustment_factor = 1.0
            
            # 連敗調整
            if self.consecutive_loss_count >= 3:
                # 連敗時はベット額を段階的に削減
                reduction = min(0.8, 0.9 ** self.consecutive_loss_count)
                adjustment_factor *= reduction
                print(f"[INFO] 連敗調整: {self.consecutive_loss_count}連敗, 調整係数={reduction:.2f}")
            
            # 連勝調整
            elif self.win_streak >= 3:
                # 連勝時はベット額を慎重に増加
                increase = min(1.3, 1.1 ** min(self.win_streak, 5))
                adjustment_factor *= increase
                print(f"[INFO] 連勝調整: {self.win_streak}連勝, 調整係数={increase:.2f}")
            
            # 資金残高調整
            bankroll_ratio = self.current_bankroll / 10000  # 初期資金に対する比率
            if bankroll_ratio < 0.5:
                # 資金が半分以下の場合は保守的に
                adjustment_factor *= 0.5
                print("[INFO] 低資金調整: 保守的ベット")
            elif bankroll_ratio > 2.0:
                # 資金が2倍以上の場合は積極的に
                adjustment_factor *= 1.2
                print("[INFO] 高資金調整: 積極的ベット")
            
            # 1日の使用限度チェック
            daily_limit_amount = self.current_bankroll * self.daily_limit
            if self.daily_spent >= daily_limit_amount:
                print(f"[WARNING] 日次限度額到達: {self.daily_spent}円/{daily_limit_amount}円")
                return 0
            
            adjusted_amount = int(base_bet_amount * adjustment_factor)
            
            # 残り使用可能額をチェック
            remaining_daily_budget = daily_limit_amount - self.daily_spent
            adjusted_amount = min(adjusted_amount, remaining_daily_budget)
            
            return max(0, adjusted_amount)
        
        except Exception as e:
            print(f"[ERROR] 動的ベット調整エラー: {e}")
            return base_bet_amount
    
    def multi_race_optimization(self, race_predictions):
        """複数レース最適化"""
        try:
            if len(race_predictions) <= 1:
                return race_predictions
            
            # 各レースの期待値を計算
            race_values = []
            for race in race_predictions:
                confidence = race.get('confidence', 50) / 100.0
                estimated_odds = race.get('estimated_odds', 3.0)
                expected_value = confidence * (estimated_odds - 1) - (1 - confidence)
                
                race_values.append({
                    'race': race,
                    'expected_value': expected_value,
                    'confidence': confidence,
                    'risk_score': 1.0 - confidence
                })
            
            # 期待値でソート
            race_values.sort(key=lambda x: x['expected_value'], reverse=True)
            
            # 上位レースを選択（資金配分を考慮）
            available_budget = self.current_bankroll * self.daily_limit - self.daily_spent
            selected_races = []
            total_allocation = 0
            
            for race_value in race_values:
                if race_value['expected_value'] > 0 and total_allocation < available_budget:
                    # 資金配分を調整
                    allocation_ratio = min(0.3, race_value['confidence'] * 0.5)
                    allocation = available_budget * allocation_ratio
                    
                    if total_allocation + allocation <= available_budget:
                        race_value['race']['recommended_bet'] = int(allocation)
                        selected_races.append(race_value['race'])
                        total_allocation += allocation
            
            print(f"[INFO] 複数レース最適化: {len(selected_races)}レース選択, 総配分={total_allocation}円")
            return selected_races
        
        except Exception as e:
            print(f"[ERROR] 複数レース最適化エラー: {e}")
            return race_predictions
    
    def risk_diversification(self, race_prediction):
        """リスク分散投資"""
        try:
            confidence = race_prediction.get('confidence', 50) / 100.0
            base_bet = race_prediction.get('recommended_bet', 1000)
            
            # 券種別配分比率
            bet_distribution = {
                'win': 0.5,      # 単勝 50%
                'place': 0.3,    # 複勝 30%
                'trifecta': 0.2  # 三連単 20%
            }
            
            # 信頼度による調整
            if confidence < 0.6:
                # 低信頼度の場合は複勝を重視
                bet_distribution = {'win': 0.3, 'place': 0.5, 'trifecta': 0.2}
            elif confidence > 0.8:
                # 高信頼度の場合は単勝を重視
                bet_distribution = {'win': 0.6, 'place': 0.2, 'trifecta': 0.2}
            
            diversified_bets = {}
            for bet_type, ratio in bet_distribution.items():
                bet_amount = int(base_bet * ratio)
                if bet_amount >= 100:  # 最小ベット額
                    diversified_bets[bet_type] = {
                        'amount': bet_amount,
                        'target': race_prediction.get(bet_type, [1]),
                        'confidence': confidence,
                        'expected_odds': self._estimate_odds(bet_type, confidence)
                    }
            
            print(f"[INFO] リスク分散投資: {len(diversified_bets)}券種, 総額={base_bet}円")
            return diversified_bets
        
        except Exception as e:
            print(f"[ERROR] リスク分散投資エラー: {e}")
            return {'win': {'amount': 1000, 'target': [1], 'confidence': 0.5, 'expected_odds': 3.0}}
    
    def _estimate_odds(self, bet_type, confidence):
        """オッズ推定"""
        try:
            # 信頼度からオッズを逆算
            if bet_type == 'win':
                # 単勝: 高信頼度 = 低オッズ
                return max(1.5, 10.0 / max(0.1, confidence * 10))
            elif bet_type == 'place':
                # 複勝: より低オッズ
                return max(1.2, 5.0 / max(0.1, confidence * 10))
            elif bet_type == 'trifecta':
                # 三連単: 高オッズ
                return max(10.0, 100.0 / max(0.01, confidence * 100))
            else:
                return 3.0
        except:
            return 3.0
    
    def calculate_optimal_bet(self, race_prediction, strategy_name='moderate'):
        """最適ベット額計算"""
        try:
            confidence = race_prediction.get('confidence', 50) / 100.0
            estimated_odds = race_prediction.get('estimated_odds', 3.0)
            
            strategy_config = self.strategies.get(strategy_name, self.strategies['moderate'])
            
            # ケリー基準による基本ベット額
            kelly_fraction = self.kelly_criterion(confidence, estimated_odds, strategy_config['kelly_multiplier'])
            base_bet_amount = int(self.current_bankroll * kelly_fraction)
            
            # 戦略別最大ベット額制限
            max_bet = int(self.current_bankroll * strategy_config['max_bet_ratio'])
            base_bet_amount = min(base_bet_amount, max_bet)
            
            # 動的調整
            adjusted_bet = self.dynamic_bet_adjustment(base_bet_amount, strategy_name)
            
            # リスク分散
            race_prediction['recommended_bet'] = adjusted_bet
            diversified_bets = self.risk_diversification(race_prediction)
            
            result = {
                'strategy': strategy_name,
                'total_bet': adjusted_bet,
                'diversified_bets': diversified_bets,
                'kelly_fraction': kelly_fraction,
                'confidence': confidence,
                'estimated_roi': (confidence * (estimated_odds - 1) - (1 - confidence)) * 100,
                'risk_level': strategy_config['risk_tolerance']
            }
            
            print(f"[INFO] 最適ベット計算完了: {strategy_name}戦略, 総額={adjusted_bet}円")
            return result
        
        except Exception as e:
            print(f"[ERROR] 最適ベット計算エラー: {e}")
            return {
                'strategy': strategy_name,
                'total_bet': 1000,
                'diversified_bets': {'win': {'amount': 1000, 'target': [1], 'confidence': 0.5}},
                'error': str(e)
            }
    
    def update_investment_result(self, race_key, bet_result, actual_result):
        """投資結果の更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            profit_loss = 0
            
            # 各券種の結果を処理
            for bet_type, bet_info in bet_result.get('diversified_bets', {}).items():
                bet_amount = bet_info.get('amount', 0)
                target = bet_info.get('target', [])
                
                # 的中判定（簡略版）
                is_hit = False
                payout = 0
                
                if bet_type == 'win' and actual_result.get('win') in target:
                    is_hit = True
                    payout = bet_amount * bet_info.get('expected_odds', 3.0)
                elif bet_type == 'place' and any(p in target for p in actual_result.get('place', [])):
                    is_hit = True
                    payout = bet_amount * bet_info.get('expected_odds', 2.0)
                elif bet_type == 'trifecta' and actual_result.get('trifecta') == target:
                    is_hit = True
                    payout = bet_amount * bet_info.get('expected_odds', 50.0)
                
                # 損益計算
                race_profit_loss = payout - bet_amount if is_hit else -bet_amount
                profit_loss += race_profit_loss
                
                # データベースに記録
                cursor.execute('''
                    INSERT INTO investment_history 
                    (date_str, race_key, strategy_name, bet_type, bet_amount, 
                     predicted_confidence, actual_odds, result, profit_loss, bankroll_after, roi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_str,
                    race_key,
                    bet_result.get('strategy', 'moderate'),
                    bet_type,
                    bet_amount,
                    bet_info.get('confidence', 0.5),
                    payout / bet_amount if payout > 0 else 0.0,
                    'HIT' if is_hit else 'MISS',
                    race_profit_loss,
                    self.current_bankroll + race_profit_loss,
                    (race_profit_loss / bet_amount * 100) if bet_amount > 0 else 0.0
                ))
            
            # 資金とストリークを更新
            self.current_bankroll += profit_loss
            # daily_spentは@propertyでリアルタイム計算するため、ここでは更新不要
            
            if profit_loss > 0:
                self.win_streak += 1
                self.consecutive_loss_count = 0
            else:
                self.consecutive_loss_count += 1
                self.win_streak = 0
            
            conn.commit()
            conn.close()
            
            print(f"[INFO] 投資結果更新: 損益={profit_loss}円, 現在資金={self.current_bankroll}円")
            return {
                'profit_loss': profit_loss,
                'new_bankroll': self.current_bankroll,
                'win_streak': self.win_streak,
                'loss_streak': self.consecutive_loss_count
            }
        
        except Exception as e:
            print(f"[ERROR] 投資結果更新エラー: {e}")
            return {'error': str(e)}
    
    def get_strategy_recommendation(self, current_performance=None):
        """戦略推奨"""
        try:
            if not self.performance_metrics:
                return 'moderate'
            
            best_strategy = 'moderate'
            best_score = -float('inf')
            
            for strategy_name, metrics in self.performance_metrics.items():
                # 総合スコア計算（ROI重視）
                roi_score = metrics.get('avg_roi', 0.0) * 0.5
                win_rate_score = metrics.get('win_rate', 0.0) * 0.3
                drawdown_penalty = metrics.get('max_drawdown', 0.0) * -0.2
                
                total_score = roi_score + win_rate_score + drawdown_penalty
                
                if total_score > best_score:
                    best_score = total_score
                    best_strategy = strategy_name
            
            print(f"[INFO] 推奨戦略: {best_strategy} (スコア: {best_score:.2f})")
            return best_strategy
        
        except Exception as e:
            print(f"[ERROR] 戦略推奨エラー: {e}")
            return 'moderate'


def test_advanced_investment_strategy():
    """テスト実行"""
    print("=== 高度投資戦略システム テスト開始 ===")
    
    strategy = AdvancedInvestmentStrategy()
    
    # テストレース予想
    test_prediction = {
        'win': 1,
        'place': [1, 2],
        'trifecta': [1, 2, 3],
        'confidence': 75.0,
        'estimated_odds': 4.2
    }
    
    print("\n1. 最適ベット計算テスト")
    optimal_bet = strategy.calculate_optimal_bet(test_prediction, 'moderate')
    print(f"最適ベット結果: {optimal_bet}")
    
    print("\n2. 複数レース最適化テスト")
    multi_races = [test_prediction.copy() for _ in range(3)]
    for i, race in enumerate(multi_races):
        race['confidence'] = 70.0 + i * 5
        race['estimated_odds'] = 3.0 + i * 0.5
    
    optimized_races = strategy.multi_race_optimization(multi_races)
    print(f"最適化後レース数: {len(optimized_races)}")
    
    print("\n3. 戦略推奨テスト")
    recommended_strategy = strategy.get_strategy_recommendation()
    print(f"推奨戦略: {recommended_strategy}")
    
    print(f"\n4. 現在の投資状況")
    print(f"現在資金: {strategy.current_bankroll}円")
    print(f"連勝記録: {strategy.win_streak}")
    print(f"連敗記録: {strategy.consecutive_loss_count}")
    
    print("\n=== テスト完了 ===")
    return optimal_bet


if __name__ == "__main__":
    test_advanced_investment_strategy()