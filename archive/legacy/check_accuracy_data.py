#!/usr/bin/env python3
"""
精度データ確認スクリプト
"""
import sqlite3
import json
import os
from datetime import datetime

def check_database_stats():
    """データベース統計確認"""
    cache_dir = "cache"
    results = {}
    
    # 1. prediction_accuracy.db
    db_path = os.path.join(cache_dir, "prediction_accuracy.db")
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # テーブル一覧
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                results['prediction_accuracy'] = {
                    'exists': True,
                    'tables': [t[0] for t in tables]
                }
                
                # predictions テーブルのデータ数
                if 'predictions' in [t[0] for t in tables]:
                    cursor.execute("SELECT COUNT(*) FROM predictions;")
                    count = cursor.fetchone()[0]
                    results['prediction_accuracy']['prediction_count'] = count
                    
                    # 検証済み予測数
                    cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_verified = 1;")
                    verified = cursor.fetchone()[0]
                    results['prediction_accuracy']['verified_count'] = verified
                    
                    # 平均精度
                    cursor.execute("SELECT AVG(accuracy_score) FROM predictions WHERE accuracy_score IS NOT NULL;")
                    avg_acc = cursor.fetchone()[0]
                    results['prediction_accuracy']['average_accuracy'] = avg_acc
                
        except Exception as e:
            results['prediction_accuracy'] = {'error': str(e)}
    else:
        results['prediction_accuracy'] = {'exists': False}
    
    # 2. adaptive_learning.db
    db_path = os.path.join(cache_dir, "adaptive_learning.db")
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                results['adaptive_learning'] = {
                    'exists': True,
                    'tables': [t[0] for t in tables]
                }
                
                # 学習メトリクス数
                if 'learning_metrics' in [t[0] for t in tables]:
                    cursor.execute("SELECT COUNT(*) FROM learning_metrics;")
                    count = cursor.fetchone()[0]
                    results['adaptive_learning']['metrics_count'] = count
                    
                    # 最新精度
                    cursor.execute("SELECT accuracy_rate FROM learning_metrics ORDER BY timestamp DESC LIMIT 1;")
                    latest = cursor.fetchone()
                    if latest:
                        results['adaptive_learning']['latest_accuracy'] = latest[0]
                
        except Exception as e:
            results['adaptive_learning'] = {'error': str(e)}
    else:
        results['adaptive_learning'] = {'exists': False}
    
    # 3. quantum_precision.db
    db_path = os.path.join(cache_dir, "quantum_precision.db")
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                results['quantum_precision'] = {
                    'exists': True,
                    'tables': [t[0] for t in tables]
                }
                
                # 量子予測数
                if 'quantum_predictions' in [t[0] for t in tables]:
                    cursor.execute("SELECT COUNT(*) FROM quantum_predictions;")
                    count = cursor.fetchone()[0]
                    results['quantum_precision']['prediction_count'] = count
                    
                    # 平均信頼度向上
                    cursor.execute("SELECT AVG(boosted_confidence) FROM quantum_predictions;")
                    avg_boost = cursor.fetchone()[0]
                    if avg_boost:
                        results['quantum_precision']['average_boosted_confidence'] = avg_boost
                
        except Exception as e:
            results['quantum_precision'] = {'error': str(e)}
    else:
        results['quantum_precision'] = {'exists': False}
    
    # 4. accuracy_monitor.db
    db_path = os.path.join(cache_dir, "accuracy_monitor.db")
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                results['accuracy_monitor'] = {
                    'exists': True,
                    'tables': [t[0] for t in tables]
                }
                
                # スナップショット数
                if 'accuracy_snapshots' in [t[0] for t in tables]:
                    cursor.execute("SELECT COUNT(*) FROM accuracy_snapshots;")
                    count = cursor.fetchone()[0]
                    results['accuracy_monitor']['snapshot_count'] = count
                
                # アラート数
                if 'accuracy_alerts' in [t[0] for t in tables]:
                    cursor.execute("SELECT COUNT(*) FROM accuracy_alerts;")
                    alert_count = cursor.fetchone()[0]
                    results['accuracy_monitor']['alert_count'] = alert_count
                
        except Exception as e:
            results['accuracy_monitor'] = {'error': str(e)}
    else:
        results['accuracy_monitor'] = {'exists': False}
    
    return results

if __name__ == "__main__":
    print("=" * 60)
    print("競艇予想システム精度データ確認")
    print("=" * 60)
    
    stats = check_database_stats()
    
    for db_name, data in stats.items():
        print(f"\n【{db_name}】")
        if data.get('exists', False):
            print(f"  存在: Yes")
            if 'tables' in data:
                print(f"  テーブル: {', '.join(data['tables'])}")
            if 'prediction_count' in data:
                print(f"  予測数: {data['prediction_count']}")
            if 'verified_count' in data:
                print(f"  検証済み: {data['verified_count']}")
            if 'average_accuracy' in data:
                if data['average_accuracy']:
                    print(f"  平均精度: {data['average_accuracy']:.3f} ({data['average_accuracy']*100:.1f}%)")
                else:
                    print(f"  平均精度: データなし")
            if 'latest_accuracy' in data:
                print(f"  最新精度: {data['latest_accuracy']:.3f} ({data['latest_accuracy']*100:.1f}%)")
            if 'metrics_count' in data:
                print(f"  学習メトリクス: {data['metrics_count']}")
            if 'average_boosted_confidence' in data:
                print(f"  量子向上後信頼度: {data['average_boosted_confidence']:.3f}")
            if 'snapshot_count' in data:
                print(f"  モニタースナップショット: {data['snapshot_count']}")
            if 'alert_count' in data:
                print(f"  アラート数: {data['alert_count']}")
            if 'error' in data:
                print(f"  エラー: {data['error']}")
        else:
            print(f"  存在: No")
    
    print("\n" + "=" * 60)