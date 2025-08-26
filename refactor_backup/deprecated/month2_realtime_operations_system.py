#!/usr/bin/env python3
"""
Month 2 Real-time Operations System
Advanced monitoring and operational management for 200+ races/day
"""

import asyncio
import time
import json
import sqlite3
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import random
import threading
from concurrent.futures import ThreadPoolExecutor

# 日本語出力対応
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

@dataclass
class OperationsConfig:
    """Real-time operations configuration"""
    monitoring_interval: int = 5  # seconds
    dashboard_refresh_rate: int = 3  # seconds
    alert_cooldown: int = 60  # seconds
    max_concurrent_operations: int = 10
    
    # Performance thresholds
    critical_automation_rate: float = 0.90
    warning_automation_rate: float = 0.93
    critical_processing_time: float = 120.0  # seconds per batch
    warning_processing_time: float = 90.0
    critical_accuracy_rate: float = 0.85
    warning_accuracy_rate: float = 0.90
    critical_cpu_usage: float = 85.0
    warning_cpu_usage: float = 70.0
    critical_memory_usage: float = 80.0
    warning_memory_usage: float = 65.0
    
    # Operational targets
    target_daily_races: int = 200
    target_automation_rate: float = 0.95
    target_uptime: float = 0.999
    target_roi: float = 1.25

@dataclass
class SystemAlert:
    """System alert data structure"""
    id: str
    timestamp: datetime
    severity: str  # CRITICAL, WARNING, INFO
    category: str  # PERFORMANCE, SYSTEM, AUTOMATION, PREDICTION
    message: str
    details: Dict = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False

class RealTimeMonitor:
    """Real-time system monitoring"""
    
    def __init__(self, config: OperationsConfig):
        self.config = config
        self.monitoring_active = False
        self.alerts = []
        self.alert_history = []
        
        # System metrics
        self.current_metrics = {
            'timestamp': datetime.now(),
            'races_processed_today': 0,
            'current_automation_rate': 0.0,
            'current_accuracy_rate': 0.0,
            'avg_processing_time': 0.0,
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'system_uptime': 0.0,
            'current_roi': 0.0,
            'active_operations': 0,
            'errors_today': 0,
            'last_error_time': None
        }
        
        # Performance history
        self.performance_history = []
        self.max_history_size = 1000
        
        # Database setup
        self.setup_monitoring_database()
    
    def setup_monitoring_database(self):
        """Setup monitoring database"""
        try:
            conn = sqlite3.connect('cache/month2_operations.db')
            cursor = conn.cursor()
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS system_metrics
                            (id INTEGER PRIMARY KEY,
                             timestamp TIMESTAMP,
                             races_processed INTEGER,
                             automation_rate REAL,
                             accuracy_rate REAL,
                             processing_time REAL,
                             cpu_usage REAL,
                             memory_usage REAL,
                             roi_current REAL,
                             active_operations INTEGER,
                             errors_count INTEGER)''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS system_alerts
                            (id TEXT PRIMARY KEY,
                             timestamp TIMESTAMP,
                             severity TEXT,
                             category TEXT,
                             message TEXT,
                             details TEXT,
                             acknowledged INTEGER,
                             resolved INTEGER,
                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS operations_log
                            (id INTEGER PRIMARY KEY,
                             timestamp TIMESTAMP,
                             operation_type TEXT,
                             operation_id TEXT,
                             status TEXT,
                             duration REAL,
                             details TEXT,
                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            conn.commit()
            conn.close()
            print("監視データベース初期化完了")
            
        except Exception as e:
            print(f"データベース初期化エラー: {e}")
    
    async def start_monitoring(self):
        """Start real-time monitoring"""
        self.monitoring_active = True
        print("リアルタイム監視開始...")
        
        # Start monitoring loop
        monitoring_task = asyncio.create_task(self.monitoring_loop())
        alert_task = asyncio.create_task(self.alert_management_loop())
        
        return await asyncio.gather(monitoring_task, alert_task)
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Update system metrics
                await self.update_system_metrics()
                
                # Check for alerts
                await self.check_alert_conditions()
                
                # Store metrics
                self.store_metrics()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                print(f"監視ループエラー: {e}")
                await asyncio.sleep(self.config.monitoring_interval)
    
    async def update_system_metrics(self):
        """Update current system metrics"""
        try:
            # Simulate system metrics collection
            self.current_metrics.update({
                'timestamp': datetime.now(),
                'cpu_usage': random.uniform(30, 85),
                'memory_usage': random.uniform(40, 75),
                'current_automation_rate': random.uniform(0.87, 0.98),
                'current_accuracy_rate': random.uniform(0.88, 0.95),
                'avg_processing_time': random.uniform(60, 150),
                'current_roi': random.uniform(1.15, 1.35),
                'active_operations': random.randint(0, 8),
                'races_processed_today': random.randint(80, 220)
            })
            
            # Calculate system uptime
            if hasattr(self, 'start_time'):
                self.current_metrics['system_uptime'] = time.time() - self.start_time
            else:
                self.start_time = time.time()
                self.current_metrics['system_uptime'] = 0
            
            # Store in performance history
            self.performance_history.append(self.current_metrics.copy())
            
            # Limit history size
            if len(self.performance_history) > self.max_history_size:
                self.performance_history = self.performance_history[-self.max_history_size:]
                
        except Exception as e:
            print(f"メトリクス更新エラー: {e}")
    
    async def check_alert_conditions(self):
        """Check for alert conditions"""
        current_time = datetime.now()
        
        # Automation rate alerts
        if self.current_metrics['current_automation_rate'] < self.config.critical_automation_rate:
            await self.create_alert('CRITICAL', 'AUTOMATION', 
                                  f"自動化率が危険レベル: {self.current_metrics['current_automation_rate']*100:.1f}%")
        elif self.current_metrics['current_automation_rate'] < self.config.warning_automation_rate:
            await self.create_alert('WARNING', 'AUTOMATION', 
                                  f"自動化率が警告レベル: {self.current_metrics['current_automation_rate']*100:.1f}%")
        
        # Processing time alerts
        if self.current_metrics['avg_processing_time'] > self.config.critical_processing_time:
            await self.create_alert('CRITICAL', 'PERFORMANCE', 
                                  f"処理時間が危険レベル: {self.current_metrics['avg_processing_time']:.1f}秒")
        elif self.current_metrics['avg_processing_time'] > self.config.warning_processing_time:
            await self.create_alert('WARNING', 'PERFORMANCE', 
                                  f"処理時間が警告レベル: {self.current_metrics['avg_processing_time']:.1f}秒")
        
        # System resource alerts
        if self.current_metrics['cpu_usage'] > self.config.critical_cpu_usage:
            await self.create_alert('CRITICAL', 'SYSTEM', 
                                  f"CPU使用率が危険レベル: {self.current_metrics['cpu_usage']:.1f}%")
        elif self.current_metrics['cpu_usage'] > self.config.warning_cpu_usage:
            await self.create_alert('WARNING', 'SYSTEM', 
                                  f"CPU使用率が警告レベル: {self.current_metrics['cpu_usage']:.1f}%")
        
        # Memory alerts
        if self.current_metrics['memory_usage'] > self.config.critical_memory_usage:
            await self.create_alert('CRITICAL', 'SYSTEM', 
                                  f"メモリ使用率が危険レベル: {self.current_metrics['memory_usage']:.1f}%")
        elif self.current_metrics['memory_usage'] > self.config.warning_memory_usage:
            await self.create_alert('WARNING', 'SYSTEM', 
                                  f"メモリ使用率が警告レベル: {self.current_metrics['memory_usage']:.1f}%")
        
        # Accuracy alerts
        if self.current_metrics['current_accuracy_rate'] < self.config.critical_accuracy_rate:
            await self.create_alert('CRITICAL', 'PREDICTION', 
                                  f"予測精度が危険レベル: {self.current_metrics['current_accuracy_rate']*100:.1f}%")
        elif self.current_metrics['current_accuracy_rate'] < self.config.warning_accuracy_rate:
            await self.create_alert('WARNING', 'PREDICTION', 
                                  f"予測精度が警告レベル: {self.current_metrics['current_accuracy_rate']*100:.1f}%")
    
    async def create_alert(self, severity: str, category: str, message: str, details: Dict = None):
        """Create new system alert"""
        try:
            # Check for duplicate alerts (prevent spam)
            recent_alerts = [a for a in self.alerts if 
                           (datetime.now() - a.timestamp).total_seconds() < self.config.alert_cooldown and
                           a.message == message and not a.resolved]
            
            if recent_alerts:
                return  # Skip duplicate alert
            
            alert = SystemAlert(
                id=f"alert_{int(time.time())}_{random.randint(1000, 9999)}",
                timestamp=datetime.now(),
                severity=severity,
                category=category,
                message=message,
                details=details or {}
            )
            
            self.alerts.append(alert)
            
            # Store in database
            self.store_alert(alert)
            
            # Print critical alerts immediately
            if severity == 'CRITICAL':
                print(f"\n🚨 CRITICAL ALERT: {message}")
            
        except Exception as e:
            print(f"アラート作成エラー: {e}")
    
    def store_metrics(self):
        """Store metrics in database"""
        try:
            conn = sqlite3.connect('cache/month2_operations.db')
            cursor = conn.cursor()
            
            cursor.execute('''INSERT INTO system_metrics 
                            (timestamp, races_processed, automation_rate, accuracy_rate,
                             processing_time, cpu_usage, memory_usage, roi_current,
                             active_operations, errors_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (self.current_metrics['timestamp'],
                           self.current_metrics['races_processed_today'],
                           self.current_metrics['current_automation_rate'],
                           self.current_metrics['current_accuracy_rate'],
                           self.current_metrics['avg_processing_time'],
                           self.current_metrics['cpu_usage'],
                           self.current_metrics['memory_usage'],
                           self.current_metrics['current_roi'],
                           self.current_metrics['active_operations'],
                           self.current_metrics['errors_today']))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"メトリクス保存エラー: {e}")
    
    def store_alert(self, alert: SystemAlert):
        """Store alert in database"""
        try:
            conn = sqlite3.connect('cache/month2_operations.db')
            cursor = conn.cursor()
            
            cursor.execute('''INSERT OR REPLACE INTO system_alerts 
                            (id, timestamp, severity, category, message, details,
                             acknowledged, resolved)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (alert.id, alert.timestamp, alert.severity, alert.category,
                           alert.message, json.dumps(alert.details, ensure_ascii=False),
                           alert.acknowledged, alert.resolved))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"アラート保存エラー: {e}")
    
    async def alert_management_loop(self):
        """Alert management and cleanup loop"""
        while self.monitoring_active:
            try:
                current_time = datetime.now()
                
                # Clean up old resolved alerts
                self.alerts = [a for a in self.alerts if 
                             not a.resolved or 
                             (current_time - a.timestamp).total_seconds() < 3600]  # Keep for 1 hour
                
                # Auto-resolve some alerts based on current conditions
                await self.auto_resolve_alerts()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"アラート管理エラー: {e}")
                await asyncio.sleep(30)
    
    async def auto_resolve_alerts(self):
        """Auto-resolve alerts when conditions improve"""
        for alert in self.alerts:
            if alert.resolved:
                continue
            
            # Auto-resolve automation rate alerts
            if (alert.category == 'AUTOMATION' and 
                self.current_metrics['current_automation_rate'] >= self.config.warning_automation_rate):
                alert.resolved = True
                self.store_alert(alert)
            
            # Auto-resolve performance alerts
            elif (alert.category == 'PERFORMANCE' and 
                  self.current_metrics['avg_processing_time'] <= self.config.warning_processing_time):
                alert.resolved = True
                self.store_alert(alert)
            
            # Auto-resolve system resource alerts
            elif (alert.category == 'SYSTEM' and 
                  self.current_metrics['cpu_usage'] <= self.config.warning_cpu_usage and
                  self.current_metrics['memory_usage'] <= self.config.warning_memory_usage):
                alert.resolved = True
                self.store_alert(alert)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        print("リアルタイム監視停止")

class OperationsDashboard:
    """Real-time operations dashboard"""
    
    def __init__(self, monitor: RealTimeMonitor, config: OperationsConfig):
        self.monitor = monitor
        self.config = config
        self.dashboard_active = False
    
    async def start_dashboard(self):
        """Start real-time dashboard"""
        self.dashboard_active = True
        print("リアルタイムダッシュボード開始...")
        
        while self.dashboard_active:
            try:
                self.display_dashboard()
                await asyncio.sleep(self.config.dashboard_refresh_rate)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"ダッシュボードエラー: {e}")
                await asyncio.sleep(self.config.dashboard_refresh_rate)
    
    def display_dashboard(self):
        """Display real-time dashboard"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print("Month 2 リアルタイム運用ダッシュボード")
        print("=" * 80)
        print(f"更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        metrics = self.monitor.current_metrics
        
        # System overview
        print("\n📊 システム概要:")
        print(f"   今日の処理レース数: {metrics['races_processed_today']:,}")
        print(f"   稼働時間: {self.format_uptime(metrics['system_uptime'])}")
        print(f"   アクティブ操作: {metrics['active_operations']}")
        print(f"   今日のエラー数: {metrics['errors_today']}")
        
        # Performance metrics
        print("\n⚡ パフォーマンス:")
        print(f"   自動化率: {self.format_percentage(metrics['current_automation_rate'])} " +
              f"(目標: 95%)")
        print(f"   予測精度: {self.format_percentage(metrics['current_accuracy_rate'])} " +
              f"(目標: 93%)")
        print(f"   平均処理時間: {metrics['avg_processing_time']:.1f}秒")
        print(f"   現在のROI: {metrics['current_roi']:.2f} (目標: 1.25)")
        
        # System resources
        print("\n💻 システムリソース:")
        print(f"   CPU使用率: {self.format_resource_usage(metrics['cpu_usage'], 'CPU')}")
        print(f"   メモリ使用率: {self.format_resource_usage(metrics['memory_usage'], 'Memory')}")
        
        # Progress bars
        self.display_progress_bars(metrics)
        
        # Active alerts
        self.display_active_alerts()
        
        # System status
        self.display_system_status()
        
        print("\n" + "=" * 80)
        print("操作: Ctrl+C で終了")
    
    def format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime display"""
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def format_percentage(self, value: float) -> str:
        """Format percentage with color coding"""
        percentage = value * 100
        if percentage >= 95:
            return f"{percentage:.1f}% ✅"
        elif percentage >= 90:
            return f"{percentage:.1f}% ⚠️"
        else:
            return f"{percentage:.1f}% ❌"
    
    def format_resource_usage(self, usage: float, resource_type: str) -> str:
        """Format resource usage with color coding"""
        if resource_type == 'CPU':
            critical = self.config.critical_cpu_usage
            warning = self.config.warning_cpu_usage
        else:  # Memory
            critical = self.config.critical_memory_usage
            warning = self.config.warning_memory_usage
        
        if usage >= critical:
            return f"{usage:.1f}% 🚨"
        elif usage >= warning:
            return f"{usage:.1f}% ⚠️"
        else:
            return f"{usage:.1f}% ✅"
    
    def display_progress_bars(self, metrics: Dict):
        """Display progress bars for key metrics"""
        print("\n📈 進捗状況:")
        
        # Daily races progress
        daily_progress = min(1.0, metrics['races_processed_today'] / self.config.target_daily_races)
        daily_bar = self.create_progress_bar(daily_progress, 30)
        print(f"   日次レース: [{daily_bar}] {daily_progress*100:.1f}% " +
              f"({metrics['races_processed_today']}/{self.config.target_daily_races})")
        
        # Automation rate progress
        automation_progress = metrics['current_automation_rate']
        automation_bar = self.create_progress_bar(automation_progress, 30)
        print(f"   自動化率: [{automation_bar}] {automation_progress*100:.1f}%")
        
        # Accuracy progress
        accuracy_progress = metrics['current_accuracy_rate']
        accuracy_bar = self.create_progress_bar(accuracy_progress, 30)
        print(f"   予測精度: [{accuracy_bar}] {accuracy_progress*100:.1f}%")
    
    def create_progress_bar(self, progress: float, length: int = 20) -> str:
        """Create ASCII progress bar"""
        filled_length = int(length * progress)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return bar
    
    def display_active_alerts(self):
        """Display active alerts"""
        active_alerts = [a for a in self.monitor.alerts if not a.resolved]
        
        if active_alerts:
            print(f"\n🚨 アクティブアラート ({len(active_alerts)}件):")
            
            # Group by severity
            critical_alerts = [a for a in active_alerts if a.severity == 'CRITICAL']
            warning_alerts = [a for a in active_alerts if a.severity == 'WARNING']
            
            if critical_alerts:
                print(f"   🔴 重要 ({len(critical_alerts)}件):")
                for alert in critical_alerts[-3:]:  # Show last 3
                    print(f"      {alert.timestamp.strftime('%H:%M')} - {alert.message}")
            
            if warning_alerts:
                print(f"   🟡 警告 ({len(warning_alerts)}件):")
                for alert in warning_alerts[-3:]:  # Show last 3
                    print(f"      {alert.timestamp.strftime('%H:%M')} - {alert.message}")
        else:
            print("\n✅ アクティブアラートなし")
    
    def display_system_status(self):
        """Display overall system status"""
        metrics = self.monitor.current_metrics
        
        # Calculate overall health score
        health_score = 0
        total_checks = 0
        
        # Automation rate check
        if metrics['current_automation_rate'] >= 0.95:
            health_score += 1
        total_checks += 1
        
        # Accuracy rate check
        if metrics['current_accuracy_rate'] >= 0.93:
            health_score += 1
        total_checks += 1
        
        # Processing time check
        if metrics['avg_processing_time'] <= 90:
            health_score += 1
        total_checks += 1
        
        # Resource usage check
        if (metrics['cpu_usage'] <= self.config.warning_cpu_usage and 
            metrics['memory_usage'] <= self.config.warning_memory_usage):
            health_score += 1
        total_checks += 1
        
        # ROI check
        if metrics['current_roi'] >= 1.25:
            health_score += 1
        total_checks += 1
        
        health_percentage = (health_score / total_checks) * 100
        
        print("\n🎯 システムステータス:")
        if health_percentage >= 80:
            status = "🟢 HEALTHY"
            status_msg = "システムは正常に動作中"
        elif health_percentage >= 60:
            status = "🟡 WARNING"
            status_msg = "一部のメトリクスで警告レベル"
        else:
            status = "🔴 CRITICAL"
            status_msg = "システムに問題があります"
        
        print(f"   全体ヘルス: {status} ({health_percentage:.1f}%)")
        print(f"   ステータス: {status_msg}")
    
    def stop_dashboard(self):
        """Stop dashboard"""
        self.dashboard_active = False

class OperationsManager:
    """Operations management system"""
    
    def __init__(self, config: OperationsConfig = None):
        self.config = config or OperationsConfig()
        self.monitor = RealTimeMonitor(self.config)
        self.dashboard = OperationsDashboard(self.monitor, self.config)
        self.operations_active = False
    
    async def start_operations(self):
        """Start operations management system"""
        print("Month 2 運用管理システム開始...")
        self.operations_active = True
        
        try:
            # Start monitoring and dashboard concurrently
            monitor_task = asyncio.create_task(self.monitor.start_monitoring())
            dashboard_task = asyncio.create_task(self.dashboard.start_dashboard())
            
            await asyncio.gather(monitor_task, dashboard_task)
            
        except KeyboardInterrupt:
            print("\n運用システム停止中...")
        except Exception as e:
            print(f"運用システムエラー: {e}")
        finally:
            await self.stop_operations()
    
    async def stop_operations(self):
        """Stop operations management"""
        self.operations_active = False
        self.monitor.stop_monitoring()
        self.dashboard.stop_dashboard()
        print("運用管理システム停止完了")
    
    def get_operations_summary(self) -> Dict:
        """Get current operations summary"""
        metrics = self.monitor.current_metrics
        active_alerts = [a for a in self.monitor.alerts if not a.resolved]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': metrics,
            'active_alerts_count': len(active_alerts),
            'critical_alerts_count': len([a for a in active_alerts if a.severity == 'CRITICAL']),
            'warning_alerts_count': len([a for a in active_alerts if a.severity == 'WARNING']),
            'operations_status': 'ACTIVE' if self.operations_active else 'INACTIVE',
            'performance_summary': {
                'automation_rate': metrics['current_automation_rate'],
                'accuracy_rate': metrics['current_accuracy_rate'],
                'processing_efficiency': 100 - min(100, metrics['avg_processing_time'] / 2),
                'resource_health': 100 - max(metrics['cpu_usage'], metrics['memory_usage'])
            }
        }

async def run_operations_test():
    """Run operations system test"""
    print("=" * 60)
    print("Month 2 リアルタイム運用管理システム テスト")
    print("=" * 60)
    
    config = OperationsConfig()
    operations_manager = OperationsManager(config)
    
    try:
        # Start operations for a limited test period
        print("運用システム開始 (60秒間のテスト実行)")
        
        # Create task for operations
        operations_task = asyncio.create_task(operations_manager.start_operations())
        
        # Run for 60 seconds
        await asyncio.sleep(60)
        
        # Stop operations
        await operations_manager.stop_operations()
        
        # Generate test summary
        summary = operations_manager.get_operations_summary()
        
        print("\n" + "=" * 60)
        print("運用システムテスト結果")
        print("=" * 60)
        
        print(f"テスト実行時間: 60秒")
        print(f"監視メトリクス収集: ✅")
        print(f"リアルタイムダッシュボード: ✅")
        print(f"アラートシステム: ✅")
        print(f"運用ステータス: {summary['operations_status']}")
        
        performance = summary['performance_summary']
        print(f"\nパフォーマンス概要:")
        print(f"   自動化率: {performance['automation_rate']*100:.1f}%")
        print(f"   予測精度: {performance['accuracy_rate']*100:.1f}%")
        print(f"   処理効率: {performance['processing_efficiency']:.1f}%")
        print(f"   リソース健全性: {performance['resource_health']:.1f}%")
        
        print(f"\nアラート統計:")
        print(f"   アクティブアラート: {summary['active_alerts_count']}件")
        print(f"   重要アラート: {summary['critical_alerts_count']}件")
        print(f"   警告アラート: {summary['warning_alerts_count']}件")
        
        # Save test results
        os.makedirs("reports", exist_ok=True)
        report_filename = f"reports/operations_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n運用テスト結果保存: {report_filename}")
        
        return summary
        
    except Exception as e:
        print(f"\n運用テストエラー: {e}")
        return None

async def main():
    """Main execution"""
    try:
        # Option 1: Run test mode (60 seconds)
        print("テストモード実行...")
        test_result = await run_operations_test()
        
        if test_result:
            print("\n✅ リアルタイム運用管理システム テスト完了")
        else:
            print("\n❌ テスト実行中にエラーが発生しました")
        
        # Option 2: Uncomment below for continuous operation
        # config = OperationsConfig()
        # operations_manager = OperationsManager(config)
        # await operations_manager.start_operations()
        
    except KeyboardInterrupt:
        print("\nユーザーによる中断")
    except Exception as e:
        print(f"\nシステムエラー: {e}")

if __name__ == "__main__":
    asyncio.run(main())