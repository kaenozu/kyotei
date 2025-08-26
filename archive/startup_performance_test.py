#!/usr/bin/env python3
"""
起動パフォーマンステストツール
各モジュールの初期化時間を詳細に測定
"""

import time
import sys
import importlib
from pathlib import Path
from typing import Dict, List

# プロジェクトパスをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class StartupProfiler:
    """起動時間プロファイラー"""
    
    def __init__(self):
        self.timing_records = []
        self.start_time = time.time()
    
    def time_import(self, module_name: str, import_func):
        """インポート時間測定"""
        start = time.time()
        try:
            result = import_func()
            duration = time.time() - start
            self.timing_records.append({
                'module': module_name,
                'duration': duration,
                'status': 'success'
            })
            print(f"[OK] {module_name}: {duration:.3f}秒")
            return result
        except Exception as e:
            duration = time.time() - start
            self.timing_records.append({
                'module': module_name,
                'duration': duration,
                'status': 'error',
                'error': str(e)
            })
            print(f"[ERROR] {module_name}: {duration:.3f}秒 (エラー: {e})")
            return None
    
    def get_report(self) -> Dict:
        """パフォーマンスレポート取得"""
        total_time = time.time() - self.start_time
        
        # 時間順でソート
        sorted_records = sorted(self.timing_records, 
                              key=lambda x: x['duration'], reverse=True)
        
        return {
            'total_startup_time': total_time,
            'module_count': len(self.timing_records),
            'slowest_modules': sorted_records[:10],
            'failed_modules': [r for r in self.timing_records if r['status'] == 'error'],
            'timing_breakdown': self.timing_records
        }

def main():
    """メイン実行"""
    profiler = StartupProfiler()
    print("[START] 起動パフォーマンステスト開始\n")
    
    # 基本モジュールのテスト
    print("[BASIC] 基本モジュールテスト:")
    basic_modules = [
        ('json', lambda: __import__('json')),
        ('sqlite3', lambda: __import__('sqlite3')),
        ('requests', lambda: __import__('requests')),
        ('numpy', lambda: __import__('numpy')),
        ('pandas', lambda: __import__('pandas')),
        ('sklearn', lambda: __import__('sklearn')),
        ('flask', lambda: __import__('flask')),
    ]
    
    for name, import_func in basic_modules:
        profiler.time_import(name, import_func)
    
    print("\n[PROJECT] プロジェクトモジュールテスト:")
    
    # 設定モジュール
    profiler.time_import('config', lambda: __import__('config'))
    
    # コアモジュール
    try:
        profiler.time_import('src.config', 
                           lambda: importlib.import_module('src.config'))
        
        profiler.time_import('src.core.predictor', 
                           lambda: importlib.import_module('src.core.predictor'))
        
        profiler.time_import('src.core.data_access', 
                           lambda: importlib.import_module('src.core.data_access'))
    except Exception as e:
        print(f"コアモジュール読み込みエラー: {e}")
    
    # MLモジュール
    try:
        profiler.time_import('ml_predictor', 
                           lambda: __import__('ml_predictor'))
        profiler.time_import('advanced_ml_predictor', 
                           lambda: __import__('advanced_ml_predictor'))
    except Exception as e:
        print(f"MLモジュール読み込みエラー: {e}")
    
    # Webモジュール
    try:
        if Path('src/web').exists():
            profiler.time_import('src.web.api_client', 
                               lambda: importlib.import_module('src.web.api_client'))
            profiler.time_import('src.web.prediction_engine', 
                               lambda: importlib.import_module('src.web.prediction_engine'))
            profiler.time_import('src.web.app', 
                               lambda: importlib.import_module('src.web.app'))
    except Exception as e:
        print(f"Webモジュール読み込みエラー: {e}")
    
    # パフォーマンス監視モジュール
    try:
        profiler.time_import('src.utils.performance_monitor',
                           lambda: importlib.import_module('src.utils.performance_monitor'))
    except Exception as e:
        print(f"パフォーマンス監視モジュール読み込みエラー: {e}")
    
    # データベース初期化テスト
    print("\n[DATABASE] データベース初期化テスト:")
    
    def test_db_init():
        try:
            import sqlite3
            db_path = "cache/startup_test.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
            conn.close()
            return True
        except Exception:
            return False
    
    profiler.time_import('database_init', test_db_init)
    
    # レポート生成
    print("\n[REPORT] パフォーマンスレポート:")
    report = profiler.get_report()
    
    print(f"合計起動時間: {report['total_startup_time']:.3f}秒")
    print(f"テスト対象モジュール数: {report['module_count']}")
    
    if report['failed_modules']:
        print(f"失敗したモジュール: {len(report['failed_modules'])}個")
        for failed in report['failed_modules']:
            print(f"  - {failed['module']}: {failed['error']}")
    
    print("\n[SLOW] 最も時間のかかったモジュール:")
    for i, module in enumerate(report['slowest_modules'][:5], 1):
        print(f"  {i}. {module['module']}: {module['duration']:.3f}秒")
    
    # 最適化提案
    print("\n[OPTIMIZE] 最適化提案:")
    slow_modules = [m for m in report['timing_breakdown'] 
                    if m['duration'] > 0.5 and m['status'] == 'success']
    
    if slow_modules:
        print("以下のモジュールの遅延ロード化を検討:")
        for module in slow_modules:
            print(f"  - {module['module']} ({module['duration']:.3f}秒)")
    
    # 推奨対策
    print("\n[ACTION] 推奨対策:")
    if report['total_startup_time'] > 10:
        print("  1. 重いMLライブラリの遅延ロード")
        print("  2. データベース初期化の非同期化")
        print("  3. キャッシュファイルの事前生成")
    elif report['total_startup_time'] > 5:
        print("  1. 一部モジュールの遅延ロード")
        print("  2. インポート順序の最適化")
    else:
        print("  現在の起動時間は許容範囲内です")
    
    return report

if __name__ == "__main__":
    try:
        report = main()
        
        # 結果をJSONファイルに保存
        import json
        with open("startup_performance_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n[SAVE] 詳細レポートを 'startup_performance_report.json' に保存しました")
        
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        sys.exit(1)