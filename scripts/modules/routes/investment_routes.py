#!/usr/bin/env python3
"""
Investment Routes - 投資関連ルート
投資ダッシュボード、ベット推奨、信頼度可視化など
"""

import json
import logging
import sqlite3
from datetime import datetime
from flask import jsonify, render_template

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_fetcher import VENUE_MAPPING

logger = logging.getLogger(__name__)

class InvestmentRoutes:
    """投資関連ルートハンドラー"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class):
        self.app = app
        self.fetcher = fetcher
        self.AccuracyTracker = accuracy_tracker_class
        
        self._register_routes()
    
    def _register_routes(self):
        """投資関連ルートを登録"""
        self.app.add_url_rule('/api/investment/dashboard', 'investment_dashboard', self.api_investment_dashboard)
        self.app.add_url_rule('/api/confidence/<race_key>', 'confidence_visualization', self.api_confidence_visualization)
        self.app.add_url_rule('/api/bet-recommendation/<race_key>', 'bet_recommendation', self.api_bet_recommendation)
        self.app.add_url_rule('/api/alerts', 'realtime_alerts', self.api_realtime_alerts)
        self.app.add_url_rule('/dashboard', 'enhanced_dashboard', self.enhanced_dashboard)
    
    def api_investment_dashboard(self):
        """投資ダッシュボードAPI"""
        try:
            # 投資戦略システムのインポート（動的）
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                from advanced_investment_strategy import AdvancedInvestmentStrategy
                
                strategy = AdvancedInvestmentStrategy()
                
                # 現在の投資状況取得
                investment_summary = {
                    'daily_spent': strategy.daily_spent,
                    'daily_budget': strategy.daily_budget,
                    'budget_remaining': max(0, strategy.daily_budget - strategy.daily_spent),
                    'win_rate_today': 0.0,
                    'roi_today': 0.0,
                    'recommended_races': []
                }
                
                # 今日の高信頼度レース推奨
                tracker = self.AccuracyTracker()
                today = datetime.now().strftime('%Y-%m-%d')
                
                with sqlite3.connect(tracker.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT venue_id, race_number, prediction_data
                        FROM race_details 
                        WHERE race_date = ? AND prediction_data IS NOT NULL
                    """, (today,))
                    
                    high_confidence_races = []
                    for row in cursor.fetchall():
                        venue_id, race_number, prediction_data_json = row
                        try:
                            prediction_data = json.loads(prediction_data_json)
                            confidence = prediction_data.get('confidence', 0)
                            
                            if confidence >= 0.55:  # 55%以上の信頼度
                                race_info = {
                                    'venue_id': venue_id,
                                    'venue_name': VENUE_MAPPING.get(venue_id, '不明'),
                                    'race_number': race_number,
                                    'confidence': confidence,
                                    'predicted_win': prediction_data.get('recommended_win', 1),
                                    'predicted_place': prediction_data.get('recommended_place', [1, 2, 3])
                                }
                                high_confidence_races.append(race_info)
                        except:
                            continue
                    
                    # 信頼度順でソート
                    high_confidence_races.sort(key=lambda x: x['confidence'], reverse=True)
                    investment_summary['recommended_races'] = high_confidence_races[:5]  # 上位5件
                
                return jsonify({
                    'success': True,
                    'investment_summary': investment_summary
                })
                
            except ImportError:
                # 投資戦略システムが利用できない場合のフォールバック
                return jsonify({
                    'success': True,
                    'investment_summary': {
                        'daily_spent': 0,
                        'daily_budget': 10000,
                        'budget_remaining': 10000,
                        'win_rate_today': 0.0,
                        'roi_today': 0.0,
                        'recommended_races': []
                    }
                })
                
        except Exception as e:
            logger.error(f"投資ダッシュボードエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_confidence_visualization(self, race_key):
        """信頼度可視化API"""
        try:
            parts = race_key.split('_')
            if len(parts) != 2:
                return jsonify({'success': False, 'error': '不正なレースキー'})
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            
            tracker = self.AccuracyTracker()
            today = datetime.now().strftime('%Y-%m-%d')
            
            with sqlite3.connect(tracker.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT prediction_data
                    FROM race_details 
                    WHERE race_date = ? AND venue_id = ? AND race_number = ?
                """, (today, venue_id, race_number))
                
                row = cursor.fetchone()
                if row:
                    try:
                        prediction_data = json.loads(row[0])
                        
                        confidence_breakdown = {
                            'overall_confidence': prediction_data.get('confidence', 0),
                            'factors': {
                                'statistical_accuracy': 0.8,
                                'historical_performance': 0.7,
                                'recent_form': 0.6,
                                'weather_conditions': 0.5
                            },
                            'risk_level': 'medium',
                            'recommendation': 'moderate_bet'
                        }
                        
                        # 信頼度に基づくリスクレベル判定
                        confidence = prediction_data.get('confidence', 0)
                        if confidence >= 0.7:
                            confidence_breakdown['risk_level'] = 'low'
                            confidence_breakdown['recommendation'] = 'strong_bet'
                        elif confidence >= 0.5:
                            confidence_breakdown['risk_level'] = 'medium'
                            confidence_breakdown['recommendation'] = 'moderate_bet'
                        else:
                            confidence_breakdown['risk_level'] = 'high'
                            confidence_breakdown['recommendation'] = 'avoid'
                        
                        return jsonify({
                            'success': True,
                            'race_key': race_key,
                            'confidence_data': confidence_breakdown
                        })
                        
                    except Exception as e:
                        logger.error(f"信頼度データ解析エラー: {e}")
            
            # データがない場合のフォールバック
            return jsonify({
                'success': True,
                'race_key': race_key,
                'confidence_data': {
                    'overall_confidence': 0.5,
                    'factors': {
                        'statistical_accuracy': 0.5,
                        'historical_performance': 0.5,
                        'recent_form': 0.5,
                        'weather_conditions': 0.5
                    },
                    'risk_level': 'high',
                    'recommendation': 'no_data'
                }
            })
            
        except Exception as e:
            logger.error(f"信頼度可視化エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_bet_recommendation(self, race_key):
        """ベット推奨API"""
        try:
            parts = race_key.split('_')
            if len(parts) != 2:
                return jsonify({'success': False, 'error': '不正なレースキー'})
            
            venue_id = int(parts[0])
            race_number = int(parts[1])
            
            tracker = self.AccuracyTracker()
            today = datetime.now().strftime('%Y-%m-%d')
            
            with sqlite3.connect(tracker.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT prediction_data
                    FROM race_details 
                    WHERE race_date = ? AND venue_id = ? AND race_number = ?
                """, (today, venue_id, race_number))
                
                row = cursor.fetchone()
                if row:
                    try:
                        prediction_data = json.loads(row[0])
                        confidence = prediction_data.get('confidence', 0)
                        predicted_win = prediction_data.get('recommended_win', 1)
                        predicted_place = prediction_data.get('recommended_place', [1, 2, 3])
                        
                        # ベット推奨計算
                        bet_recommendations = {
                            'win_bet': {
                                'boat': predicted_win,
                                'recommended_amount': min(1000, confidence * 2000),
                                'confidence': confidence,
                                'expected_return': confidence * 3.0
                            },
                            'place_bet': {
                                'boats': predicted_place[:2],
                                'recommended_amount': min(500, confidence * 1000),
                                'confidence': confidence * 0.8,
                                'expected_return': confidence * 1.5
                            },
                            'strategy': 'conservative' if confidence < 0.6 else 'aggressive'
                        }
                        
                        return jsonify({
                            'success': True,
                            'race_key': race_key,
                            'bet_recommendations': bet_recommendations
                        })
                        
                    except Exception as e:
                        logger.error(f"ベット推奨データ解析エラー: {e}")
            
            # データがない場合のフォールバック
            return jsonify({
                'success': True,
                'race_key': race_key,
                'bet_recommendations': {
                    'win_bet': {
                        'boat': 1,
                        'recommended_amount': 100,
                        'confidence': 0.3,
                        'expected_return': 0.9
                    },
                    'place_bet': {
                        'boats': [1, 2],
                        'recommended_amount': 100,
                        'confidence': 0.4,
                        'expected_return': 0.6
                    },
                    'strategy': 'avoid'
                }
            })
            
        except Exception as e:
            logger.error(f"ベット推奨エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def api_realtime_alerts(self):
        """リアルタイムアラートAPI"""
        try:
            alerts = []
            
            # 高信頼度レースアラート
            tracker = self.AccuracyTracker()
            today = datetime.now().strftime('%Y-%m-%d')
            
            with sqlite3.connect(tracker.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT venue_id, race_number, prediction_data
                    FROM race_details 
                    WHERE race_date = ? AND prediction_data IS NOT NULL
                """, (today,))
                
                for row in cursor.fetchall():
                    venue_id, race_number, prediction_data_json = row
                    try:
                        prediction_data = json.loads(prediction_data_json)
                        confidence = prediction_data.get('confidence', 0)
                        
                        if confidence >= 0.7:  # 70%以上の高信頼度
                            alert = {
                                'type': 'high_confidence',
                                'message': f"{VENUE_MAPPING.get(venue_id, '不明')} {race_number}R - 高信頼度 {confidence:.1%}",
                                'venue_id': venue_id,
                                'race_number': race_number,
                                'confidence': confidence,
                                'timestamp': datetime.now().isoformat()
                            }
                            alerts.append(alert)
                    except:
                        continue
            
            return jsonify({
                'success': True,
                'alerts': alerts
            })
            
        except Exception as e:
            logger.error(f"リアルタイムアラートエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def enhanced_dashboard(self):
        """統合ダッシュボードページ"""
        try:
            return render_template('enhanced_dashboard.html',
                                 title='競艇予想統合ダッシュボード',
                                 current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'))
        except Exception as e:
            logger.error(f"ダッシュボードページエラー: {e}")
            return f"ダッシュボードエラー: {str(e)}", 500