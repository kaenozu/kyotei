#!/usr/bin/env python3
"""
BoatraceOpenAPI専用システム - 投資管理システム
賭け金管理・収支計算・ROI分析による実用性大幅向上
"""

import sqlite3
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class BetType(Enum):
    """賭け種別"""
    WIN = "単勝"           # 1着予想
    PLACE = "複勝"         # 2着以内予想
    EXACTA = "2連単"       # 1-2着順番予想
    QUINELLA = "2連複"     # 1-2着組み合わせ予想
    TRIFECTA = "3連単"     # 1-2-3着順番予想
    TRIO = "3連複"         # 1-2-3着組み合わせ予想


class BetStatus(Enum):
    """賭け状況"""
    PENDING = "予想中"
    PLACED = "購入済み"
    WON = "的中"
    LOST = "不的中"
    CANCELLED = "取消"


@dataclass
class BetRecord:
    """賭け記録"""
    bet_id: str
    timestamp: str
    venue_id: int
    venue_name: str
    race_number: int
    bet_type: BetType
    bet_numbers: List[int]  # 予想番号
    stake_amount: float     # 賭け金
    odds: Optional[float]   # オッズ
    payout: Optional[float] # 払戻金
    status: BetStatus
    prediction_confidence: Optional[float] = None  # 予想信頼度
    actual_result: Optional[List[int]] = None      # 実際の結果
    profit_loss: Optional[float] = None            # 損益
    notes: Optional[str] = None                    # メモ
    
    def calculate_profit_loss(self) -> float:
        """損益計算"""
        if self.status == BetStatus.WON and self.payout:
            return self.payout - self.stake_amount
        elif self.status == BetStatus.LOST:
            return -self.stake_amount
        else:
            return 0.0
    
    def get_roi(self) -> float:
        """ROI計算"""
        if self.stake_amount == 0:
            return 0.0
        profit_loss = self.calculate_profit_loss()
        return (profit_loss / self.stake_amount) * 100


@dataclass
class InvestmentStrategy:
    """投資戦略"""
    name: str
    max_daily_stake: float          # 1日最大賭け金
    max_race_stake: float           # 1レース最大賭け金
    min_confidence_threshold: float # 最低信頼度閾値
    preferred_bet_types: List[BetType] # 優先賭け種別
    risk_level: str                 # リスクレベル (low/medium/high)
    kelly_criterion_enabled: bool   # ケリー基準使用
    stop_loss_percentage: float     # 損切りライン(%)
    target_roi_percentage: float    # 目標ROI(%)


class InvestmentManager:
    """投資管理システム"""
    
    def __init__(self, db_path: str = "cache/investment.db"):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.current_strategy = self._load_default_strategy()
        
        # データベース初期化
        self._init_database()
    
    def _init_database(self):
        """データベース初期化"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 賭け記録テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bet_records (
                    bet_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    venue_id INTEGER NOT NULL,
                    venue_name TEXT NOT NULL,
                    race_number INTEGER NOT NULL,
                    bet_type TEXT NOT NULL,
                    bet_numbers TEXT NOT NULL,
                    stake_amount REAL NOT NULL,
                    odds REAL,
                    payout REAL,
                    status TEXT NOT NULL,
                    prediction_confidence REAL,
                    actual_result TEXT,
                    profit_loss REAL,
                    notes TEXT
                )
            """)
            
            # 投資戦略テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS investment_strategies (
                    strategy_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    config TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE
                )
            """)
            
            # 日次統計テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_stake REAL NOT NULL,
                    total_payout REAL NOT NULL,
                    profit_loss REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    roi REAL NOT NULL,
                    bet_count INTEGER NOT NULL
                )
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.info("投資管理データベース初期化完了")
            
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
    
    def _load_default_strategy(self) -> InvestmentStrategy:
        """デフォルト投資戦略読み込み"""
        return InvestmentStrategy(
            name="保守的戦略",
            max_daily_stake=10000.0,      # 1日1万円まで
            max_race_stake=1000.0,        # 1レース1000円まで
            min_confidence_threshold=0.7, # 信頼度70%以上
            preferred_bet_types=[BetType.WIN, BetType.PLACE],
            risk_level="low",
            kelly_criterion_enabled=False,
            stop_loss_percentage=20.0,    # 20%損失で停止
            target_roi_percentage=15.0    # 目標ROI 15%
        )
    
    def calculate_optimal_stake(self, prediction_confidence: float, 
                              expected_odds: float) -> float:
        """最適賭け金計算"""
        try:
            # 信頼度チェック
            if prediction_confidence < self.current_strategy.min_confidence_threshold:
                return 0.0
            
            # 今日の累計賭け金チェック
            today_total = self.get_daily_stats(datetime.now().date())
            if today_total and today_total['total_stake'] >= self.current_strategy.max_daily_stake:
                self.logger.warning("本日の最大賭け金に達しています")
                return 0.0
            
            # 基本賭け金計算
            base_stake = self.current_strategy.max_race_stake
            
            # 信頼度による調整
            confidence_multiplier = min(prediction_confidence / 0.8, 1.0)
            
            # ケリー基準使用の場合
            if self.current_strategy.kelly_criterion_enabled and expected_odds > 1.0:
                kelly_fraction = self._calculate_kelly_criterion(
                    prediction_confidence, expected_odds
                )
                base_stake *= kelly_fraction
            else:
                base_stake *= confidence_multiplier
            
            # 上限チェック
            remaining_daily_budget = self.current_strategy.max_daily_stake
            if today_total:
                remaining_daily_budget -= today_total['total_stake']
            
            optimal_stake = min(
                base_stake,
                self.current_strategy.max_race_stake,
                remaining_daily_budget
            )
            
            return round(max(optimal_stake, 0), 0)
            
        except Exception as e:
            self.logger.error(f"最適賭け金計算エラー: {e}")
            return 0.0
    
    def _calculate_kelly_criterion(self, win_probability: float, odds: float) -> float:
        """ケリー基準計算"""
        if odds <= 1.0 or win_probability <= 0:
            return 0.0
        
        # ケリー比率 = (オッズ * 勝率 - 1) / (オッズ - 1)
        kelly_fraction = (odds * win_probability - 1) / (odds - 1)
        
        # リスク管理のため最大25%に制限
        return max(0, min(kelly_fraction, 0.25))
    
    def place_bet(self, venue_id: int, venue_name: str, race_number: int,
                  bet_type: BetType, bet_numbers: List[int], 
                  prediction_confidence: float, expected_odds: float,
                  notes: Optional[str] = None) -> Optional[BetRecord]:
        """賭け実行"""
        try:
            # 最適賭け金計算
            stake_amount = self.calculate_optimal_stake(prediction_confidence, expected_odds)
            
            if stake_amount <= 0:
                self.logger.info("賭け金が0円のため賭けをスキップ")
                return None
            
            # 賭け記録作成
            bet_id = f"BET_{int(datetime.now().timestamp())}_{venue_id}_{race_number}"
            
            bet_record = BetRecord(
                bet_id=bet_id,
                timestamp=datetime.now().isoformat(),
                venue_id=venue_id,
                venue_name=venue_name,
                race_number=race_number,
                bet_type=bet_type,
                bet_numbers=bet_numbers,
                stake_amount=stake_amount,
                odds=expected_odds,
                payout=None,
                status=BetStatus.PLACED,
                prediction_confidence=prediction_confidence,
                notes=notes
            )
            
            # データベース保存
            self._save_bet_record(bet_record)
            
            self.logger.info(f"賭け実行: {bet_id} - {stake_amount}円")
            return bet_record
            
        except Exception as e:
            self.logger.error(f"賭け実行エラー: {e}")
            return None
    
    def update_bet_result(self, bet_id: str, actual_result: List[int], 
                         payout: float = 0.0) -> bool:
        """賭け結果更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 既存記録取得
            cursor.execute("SELECT * FROM bet_records WHERE bet_id = ?", (bet_id,))
            row = cursor.fetchone()
            
            if not row:
                self.logger.warning(f"賭け記録が見つかりません: {bet_id}")
                return False
            
            # 的中判定
            bet_numbers = json.loads(row[6])  # bet_numbers
            bet_type = BetType(row[5])        # bet_type
            
            is_win = self._check_win_condition(bet_type, bet_numbers, actual_result)
            status = BetStatus.WON if is_win else BetStatus.LOST
            profit_loss = payout - row[7] if is_win else -row[7]  # payout - stake_amount
            
            # 結果更新
            cursor.execute("""
                UPDATE bet_records 
                SET actual_result = ?, payout = ?, status = ?, profit_loss = ?
                WHERE bet_id = ?
            """, (json.dumps(actual_result), payout, status.value, profit_loss, bet_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"賭け結果更新: {bet_id} - {status.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"賭け結果更新エラー: {e}")
            return False
    
    def _check_win_condition(self, bet_type: BetType, bet_numbers: List[int], 
                           actual_result: List[int]) -> bool:
        """的中判定"""
        if not actual_result or len(actual_result) < 3:
            return False
        
        if bet_type == BetType.WIN:
            return bet_numbers[0] == actual_result[0]
        elif bet_type == BetType.PLACE:
            return bet_numbers[0] in actual_result[:2]
        elif bet_type == BetType.EXACTA:
            return (len(bet_numbers) >= 2 and 
                   bet_numbers[0] == actual_result[0] and 
                   bet_numbers[1] == actual_result[1])
        elif bet_type == BetType.QUINELLA:
            return (len(bet_numbers) >= 2 and 
                   set(bet_numbers[:2]) == set(actual_result[:2]))
        elif bet_type == BetType.TRIFECTA:
            return (len(bet_numbers) >= 3 and 
                   bet_numbers[:3] == actual_result[:3])
        elif bet_type == BetType.TRIO:
            return (len(bet_numbers) >= 3 and 
                   set(bet_numbers[:3]) == set(actual_result[:3]))
        
        return False
    
    def _save_bet_record(self, bet_record: BetRecord):
        """賭け記録保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO bet_records (
                    bet_id, timestamp, venue_id, venue_name, race_number,
                    bet_type, bet_numbers, stake_amount, odds, payout,
                    status, prediction_confidence, actual_result, profit_loss, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet_record.bet_id,
                bet_record.timestamp,
                bet_record.venue_id,
                bet_record.venue_name,
                bet_record.race_number,
                bet_record.bet_type.value,
                json.dumps(bet_record.bet_numbers),
                bet_record.stake_amount,
                bet_record.odds,
                bet_record.payout,
                bet_record.status.value,
                bet_record.prediction_confidence,
                json.dumps(bet_record.actual_result) if bet_record.actual_result else None,
                bet_record.profit_loss,
                bet_record.notes
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"賭け記録保存エラー: {e}")
    
    def get_daily_stats(self, date: datetime.date) -> Optional[Dict[str, Any]]:
        """日次統計取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_str = date.strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT 
                    SUM(stake_amount) as total_stake,
                    SUM(COALESCE(payout, 0)) as total_payout,
                    SUM(COALESCE(profit_loss, -stake_amount)) as profit_loss,
                    COUNT(*) as bet_count,
                    SUM(CASE WHEN status = '的中' THEN 1 ELSE 0 END) as win_count
                FROM bet_records 
                WHERE DATE(timestamp) = ?
            """, (date_str,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:  # total_stake が存在する場合
                total_stake, total_payout, profit_loss, bet_count, win_count = row
                win_rate = (win_count / bet_count) * 100 if bet_count > 0 else 0
                roi = (profit_loss / total_stake) * 100 if total_stake > 0 else 0
                
                return {
                    'date': date_str,
                    'total_stake': total_stake,
                    'total_payout': total_payout,
                    'profit_loss': profit_loss,
                    'win_rate': win_rate,
                    'roi': roi,
                    'bet_count': bet_count,
                    'win_count': win_count
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"日次統計取得エラー: {e}")
            return None
    
    def get_period_summary(self, days: int = 30) -> Dict[str, Any]:
        """期間サマリー取得"""
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    SUM(stake_amount) as total_stake,
                    SUM(COALESCE(payout, 0)) as total_payout,
                    SUM(COALESCE(profit_loss, -stake_amount)) as profit_loss,
                    COUNT(*) as bet_count,
                    SUM(CASE WHEN status = '的中' THEN 1 ELSE 0 END) as win_count,
                    AVG(prediction_confidence) as avg_confidence
                FROM bet_records 
                WHERE DATE(timestamp) >= ?
            """, (start_date.strftime('%Y-%m-%d'),))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                total_stake, total_payout, profit_loss, bet_count, win_count, avg_confidence = row
                win_rate = (win_count / bet_count) * 100 if bet_count > 0 else 0
                roi = (profit_loss / total_stake) * 100 if total_stake > 0 else 0
                
                return {
                    'period_days': days,
                    'total_stake': total_stake,
                    'total_payout': total_payout,
                    'profit_loss': profit_loss,
                    'win_rate': win_rate,
                    'roi': roi,
                    'bet_count': bet_count,
                    'win_count': win_count,
                    'avg_confidence': avg_confidence or 0,
                    'daily_average_stake': total_stake / days if total_stake else 0,
                    'daily_average_profit': profit_loss / days if profit_loss else 0
                }
            
            return {
                'period_days': days,
                'total_stake': 0,
                'total_payout': 0,
                'profit_loss': 0,
                'win_rate': 0,
                'roi': 0,
                'bet_count': 0,
                'win_count': 0,
                'avg_confidence': 0,
                'daily_average_stake': 0,
                'daily_average_profit': 0
            }
            
        except Exception as e:
            self.logger.error(f"期間サマリー取得エラー: {e}")
            return {}
    
    def get_recent_bets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近の賭け記録取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM bet_records 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # 辞書形式に変換
            columns = [
                'bet_id', 'timestamp', 'venue_id', 'venue_name', 'race_number',
                'bet_type', 'bet_numbers', 'stake_amount', 'odds', 'payout',
                'status', 'prediction_confidence', 'actual_result', 'profit_loss', 'notes'
            ]
            
            result = []
            for row in rows:
                bet_dict = dict(zip(columns, row))
                # JSON文字列をパース
                bet_dict['bet_numbers'] = json.loads(bet_dict['bet_numbers'])
                if bet_dict['actual_result']:
                    bet_dict['actual_result'] = json.loads(bet_dict['actual_result'])
                result.append(bet_dict)
            
            return result
            
        except Exception as e:
            self.logger.error(f"最近の賭け記録取得エラー: {e}")
            return []


# グローバルインスタンス
investment_manager = InvestmentManager()