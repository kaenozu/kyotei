#!/usr/bin/env python3
"""
競艇予想システム - シンプル起動スクリプト
統一版システムの簡単起動用
"""

import sys
from accuracy_tracker import KyoteiSystem

def main():
    """シンプル起動"""
    print("=" * 50)
    print("競艇予想システム")
    print("=" * 50)
    
    try:
        system = KyoteiSystem()
        
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command in ['web', 'server']:
                print("Webサーバーを起動しています...")
                port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
                system.start_web_server(port)
                
            elif command in ['test', 'テスト']:
                print("予想テストを実行します...")
                system.run_prediction_test()
                
            elif command in ['accuracy', '的中率']:
                print("的中率分析を実行します...")
                system.show_accuracy_report()
                
            else:
                print("使用方法:")
                print("  python start_kyotei.py web      # Webサーバー起動")
                print("  python start_kyotei.py test     # 予想テスト")
                print("  python start_kyotei.py accuracy # 的中率分析")
        else:
            # 対話モード
            while True:
                print("\n何をしますか？")
                print("1. Webサーバー起動")
                print("2. 予想テスト")
                print("3. 的中率分析")
                print("4. 終了")
                
                choice = input("選択 (1-4): ").strip()
                
                if choice == '1':
                    port = input("ポート番号 (デフォルト:5000): ").strip()
                    port = int(port) if port.isdigit() else 5000
                    print(f"Webサーバーをポート{port}で起動します...")
                    system.start_web_server(port)
                    break
                    
                elif choice == '2':
                    print("予想テストを実行します...")
                    system.run_prediction_test()
                    
                elif choice == '3':
                    print("的中率分析を実行します...")
                    system.show_accuracy_report()
                    
                elif choice == '4':
                    print("終了します。")
                    break
                    
                else:
                    print("無効な選択です。1-4を入力してください。")
    
    except KeyboardInterrupt:
        print("\n終了します。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()