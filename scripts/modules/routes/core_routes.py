#!/usr/bin/env python3
"""
Core Routes - 基本ルート
メインページとテストページなどの基本機能
"""

import logging
from datetime import datetime
from flask import render_template, request

logger = logging.getLogger(__name__)

class CoreRoutes:
    """基本ルートハンドラー"""
    
    def __init__(self, app, fetcher):
        self.app = app
        self.fetcher = fetcher
        self._register_routes()
    
    def _register_routes(self):
        """基本ルートを登録"""
        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/test', 'test', self.test)
    
    def index(self):
        """メインページ（軽量化版）"""
        # 日付パラメータ取得
        date_param = request.args.get('date')
        if date_param:
            try:
                selected_date = datetime.strptime(date_param, '%Y-%m-%d')
                current_time = selected_date.strftime('%Y年%m月%d日') + ' のレース'
            except ValueError:
                selected_date = datetime.now()
                current_time = selected_date.strftime('%Y年%m月%d日 %H:%M')
        else:
            selected_date = datetime.now()
            current_time = selected_date.strftime('%Y年%m月%d日 %H:%M')
        
        # 今日の日付をデフォルト値として設定
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        return render_template('openapi_index.html',
                             races=[],
                             total_races=0,
                             loading=True,
                             current_time=current_time,
                             selected_date=date_param,  # 今日の場合はNoneを渡す
                             today_date=today_date)
    
    def test(self):
        """テストページ"""
        return "System OK", 200