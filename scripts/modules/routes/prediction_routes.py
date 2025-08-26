#!/usr/bin/env python3
"""
Prediction Routes - 予想関連ルート
レース予想ページとenhanced prediction機能
"""

import json
import logging
from datetime import datetime
from flask import render_template, jsonify, request

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_fetcher import VENUE_MAPPING, calculate_prediction

logger = logging.getLogger(__name__)

class PredictionRoutes:
    """予想関連ルートハンドラー"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class, enhanced_predictor_class):
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        self.EnhancedPredictor = enhanced_predictor_class
        
        # EnhancedPredictor単一インスタンス（重い初期化を1回のみ）
        self._enhanced_predictor_instance = None
        
        self._register_routes()
    
    def _register_routes(self):
        """予想関連ルートを登録"""
        self.app.add_url_rule('/predict/<race_id>', 'predict_race', self.predict_race)
        self.app.add_url_rule('/api/races/enhanced-prediction/<race_key>', 'get_enhanced_prediction', self.get_enhanced_prediction)
    
    def predict_race(self, race_id):
        """レース予想ページ"""
        try:
            # race_id解析 (venue_race または venue_race_date)
            parts = race_id.split('_')
            if len(parts) < 2 or len(parts) > 3:
                return f"不正なレースID: {race_id}", 400
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            race_date = parts[2] if len(parts) == 3 else None
            
            race_data = None
            prediction_result = None
            venue_name = VENUE_MAPPING.get(venue_id, '不明')
            is_from_database = False
            
            # まず今日のAPIデータから取得を試行
            if race_date is None or race_date == datetime.now().strftime('%Y-%m-%d'):
                race_data = self.fetcher.get_race_detail(venue_id, race_number)
            
            # APIデータがない場合、データベースから取得
            if not race_data:
                try:
                    tracker = self.AccuracyTracker()
                    saved_data = tracker.get_race_details(venue_id, race_number, race_date)
                    if saved_data:
                        race_data = saved_data['race_data']
                        prediction_result = saved_data['prediction_data']
                        venue_name = saved_data['venue_name']
                        is_from_database = True
                        logger.info(f"データベースからレース詳細を取得: {venue_name} {race_number}R")
                except Exception as e:
                    logger.warning(f"データベースからの取得失敗: {e}")
            
            if not race_data:
                # Refererヘッダーから戻り先を取得
                referer = request.headers.get('Referer', '')
                back_url = '/accuracy' if 'accuracy' in referer else '/'
                
                return render_template('openapi_predict.html',
                                     error=f"レースデータが見つかりません: {race_id}",
                                     race_id=race_id,
                                     venue_name=venue_name,
                                     race_number=race_number,
                                     back_url=back_url,
                                     show_back_button=True)
            
            # 基本情報
            start_time = race_data.get('race_closed_at', '未定')
            race_title = race_data.get('race_title', '')
            
            # 予想計算（常に最新の予想を計算）
            enhanced_predictor = self.EnhancedPredictor()
            new_prediction = enhanced_predictor.calculate_enhanced_prediction(venue_id, race_number, 'today')
            
            logger.info(f"予想詳細 {venue_name} {race_number}R - DB予想:{prediction_result is not None}, 新予想:{new_prediction is not None}")
            
            if new_prediction:
                prediction_result = new_prediction
                logger.info(f"新しい予想使用 {venue_name} {race_number}R: 推奨={new_prediction.get('recommended_win')}, 複勝={new_prediction.get('recommended_place')}, 信頼度={new_prediction.get('confidence', 0):.6f}")
                # 新しい予想をデータベースに保存/更新
                if not is_from_database:
                    try:
                        tracker = self.AccuracyTracker()
                        tracker.save_race_details(race_data, prediction_result)
                        logger.info(f"新しい予想をデータベースに保存: {venue_name} {race_number}R")
                    except Exception as e:
                        logger.warning(f"予想保存エラー: {e}")
            elif not prediction_result:
                # 新しい計算も失敗し、データベース予想もない場合のフォールバック
                logger.warning("強化予想システム失敗、従来システムを使用")
                prediction_result = calculate_prediction(race_data)
            else:
                logger.info(f"データベース予想使用: 推奨={prediction_result.get('recommended_win')}, 信頼度={prediction_result.get('confidence', 0):.6f}")
                
                # 予想データとレース詳細データを保存
                if not is_from_database:
                    try:
                        tracker = self.AccuracyTracker()
                        # 予想データ保存（的中率追跡用）
                        tracker.save_prediction(race_data, prediction_result)
                        # レース詳細データ保存（予想詳細画面永続化用）
                        tracker.save_race_details(race_data, prediction_result)
                    except Exception as e:
                        logger.warning(f"データ保存失敗: {e}")
            
            # レーサーを予想着順順（予想値の高い順）にソート
            sorted_racers = sorted(prediction_result['racers'], 
                                 key=lambda x: x.get('prediction', 0), 
                                 reverse=True)
            
            # Refererヘッダーから戻り先を取得
            referer = request.headers.get('Referer', '')
            back_url = '/accuracy' if 'accuracy' in referer else '/'
            
            return render_template('openapi_predict.html',
                                 venue_id=venue_id,
                                 venue_name=venue_name,
                                 race_number=race_number,
                                 start_time=start_time,
                                 race_title=race_title,
                                 racers=sorted_racers,
                                 predictions=prediction_result['predictions'],
                                 recommended_win=prediction_result['recommended_win'],
                                 recommended_place=prediction_result['recommended_place'],
                                 confidence=prediction_result['confidence'],
                                 betting_recommendations=prediction_result.get('betting_recommendations'),
                                 back_url=back_url,
                                 show_back_button=True)
        
        except Exception as e:
            logger.error(f"予想ページエラー: {e}")
            # Refererヘッダーから戻り先を取得
            referer = request.headers.get('Referer', '')
            back_url = '/accuracy' if 'accuracy' in referer else '/'
            
            return render_template('openapi_predict.html',
                                 error=f"予想エラー: {str(e)}",
                                 race_id=race_id,
                                 back_url=back_url,
                                 show_back_button=True)
    
    def get_enhanced_prediction(self, race_key):
        """強化予想システムAPI"""
        try:
            if not self._enhanced_predictor_instance:
                logger.info("EnhancedPredictorインスタンス初期化中...")
                self._enhanced_predictor_instance = self.EnhancedPredictor()
                logger.info("EnhancedPredictorインスタンス初期化完了")
            
            # race_key解析: venue_race_date
            parts = race_key.split('_')
            if len(parts) < 2:
                return jsonify({'error': 'Invalid race key format'}), 400
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            date_str = parts[2] if len(parts) > 2 else 'today'
            
            logger.info(f"強化予想API要求: {VENUE_MAPPING.get(venue_id)} {race_number}R {date_str}")
            
            prediction = self._enhanced_predictor_instance.calculate_enhanced_prediction(
                venue_id, race_number, date_str
            )
            
            if prediction:
                logger.info(f"強化予想成功: 信頼度={prediction.get('confidence', 0):.6f}")
                return jsonify({
                    'success': True,
                    'prediction': prediction
                })
            else:
                logger.warning("強化予想データが取得できませんでした")
                return jsonify({'error': 'No prediction data available'}), 404
                
        except Exception as e:
            logger.error(f"強化予想エラー: {e}")
            return jsonify({'error': str(e)}), 500