#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投資分析モジュール - Phase 2: 高度分析機能
競艇予想投資の詳細分析とリスク管理
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import math
from collections import defaultdict


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    var_95: float  # 95% Value at Risk
    expected_shortfall: float
    calmar_ratio: float
    win_streak: int
    loss_streak: int
    consecutive_wins: int
    consecutive_losses: int


@dataclass
class VenueAnalysis:
    """会場別分析結果"""
    venue_id: int
    venue_name: str
    total_bets: int
    win_rate: float
    roi: float
    avg_odds: float
    avg_stake: float
    profit_loss: float
    confidence_accuracy: float
    best_bet_types: List[str]


@dataclass
class TimeSeriesAnalysis:
    """時系列分析結果"""
    daily_pnl: List[float]
    cumulative_pnl: List[float]
    rolling_sharpe: List[float]
    rolling_vol: List[float]
    dates: List[str]
    trend_direction: str
    momentum: float


class InvestmentAnalytics:
    """投資分析エンジン"""
    
    def __init__(self, db_path: str = "cache/investment_records.db"):
        self.db_path = db_path
        self.ensure_database()
    
    def ensure_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bet_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                venue_id INTEGER NOT NULL,
                venue_name TEXT NOT NULL,
                race_number INTEGER NOT NULL,
                bet_type TEXT NOT NULL,
                combination TEXT,
                stake_amount REAL NOT NULL,
                odds REAL,
                payout REAL,
                profit_loss REAL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                prediction_factors TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def calculate_performance_metrics(self, days: int = 30) -> PerformanceMetrics:
        """詳細パフォーマンス指標計算"""
        conn = sqlite3.connect(self.db_path)
        
        # データ取得
        query = '''
            SELECT profit_loss, timestamp, status 
            FROM bet_records 
            WHERE timestamp >= date('now', '-{} days')
            AND status IN ('的中', '不的中')
            ORDER BY timestamp
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        returns = df['profit_loss'].values
        daily_returns = self._aggregate_daily_returns(df)
        
        # リスク指標計算
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        sortino_ratio = self._calculate_sortino_ratio(daily_returns)
        max_drawdown = self._calculate_max_drawdown(np.cumsum(returns))
        volatility = np.std(daily_returns) * np.sqrt(252)  # 年間ボラティリティ
        var_95 = np.percentile(daily_returns, 5)
        expected_shortfall = np.mean(daily_returns[daily_returns <= var_95])
        calmar_ratio = np.mean(daily_returns) * 252 / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 連勝・連敗分析
        win_streak, loss_streak, current_wins, current_losses = self._analyze_streaks(df['status'].values)
        
        return PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            var_95=var_95,
            expected_shortfall=expected_shortfall if not np.isnan(expected_shortfall) else 0,
            calmar_ratio=calmar_ratio,
            win_streak=win_streak,
            loss_streak=loss_streak,
            consecutive_wins=current_wins,
            consecutive_losses=current_losses
        )
    
    def analyze_venue_performance(self, days: int = 30) -> List[VenueAnalysis]:
        """会場別パフォーマンス分析"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT venue_id, venue_name, bet_type, stake_amount, odds, 
                   payout, profit_loss, confidence, status
            FROM bet_records 
            WHERE timestamp >= date('now', '-{} days')
            ORDER BY venue_id
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return []
        
        venue_analyses = []
        
        for venue_id in df['venue_id'].unique():
            venue_data = df[df['venue_id'] == venue_id]
            venue_name = venue_data['venue_name'].iloc[0]
            
            total_bets = len(venue_data)
            wins = len(venue_data[venue_data['status'] == '的中'])
            win_rate = wins / total_bets * 100 if total_bets > 0 else 0
            
            total_stake = venue_data['stake_amount'].sum()
            total_payout = venue_data['payout'].fillna(0).sum()
            roi = (total_payout - total_stake) / total_stake * 100 if total_stake > 0 else 0
            
            avg_odds = venue_data['odds'].mean()
            avg_stake = venue_data['stake_amount'].mean()
            profit_loss = venue_data['profit_loss'].fillna(0).sum()
            
            # 信頼度精度
            confidence_accuracy = self._calculate_confidence_accuracy(venue_data)
            
            # 最適賭け種別
            best_bet_types = self._find_best_bet_types(venue_data)
            
            venue_analyses.append(VenueAnalysis(
                venue_id=venue_id,
                venue_name=venue_name,
                total_bets=total_bets,
                win_rate=win_rate,
                roi=roi,
                avg_odds=avg_odds,
                avg_stake=avg_stake,
                profit_loss=profit_loss,
                confidence_accuracy=confidence_accuracy,
                best_bet_types=best_bet_types
            ))
        
        return sorted(venue_analyses, key=lambda x: x.roi, reverse=True)
    
    def generate_time_series_analysis(self, days: int = 30) -> TimeSeriesAnalysis:
        """時系列分析"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT DATE(timestamp) as date, SUM(profit_loss) as daily_pnl
            FROM bet_records 
            WHERE timestamp >= date('now', '-{} days')
            AND profit_loss IS NOT NULL
            GROUP BY DATE(timestamp)
            ORDER BY date
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return TimeSeriesAnalysis([], [], [], [], [], "不明", 0.0)
        
        daily_pnl = df['daily_pnl'].values
        cumulative_pnl = np.cumsum(daily_pnl)
        dates = df['date'].values
        
        # ローリングシャープレシオ（7日間）
        rolling_sharpe = []
        rolling_vol = []
        
        for i in range(len(daily_pnl)):
            start_idx = max(0, i - 6)
            window_returns = daily_pnl[start_idx:i+1]
            
            if len(window_returns) >= 3:
                sharpe = np.mean(window_returns) / np.std(window_returns) if np.std(window_returns) > 0 else 0
                vol = np.std(window_returns)
            else:
                sharpe = 0
                vol = 0
            
            rolling_sharpe.append(sharpe)
            rolling_vol.append(vol)
        
        # トレンド分析
        if len(cumulative_pnl) >= 2:
            recent_trend = cumulative_pnl[-1] - cumulative_pnl[-min(7, len(cumulative_pnl))]
            trend_direction = "上昇" if recent_trend > 0 else "下降" if recent_trend < 0 else "横ばい"
            momentum = recent_trend / min(7, len(cumulative_pnl))
        else:
            trend_direction = "不明"
            momentum = 0.0
        
        return TimeSeriesAnalysis(
            daily_pnl=daily_pnl.tolist(),
            cumulative_pnl=cumulative_pnl.tolist(),
            rolling_sharpe=rolling_sharpe,
            rolling_vol=rolling_vol,
            dates=dates.tolist(),
            trend_direction=trend_direction,
            momentum=momentum
        )
    
    def calculate_risk_adjusted_kelly(self, confidence: float, odds: float, 
                                      current_bankroll: float) -> float:
        """リスク調整ケリー基準計算"""
        if confidence <= 0.5 or odds <= 1.0:
            return 0.0
        
        # 基本ケリー基準
        win_prob = confidence
        kelly_fraction = (win_prob * odds - 1) / (odds - 1)
        
        # リスク調整
        performance_metrics = self.calculate_performance_metrics(30)
        
        # ボラティリティ調整
        volatility_adjustment = max(0.1, 1.0 - performance_metrics.volatility / 0.5)
        
        # ドローダウン調整
        drawdown_adjustment = max(0.1, 1.0 - abs(performance_metrics.max_drawdown) / 0.3)
        
        # 連敗調整
        streak_adjustment = max(0.1, 1.0 - performance_metrics.consecutive_losses / 5.0)
        
        # 最終調整係数
        risk_multiplier = volatility_adjustment * drawdown_adjustment * streak_adjustment
        
        # 調整後ケリー基準（上限25%）
        adjusted_kelly = min(0.25, kelly_fraction * risk_multiplier)
        
        return max(0.0, adjusted_kelly) * current_bankroll
    
    def get_optimization_recommendations(self) -> Dict[str, any]:
        """戦略最適化推奨事項"""
        performance = self.calculate_performance_metrics(30)
        venue_analysis = self.analyze_venue_performance(30)
        time_series = self.generate_time_series_analysis(30)
        
        recommendations = {
            "risk_management": [],
            "venue_strategy": [],
            "timing_strategy": [],
            "stake_management": [],
            "overall_assessment": ""
        }
        
        # リスク管理推奨
        if performance.max_drawdown < -0.2:
            recommendations["risk_management"].append("ドローダウンが20%を超過。リスク軽減が必要")
        
        if performance.consecutive_losses > 5:
            recommendations["risk_management"].append("連敗が長期化。一時的な投資停止を検討")
        
        if performance.volatility > 0.4:
            recommendations["risk_management"].append("ボラティリティが高い。賭け金の分散を検討")
        
        # 会場戦略推奨
        best_venues = [v for v in venue_analysis if v.roi > 10 and v.total_bets >= 5]
        worst_venues = [v for v in venue_analysis if v.roi < -10 and v.total_bets >= 5]
        
        if best_venues:
            recommendations["venue_strategy"].append(
                f"高収益会場: {', '.join([v.venue_name for v in best_venues[:3]])}"
            )
        
        if worst_venues:
            recommendations["venue_strategy"].append(
                f"低収益会場での投資を控える: {', '.join([v.venue_name for v in worst_venues[:3]])}"
            )
        
        # タイミング戦略
        if time_series.trend_direction == "下降" and time_series.momentum < -1000:
            recommendations["timing_strategy"].append("下降トレンド継続中。慎重な投資を推奨")
        
        # 総合評価
        if performance.sharpe_ratio > 1.0:
            recommendations["overall_assessment"] = "優秀なパフォーマンス"
        elif performance.sharpe_ratio > 0.5:
            recommendations["overall_assessment"] = "良好なパフォーマンス"
        elif performance.sharpe_ratio > 0:
            recommendations["overall_assessment"] = "平均的なパフォーマンス"
        else:
            recommendations["overall_assessment"] = "改善が必要なパフォーマンス"
        
        return recommendations
    
    def _aggregate_daily_returns(self, df: pd.DataFrame) -> np.ndarray:
        """日次リターン集計"""
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_returns = df.groupby('date')['profit_loss'].sum().values
        return daily_returns
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """シャープレシオ計算"""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        return np.mean(returns) / np.std(returns) * np.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """ソルティノレシオ計算"""
        if len(returns) == 0:
            return 0.0
        
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0:
            return float('inf') if np.mean(returns) > 0 else 0.0
        
        downside_deviation = np.std(negative_returns)
        if downside_deviation == 0:
            return 0.0
        
        return np.mean(returns) / downside_deviation * np.sqrt(252)
    
    def _calculate_max_drawdown(self, cumulative_returns: np.ndarray) -> float:
        """最大ドローダウン計算"""
        if len(cumulative_returns) == 0:
            return 0.0
        
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / np.maximum(peak, 1)
        return np.min(drawdown)
    
    def _analyze_streaks(self, statuses: np.ndarray) -> Tuple[int, int, int, int]:
        """連勝・連敗分析"""
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for status in statuses:
            if status == '的中':
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            elif status == '不的中':
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        return max_win_streak, max_loss_streak, current_win_streak, current_loss_streak
    
    def _calculate_confidence_accuracy(self, venue_data: pd.DataFrame) -> float:
        """信頼度精度計算"""
        if len(venue_data) == 0:
            return 0.0
        
        accurate_predictions = 0
        total_predictions = 0
        
        for _, row in venue_data.iterrows():
            if row['status'] in ['的中', '不的中']:
                total_predictions += 1
                confidence = row['confidence']
                actual_win = row['status'] == '的中'
                
                # 信頼度が高い（>0.7）場合の精度
                if confidence > 0.7 and actual_win:
                    accurate_predictions += 1
                elif confidence <= 0.7 and not actual_win:
                    accurate_predictions += 1
        
        return accurate_predictions / total_predictions * 100 if total_predictions > 0 else 0.0
    
    def _find_best_bet_types(self, venue_data: pd.DataFrame) -> List[str]:
        """最適賭け種別特定"""
        bet_type_performance = defaultdict(list)
        
        for _, row in venue_data.iterrows():
            if row['profit_loss'] is not None:
                bet_type_performance[row['bet_type']].append(row['profit_loss'])
        
        best_types = []
        for bet_type, profits in bet_type_performance.items():
            if len(profits) >= 3:  # 最低3回の実績
                avg_profit = np.mean(profits)
                if avg_profit > 0:
                    best_types.append((bet_type, avg_profit))
        
        # 平均利益順でソート
        best_types.sort(key=lambda x: x[1], reverse=True)
        return [bt[0] for bt in best_types[:3]]  # 上位3つ


if __name__ == "__main__":
    # テスト実行
    analytics = InvestmentAnalytics()
    
    # サンプルデータでテスト
    print("投資分析システムテスト実行中...")
    
    performance = analytics.calculate_performance_metrics(30)
    print(f"シャープレシオ: {performance.sharpe_ratio:.2f}")
    print(f"最大ドローダウン: {performance.max_drawdown:.2%}")
    
    recommendations = analytics.get_optimization_recommendations()
    print(f"総合評価: {recommendations['overall_assessment']}")