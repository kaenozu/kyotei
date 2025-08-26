#!/usr/bin/env python3
"""
競艇予測システム メインエントリーポイント
リファクタリング後の統合実行スクリプト
"""

import sys
from pathlib import Path

# srcディレクトリをパスに追加
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# 直接インポートでエラーを回避
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from prediction.main_predictor import ProductionPredictionSystem
from monitoring.data_monitoring_system import DataMonitoringSystem
from core.logging_config import setup_logging

def main():
    """メイン実行関数"""
    logger = setup_logging(__name__)
    logger.info("=== 競艇予測システム起動 ===")
    logger.info("リファクタリング済み統合システム v2.0")
    
    try:
        # 実戦予測システム起動
        predictor = ProductionPredictionSystem()
        logger.info("実戦予測システム初期化完了")
        
        # 監視システム起動
        monitor = DataMonitoringSystem()
        logger.info("監視システム初期化完了")
        
        # 日次予測実行
        logger.info("日次予測実行開始...")
        predictor.run_daily_predictions()
        
        # システム健全性監視
        logger.info("システム監視実行...")
        monitor.run_daily_monitoring()
        
        logger.info("=== システム正常完了 ===")
        
    except Exception as e:
        logger.error(f"システムエラー: {e}")
        raise

if __name__ == "__main__":
    main()