#!/usr/bin/env python3
"""
Core Routes - 基本ルート
メインページとテストページなどの基本機能
"""

import logging
from datetime import datetime
from flask import render_template

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
        return render_template('openapi_index.html',
                             races=[],
                             total_races=0,
                             loading=True,
                             current_time=datetime.now().strftime('%Y年%m月%d日 %H:%M'))
    
    def test(self):
        """テストページ"""
        return "System OK", 200