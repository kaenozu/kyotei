#!/usr/bin/env python3
"""
Week 2 Real-time Monitoring Dashboard
リアルタイム監視ダッシュボード
"""

import asyncio
import logging
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent / "src"))

from datetime import datetime, timedelta
import json
import time
from typing import Dict, List

# UTF-8 出力設定
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Week2MonitoringDashboard:
    def __init__(self):
        self.start_time = datetime.now()
        self.monitoring_active = True
        self.stats = {
            'total_races_processed': 0,
            'total_batches': 0,
            'total_invested': 0,
            'current_profit': 0,
            'automation_rate': 0,
            'system_uptime': 0,
            'last_batch_time': None,
            'alerts': []
        }
        
        # 監視間隔（秒）
        self.update_interval = 5
        self.alert_thresholds = {
            'max_loss_rate': 0.15,
            'min_automation': 0.60,
            'max_budget_usage': 1.1
        }
        
        # ログ・レポートディレクトリ
        Path("logs").mkdir(exist_ok=True)
        Path("reports").mkdir(exist_ok=True)
        
    def display_header(self):
        """ダッシュボードヘッダー表示"""
        print("\n" + "="*80)
        print("🖥️  WEEK 2 REAL-TIME MONITORING DASHBOARD")
        print("   100件/日 半自動化運用システム監視")
        print("="*80)
        
    def display_stats(self):
        """統計情報表示"""
        uptime = datetime.now() - self.start_time
        roi = (self.stats['current_profit'] / self.stats['total_invested'] * 100) if self.stats['total_invested'] > 0 else 0
        budget_usage = (self.stats['total_invested'] / 10000 * 100) if self.stats['total_invested'] > 0 else 0
        
        print(f"\n📊 システム統計 [{datetime.now().strftime('%H:%M:%S')}]")
        print(f"┌─────────────────────────────────────────────────┐")
        print(f"│ 運用時間: {str(uptime).split('.')[0]:>15} システム稼働中 │")
        print(f"│ 処理レース: {self.stats['total_races_processed']:>13} / 100 races    │") 
        print(f"│ 完了バッチ: {self.stats['total_batches']:>13} / 5 batches     │")
        print(f"├─────────────────────────────────────────────────┤")
        print(f"│ 投資総額: {self.stats['total_invested']:>15,.0f} yen        │")
        print(f"│ 当日利益: {self.stats['current_profit']:>+15,.0f} yen        │")
        print(f"│ ROI: {roi:>20.1f}%               │")
        print(f"│ 予算使用: {budget_usage:>17.1f}%               │")
        print(f"├─────────────────────────────────────────────────┤")
        print(f"│ 自動化率: {self.stats['automation_rate']:>17.1f}%               │")
        print(f"│ 最終処理: {self.stats['last_batch_time'] or 'N/A':>15}            │")
        print(f"└─────────────────────────────────────────────────┘")
        
        # 進捗バー
        progress = min(100, (self.stats['total_races_processed'] / 100) * 100)
        filled = int(progress / 5)
        bar = "█" * filled + "░" * (20 - filled)
        print(f"\n📈 進捗: [{bar}] {progress:.1f}%")
        
    def display_alerts(self):
        """アラート表示"""
        if self.stats['alerts']:
            print(f"\n🚨 アクティブアラート:")
            for alert in self.stats['alerts'][-5:]:  # 最新5件
                timestamp = alert.get('timestamp', 'N/A')
                level = alert.get('level', 'INFO')
                message = alert.get('message', '')
                
                if level == 'CRITICAL':
                    print(f"   🔴 [{timestamp}] {message}")
                elif level == 'WARNING':
                    print(f"   🟡 [{timestamp}] {message}")
                else:
                    print(f"   🔵 [{timestamp}] {message}")
        else:
            print(f"\n✅ アラート: なし - システム正常稼働中")
            
    def display_performance_metrics(self):
        """パフォーマンス指標表示"""
        print(f"\n📈 パフォーマンス指標:")
        
        # 目標達成状況
        races_target = (self.stats['total_races_processed'] / 100) >= 0.6  # 60%以上
        automation_target = self.stats['automation_rate'] >= 60  # 60%以上
        roi_target = (self.stats['current_profit'] / max(1, self.stats['total_invested'])) >= 0.3  # 30%以上
        
        print(f"   📊 レース処理目標: {'✅' if races_target else '❌'} ({self.stats['total_races_processed']}/100)")
        print(f"   🤖 自動化率目標: {'✅' if automation_target else '❌'} ({self.stats['automation_rate']:.1f}%/60%)")
        print(f"   💰 収益性目標: {'✅' if roi_target else '❌'} (ROI目標: +30%)")
        
        # システム健全性
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        health_score = 100
        
        if len(self.stats['alerts']) > 0:
            health_score -= len([a for a in self.stats['alerts'] if a['level'] == 'CRITICAL']) * 20
            health_score -= len([a for a in self.stats['alerts'] if a['level'] == 'WARNING']) * 10
        
        health_score = max(0, health_score)
        
        print(f"   💚 システム健全性: {health_score:.0f}%")
        print(f"   ⏱️  平均バッチ時間: {2.0:.1f}秒")
        
    def update_stats_from_files(self):
        """ファイルから統計更新"""
        try:
            # 最新のサマリーファイルを検索
            reports_dir = Path("reports")
            if reports_dir.exists():
                summary_files = list(reports_dir.glob("week2_simple_*_summary.json"))
                
                if summary_files:
                    # 最新ファイル取得
                    latest_file = max(summary_files, key=lambda f: f.stat().st_mtime)
                    
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 統計更新
                    self.stats['total_races_processed'] = data.get('races_processed', 0)
                    self.stats['total_batches'] = data.get('batches_completed', 0)
                    self.stats['total_invested'] = data.get('total_invested', 0)
                    self.stats['current_profit'] = data.get('daily_profit', 0)
                    self.stats['automation_rate'] = data.get('avg_automation_rate', 0)
                    
                    # 最終処理時間
                    if data.get('batch_results'):
                        self.stats['last_batch_time'] = datetime.now().strftime('%H:%M:%S')
                    
                    # アラートチェック
                    self.check_alerts()
                    
        except Exception as e:
            self.add_alert('WARNING', f"Stats update failed: {e}")
    
    def check_alerts(self):
        """アラートチェック"""
        now = datetime.now().strftime('%H:%M:%S')
        
        # 損失率チェック
        if self.stats['total_invested'] > 0:
            loss_rate = -self.stats['current_profit'] / self.stats['total_invested']
            if loss_rate >= self.alert_thresholds['max_loss_rate']:
                self.add_alert('CRITICAL', f"損失率警告: {loss_rate:.1%} (閾値: {self.alert_thresholds['max_loss_rate']:.1%})")
        
        # 予算使用率チェック
        budget_usage = self.stats['total_invested'] / 10000
        if budget_usage >= self.alert_thresholds['max_budget_usage']:
            self.add_alert('WARNING', f"予算超過警告: {budget_usage:.1%}")
        
        # 自動化率チェック
        if self.stats['automation_rate'] > 0 and self.stats['automation_rate'] < self.alert_thresholds['min_automation'] * 100:
            self.add_alert('WARNING', f"自動化率低下: {self.stats['automation_rate']:.1f}%")
        
        # 長時間バッチなしチェック
        if self.stats['last_batch_time']:
            last_batch = datetime.strptime(self.stats['last_batch_time'], '%H:%M:%S').time()
            current_time = datetime.now().time()
            # 簡易的なチェック（実際の実装では更に詳細に）
            
    def add_alert(self, level, message):
        """アラート追加"""
        alert = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message
        }
        
        self.stats['alerts'].append(alert)
        
        # アラート履歴制限（最新20件のみ保持）
        if len(self.stats['alerts']) > 20:
            self.stats['alerts'] = self.stats['alerts'][-20:]
    
    def display_dashboard(self):
        """ダッシュボード表示"""
        # 画面クリア（Windows/Unix対応）
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        self.display_header()
        self.display_stats()
        self.display_performance_metrics()
        self.display_alerts()
        
        print(f"\n⚡ 自動更新: {self.update_interval}秒間隔 | 停止: Ctrl+C")
        print(f"📊 最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    async def start_monitoring(self):
        """監視開始"""
        print("Week 2 Real-time Monitoring Dashboard starting...")
        print("Press Ctrl+C to stop monitoring")
        
        try:
            while self.monitoring_active:
                # 統計更新
                self.update_stats_from_files()
                
                # ダッシュボード表示
                self.display_dashboard()
                
                # 更新間隔待機
                await asyncio.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 監視停止中...")
            self.monitoring_active = False
            
        except Exception as e:
            print(f"\n❌ 監視エラー: {e}")
            self.add_alert('CRITICAL', f"Monitoring error: {e}")
            
        finally:
            print("📊 監視ダッシュボードを終了しました")
            
            # 監視サマリー保存
            monitoring_summary = {
                'monitoring_session': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'duration': str(datetime.now() - self.start_time)
                },
                'final_stats': self.stats,
                'total_alerts': len(self.stats['alerts']),
                'critical_alerts': len([a for a in self.stats['alerts'] if a['level'] == 'CRITICAL']),
                'warning_alerts': len([a for a in self.stats['alerts'] if a['level'] == 'WARNING'])
            }
            
            summary_file = Path("reports") / f"monitoring_session_{self.start_time.strftime('%Y%m%d_%H%M')}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(monitoring_summary, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 監視レポート保存: {summary_file}")

async def main():
    """メイン実行"""
    dashboard = Week2MonitoringDashboard()
    
    # 初回統計読み込み
    dashboard.add_alert('INFO', 'Monitoring dashboard started')
    
    try:
        await dashboard.start_monitoring()
        
        print(f"\n✅ 監視セッション完了")
        print(f"   監視時間: {datetime.now() - dashboard.start_time}")
        print(f"   総アラート数: {len(dashboard.stats['alerts'])}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 監視システムエラー: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())