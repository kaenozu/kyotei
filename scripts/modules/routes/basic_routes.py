#!/usr/bin/env python3
"""
基本ルート管理
メインページとAPI基本機能を提供
"""

import logging
from flask import jsonify, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.dummy_data_generator import format_race_data_for_api

logger = logging.getLogger(__name__)

class BasicRoutes:
    """基本ルートハンドラー"""
    
    def __init__(self, app, fetcher):
        self.app = app
        self.fetcher = fetcher
        self._register_routes()
    
    def _register_routes(self):
        """基本ルートを登録"""
        # self.app.add_url_rule('/test-basic', 'test_route', self.test_route)
        self.app.add_url_rule('/api/races/basic', 'basic_routes_api_races', self.api_races)
        self.app.add_url_rule('/api/races/clear-cache', 'clear_cache', self.clear_cache)
        self.app.add_url_rule('/api/debug/db-test', 'debug_db_test', self.debug_db_test)
    
    
    def test_route(self):
        """テストルート"""
        return "Test route working"
    
    def api_races(self):
        """レース一覧API"""
        try:
            # 日付パラメータ取得
            date_param = request.args.get('date')
            logger.info(f"API呼び出し: date_param={date_param}")
            
            if date_param:
                # 過去の日付が指定された場合、直接データベースから取得
                logger.info(f"過去の日付が指定されました: {date_param}")
                
                try:
                    import sqlite3
                    import os
                    # プロジェクトルートのデータベースパス
                    current_dir = os.path.dirname(os.path.abspath(__file__))  # routes/
                    modules_dir = os.path.dirname(current_dir)                # modules/
                    scripts_dir = os.path.dirname(modules_dir)                # scripts/
                    project_root = os.path.dirname(scripts_dir)              # kyotei/
                    db_path = os.path.join(project_root, 'cache', 'comprehensive_kyotei.db')
                    
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT venue_id, race_number, race_title, start_time
                        FROM race_info 
                        WHERE race_date = ?
                        ORDER BY venue_id, race_number
                    """, (date_param,))
                    
                    rows = cursor.fetchall()
                    conn.close()
                    
                    logger.info(f"過去レース取得: {len(rows)}件")
                    
                    if rows:
                        venue_names = {
                            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
                            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
                            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
                            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
                        }
                        
                        # 直接formatted_racesを作成
                        formatted_races = []
                        from datetime import datetime
                        now = datetime.now()
                        today_str = now.strftime('%Y-%m-%d')
                        
                        for row in rows:
                            # レース時刻から終了判定
                            is_finished = False
                            start_time_display = row[3] or '不明'
                            
                            if date_param != today_str:
                                # 今日以外は終了済み
                                is_finished = True
                            elif row[3] and row[3] != '不明':
                                # 今日のレースで時刻が分かる場合は現在時刻と比較
                                try:
                                    race_time = datetime.strptime(f"{date_param} {row[3]}", '%Y-%m-%d %H:%M:%S')
                                    is_finished = now > race_time
                                except:
                                    # 時刻パースに失敗した場合は未完了とする
                                    is_finished = False
                            
                            race = {
                                'race_id': f"{row[0]}_{row[1]}",
                                'venue_name': venue_names.get(row[0], f'会場{row[0]}'),
                                'race_number': row[1],
                                'race_title': row[2] or '',
                                'start_time': start_time_display,
                                'is_finished': is_finished,
                                'prediction': None
                            }
                            formatted_races.append(race)
                        
                        return jsonify({
                            'success': True, 
                            'races': formatted_races,
                            'count': len(formatted_races)
                        })
                    else:
                        logger.warning(f"指定日付のレースが見つかりません: {date_param}")
                        return jsonify({
                            'success': True, 
                            'races': [],
                            'count': 0
                        })
                        
                except Exception as e:
                    logger.error(f"過去レース取得エラー: {e}")
                    return jsonify({
                        'success': False,
                        'error': str(e),
                        'races': []
                    }), 500
                    
            else:
                # APIフェッチャーから今日のレースを取得
                logger.info("今日のレースを取得")
                raw_races = self.fetcher.get_today_races()
            
            # programs配列を抽出してracesとして返す
            raw_races_list = []
            if raw_races and 'programs' in raw_races:
                raw_races_list = raw_races['programs']
            elif isinstance(raw_races, list):
                raw_races_list = raw_races
            else:
                # 直接データベースから取得した場合の処理を追加
                if date_param and not raw_races:
                    logger.warning(f"過去レース取得失敗、代替処理を実行: {date_param}")
                    raw_races_list = []
            
            # JavaScript用にフォーマット
            formatted_races = format_race_data_for_api(raw_races_list)
            
            logger.debug(f"API races returning {len(formatted_races)} formatted races")
            
            return jsonify({
                'success': True, 
                'races': formatted_races,
                'count': len(formatted_races)
            })
            
        except Exception as e:
            logger.error(f"レース一覧API エラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'races': []
            }), 500
    
    def _get_races_by_date(self, date_str):
        """指定日付のレースを取得"""
        try:
            logger.info(f"過去レース取得開始: {date_str}")
            from scripts.modules.core.real_api_tracker import RealAPITracker
            tracker = RealAPITracker()
            
            # データベースから指定日付のレースを取得
            saved_races = tracker.get_all_races_by_date(date_str)
            logger.info(f"データベースから取得したレース数: {len(saved_races)}")
            
            if not saved_races:
                return None
            
            # BoatraceOpenAPI形式に変換
            programs = []
            for race in saved_races:
                program = {
                    'venue_id': race.get('venue_id'),
                    'race_number': race.get('race_number'),
                    'race_title': race.get('race_title', ''),
                    'start_time': race.get('start_time'),
                    'venue_name': race.get('venue_name', ''),
                    'race_closed_at': race.get('start_time')  # 発走時刻を締切時刻として使用
                }
                programs.append(program)
            
            return {'programs': programs}
            
        except Exception as e:
            logger.error(f"過去レース取得エラー: {e}")
            return None
    
    def debug_db_test(self):
        """データベース接続デバッグ用"""
        try:
            import sqlite3
            import os
            from flask import request
            
            date_param = request.args.get('date', '2025-08-30')
            
            # パス解決
            current_dir = os.path.dirname(os.path.abspath(__file__))
            modules_dir = os.path.dirname(current_dir)
            scripts_dir = os.path.dirname(modules_dir)
            project_root = os.path.dirname(scripts_dir)
            db_path = os.path.join(project_root, 'cache', 'accuracy_tracker.db')
            
            result = {
                'current_dir': current_dir,
                'modules_dir': modules_dir,
                'scripts_dir': scripts_dir,
                'project_root': project_root,
                'db_path': db_path,
                'db_exists': os.path.exists(db_path),
                'date_param': date_param
            }
            
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # テーブル存在確認
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='race_details'")
                table_exists = cursor.fetchone() is not None
                result['table_exists'] = table_exists
                
                if table_exists:
                    # レコード数確認
                    cursor.execute("SELECT COUNT(*) FROM race_details WHERE race_date = ?", (date_param,))
                    count = cursor.fetchone()[0]
                    result['record_count'] = count
                    
                    # サンプルデータ取得
                    cursor.execute("SELECT venue_id, race_number, race_title FROM race_details WHERE race_date = ? LIMIT 3", (date_param,))
                    samples = cursor.fetchall()
                    result['samples'] = samples
                
                conn.close()
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def clear_cache(self):
        """キャッシュクリアAPI"""
        try:
            # キャッシュクリア処理（実装は将来の課題）
            logger.info("キャッシュクリア要求を受信")
            
            return jsonify({
                'success': True,
                'message': 'キャッシュクリア完了'
            })
            
        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500