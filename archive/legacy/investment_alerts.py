#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投資アラートシステム - Phase 3: 実用化機能
リスク監視・パフォーマンス通知・トレンド検知
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from investment_analytics import InvestmentAnalytics, PerformanceMetrics


class AlertSeverity(Enum):
    """アラート重要度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertType(Enum):
    """アラート種別"""
    PERFORMANCE = "performance"
    RISK = "risk"
    STREAK = "streak"
    DRAWDOWN = "drawdown"
    BUDGET = "budget"
    CONFIDENCE = "confidence"
    TREND = "trend"


@dataclass
class AlertRule:
    """アラートルール"""
    id: str
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: str  # 条件式
    threshold: float
    enabled: bool = True
    cooldown_minutes: int = 60  # 連続アラート防止（分）
    notification_methods: List[str] = None  # ['email', 'log', 'webhook']
    custom_message: str = ""


@dataclass
class Alert:
    """アラート"""
    id: str
    rule_id: str
    timestamp: datetime
    severity: AlertSeverity
    alert_type: AlertType
    title: str
    message: str
    data: Dict
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


class InvestmentAlertSystem:
    """投資アラートシステム"""
    
    def __init__(self, db_path: str = "cache/investment_records.db"):
        self.db_path = db_path
        self.analytics = InvestmentAnalytics(db_path)
        self.alert_db_path = "cache/investment_alerts.db"
        self.rules: Dict[str, AlertRule] = {}
        self.last_triggered: Dict[str, datetime] = {}
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # ログ設定
        self.logger = logging.getLogger(__name__)
        
        # データベース初期化
        self.ensure_alert_database()
        
        # デフォルトルール設定
        self._setup_default_rules()
    
    def ensure_alert_database(self):
        """アラートデータベース初期化"""
        conn = sqlite3.connect(self.alert_db_path)
        
        # アラート履歴テーブル
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # アラートルールテーブル
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                condition_text TEXT NOT NULL,
                threshold REAL NOT NULL,
                enabled INTEGER DEFAULT 1,
                cooldown_minutes INTEGER DEFAULT 60,
                notification_methods TEXT,
                custom_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _setup_default_rules(self):
        """デフォルトアラートルール設定"""
        default_rules = [
            AlertRule(
                id="consecutive_losses_5",
                name="連敗5回警告",
                alert_type=AlertType.STREAK,
                severity=AlertSeverity.WARNING,
                condition="consecutive_losses >= 5",
                threshold=5.0,
                notification_methods=['log', 'email'],
                custom_message="連敗が5回に達しました。投資戦略の見直しを検討してください。"
            ),
            AlertRule(
                id="consecutive_losses_10",
                name="連敗10回緊急",
                alert_type=AlertType.STREAK,
                severity=AlertSeverity.CRITICAL,
                condition="consecutive_losses >= 10",
                threshold=10.0,
                notification_methods=['log', 'email'],
                custom_message="連敗が10回に達しました。緊急に投資を停止し戦略を見直してください。"
            ),
            AlertRule(
                id="drawdown_20_percent",
                name="ドローダウン20%警告",
                alert_type=AlertType.DRAWDOWN,
                severity=AlertSeverity.WARNING,
                condition="max_drawdown <= -0.20",
                threshold=-0.20,
                notification_methods=['log', 'email'],
                custom_message="最大ドローダウンが20%を超過しました。リスク管理の強化が必要です。"
            ),
            AlertRule(
                id="drawdown_30_percent",
                name="ドローダウン30%緊急",
                alert_type=AlertType.DRAWDOWN,
                severity=AlertSeverity.CRITICAL,
                condition="max_drawdown <= -0.30",
                threshold=-0.30,
                notification_methods=['log', 'email'],
                custom_message="最大ドローダウンが30%を超過しました。即座に投資を停止してください。"
            ),
            AlertRule(
                id="daily_loss_limit",
                name="日次損失限度額",
                alert_type=AlertType.BUDGET,
                severity=AlertSeverity.WARNING,
                condition="daily_loss >= 10000",
                threshold=10000.0,
                notification_methods=['log', 'email'],
                custom_message="本日の損失が1万円を超過しました。投資を控えることを推奨します。"
            ),
            AlertRule(
                id="low_confidence_warning",
                name="低信頼度賭け警告",
                alert_type=AlertType.CONFIDENCE,
                severity=AlertSeverity.INFO,
                condition="avg_confidence_7days < 0.6",
                threshold=0.6,
                notification_methods=['log'],
                custom_message="7日間の平均信頼度が60%を下回っています。予想精度の確認が必要です。"
            ),
            AlertRule(
                id="negative_trend_warning",
                name="下降トレンド警告",
                alert_type=AlertType.TREND,
                severity=AlertSeverity.WARNING,
                condition="trend_momentum < -2000",
                threshold=-2000.0,
                notification_methods=['log', 'email'],
                custom_message="下降トレンドが継続しています。投資戦略の見直しを検討してください。"
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """アラートルール追加"""
        self.rules[rule.id] = rule
        
        # データベースに保存
        conn = sqlite3.connect(self.alert_db_path)
        conn.execute('''
            INSERT OR REPLACE INTO alert_rules 
            (id, name, alert_type, severity, condition_text, threshold, enabled, 
             cooldown_minutes, notification_methods, custom_message, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule.id, rule.name, rule.alert_type.value, rule.severity.value,
            rule.condition, rule.threshold, int(rule.enabled),
            rule.cooldown_minutes, 
            json.dumps(rule.notification_methods or []),
            rule.custom_message, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    
    def remove_rule(self, rule_id: str):
        """アラートルール削除"""
        if rule_id in self.rules:
            del self.rules[rule_id]
        
        conn = sqlite3.connect(self.alert_db_path)
        conn.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
        conn.commit()
        conn.close()
    
    def check_alerts(self) -> List[Alert]:
        """アラートチェック実行"""
        triggered_alerts = []
        
        # 現在のパフォーマンス取得
        performance = self.analytics.calculate_performance_metrics(30)
        time_series = self.analytics.generate_time_series_analysis(30)
        today_stats = self._get_today_stats()
        
        # 各ルールをチェック
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            # クールダウンチェック
            if self._is_in_cooldown(rule_id, rule.cooldown_minutes):
                continue
            
            # 条件評価
            if self._evaluate_condition(rule, performance, time_series, today_stats):
                alert = self._create_alert(rule, performance, time_series, today_stats)
                triggered_alerts.append(alert)
                
                # クールダウン記録
                self.last_triggered[rule_id] = datetime.now()
                
                # 通知実行
                self._send_notifications(alert, rule)
                
                # データベースに保存
                self._save_alert(alert)
        
        return triggered_alerts
    
    def _evaluate_condition(self, rule: AlertRule, performance: PerformanceMetrics, 
                           time_series, today_stats: Dict) -> bool:
        """条件評価"""
        try:
            # 評価用コンテキスト
            context = {
                'consecutive_losses': performance.consecutive_losses,
                'consecutive_wins': performance.consecutive_wins,
                'max_drawdown': performance.max_drawdown,
                'sharpe_ratio': performance.sharpe_ratio,
                'volatility': performance.volatility,
                'daily_loss': abs(today_stats.get('daily_profit', 0)) if today_stats.get('daily_profit', 0) < 0 else 0,
                'daily_profit': today_stats.get('daily_profit', 0),
                'avg_confidence_7days': today_stats.get('avg_confidence_7days', 0),
                'trend_momentum': time_series.momentum,
                'win_rate': today_stats.get('win_rate', 0)
            }
            
            # 条件式評価
            return eval(rule.condition, {"__builtins__": {}}, context)
            
        except Exception as e:
            self.logger.error(f"条件評価エラー (ルール: {rule.id}): {e}")
            return False
    
    def _create_alert(self, rule: AlertRule, performance: PerformanceMetrics, 
                     time_series, today_stats: Dict) -> Alert:
        """アラート作成"""
        alert_id = f"{rule.id}_{int(datetime.now().timestamp())}"
        
        # データ収集
        alert_data = {
            'performance_metrics': {
                'consecutive_losses': performance.consecutive_losses,
                'consecutive_wins': performance.consecutive_wins,
                'max_drawdown': performance.max_drawdown,
                'sharpe_ratio': performance.sharpe_ratio,
                'volatility': performance.volatility
            },
            'today_stats': today_stats,
            'trend_momentum': time_series.momentum,
            'trend_direction': time_series.trend_direction
        }
        
        # メッセージ生成
        message = rule.custom_message
        if not message:
            message = self._generate_default_message(rule, alert_data)
        
        return Alert(
            id=alert_id,
            rule_id=rule.id,
            timestamp=datetime.now(),
            severity=rule.severity,
            alert_type=rule.alert_type,
            title=rule.name,
            message=message,
            data=alert_data
        )
    
    def _generate_default_message(self, rule: AlertRule, data: Dict) -> str:
        """デフォルトメッセージ生成"""
        if rule.alert_type == AlertType.STREAK:
            losses = data['performance_metrics']['consecutive_losses']
            return f"連敗が{losses}回に達しました。投資戦略の見直しを検討してください。"
        
        elif rule.alert_type == AlertType.DRAWDOWN:
            drawdown = data['performance_metrics']['max_drawdown']
            return f"最大ドローダウンが{drawdown:.1%}に達しました。リスク管理の強化が必要です。"
        
        elif rule.alert_type == AlertType.BUDGET:
            daily_loss = data['today_stats'].get('daily_loss', 0)
            return f"本日の損失が¥{daily_loss:,.0f}に達しました。"
        
        elif rule.alert_type == AlertType.TREND:
            momentum = data['trend_momentum']
            direction = data['trend_direction']
            return f"{direction}トレンドが継続中（モメンタム: {momentum:.0f}）"
        
        else:
            return f"アラート条件が満たされました: {rule.condition}"
    
    def _get_today_stats(self) -> Dict:
        """本日の統計取得"""
        conn = sqlite3.connect(self.db_path)
        
        # 本日の損益
        query = '''
            SELECT 
                COALESCE(SUM(profit_loss), 0) as daily_profit,
                COALESCE(AVG(confidence), 0) as avg_confidence,
                COUNT(*) as bet_count,
                COUNT(CASE WHEN status = '的中' THEN 1 END) as wins
            FROM bet_records 
            WHERE DATE(timestamp) = DATE('now')
        '''
        
        result = conn.execute(query).fetchone()
        conn.close()
        
        daily_profit, avg_confidence, bet_count, wins = result
        win_rate = (wins / bet_count * 100) if bet_count > 0 else 0
        
        # 7日間の平均信頼度
        conn = sqlite3.connect(self.db_path)
        query_7days = '''
            SELECT COALESCE(AVG(confidence), 0) as avg_confidence_7days
            FROM bet_records 
            WHERE timestamp >= date('now', '-7 days')
        '''
        avg_confidence_7days = conn.execute(query_7days).fetchone()[0]
        conn.close()
        
        return {
            'daily_profit': daily_profit,
            'avg_confidence': avg_confidence,
            'avg_confidence_7days': avg_confidence_7days,
            'bet_count': bet_count,
            'win_rate': win_rate,
            'daily_loss': abs(daily_profit) if daily_profit < 0 else 0
        }
    
    def _is_in_cooldown(self, rule_id: str, cooldown_minutes: int) -> bool:
        """クールダウン中かチェック"""
        if rule_id not in self.last_triggered:
            return False
        
        elapsed = datetime.now() - self.last_triggered[rule_id]
        return elapsed.total_seconds() < (cooldown_minutes * 60)
    
    def _send_notifications(self, alert: Alert, rule: AlertRule):
        """通知送信"""
        if not rule.notification_methods:
            return
        
        for method in rule.notification_methods:
            try:
                if method == 'log':
                    self._send_log_notification(alert)
                elif method == 'email':
                    self._send_email_notification(alert)
                elif method == 'webhook':
                    self._send_webhook_notification(alert)
            except Exception as e:
                self.logger.error(f"通知送信エラー ({method}): {e}")
    
    def _send_log_notification(self, alert: Alert):
        """ログ通知"""
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.EMERGENCY: logging.CRITICAL
        }.get(alert.severity, logging.INFO)
        
        self.logger.log(log_level, f"投資アラート [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
    
    def _send_email_notification(self, alert: Alert):
        """メール通知（設定されている場合）"""
        # 実装例：環境変数から設定を読み取り
        # 実際の使用時は適切な設定を行ってください
        pass
    
    def _send_webhook_notification(self, alert: Alert):
        """Webhook通知（設定されている場合）"""
        # 実装例：Slackやディスコードなどへの通知
        pass
    
    def _save_alert(self, alert: Alert):
        """アラート保存"""
        conn = sqlite3.connect(self.alert_db_path)
        conn.execute('''
            INSERT INTO alert_history 
            (id, rule_id, timestamp, severity, alert_type, title, message, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.id, alert.rule_id, alert.timestamp.isoformat(),
            alert.severity.value, alert.alert_type.value,
            alert.title, alert.message, json.dumps(alert.data, default=str)
        ))
        conn.commit()
        conn.close()
    
    def start_monitoring(self, interval_minutes: int = 5):
        """監視開始"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, 
            args=(interval_minutes,),
            daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info(f"投資アラート監視開始（間隔: {interval_minutes}分）")
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("投資アラート監視停止")
    
    def _monitoring_loop(self, interval_minutes: int):
        """監視ループ"""
        while self.monitoring_active:
            try:
                alerts = self.check_alerts()
                if alerts:
                    self.logger.info(f"アラート{len(alerts)}件を検出・通知しました")
            except Exception as e:
                self.logger.error(f"アラート監視エラー: {e}")
            
            # 指定間隔待機
            for _ in range(interval_minutes * 60):
                if not self.monitoring_active:
                    break
                time.sleep(1)
    
    def get_alert_history(self, days: int = 7) -> List[Dict]:
        """アラート履歴取得"""
        conn = sqlite3.connect(self.alert_db_path)
        
        query = '''
            SELECT * FROM alert_history 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
        '''.format(days)
        
        cursor = conn.execute(query)
        columns = [description[0] for description in cursor.description]
        
        alerts = []
        for row in cursor.fetchall():
            alert_dict = dict(zip(columns, row))
            alert_dict['data'] = json.loads(alert_dict['data']) if alert_dict['data'] else {}
            alerts.append(alert_dict)
        
        conn.close()
        return alerts
    
    def acknowledge_alert(self, alert_id: str):
        """アラート確認"""
        conn = sqlite3.connect(self.alert_db_path)
        conn.execute('''
            UPDATE alert_history 
            SET acknowledged = 1, acknowledged_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), alert_id))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    # テスト実行
    alert_system = InvestmentAlertSystem()
    
    print("投資アラートシステムテスト実行中...")
    
    # アラートチェック
    alerts = alert_system.check_alerts()
    print(f"検出されたアラート: {len(alerts)}件")
    
    for alert in alerts:
        print(f"  - [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
    
    # 監視開始（テスト用に短い間隔）
    # alert_system.start_monitoring(interval_minutes=1)
    
    # アラート履歴
    history = alert_system.get_alert_history(7)
    print(f"過去7日間のアラート履歴: {len(history)}件")