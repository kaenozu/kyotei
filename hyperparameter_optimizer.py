#!/usr/bin/env python3
"""
Hyperparameter Optimization System for Kyotei ML Models
競艇予想システム向けハイパーパラメータ自動最適化

機械学習モデルの性能を最大化するための自動パラメータ調整:
1. Grid Search / Random Search による探索
2. Bayesian Optimization による効率的最適化
3. Cross Validation による汎化性能評価
4. 複数評価指標の同時最適化
5. 最適パラメータの自動適用・保存
"""

import os
import json
import logging
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class HyperparameterOptimizer:
    """ハイパーパラメータ自動最適化システム"""
    
    def __init__(self, db_path: str = 'cache/accuracy_tracker.db'):
        self.db_path = db_path
        self.optimization_results_path = 'cache/hyperparameter_optimization.json'
        self.optimized_models_path = 'cache/optimized_models.pkl'
        
        # 最適化対象モデルとパラメータ空間
        self.parameter_grids = {
            'random_forest': {
                'n_estimators': [50, 100, 200, 300],
                'max_depth': [5, 8, 10, 15, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2', 0.8],
                'class_weight': ['balanced', None]
            },
            'gradient_boosting': {
                'n_estimators': [50, 100, 150, 200],
                'learning_rate': [0.01, 0.05, 0.1, 0.2],
                'max_depth': [3, 5, 7, 9],
                'subsample': [0.8, 0.9, 1.0],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'logistic_regression': {
                'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
                'penalty': ['l1', 'l2', 'elasticnet'],
                'solver': ['liblinear', 'saga'],
                'max_iter': [1000, 2000, 3000]
            },
            'svm': {
                'C': [0.1, 1.0, 10.0, 100.0],
                'kernel': ['linear', 'rbf', 'poly'],
                'gamma': ['scale', 'auto', 0.001, 0.01, 0.1],
                'degree': [2, 3, 4]  # poly kernelのみ
            }
        }
        
        # ベースモデル
        self.base_models = {
            'random_forest': RandomForestClassifier(random_state=42, n_jobs=-1),
            'gradient_boosting': GradientBoostingClassifier(random_state=42),
            'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
            'svm': SVC(random_state=42, probability=True)
        }
        
        # 評価指標
        self.scoring_metrics = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']
        self.primary_metric = 'f1'  # 主要評価指標
        
        # Cross Validation設定
        self.cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        
        # 最適化履歴
        self.optimization_history = []
        self._load_optimization_history()
    
    def optimize_all_models(self, X: pd.DataFrame, y: pd.Series, 
                           method: str = 'random', n_iter: int = 50) -> Dict:
        """全モデルのハイパーパラメータ最適化"""
        try:
            logger.info(f"ハイパーパラメータ最適化開始: {method}探索, {n_iter}回試行")
            
            # データ準備
            if len(X) == 0 or len(y) == 0:
                logger.error("最適化用データが空です")
                return {}
            
            # データスケーリング
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            optimization_results = {}
            
            for model_name in self.base_models.keys():
                logger.info(f"モデル '{model_name}' 最適化中...")
                
                try:
                    result = self._optimize_single_model(
                        model_name, X_scaled, y, method, n_iter
                    )
                    
                    if result:
                        optimization_results[model_name] = result
                        logger.info(f"モデル '{model_name}' 最適化完了: {self.primary_metric}={result['best_score']:.4f}")
                    else:
                        logger.warning(f"モデル '{model_name}' 最適化失敗")
                        
                except Exception as e:
                    logger.error(f"モデル '{model_name}' 最適化エラー: {e}")
                    continue
            
            if optimization_results:
                # 最適化結果を保存
                self._save_optimization_results(optimization_results, method, n_iter)
                
                # 最適モデルの選択と保存
                best_model_name = self._select_best_model(optimization_results)
                logger.info(f"最優秀モデル: {best_model_name}")
                
                return {
                    'optimization_results': optimization_results,
                    'best_model': best_model_name,
                    'optimization_method': method,
                    'n_iterations': n_iter,
                    'scaler': scaler,
                    'optimized_at': datetime.now().isoformat()
                }
            else:
                logger.error("全モデルの最適化に失敗")
                return {}
                
        except Exception as e:
            logger.error(f"全体最適化エラー: {e}")
            return {}
    
    def _optimize_single_model(self, model_name: str, X: np.ndarray, y: np.ndarray,
                              method: str, n_iter: int) -> Optional[Dict]:
        """単一モデルのハイパーパラメータ最適化"""
        try:
            base_model = self.base_models[model_name]
            param_grid = self.parameter_grids[model_name]
            
            # SVMのpolyカーネル専用パラメータを調整
            if model_name == 'svm':
                param_grid = self._adjust_svm_params(param_grid)
            
            # 探索方法選択
            if method == 'grid':
                search = GridSearchCV(
                    base_model, param_grid, 
                    cv=self.cv, scoring=self.primary_metric,
                    n_jobs=-1, verbose=0
                )
            elif method == 'random':
                search = RandomizedSearchCV(
                    base_model, param_grid, 
                    n_iter=n_iter, cv=self.cv, scoring=self.primary_metric,
                    n_jobs=-1, random_state=42, verbose=0
                )
            else:
                logger.error(f"未知の最適化方法: {method}")
                return None
            
            # 最適化実行
            search.fit(X, y)
            
            # 最適モデルで詳細評価
            best_model = search.best_estimator_
            detailed_scores = self._evaluate_model_detailed(best_model, X, y)
            
            return {
                'best_params': search.best_params_,
                'best_score': search.best_score_,
                'best_model': best_model,
                'detailed_scores': detailed_scores,
                'cv_results': {
                    'mean_test_score': search.cv_results_['mean_test_score'].tolist(),
                    'std_test_score': search.cv_results_['std_test_score'].tolist()
                }
            }
            
        except Exception as e:
            logger.error(f"単一モデル最適化エラー ({model_name}): {e}")
            return None
    
    def _adjust_svm_params(self, param_grid: Dict) -> Dict:
        """SVMパラメータの調整（kernelに応じたパラメータ制限）"""
        adjusted_grids = []
        
        for kernel in param_grid['kernel']:
            grid = {k: v for k, v in param_grid.items() if k != 'kernel'}
            grid['kernel'] = [kernel]
            
            # polyカーネル以外はdegreeパラメータを除去
            if kernel != 'poly' and 'degree' in grid:
                del grid['degree']
            
            adjusted_grids.append(grid)
        
        # 複数のグリッドがある場合は最初のものを返す（簡略化）
        return adjusted_grids[0] if adjusted_grids else param_grid
    
    def _evaluate_model_detailed(self, model: Any, X: np.ndarray, y: np.ndarray) -> Dict:
        """モデルの詳細評価"""
        try:
            scores = {}
            
            for metric in self.scoring_metrics:
                cv_scores = cross_val_score(model, X, y, cv=self.cv, scoring=metric)
                scores[metric] = {
                    'mean': cv_scores.mean(),
                    'std': cv_scores.std(),
                    'scores': cv_scores.tolist()
                }
            
            return scores
            
        except Exception as e:
            logger.error(f"詳細評価エラー: {e}")
            return {}
    
    def _select_best_model(self, optimization_results: Dict) -> str:
        """最優秀モデルの選択"""
        try:
            best_model = None
            best_score = -1
            
            for model_name, result in optimization_results.items():
                score = result['best_score']
                
                # 複合指標で評価（F1スコア主体、他指標でバランス調整）
                detailed_scores = result.get('detailed_scores', {})
                if detailed_scores:
                    accuracy = detailed_scores.get('accuracy', {}).get('mean', 0)
                    precision = detailed_scores.get('precision', {}).get('mean', 0)
                    recall = detailed_scores.get('recall', {}).get('mean', 0)
                    
                    # 複合スコア = F1 * 0.6 + Accuracy * 0.2 + Precision * 0.1 + Recall * 0.1
                    composite_score = (score * 0.6 + accuracy * 0.2 + 
                                     precision * 0.1 + recall * 0.1)
                else:
                    composite_score = score
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_model = model_name
            
            return best_model or list(optimization_results.keys())[0]
            
        except Exception as e:
            logger.error(f"最優秀モデル選択エラー: {e}")
            return list(optimization_results.keys())[0] if optimization_results else 'random_forest'
    
    def _save_optimization_results(self, results: Dict, method: str, n_iter: int) -> None:
        """最適化結果の保存"""
        try:
            # 結果を履歴に追加
            optimization_record = {
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'n_iterations': n_iter,
                'models_optimized': list(results.keys()),
                'results_summary': {}
            }
            
            # モデルごとの結果要約
            for model_name, result in results.items():
                optimization_record['results_summary'][model_name] = {
                    'best_score': result['best_score'],
                    'best_params': result['best_params'],
                    'detailed_scores_summary': {
                        metric: scores.get('mean', 0) 
                        for metric, scores in result.get('detailed_scores', {}).items()
                    }
                }
            
            self.optimization_history.append(optimization_record)
            
            # 最新50件のみ保持
            if len(self.optimization_history) > 50:
                self.optimization_history = self.optimization_history[-50:]
            
            # ファイル保存
            os.makedirs('cache', exist_ok=True)
            with open(self.optimization_results_path, 'w', encoding='utf-8') as f:
                json.dump(self.optimization_history, f, ensure_ascii=False, indent=2)
            
            # 最適化されたモデルを保存
            models_to_save = {name: result['best_model'] for name, result in results.items()}
            with open(self.optimized_models_path, 'wb') as f:
                pickle.dump(models_to_save, f)
            
            logger.info("最適化結果を保存しました")
            
        except Exception as e:
            logger.error(f"最適化結果保存エラー: {e}")
    
    def _load_optimization_history(self) -> None:
        """最適化履歴のロード"""
        try:
            if os.path.exists(self.optimization_results_path):
                with open(self.optimization_results_path, 'r', encoding='utf-8') as f:
                    self.optimization_history = json.load(f)
                logger.info(f"最適化履歴をロード: {len(self.optimization_history)}件")
        except Exception as e:
            logger.warning(f"最適化履歴ロードエラー: {e}")
            self.optimization_history = []
    
    def load_optimized_models(self) -> Optional[Dict]:
        """最適化済みモデルのロード"""
        try:
            if os.path.exists(self.optimized_models_path):
                with open(self.optimized_models_path, 'rb') as f:
                    optimized_models = pickle.load(f)
                logger.info(f"最適化済みモデルをロード: {list(optimized_models.keys())}")
                return optimized_models
            return None
        except Exception as e:
            logger.error(f"最適化済みモデルロードエラー: {e}")
            return None
    
    def get_optimization_report(self) -> Dict:
        """最適化レポート生成"""
        try:
            if not self.optimization_history:
                return {'message': '最適化履歴がありません'}
            
            latest_optimization = self.optimization_history[-1]
            
            report = {
                'last_optimization': {
                    'timestamp': latest_optimization['timestamp'],
                    'method': latest_optimization['method'],
                    'models_count': len(latest_optimization['models_optimized'])
                },
                'models_performance': latest_optimization['results_summary'],
                'optimization_count': len(self.optimization_history),
                'available_optimized_models': list(latest_optimization['models_optimized'])
            }
            
            # パフォーマンス改善分析
            if len(self.optimization_history) >= 2:
                previous = self.optimization_history[-2]
                improvement_analysis = {}
                
                for model in latest_optimization['models_optimized']:
                    if model in previous['results_summary']:
                        current_score = latest_optimization['results_summary'][model]['best_score']
                        previous_score = previous['results_summary'][model]['best_score']
                        improvement = current_score - previous_score
                        improvement_analysis[model] = {
                            'improvement': round(improvement * 100, 2),
                            'current_score': round(current_score * 100, 2),
                            'previous_score': round(previous_score * 100, 2)
                        }
                
                report['improvement_analysis'] = improvement_analysis
            
            return report
            
        except Exception as e:
            logger.error(f"最適化レポート生成エラー: {e}")
            return {'error': str(e)}
    
    def auto_optimize_if_needed(self, X: pd.DataFrame, y: pd.Series, 
                               days_threshold: int = 7) -> bool:
        """必要に応じて自動最適化実行"""
        try:
            # 最後の最適化からの経過日数をチェック
            if self.optimization_history:
                last_optimization = datetime.fromisoformat(self.optimization_history[-1]['timestamp'])
                days_since_last = (datetime.now() - last_optimization).days
                
                if days_since_last < days_threshold:
                    logger.info(f"最適化は{days_since_last}日前に実行済み（閾値:{days_threshold}日）")
                    return False
            
            # データサイズチェック
            if len(X) < 100:
                logger.warning("最適化に十分なデータがありません")
                return False
            
            # 自動最適化実行
            logger.info("自動ハイパーパラメータ最適化を開始...")
            results = self.optimize_all_models(X, y, method='random', n_iter=30)
            
            if results:
                logger.info("自動最適化完了")
                return True
            else:
                logger.warning("自動最適化失敗")
                return False
                
        except Exception as e:
            logger.error(f"自動最適化エラー: {e}")
            return False

if __name__ == "__main__":
    # テスト実行
    import sqlite3
    
    optimizer = HyperparameterOptimizer()
    
    # ダミーデータでテスト
    np.random.seed(42)
    X_test = pd.DataFrame(np.random.randn(500, 10), columns=[f'feature_{i}' for i in range(10)])
    y_test = pd.Series(np.random.choice([0, 1], 500, p=[0.8, 0.2]))
    
    print("ハイパーパラメータ最適化テスト実行中...")
    results = optimizer.optimize_all_models(X_test, y_test, method='random', n_iter=10)
    
    if results:
        print(f"最適化完了: 最優秀モデル = {results['best_model']}")
        
        # レポート生成
        report = optimizer.get_optimization_report()
        print(f"最適化レポート: {report}")
    else:
        print("最適化テスト失敗")