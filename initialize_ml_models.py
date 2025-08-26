#!/usr/bin/env python3
"""
機械学習モデル初期学習スクリプト
"""
import sys
import os
import logging

# プロジェクトルートをsys.pathに追加
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_advanced_ml():
    """Advanced ML Predictorを初期化・学習"""
    try:
        logger.info("Advanced ML Predictor初期化中...")
        from advanced_ml_predictor import AdvancedMLPredictor
        
        predictor = AdvancedMLPredictor()
        
        # 明示的にモデル学習を実行
        logger.info("モデル学習を開始...")
        predictor._train_models()
        
        logger.info("Advanced ML Predictor初期化完了")
        return True
        
    except Exception as e:
        logger.error(f"Advanced ML Predictor初期化エラー: {e}")
        return False

def initialize_improved_ml():
    """Improved ML Predictorを初期化・学習"""
    try:
        logger.info("Improved ML Predictor初期化中...")
        from improved_ml_predictor import ImprovedMLPredictor
        
        predictor = ImprovedMLPredictor()
        
        # 初期化時に自動で学習が実行されるはず
        logger.info("Improved ML Predictor初期化完了")
        return True
        
    except Exception as e:
        logger.error(f"Improved ML Predictor初期化エラー: {e}")
        return False

def main():
    """メイン処理"""
    logger.info("機械学習モデル初期学習を開始")
    
    # cacheディレクトリ作成
    os.makedirs('cache', exist_ok=True)
    
    success_count = 0
    
    # Advanced ML初期化
    if initialize_advanced_ml():
        success_count += 1
    
    # Improved ML初期化  
    if initialize_improved_ml():
        success_count += 1
    
    logger.info(f"初期化完了: {success_count}/2 システムが成功")
    
    if success_count > 0:
        logger.info("機械学習システムの準備が完了しました")
        return True
    else:
        logger.error("すべての機械学習システムの初期化に失敗しました")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)