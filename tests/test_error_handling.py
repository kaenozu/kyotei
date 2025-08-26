#!/usr/bin/env python3
"""
拡張エラーハンドリングシステムのテスト
ユーザビリティ向上機能の動作確認
"""

import logging
import json
import time
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_error_pattern_matching():
    """エラーパターンマッチングテスト"""
    print("=== エラーパターンマッチングテスト ===")
    
    try:
        from enhanced_error_handler import enhanced_error_handler, ErrorContext
        
        # テスト用例外
        test_cases = [
            (ConnectionError("Connection timeout after 30s"), "connection_timeout"),
            (requests.exceptions.HTTPError("429 Too Many Requests"), "api_rate_limit"),
            (FileNotFoundError("Race data not found"), "data_not_found"),
            (ValueError("Invalid venue ID: 25"), "invalid_input"),
            (RuntimeError("Internal server error"), "server_error")
        ]
        
        success_count = 0
        
        for exception, expected_pattern in test_cases:
            try:
                # エラーコンテキスト作成
                context = ErrorContext(
                    request_path="/test",
                    request_method="GET",
                    user_agent="Test Agent"
                )
                
                # 拡張エラー作成
                enhanced_error = enhanced_error_handler.create_enhanced_error(exception, context)
                
                print(f"✓ {type(exception).__name__}: {enhanced_error.title}")
                print(f"  カテゴリ: {enhanced_error.category.value}")
                print(f"  重要度: {enhanced_error.severity.value}")
                print(f"  解決策数: {len(enhanced_error.solutions)}")
                print(f"  回復可能: {enhanced_error.is_recoverable}")
                
                success_count += 1
                
            except Exception as e:
                print(f"✗ {type(exception).__name__} 処理失敗: {e}")
        
        print(f"\n結果: {success_count}/{len(test_cases)} 成功")
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_recovery_mechanisms():
    """自動復旧メカニズムテスト"""
    print("\n=== 自動復旧メカニズムテスト ===")
    
    try:
        from enhanced_error_handler import enhanced_error_handler, ErrorContext
        import requests
        
        # 接続タイムアウトエラーテスト
        timeout_error = requests.exceptions.ConnectTimeout("Connection timeout")
        context = ErrorContext(request_path="/api/test")
        
        enhanced_error = enhanced_error_handler.create_enhanced_error(timeout_error, context)
        
        print(f"エラー: {enhanced_error.title}")
        print(f"解決策:")
        for i, solution in enumerate(enhanced_error.solutions, 1):
            print(f"  {i}. {solution.title} (成功率: {solution.success_probability:.1%})")
        
        # 自動復旧試行
        recovery_result = enhanced_error_handler.attempt_recovery(enhanced_error)
        
        if recovery_result:
            print(f"\n✓ 自動復旧試行実行")
            print(f"  アクション: {recovery_result['action']}")
            print(f"  メッセージ: {recovery_result['message']}")
            print(f"  自動実行: {recovery_result['auto_execute']}")
            
            if 'delay' in recovery_result:
                print(f"  遅延: {recovery_result['delay']}秒")
        else:
            print("✗ 自動復旧不可")
        
        # 復旧試行回数確認
        print(f"復旧試行回数: {enhanced_error.recovery_attempts}/{enhanced_error.max_recovery_attempts}")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_user_friendly_responses():
    """ユーザーフレンドリーレスポンステスト"""
    print("\n=== ユーザーフレンドリーレスポンステスト ===")
    
    try:
        from enhanced_error_handler import enhanced_error_handler, ErrorContext
        
        # 404エラーテスト
        not_found_error = FileNotFoundError("Race not found for venue 03, race 15")
        context = ErrorContext(
            request_path="/api/prediction/3/15",
            request_method="GET",
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="127.0.0.1"
        )
        
        enhanced_error = enhanced_error_handler.create_enhanced_error(not_found_error, context)
        response = enhanced_error_handler.generate_user_friendly_response(enhanced_error)
        
        print("✓ ユーザーフレンドリーレスポンス生成成功")
        print(f"  エラーID: {response['error']['id']}")
        print(f"  タイトル: {response['error']['title']}")
        print(f"  メッセージ: {response['error']['message']}")
        print(f"  重要度: {response['error']['severity']}")
        print(f"  カテゴリ: {response['error']['category']}")
        
        print(f"  解決策:")
        for solution in response['error']['solutions']:
            print(f"    - {solution['title']}: {solution['description']}")
            print(f"      推定時間: {solution['estimated_time']}秒")
            print(f"      成功率: {solution['success_rate']}%")
        
        # JSON形式確認
        json_str = json.dumps(response, ensure_ascii=False, indent=2)
        print(f"\n  JSON サイズ: {len(json_str)} 文字")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_error_analytics():
    """エラー分析ログテスト"""
    print("\n=== エラー分析ログテスト ===")
    
    try:
        from enhanced_error_handler import enhanced_error_handler, ErrorContext
        
        # 複数エラーでパターン分析
        error_patterns = [
            (ConnectionError("timeout"), "/api/races"),
            (ValueError("invalid input"), "/api/prediction/99/1"),
            (RuntimeError("server error"), "/predict/3/5"),
            (requests.exceptions.HTTPError("429"), "/api/transparency/1/1")
        ]
        
        for exception, path in error_patterns:
            context = ErrorContext(
                request_path=path,
                request_method="GET",
                user_agent=f"TestBot/1.0",
                ip_address="192.168.1.100"
            )
            
            enhanced_error = enhanced_error_handler.create_enhanced_error(exception, context)
            enhanced_error_handler.log_error_analytics(enhanced_error)
            
            print(f"✓ 分析ログ記録: {enhanced_error.category.value} - {path}")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_error_context():
    """エラーコンテキストテスト"""
    print("\n=== エラーコンテキストテスト ===")
    
    try:
        from enhanced_error_handler import ErrorContext
        
        # 詳細コンテキスト作成
        context = ErrorContext(
            user_id="test_user_001",
            session_id="sess_12345",
            request_path="/api/prediction/11/8",
            request_method="POST",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ip_address="203.0.113.100",
            additional_data={
                "venue_name": "びわこ",
                "race_number": 8,
                "prediction_type": "advanced",
                "cache_hit": False
            }
        )
        
        print("✓ エラーコンテキスト作成成功")
        print(f"  ユーザーID: {context.user_id}")
        print(f"  セッションID: {context.session_id}")
        print(f"  リクエストパス: {context.request_path}")
        print(f"  メソッド: {context.request_method}")
        print(f"  IPアドレス: {context.ip_address}")
        print(f"  タイムスタンプ: {context.timestamp}")
        print(f"  追加データ: {len(context.additional_data)}項目")
        
        return True
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_performance():
    """パフォーマンステスト"""
    print("\n=== パフォーマンステスト ===")
    
    try:
        from enhanced_error_handler import enhanced_error_handler, ErrorContext
        
        # 100回エラー処理のパフォーマンス測定
        start_time = time.time()
        
        for i in range(100):
            error = RuntimeError(f"Test error {i}")
            context = ErrorContext(request_path=f"/test/{i}")
            
            enhanced_error = enhanced_error_handler.create_enhanced_error(error, context)
            response = enhanced_error_handler.generate_user_friendly_response(enhanced_error)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 100
        
        print(f"✓ パフォーマンステスト完了")
        print(f"  100回処理時間: {total_time:.3f}秒")
        print(f"  平均処理時間: {avg_time:.3f}秒")
        print(f"  1秒あたり処理数: {1/avg_time:.1f}件")
        
        # パフォーマンス基準確認
        if avg_time < 0.01:  # 10ms以下
            print("  ✓ パフォーマンス良好")
            return True
        else:
            print("  ⚠ パフォーマンス要改善")
            return False
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def main():
    """メインテスト実行"""
    print("拡張エラーハンドリングシステム テスト開始")
    print("=" * 60)
    
    results = []
    
    # 各テスト実行
    results.append(test_error_pattern_matching())
    results.append(test_recovery_mechanisms())
    results.append(test_user_friendly_responses())
    results.append(test_error_analytics())
    results.append(test_error_context())
    results.append(test_performance())
    
    # 結果集計
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"テスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("✅ すべてのテストが成功しました！")
        print("\n📝 拡張エラーハンドリング機能:")
        print("- インテリジェントエラーパターンマッチング")
        print("- 自動復旧メカニズム")
        print("- ユーザーフレンドリーエラーメッセージ")
        print("- 詳細な解決策提示")
        print("- エラー分析とログ記録")
        print("- コンテキスト情報の保持")
        print("- 高速なエラー処理")
        
        print("\n🚀 次のステップ:")
        print("1. Webサーバーを起動")
        print("2. 存在しないURLにアクセスして404エラー確認")
        print("3. /api/prediction/99/99 で無効データエラー確認")
        print("4. 各種エラーシナリオで動作確認")
    else:
        print("❌ 一部テストが失敗しました")
    
    return passed == total


if __name__ == "__main__":
    main()