#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム不安要素分析 - 潜在的リスクと対策
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path

def analyze_system_risks():
    """システムの不安要素を包括的に分析"""
    
    print("=" * 70)
    print("システム不安要素分析レポート")
    print("=" * 70)
    print(f"分析日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    print()
    
    risks = []
    
    # 1. データ依存リスク
    print("【1. データ依存リスク】")
    print("-" * 50)
    
    # BoatraceOpenAPI接続テスト
    try:
        response = requests.get("https://boatraceopenapi.github.io/programs/v2/20250822.json", timeout=10)
        if response.status_code == 200:
            print("OK: BoatraceOpenAPI接続正常")
        else:
            print(f"WARNING: BoatraceOpenAPI応答異常 (ステータス: {response.status_code})")
            risks.append("BoatraceOpenAPIの不安定性")
    except Exception as e:
        print(f"ERROR: BoatraceOpenAPI接続失敗 - {e}")
        risks.append("BoatraceOpenAPI接続不可")
    
    # APIレート制限確認
    print("CAUTION: APIには非公式レート制限がある可能性")
    risks.append("APIレート制限による制約")
    
    # 2. 設定・環境リスク  
    print("\n【2. 設定・環境リスク】")
    print("-" * 50)
    
    # .env ファイル確認
    if os.path.exists('.env'):
        print("OK: .env設定ファイル存在")
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'SECRET_KEY=' in content and len(content.split('SECRET_KEY=')[1].split('\n')[0]) > 10:
                    print("OK: SECRET_KEY設定済み")
                else:
                    print("WARNING: SECRET_KEY不適切")
                    risks.append("セキュリティキー設定不備")
        except Exception as e:
            print(f"WARNING: .env読み込みエラー - {e}")
            risks.append("設定ファイル読み込み問題")
    else:
        print("ERROR: .env設定ファイル不存在")
        risks.append("設定ファイル不存在")
    
    # Python依存関係
    required_packages = ['flask', 'requests', 'pandas', 'numpy', 'matplotlib', 'reportlab']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"OK: {package}インストール済み")
        except ImportError:
            print(f"ERROR: {package}未インストール")
            missing_packages.append(package)
    
    if missing_packages:
        risks.append(f"必要パッケージ未インストール: {', '.join(missing_packages)}")
    
    # 3. データベースリスク
    print("\n【3. データベースリスク】")
    print("-" * 50)
    
    cache_dir = Path("cache")
    if not cache_dir.exists():
        print("WARNING: キャッシュディレクトリ不存在")
        risks.append("キャッシュディレクトリ未作成")
    else:
        print("OK: キャッシュディレクトリ存在")
    
    # SQLiteファイル権限確認
    try:
        test_db = "cache/test_permissions.db"
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
        conn.close()
        os.remove(test_db)
        print("OK: データベース書き込み権限正常")
    except Exception as e:
        print(f"ERROR: データベース権限問題 - {e}")
        risks.append("データベースファイル権限不足")
    
    # 4. 予想精度リスク
    print("\n【4. 予想精度リスク】")
    print("-" * 50)
    
    print("CAUTION: 予想システムの限界事項:")
    prediction_risks = [
        "過去データに基づく予想のため未来保証なし",
        "急激な環境変化（天候・選手状況）への対応遅れ",
        "機械学習モデルの過学習リスク", 
        "サンプルサイズ不足時の精度低下",
        "会場・レース特性の変化への適応遅れ"
    ]
    
    for risk in prediction_risks:
        print(f"  - {risk}")
        risks.append(f"予想精度: {risk}")
    
    # 5. 投資リスク
    print("\n【5. 投資管理リスク】")
    print("-" * 50)
    
    investment_risks = [
        "Kelly基準は理論値であり実際の最適解と異なる可能性",
        "連続する不的中による資金枯渇リスク",
        "感情的判断によるシステム逸脱",
        "オッズ変動によるリアルタイム計算誤差",
        "投資上限設定の甘さによる過度なリスク"
    ]
    
    for risk in investment_risks:
        print(f"  - {risk}")
        risks.append(f"投資管理: {risk}")
    
    # 6. システム運用リスク
    print("\n【6. システム運用リスク】")
    print("-" * 50)
    
    # ポート使用確認
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        if result == 0:
            print("WARNING: ポート5000が既に使用中")
            risks.append("ポート競合リスク")
        else:
            print("OK: ポート5000利用可能")
    except Exception:
        print("WARNING: ポート確認失敗")
    
    # メモリ使用量予測
    print("CAUTION: システムリソース要件:")
    print("  - メモリ: 推定500MB-1GB（レポート生成時）")
    print("  - ディスク: 100MB-1GB（ログ・キャッシュ・レポート）")
    print("  - CPU: 中程度（機械学習計算時）")
    
    # 7. セキュリティリスク  
    print("\n【7. セキュリティリスク】")
    print("-" * 50)
    
    security_risks = [
        "個人投資データの外部流出リスク",
        "Webアプリケーションへの不正アクセス",
        "SQLインジェクション攻撃（対策実装済み）",
        "CSRF攻撃（対策実装済み）",
        "機密情報のログ出力リスク"
    ]
    
    for risk in security_risks:
        print(f"  - {risk}")
        risks.append(f"セキュリティ: {risk}")
    
    # 8. 法的・倫理的リスク
    print("\n【8. 法的・倫理的リスク】")
    print("-" * 50)
    
    legal_risks = [
        "ギャンブル依存症誘発の可能性",
        "投資助言業規制への抵触リスク",
        "BoatraceOpenAPI利用規約違反リスク",
        "個人情報保護法への対応必要性",
        "過度な自動化による公平性問題"
    ]
    
    for risk in legal_risks:
        print(f"  - {risk}")
        risks.append(f"法的: {risk}")
    
    # リスク評価サマリー
    print("\n" + "=" * 70)
    print("リスク評価サマリー")
    print("=" * 70)
    
    print(f"特定されたリスク総数: {len(risks)}")
    print()
    
    # 重要度別分類
    critical_risks = [r for r in risks if any(word in r for word in ['接続不可', '未インストール', '権限不足'])]
    high_risks = [r for r in risks if any(word in r for word in ['予想精度', '投資管理', 'セキュリティ'])]
    medium_risks = [r for r in risks if r not in critical_risks and r not in high_risks]
    
    if critical_risks:
        print("🚨 【重大】即座対応必須:")
        for risk in critical_risks:
            print(f"  - {risk}")
        print()
    
    if high_risks:
        print("⚠️ 【高】注意深い管理必要:")
        for risk in high_risks[:5]:  # 上位5つ表示
            print(f"  - {risk}")
        if len(high_risks) > 5:
            print(f"  ... 他{len(high_risks)-5}件")
        print()
    
    if medium_risks:
        print("💡 【中】認識・対策推奨:")
        print(f"  - 計{len(medium_risks)}件のリスク要因")
        print()
    
    # 総合評価
    if len(critical_risks) == 0:
        if len(high_risks) <= 3:
            print("📊 総合評価: 【運用可能】")
            print("   重大な問題はなく、高リスク要因も管理可能レベル")
        else:
            print("📊 総合評価: 【要注意運用】") 
            print("   基本運用は可能だが、リスク管理の強化が必要")
    else:
        print("📊 総合評価: 【運用延期推奨】")
        print("   重大な問題があり、解決後の運用開始を推奨")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    analyze_system_risks()