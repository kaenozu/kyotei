#!/usr/bin/env python3
"""
予想ルート（リファクタリング版）
レース予想ページとenhanced prediction機能を責任分離で実装
"""

import logging
from datetime import datetime
from flask import render_template, jsonify, request

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_fetcher import VENUE_MAPPING, calculate_prediction

logger = logging.getLogger(__name__)

class PredictionRoutes:
    """予想関連ルートハンドラー（リファクタリング版）"""
    
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
        self.app.add_url_rule('/race-result/<race_id>', 'predict_race_new', self.predict_race)
        self.app.add_url_rule('/api/races/enhanced-prediction/<race_key>', 'get_enhanced_prediction', self.get_enhanced_prediction)
    
    def predict_race(self, race_id):
        """レース予想ページ（メイン制御）"""
        try:
            # レースIDを解析
            race_info = self._parse_race_id(race_id)
            if not race_info['valid']:
                return race_info['error_response']
            
            # レースデータを取得
            race_data, prediction_result = self._fetch_race_data(race_info)
            
            # レース結果を取得
            race_results = self._get_race_results(race_info)
            
            # 予想結果を取得
            prediction_result = self._get_prediction_result(race_data, prediction_result, race_info)
            
            if not prediction_result:
                return self._render_error_template(race_id, "予想データの生成に失敗しました。しばらく時間をおいて再度お試しください。")
            
            # テンプレートを描画
            return self._render_race_template(race_info, race_data, prediction_result, race_results)
            
        except Exception as e:
            logger.error(f"予想ページエラー: {e}")
            return self._render_error_template(race_id, f"予想エラー: {str(e)}")
    
    def _parse_race_id(self, race_id):
        """レースIDを解析"""
        try:
            parts = race_id.split('_')
            if len(parts) < 2 or len(parts) > 3:
                return {
                    'valid': False,
                    'error_response': (f"不正なレースID: {race_id}", 400)
                }
            
            return {
                'valid': True,
                'venue_id': int(parts[0]),
                'race_number': int(parts[1]),
                'race_date': parts[2] if len(parts) == 3 else None,
                'venue_name': VENUE_MAPPING.get(int(parts[0]), '不明'),
                'race_id': race_id
            }
            
        except (ValueError, IndexError) as e:
            return {
                'valid': False,
                'error_response': (f"レースID解析エラー: {race_id}", 400)
            }
    
    def _fetch_race_data(self, race_info):
        """レースデータを取得"""
        race_data = None
        prediction_result = None
        
        # 今日のAPIデータから取得を試行
        if (race_info['race_date'] is None or 
            race_info['race_date'] == datetime.now().strftime('%Y-%m-%d')):
            race_data = self.fetcher.get_race_detail(race_info['venue_id'], race_info['race_number'])
        
        # APIデータがない場合、データベースから取得
        if not race_data:
            saved_data = self._get_saved_race_data(race_info)
            if saved_data:
                race_data = saved_data['race_data']
                prediction_result = saved_data['prediction_data']
        
        return race_data, prediction_result
    
    def _get_saved_race_data(self, race_info):
        """保存済みレースデータを取得"""
        try:
            tracker = self.AccuracyTracker()
            saved_data = tracker.get_race_details(
                race_info['venue_id'], 
                race_info['race_number'], 
                race_info['race_date']
            )
            if saved_data and saved_data.get('status') == 'found':
                logger.info(f"データベースからレース詳細を取得: {race_info['venue_name']} {race_info['race_number']}R")
                # DummyAccuracyTrackerの戻り値を適切な形式に変換
                return {
                    'race_data': None,  # 実際のレースデータはDummyなので None
                    'prediction_data': saved_data.get('prediction', {})
                }
        except Exception as e:
            logger.warning(f"データベースからの取得失敗: {e}")
        
        return None
    
    def _get_race_results(self, race_info):
        """レース結果を取得（過去レース対応）"""
        try:
            # まず今日のレースから結果を取得
            today_races = self.fetcher.get_today_races()
            if today_races and 'race_results' in today_races:
                for race_result in today_races['race_results']:
                    if (race_result.get('venue_id') == race_info['venue_id'] and 
                        race_result.get('race_number') == race_info['race_number']):
                        
                        winning_boat = race_result.get('winning_boat')
                        place_results = race_result.get('place_results', [])
                        
                        if winning_boat:
                            logger.info(f"今日のレースから結果取得: {race_info['venue_name']} {race_info['race_number']}R - 勝者={winning_boat}号艇")
                            return {
                                'venue_id': race_info['venue_id'],
                                'race_number': race_info['race_number'],
                                'winning_boat': winning_boat,
                                'place_results': place_results,
                                'status': 'found'
                            }
            
            # BoatraceOpenAPIの結果APIから直接取得を試行
            try:
                import requests
                race_date = race_info.get('race_date', datetime.now().strftime('%Y-%m-%d'))
                results_url = f"https://boatraceopenapi.github.io/results/v2/{race_date.replace('-', '')}.json"
                response = requests.get(results_url, timeout=10)
                
                if response.status_code == 200:
                    results_data = response.json()
                    for race_result in results_data.get('results', []):
                        if (race_result.get('race_stadium_number') == race_info['venue_id'] and 
                            race_result.get('race_number') == race_info['race_number']):
                            
                            winning_boat = race_result.get('win')
                            place_results = race_result.get('place', [])
                            trifecta = race_result.get('trifecta', '')
                            
                            if winning_boat:
                                logger.info(f"BoatraceOpenAPIから結果取得: {race_info['venue_name']} {race_info['race_number']}R - 勝者={winning_boat}号艇")
                                return {
                                    'venue_id': race_info['venue_id'],
                                    'race_number': race_info['race_number'],
                                    'winning_boat': winning_boat,
                                    'place_results': place_results,
                                    'trifecta': trifecta,
                                    'status': 'found'
                                }
            except Exception as e:
                logger.warning(f"BoatraceOpenAPI結果取得失敗: {e}")
            
            # フォールバック: AccuracyTrackerから取得
            tracker = self.AccuracyTracker()
            race_results = tracker.get_race_results(
                race_info['venue_id'], 
                race_info['race_number'], 
                race_info['race_date']
            )
            if race_results:
                logger.info(f"AccuracyTrackerからレース結果取得: {race_info['venue_name']} {race_info['race_number']}R")
            return race_results
            
        except Exception as e:
            logger.warning(f"レース結果取得エラー: {e}")
            return None
    
    def _get_prediction_result(self, race_data, existing_prediction, race_info):
        """予想結果を取得"""
        if existing_prediction:
            logger.info(f"保存済み予想使用 {race_info['venue_name']} {race_info['race_number']}R")
            return existing_prediction
        
        # 動作確認済みのAccuracyTracker内の予想システムを使用
        try:
            tracker = self.AccuracyTracker()
            # venue_idとrace_numberで予想を生成
            new_prediction = tracker._generate_real_prediction(
                race_info['venue_id'], 
                race_info['race_number'], 
                race_data  # race_dataをオプション引数として渡す
            )
            
            if new_prediction:
                logger.info(f"予想システム使用 {race_info['venue_name']} {race_info['race_number']}R")
                return new_prediction
                
        except Exception as e:
            logger.warning(f"予想システム失敗: {e}")
        
        # フォールバック: race_dataがある場合のみ従来システムを使用
        if race_data:
            logger.warning("従来システムを使用")
            prediction = calculate_prediction(race_data)
            if prediction:
                return prediction
            else:
                logger.warning("従来システムでも予想データを生成できませんでした")
        
        # 最後のフォールバック: APIから直接データを取得して予想
        logger.info("APIから直接データを取得して予想を試行")
        try:
            # 今日のデータを取得
            today_data = self.fetcher.get_race_detail(race_info['venue_id'], race_info['race_number'])
            if today_data:
                prediction = calculate_prediction(today_data)
                if prediction:
                    logger.info(f"API直接取得で予想成功: {race_info['venue_name']} {race_info['race_number']}R")
                    return prediction
        except Exception as api_e:
            logger.warning(f"API直接取得失敗: {api_e}")
        
        # 終了済みレースの場合、結果データから簡易予想を生成
        logger.info("終了済みレースの場合、結果から情報を表示")
        try:
            race_results = self._get_race_results(race_info)
            if race_results and race_results.get('winning_boat'):
                logger.info(f"終了済みレース: {race_info['venue_name']} {race_info['race_number']}R - 結果表示モード")
                # 結果から簡易予想形式を生成
                return self._create_result_display(race_results, race_info)
        except Exception as result_e:
            logger.warning(f"結果データ取得失敗: {result_e}")
        
        logger.warning("全ての予想手法が失敗しました")
        return None
    
    def _save_prediction(self, race_data, prediction_result):
        """予想結果を保存"""
        try:
            tracker = self.AccuracyTracker()
            tracker.save_race_details(race_data, prediction_result)
            logger.info("新しい予想をデータベースに保存")
        except Exception as e:
            logger.warning(f"予想保存エラー: {e}")
    
    def _render_race_template(self, race_info, race_data, prediction_result, race_results):
        """レース予想テンプレートを描画"""
        # 予想結果の検証
        if not prediction_result or 'racers' not in prediction_result:
            return self._render_error_template(race_info['race_id'], "予想結果の取得に失敗しました")
        
        # レーサーを予想着順順（予想値の高い順）にソート
        sorted_racers = sorted(prediction_result['racers'], 
                             key=lambda x: x.get('prediction_score', 0), 
                             reverse=True)
        
        # 基本情報の抽出（race_dataがない場合もAPIから取得を試行）
        start_time = '未定'
        race_title = ''
        
        if race_data:
            start_time = race_data.get('race_closed_at', '未定')
            race_title = race_data.get('race_title', '')
        else:
            # race_dataがない場合、直接APIから基本情報を取得
            try:
                today_races = self.fetcher.get_today_races()
                if today_races and 'programs' in today_races:
                    for program in today_races['programs']:
                        if (program.get('race_stadium_number') == race_info['venue_id'] and 
                            program.get('race_number') == race_info['race_number']):
                            start_time = program.get('race_closed_at', '未定')
                            race_title = program.get('race_title', '')
                            logger.info(f"APIから基本情報を取得: {race_info['venue_name']} {race_info['race_number']}R - 時刻={start_time}, タイトル={race_title}")
                            break
            except Exception as e:
                logger.warning(f"基本情報取得エラー: {e}")
        
        # 戻り先URL
        referer = request.headers.get('Referer', '')
        back_url = '/accuracy' if 'accuracy' in referer else '/'
        
        return render_template('openapi_predict.html',
                             venue_id=race_info['venue_id'],
                             venue_name=race_info['venue_name'],
                             race_number=race_info['race_number'],
                             race_date=race_info['race_date'] or datetime.now().strftime('%Y-%m-%d'),
                             start_time=start_time,
                             race_title=race_title,
                             racers=sorted_racers,
                             predictions=prediction_result['predictions'],
                             recommended_win=prediction_result['recommended_win'],
                             recommended_place=prediction_result['recommended_place'],
                             confidence=prediction_result['confidence'],
                             betting_recommendations=prediction_result.get('betting_recommendations'),
                             race_results=race_results,
                             back_url=back_url,
                             show_back_button=True)
    

    def _generate_simple_prediction(self, race_info):
        """APIデータがない場合の簡易予想生成"""
        try:
            # 6艇の基本データを生成
            racers = []
            # 実際の選手名（一般的な競艇選手名）
            sample_names = ['田中太郎', '佐藤花子', '鈴木一郎', '高橋美里', '渡辺健太', '伊藤美香']
            
            for i in range(1, 7):
                racers.append({
                    'boat_number': i,
                    'racer_name': sample_names[i-1],
                    'name': sample_names[i-1],  # テンプレート用
                    'prediction_score': 0.5 + (7-i) * 0.05,  # 1号艇が最高
                    'stats': {},
                    'win_rate': 0.25 + (7-i) * 0.02,  # 1号艇が最高
                    'local_win_rate': 0.20 + (7-i) * 0.015,
                    'place_rate': 0.50 + (7-i) * 0.05,
                    'average_st': 0.15 + i * 0.005,
                    'analysis': {
                        'base_strength': 0.4 + (7-i) * 0.05,
                        'local_adaptation': 0.3 + (7-i) * 0.03,
                        'lane_advantage': 0.1 + (7-i) * 0.02,
                        'st_factor': 1.0 + (7-i) * 0.02
                    }
                })
            
            return {
                'racers': racers,
                'predictions': {
                    'win': '1',
                    'place': [1, 2, 3],
                    'trifecta': [1, 2, 3]
                },
                'recommended_win': '1',
                'recommended_place': [1, 2, 3],
                'confidence': 0.3,  # 低い信頼度
                'data_warning': 'APIデータが取得できないため、サンプルデータで予想を表示しています。',
                'betting_recommendations': {
                    'win': 'データ不足のため参考程度',
                    'place': 'データ不足のため参考程度',
                    'primary': {
                        'icon': '⚠️',
                        'risk_level': '低信頼度',
                        'strategy': '1号艇単勝（参考程度）'
                    },
                    'risk_based': [
                        {
                            'level': '低リスク',
                            'bet': '複勝 1-2-3',
                            'amount': 500,
                            'boats': [1, 2, 3],
                            'type': '低リスク',
                            'confidence': 0.65
                        }
                    ],
                    'trifecta_combos': [
                        {'combo': '1-2-3', 'amount': 200},
                        {'combo': '1-3-2', 'amount': 100}
                    ],
                    'budget_allocation': {
                        'win': 300,
                        'place': 500,
                        'trifecta': 200
                    }
                },
                'race_status': 'data_limited',
                'display_mode': 'simple'
            }
            
        except Exception as e:
            logger.error(f"簡易予想生成エラー: {e}")
            return None

    def _create_result_display(self, race_results, race_info):
        """結果データから表示用予想形式を生成"""
        try:
            winning_boat = race_results.get('winning_boat')
            place_results = race_results.get('place_results', [])
            
            # 6艇の基本情報を生成
            racers = []
            for i in range(1, 7):
                position = "1位" if i == winning_boat else ""
                if i in place_results[:3]:
                    position = f"{place_results.index(i) + 1}位"
                
                racers.append({
                    'boat_number': i,
                    'racer_name': f'{i}号艇',
                    'prediction_score': 0.8 if i == winning_boat else 0.2,
                    'position': position,
                    'is_winner': i == winning_boat
                })
            
            return {
                'racers': racers,
                'predictions': {
                    'win': str(winning_boat) if winning_boat else '不明',
                    'place': place_results[:3] if place_results else [],
                    'trifecta': place_results[:3] if len(place_results) >= 3 else []
                },
                'recommended_win': str(winning_boat) if winning_boat else '不明',
                'recommended_place': place_results[:3] if place_results else [],
                'confidence': 1.0,  # 結果なので100%
                'betting_recommendations': {
                    'win': f'{winning_boat}番艇が勝利' if winning_boat else 'データなし',
                    'place': f'着順: {" ".join([f"{i}位:{place_results[i-1]}艇" for i in range(1, min(4, len(place_results)+1))])}' if place_results else 'データなし',
                    'primary': {
                        'icon': '🏁',
                        'risk_level': 'レース終了',
                        'strategy': f'{winning_boat}番艇が勝利' if winning_boat else 'データなし'
                    },
                    'risk_based': [
                        {
                            'level': 'レース終了',
                            'bet': '結果確定済み',
                            'amount': 0,
                            'boats': [],
                            'type': 'レース終了',
                            'confidence': 1.0
                        }
                    ],
                    'trifecta_combos': [
                        {'combo': '結果確定', 'amount': 0}
                    ],
                    'budget_allocation': {
                        'win': 0,
                        'place': 0,
                        'trifecta': 0
                    }
                },
                'race_status': 'finished',
                'display_mode': 'result'
            }
            
        except Exception as e:
            logger.error(f"結果表示データ生成エラー: {e}")
            return None

    def _render_error_template(self, race_id, error_message):
        """エラーテンプレートを描画"""
        # エラー時もrace_dateを抽出して渡す
        try:
            parts = race_id.split('_')
            error_race_date = parts[2] if len(parts) == 3 else datetime.now().strftime('%Y-%m-%d')
        except:
            error_race_date = datetime.now().strftime('%Y-%m-%d')
        
        referer = request.headers.get('Referer', '')
        back_url = '/accuracy' if 'accuracy' in referer else '/'
        
        return render_template('openapi_predict.html',
                             error=f"{error_message}\n\n本日開催予定のレースの確認をお願いします。",
                             race_id=race_id,
                             race_date=error_race_date,
                             back_url=back_url,
                             show_back_button=True,
                             race_results=None)
    
    def get_enhanced_prediction(self, race_key):
        """強化予想システムAPI"""
        try:
            # race_key解析: venue_race_date
            parts = race_key.split('_')
            if len(parts) < 2:
                return jsonify({'error': 'Invalid race key format'}), 400
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            date_str = parts[2] if len(parts) > 2 else datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"強化予想API要求: {VENUE_MAPPING.get(venue_id)} {race_number}R {date_str}")
            
            # 動作確認済みのAccuracyTracker予想システムを使用
            tracker = self.AccuracyTracker()
            # venue_id, race_numberで直接予想を生成
            prediction = tracker._generate_real_prediction(venue_id, race_number)
            
            if not prediction:
                # フォールバック: APIデータと組み合わせて再試行
                race_data = self.fetcher.get_race_detail(venue_id, race_number)
                if race_data:
                    prediction = tracker._generate_real_prediction(venue_id, race_number, race_data)
                else:
                    logger.warning(f"API予想: レースデータ取得失敗 {VENUE_MAPPING.get(venue_id)} {race_number}R")
            
            if prediction:
                logger.info(f"AccuracyTracker予想成功: 信頼度={prediction.get('confidence', 0):.6f}")
                return jsonify({
                    'success': True,
                    'prediction': prediction
                })
            else:
                logger.info("AccuracyTracker予想が None を返しました - API直接取得を試行")
                
                # フォールバック: APIから直接データ取得
                try:
                    race_data = self.fetcher.get_race_detail(venue_id, race_number)
                    if race_data:
                        fallback_prediction = calculate_prediction(race_data)
                        if fallback_prediction:
                            logger.info(f"API直接取得で予想成功: 信頼度={fallback_prediction.get('confidence', 0):.6f}")
                            return jsonify({
                                'success': True,
                                'prediction': fallback_prediction
                            })
                except Exception as api_e:
                    logger.warning(f"API直接取得失敗: {api_e}")
                
                logger.warning("全ての予想手法が失敗しました")
                return jsonify({
                    'success': False,
                    'message': 'データ取得に成功しましたが、予想計算ができませんでした'
                }), 200
                
        except Exception as e:
            logger.error(f"予想API総合エラー: {e}")
            return jsonify({
                'error': '予想システムエラーが発生しました',
                'reason': f'エラー詳細: {str(e)}'
            }), 500