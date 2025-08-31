#!/usr/bin/env python3
"""
Investment Routes - 統合版
投資関連ルートを統合したクリーンなアーキテクチャ
"""

from .investment.handler import InvestmentHandler

class InvestmentRoutes:
    """投資ルートハンドラー - 統合版"""
    
    def __init__(self, app, fetcher, accuracy_tracker_class):
        # 統合ハンドラーに委譲
        self.handler = InvestmentHandler(app, fetcher, accuracy_tracker_class)