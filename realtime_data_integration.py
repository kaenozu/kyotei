"""
リアルタイムデータ統合システム v1.0

気象データ、水面状況、直前情報、オッズ変動を統合した
リアルタイム予想強化システム
"""
import requests
import json
import sqlite3
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


class RealtimeDataIntegration:
    def __init__(self, db_path='cache/accuracy_tracker.db'):
        """リアルタイムデータ統合システム初期化"""
        self.db_path = db_path
        self.weather_cache = {}
        self.odds_cache = {}
        self.venue_conditions = {}
        self.market_sentiment = {}
        
        # 外部APIエンドポイント（実際のAPIキーは環境変数から取得）
        self.apis = {
            'jma_weather': 'https://www.jma.go.jp/bosai/forecast/data/forecast/',
            'venue_conditions': 'https://boatraceopenapi.github.io/conditions/v1/',
            'odds_data': 'https://boatraceopenapi.github.io/odds/v1/'
        }
        
        self._init_database()
    
    def _init_database(self):
        """データベーステーブル初期化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # リアルタイムデータテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS realtime_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venue_id INTEGER,
                    race_number INTEGER,
                    date_str TEXT,
                    data_type TEXT,
                    data_content TEXT,
                    confidence_boost REAL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # オッズ変動履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS odds_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venue_id INTEGER,
                    race_number INTEGER,
                    date_str TEXT,
                    bet_type TEXT,
                    racer_number INTEGER,
                    odds_value REAL,
                    volume INTEGER,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("[INFO] リアルタイムデータベース初期化完了")
        
        except Exception as e:
            print(f"[ERROR] データベース初期化エラー: {e}")
    
    async def fetch_weather_data(self, venue_id):
        """気象データ取得"""
        try:
            # 会場ID to 地域コードマッピング（簡易版）
            venue_to_area = {
                1: '100000',    # 桐生 → 群馬
                2: '130000',    # 戸田 → 東京
                3: '130000',    # 江戸川 → 東京
                4: '130000',    # 平和島 → 東京
                5: '130000',    # 多摩川 → 東京
                6: '220000',    # 浜名湖 → 静岡
                7: '230000',    # 蒲郡 → 愛知
                8: '230000',    # 常滑 → 愛知
                9: '240000',    # 津 → 三重
                10: '180000',   # 三国 → 福井
                11: '250000',   # びわこ → 滋賀
                12: '270000',   # 住之江 → 大阪
                13: '280000',   # 尼崎 → 兵庫
                14: '360000',   # 鳴門 → 徳島
                15: '370000',   # 丸亀 → 香川
                16: '330000',   # 児島 → 岡山
                17: '340000',   # 宮島 → 広島
                18: '350000',   # 徳山 → 山口
                19: '350000',   # 下関 → 山口
                20: '400000',   # 若松 → 福岡
                21: '400000',   # 芦屋 → 福岡
                22: '400000',   # 福岡 → 福岡
                23: '410000',   # 唐津 → 佐賀
                24: '420000'    # 大村 → 長崎
            }
            
            area_code = venue_to_area.get(venue_id, '130000')
            
            # キャッシュチェック（5分間有効）
            cache_key = f"weather_{venue_id}"
            if cache_key in self.weather_cache:
                cached_time, cached_data = self.weather_cache[cache_key]
                if time.time() - cached_time < 300:  # 5分
                    return cached_data
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.apis['jma_weather']}{area_code}.json"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        weather_data = await response.json()
                        
                        # 天気情報の解析
                        weather_info = self._parse_weather_data(weather_data)
                        
                        # キャッシュに保存
                        self.weather_cache[cache_key] = (time.time(), weather_info)
                        
                        print(f"[INFO] 気象データ取得完了: 会場{venue_id}")
                        return weather_info
                    else:
                        print(f"[WARNING] 気象データ取得失敗: HTTP {response.status}")
                        return self._get_default_weather()
        
        except Exception as e:
            print(f"[ERROR] 気象データ取得エラー: {e}")
            return self._get_default_weather()
    
    def _parse_weather_data(self, weather_data):
        """気象データ解析"""
        try:
            forecast = weather_data[0]['timeSeries'][0]
            area_forecast = forecast['areas'][0]
            
            weather_code = area_forecast['weatherCodes'][0]
            wind_data = forecast['areas'][1] if len(forecast['areas']) > 1 else {}
            
            # 天気コードから競艇への影響を判定
            weather_impact = self._analyze_weather_impact(weather_code)
            
            return {
                'weather_code': weather_code,
                'condition': area_forecast['weathers'][0],
                'wind_direction': wind_data.get('winds', ['不明'])[0],
                'wave_height': self._estimate_wave_height(weather_code),
                'visibility': self._estimate_visibility(weather_code),
                'racing_impact': weather_impact,
                'confidence_modifier': weather_impact['confidence_modifier'],
                'update_time': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"[ERROR] 気象データ解析エラー: {e}")
            return self._get_default_weather()
    
    def _analyze_weather_impact(self, weather_code):
        """天気の競艇への影響分析"""
        try:
            weather_code = int(weather_code)
            
            if weather_code in [100, 101, 110, 111]:  # 晴れ・薄曇り
                return {
                    'condition': 'excellent',
                    'visibility_impact': 1.0,
                    'wave_impact': 0.8,
                    'confidence_modifier': 1.1,
                    'favorable_positions': [1, 2, 3]  # インコースが有利
                }
            elif weather_code in [200, 201, 210, 211]:  # 曇り
                return {
                    'condition': 'good',
                    'visibility_impact': 0.9,
                    'wave_impact': 0.9,
                    'confidence_modifier': 1.0,
                    'favorable_positions': [1, 2, 3, 4]
                }
            elif weather_code in [300, 301, 302, 303, 311, 313, 314, 320, 321, 322, 323, 324, 325]:  # 雨
                return {
                    'condition': 'poor',
                    'visibility_impact': 0.7,
                    'wave_impact': 1.3,
                    'confidence_modifier': 0.8,
                    'favorable_positions': [4, 5, 6]  # アウトコースが有利
                }
            elif weather_code in [400, 401, 402, 403, 409]:  # 雪
                return {
                    'condition': 'very_poor',
                    'visibility_impact': 0.5,
                    'wave_impact': 1.5,
                    'confidence_modifier': 0.6,
                    'favorable_positions': [5, 6]
                }
            else:
                return {
                    'condition': 'unknown',
                    'visibility_impact': 0.8,
                    'wave_impact': 1.0,
                    'confidence_modifier': 0.9,
                    'favorable_positions': [1, 2, 3, 4]
                }
        
        except:
            return self._get_default_weather()['racing_impact']
    
    def _estimate_wave_height(self, weather_code):
        """波の高さ推定"""
        weather_code = int(weather_code)
        if weather_code in [100, 101, 110, 111]:
            return 0.2
        elif weather_code in [200, 201, 210, 211]:
            return 0.3
        elif weather_code in [300, 301, 302, 303]:
            return 0.8
        else:
            return 0.5
    
    def _estimate_visibility(self, weather_code):
        """視界推定（km）"""
        weather_code = int(weather_code)
        if weather_code in [100, 101]:
            return 20.0
        elif weather_code in [110, 111, 200, 201]:
            return 15.0
        elif weather_code in [300, 301]:
            return 8.0
        else:
            return 10.0
    
    def _get_default_weather(self):
        """デフォルト天気データ"""
        return {
            'weather_code': '200',
            'condition': '曇り',
            'wind_direction': '不明',
            'wave_height': 0.3,
            'visibility': 10.0,
            'racing_impact': {
                'condition': 'good',
                'visibility_impact': 0.9,
                'wave_impact': 1.0,
                'confidence_modifier': 1.0,
                'favorable_positions': [1, 2, 3, 4]
            },
            'confidence_modifier': 1.0,
            'update_time': datetime.now().isoformat()
        }
    
    async def fetch_venue_conditions(self, venue_id, race_number):
        """会場状況データ取得"""
        try:
            cache_key = f"venue_{venue_id}_{race_number}"
            if cache_key in self.venue_conditions:
                cached_time, cached_data = self.venue_conditions[cache_key]
                if time.time() - cached_time < 180:  # 3分キャッシュ
                    return cached_data
            
            # 実際のAPI呼び出し（プレースホルダー）
            async with aiohttp.ClientSession() as session:
                url = f"{self.apis['venue_conditions']}{venue_id}/{race_number}.json"
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            conditions = self._parse_venue_conditions(data)
                        else:
                            conditions = self._get_default_venue_conditions()
                except:
                    conditions = self._get_default_venue_conditions()
            
            # キャッシュ保存
            self.venue_conditions[cache_key] = (time.time(), conditions)
            
            print(f"[INFO] 会場状況データ取得: 会場{venue_id}R{race_number}")
            return conditions
        
        except Exception as e:
            print(f"[ERROR] 会場状況取得エラー: {e}")
            return self._get_default_venue_conditions()
    
    def _parse_venue_conditions(self, data):
        """会場状況データ解析"""
        try:
            return {
                'water_temperature': data.get('water_temp', 18.0),
                'water_quality': data.get('water_quality', 'normal'),
                'current_strength': data.get('current', 'weak'),
                'maintenance_status': data.get('maintenance', 'good'),
                'crowd_level': data.get('crowd', 'normal'),
                'confidence_impact': self._calculate_venue_impact(data),
                'update_time': datetime.now().isoformat()
            }
        except:
            return self._get_default_venue_conditions()
    
    def _get_default_venue_conditions(self):
        """デフォルト会場状況"""
        return {
            'water_temperature': 18.0,
            'water_quality': 'normal',
            'current_strength': 'weak',
            'maintenance_status': 'good',
            'crowd_level': 'normal',
            'confidence_impact': 1.0,
            'update_time': datetime.now().isoformat()
        }
    
    def _calculate_venue_impact(self, venue_data):
        """会場状況の予想への影響計算"""
        try:
            impact = 1.0
            
            # 水温の影響
            water_temp = float(venue_data.get('water_temp', 18.0))
            if water_temp < 15.0:
                impact *= 0.95  # 低水温は予想精度を下げる
            elif water_temp > 25.0:
                impact *= 0.95
            else:
                impact *= 1.05
            
            # 潮流の影響
            current = venue_data.get('current', 'weak')
            if current == 'strong':
                impact *= 0.9
            elif current == 'very_strong':
                impact *= 0.85
            
            return min(1.2, max(0.8, impact))
        except:
            return 1.0
    
    async def fetch_odds_data(self, venue_id, race_number):
        """オッズデータ取得"""
        try:
            cache_key = f"odds_{venue_id}_{race_number}"
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.apis['odds_data']}{venue_id}/{race_number}.json"
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            odds_data = await response.json()
                            processed_odds = self._process_odds_data(odds_data)
                        else:
                            processed_odds = self._get_default_odds()
                except:
                    processed_odds = self._get_default_odds()
            
            # オッズ履歴に保存
            await self._save_odds_history(venue_id, race_number, processed_odds)
            
            print(f"[INFO] オッズデータ取得: 会場{venue_id}R{race_number}")
            return processed_odds
        
        except Exception as e:
            print(f"[ERROR] オッズデータ取得エラー: {e}")
            return self._get_default_odds()
    
    def _process_odds_data(self, odds_data):
        """オッズデータ処理"""
        try:
            processed = {
                'win_odds': odds_data.get('win', {}),
                'place_odds': odds_data.get('place', {}),
                'trifecta_odds': odds_data.get('trifecta', {}),
                'market_sentiment': self._analyze_market_sentiment(odds_data),
                'volume_data': odds_data.get('volume', {}),
                'update_time': datetime.now().isoformat()
            }
            
            return processed
        except:
            return self._get_default_odds()
    
    def _get_default_odds(self):
        """デフォルトオッズデータ"""
        return {
            'win_odds': {str(i): 3.0 + i * 0.5 for i in range(1, 7)},
            'place_odds': {str(i): 1.5 + i * 0.2 for i in range(1, 7)},
            'trifecta_odds': {'1-2-3': 50.0, '1-3-2': 45.0},
            'market_sentiment': {'trend': 'neutral', 'confidence': 0.5},
            'volume_data': {str(i): 1000 for i in range(1, 7)},
            'update_time': datetime.now().isoformat()
        }
    
    def _analyze_market_sentiment(self, odds_data):
        """市場心理分析"""
        try:
            win_odds = odds_data.get('win', {})
            if not win_odds:
                return {'trend': 'neutral', 'confidence': 0.5}
            
            # 人気度分析
            sorted_odds = sorted(win_odds.items(), key=lambda x: float(x[1]))
            favorite = sorted_odds[0]
            
            # 人気の偏り度計算
            odds_variance = np.var([float(odd) for odd in win_odds.values()])
            
            if odds_variance > 10.0:
                sentiment = 'volatile'
                confidence = 0.7
            elif float(favorite[1]) < 2.0:
                sentiment = 'strong_favorite'
                confidence = 0.8
            elif float(favorite[1]) > 5.0:
                sentiment = 'balanced'
                confidence = 0.6
            else:
                sentiment = 'neutral'
                confidence = 0.5
            
            return {
                'trend': sentiment,
                'confidence': confidence,
                'favorite_racer': int(favorite[0]),
                'favorite_odds': float(favorite[1]),
                'odds_variance': odds_variance
            }
        except:
            return {'trend': 'neutral', 'confidence': 0.5}
    
    async def _save_odds_history(self, venue_id, race_number, odds_data):
        """オッズ履歴保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            timestamp = datetime.now().isoformat()
            
            # 単勝オッズ保存
            for racer_str, odds_value in odds_data.get('win_odds', {}).items():
                cursor.execute('''
                    INSERT INTO odds_history 
                    (venue_id, race_number, date_str, bet_type, racer_number, odds_value, volume, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    venue_id, race_number, date_str, 'win', 
                    int(racer_str), float(odds_value), 
                    odds_data.get('volume_data', {}).get(racer_str, 0), timestamp
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] オッズ履歴保存エラー: {e}")
    
    async def get_integrated_data(self, venue_id, race_number):
        """統合リアルタイムデータ取得"""
        try:
            print(f"[INFO] リアルタイムデータ統合開始: 会場{venue_id}R{race_number}")
            
            # 並行データ取得
            weather_task = self.fetch_weather_data(venue_id)
            venue_task = self.fetch_venue_conditions(venue_id, race_number)
            odds_task = self.fetch_odds_data(venue_id, race_number)
            
            weather_data, venue_data, odds_data = await asyncio.gather(
                weather_task, venue_task, odds_task,
                return_exceptions=True
            )
            
            # エラー処理
            if isinstance(weather_data, Exception):
                weather_data = self._get_default_weather()
            if isinstance(venue_data, Exception):
                venue_data = self._get_default_venue_conditions()
            if isinstance(odds_data, Exception):
                odds_data = self._get_default_odds()
            
            # 統合データ構築
            integrated_data = {
                'venue_id': venue_id,
                'race_number': race_number,
                'weather': weather_data,
                'venue_conditions': venue_data,
                'odds': odds_data,
                'confidence_boost': self._calculate_confidence_boost(weather_data, venue_data, odds_data),
                'recommendations': self._generate_recommendations(weather_data, venue_data, odds_data),
                'update_time': datetime.now().isoformat()
            }
            
            # データベースに保存
            await self._save_integrated_data(integrated_data)
            
            print(f"[INFO] リアルタイムデータ統合完了: 信頼度補正={integrated_data['confidence_boost']:.2f}")
            return integrated_data
        
        except Exception as e:
            print(f"[ERROR] リアルタイムデータ統合エラー: {e}")
            return {
                'venue_id': venue_id,
                'race_number': race_number,
                'weather': self._get_default_weather(),
                'venue_conditions': self._get_default_venue_conditions(),
                'odds': self._get_default_odds(),
                'confidence_boost': 1.0,
                'recommendations': {},
                'error': str(e)
            }
    
    def _calculate_confidence_boost(self, weather_data, venue_data, odds_data):
        """信頼度補正値計算"""
        try:
            base_boost = 1.0
            
            # 天気による補正
            weather_boost = weather_data.get('confidence_modifier', 1.0)
            
            # 会場状況による補正
            venue_boost = venue_data.get('confidence_impact', 1.0)
            
            # 市場心理による補正
            market_confidence = odds_data.get('market_sentiment', {}).get('confidence', 0.5)
            market_boost = 0.8 + market_confidence * 0.4
            
            # 総合補正値
            total_boost = base_boost * weather_boost * venue_boost * market_boost
            
            return min(1.5, max(0.7, total_boost))
        except:
            return 1.0
    
    def _generate_recommendations(self, weather_data, venue_data, odds_data):
        """リアルタイム推奨事項生成"""
        try:
            recommendations = {
                'weather_advice': self._get_weather_advice(weather_data),
                'venue_advice': self._get_venue_advice(venue_data),
                'market_advice': self._get_market_advice(odds_data),
                'overall_strategy': self._get_overall_strategy(weather_data, venue_data, odds_data)
            }
            
            return recommendations
        except:
            return {}
    
    def _get_weather_advice(self, weather_data):
        """天気に基づく推奨事項"""
        condition = weather_data.get('racing_impact', {}).get('condition', 'good')
        
        if condition == 'excellent':
            return "好天候でインコースが有利。1-3号艇重視の予想を推奨。"
        elif condition == 'poor':
            return "悪天候でアウトコースが有利。4-6号艇の穴狙いを検討。"
        elif condition == 'very_poor':
            return "非常に悪い天候。予想精度が低下する可能性があり、慎重な投資を推奨。"
        else:
            return "通常の天候。バランスの取れた予想が有効。"
    
    def _get_venue_advice(self, venue_data):
        """会場状況に基づく推奨事項"""
        water_temp = venue_data.get('water_temperature', 18.0)
        current = venue_data.get('current_strength', 'weak')
        
        advice = []
        if water_temp < 15.0:
            advice.append("低水温のためモーターパワーが重要。")
        elif water_temp > 25.0:
            advice.append("高水温のためスタートタイミングが重要。")
        
        if current == 'strong':
            advice.append("強い潮流があり、経験豊富な選手が有利。")
        
        return " ".join(advice) if advice else "通常の会場状況。"
    
    def _get_market_advice(self, odds_data):
        """市場心理に基づく推奨事項"""
        sentiment = odds_data.get('market_sentiment', {})
        trend = sentiment.get('trend', 'neutral')
        
        if trend == 'strong_favorite':
            return "圧倒的人気が存在。複勝での安全策または穴狙いを検討。"
        elif trend == 'volatile':
            return "オッズが不安定。市場の判断が分かれており注意深い分析が必要。"
        elif trend == 'balanced':
            return "均衡の取れたレース。実力通りの結果が期待できる。"
        else:
            return "通常の市場状況。"
    
    def _get_overall_strategy(self, weather_data, venue_data, odds_data):
        """総合戦略提案"""
        confidence_boost = self._calculate_confidence_boost(weather_data, venue_data, odds_data)
        
        if confidence_boost > 1.2:
            return "高信頼度環境。積極的な投資戦略を推奨。"
        elif confidence_boost < 0.9:
            return "低信頼度環境。保守的な投資戦略を推奨。"
        else:
            return "標準的な環境。バランスの取れた投資戦略を推奨。"
    
    async def _save_integrated_data(self, data):
        """統合データ保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute('''
                INSERT INTO realtime_data 
                (venue_id, race_number, date_str, data_type, data_content, confidence_boost)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['venue_id'],
                data['race_number'],
                date_str,
                'integrated',
                json.dumps(data, ensure_ascii=False),
                data['confidence_boost']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] 統合データ保存エラー: {e}")


async def test_realtime_integration():
    """テスト実行"""
    print("=== リアルタイムデータ統合システム テスト開始 ===")
    
    integration = RealtimeDataIntegration()
    
    # テスト実行
    print("\n1. 統合データ取得テスト")
    integrated_data = await integration.get_integrated_data(12, 1)  # 住之江1R
    
    print(f"\n2. 結果表示")
    print(f"会場: {integrated_data['venue_id']}")
    print(f"レース: {integrated_data['race_number']}")
    print(f"信頼度補正: {integrated_data['confidence_boost']:.2f}")
    print(f"天気状況: {integrated_data['weather']['condition']}")
    print(f"推奨事項: {integrated_data['recommendations'].get('overall_strategy', 'なし')}")
    
    print("\n=== テスト完了 ===")
    return integrated_data


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_realtime_integration())