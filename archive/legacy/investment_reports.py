#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投資レポート生成モジュール - Phase 3: 実用化機能
競艇投資の詳細レポート・PDF出力・データエクスポート
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import csv
import io
from dataclasses import dataclass, asdict
import base64
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # GUIなし環境対応
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from investment_analytics import InvestmentAnalytics, PerformanceMetrics, VenueAnalysis


@dataclass
class ReportConfig:
    """レポート設定"""
    period_days: int = 30
    include_charts: bool = True
    include_venue_analysis: bool = True
    include_recommendations: bool = True
    export_format: str = 'pdf'  # pdf, excel, csv, json
    chart_style: str = 'professional'  # professional, minimal, colorful


class InvestmentReportGenerator:
    """投資レポート生成エンジン"""
    
    def __init__(self, db_path: str = "cache/investment_records.db"):
        self.db_path = db_path
        self.analytics = InvestmentAnalytics(db_path)
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
        
        # 日本語フォント設定
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Yu Gothic', 'Hiragino Sans', 'Noto Sans CJK JP']
        sns.set_style("whitegrid")
    
    def generate_comprehensive_report(self, config: ReportConfig = None) -> Dict[str, str]:
        """包括的投資レポート生成"""
        if config is None:
            config = ReportConfig()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_name = f"investment_report_{timestamp}"
        
        # データ収集
        performance_metrics = self.analytics.calculate_performance_metrics(config.period_days)
        venue_analysis = self.analytics.analyze_venue_performance(config.period_days)
        time_series = self.analytics.generate_time_series_analysis(config.period_days)
        recommendations = self.analytics.get_optimization_recommendations()
        
        # 基本統計
        basic_stats = self._get_basic_statistics(config.period_days)
        
        generated_files = {}
        
        # PDF レポート生成
        if config.export_format in ['pdf', 'all']:
            pdf_path = self._generate_pdf_report(
                report_name, performance_metrics, venue_analysis, 
                time_series, recommendations, basic_stats, config
            )
            generated_files['pdf'] = pdf_path
        
        # Excel レポート生成
        if config.export_format in ['excel', 'all']:
            excel_path = self._generate_excel_report(
                report_name, performance_metrics, venue_analysis, 
                time_series, recommendations, basic_stats
            )
            generated_files['excel'] = excel_path
        
        # CSV データエクスポート
        if config.export_format in ['csv', 'all']:
            csv_path = self._export_csv_data(report_name, config.period_days)
            generated_files['csv'] = csv_path
        
        # JSON データエクスポート
        if config.export_format in ['json', 'all']:
            json_path = self._export_json_data(
                report_name, performance_metrics, venue_analysis, 
                time_series, recommendations, basic_stats
            )
            generated_files['json'] = json_path
        
        return generated_files
    
    def _get_basic_statistics(self, days: int) -> Dict:
        """基本統計データ取得"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                COUNT(*) as total_bets,
                SUM(stake_amount) as total_stake,
                SUM(CASE WHEN payout IS NOT NULL THEN payout ELSE 0 END) as total_payout,
                SUM(CASE WHEN profit_loss IS NOT NULL THEN profit_loss ELSE 0 END) as total_profit,
                COUNT(CASE WHEN status = '的中' THEN 1 END) as wins,
                AVG(confidence) as avg_confidence,
                AVG(odds) as avg_odds,
                MIN(timestamp) as first_bet_date,
                MAX(timestamp) as last_bet_date
            FROM bet_records 
            WHERE timestamp >= date('now', '-{} days')
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        stats = df.iloc[0].to_dict()
        
        # 追加計算
        if stats['total_bets'] > 0:
            stats['win_rate'] = (stats['wins'] / stats['total_bets']) * 100
            stats['roi'] = (stats['total_profit'] / stats['total_stake']) * 100 if stats['total_stake'] > 0 else 0
            stats['avg_stake'] = stats['total_stake'] / stats['total_bets']
        else:
            stats['win_rate'] = 0
            stats['roi'] = 0
            stats['avg_stake'] = 0
        
        return stats
    
    def _generate_pdf_report(self, report_name: str, performance_metrics: PerformanceMetrics,
                            venue_analysis: List[VenueAnalysis], time_series, recommendations, 
                            basic_stats: Dict, config: ReportConfig) -> str:
        """PDF レポート生成"""
        pdf_path = self.output_dir / f"{report_name}.pdf"
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # タイトル
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        title = Paragraph(f"競艇投資レポート - {config.period_days}日間分析", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # サマリー
        summary_data = [
            ['項目', '値'],
            ['分析期間', f'{config.period_days}日間'],
            ['総投資額', f"¥{basic_stats['total_stake']:,.0f}"],
            ['総払戻額', f"¥{basic_stats['total_payout']:,.0f}"],
            ['総損益', f"¥{basic_stats['total_profit']:+,.0f}"],
            ['総賭け回数', f"{basic_stats['total_bets']:,}回"],
            ['的中率', f"{basic_stats['win_rate']:.1f}%"],
            ['ROI', f"{basic_stats['roi']:+.1f}%"],
            ['シャープレシオ', f"{performance_metrics.sharpe_ratio:.2f}"],
            ['最大ドローダウン', f"{performance_metrics.max_drawdown:.1%}"]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # パフォーマンス指標
        if performance_metrics:
            perf_title = Paragraph("リスク・パフォーマンス指標", styles['Heading2'])
            story.append(perf_title)
            
            perf_data = [
                ['指標', '値', '評価'],
                ['シャープレシオ', f"{performance_metrics.sharpe_ratio:.2f}", 
                 '優秀' if performance_metrics.sharpe_ratio > 1 else '良好' if performance_metrics.sharpe_ratio > 0.5 else '要改善'],
                ['ソルティノレシオ', f"{performance_metrics.sortino_ratio:.2f}", 
                 '優秀' if performance_metrics.sortino_ratio > 1 else '標準'],
                ['年間ボラティリティ', f"{performance_metrics.volatility:.1%}", 
                 '低' if performance_metrics.volatility < 0.2 else '中' if performance_metrics.volatility < 0.4 else '高'],
                ['VaR (95%)', f"¥{performance_metrics.var_95:,.0f}", ''],
                ['連勝記録', f"{performance_metrics.win_streak}回", ''],
                ['連敗記録', f"{performance_metrics.loss_streak}回", '']
            ]
            
            perf_table = Table(perf_data)
            perf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(perf_table)
            story.append(Spacer(1, 20))
        
        # 会場別分析（上位10会場）
        if venue_analysis and config.include_venue_analysis:
            venue_title = Paragraph("会場別パフォーマンス（上位10会場）", styles['Heading2'])
            story.append(venue_title)
            
            venue_data = [['会場名', '賭け回数', '的中率', 'ROI', '損益']]
            for venue in venue_analysis[:10]:
                venue_data.append([
                    venue.venue_name,
                    f"{venue.total_bets}回",
                    f"{venue.win_rate:.1f}%",
                    f"{venue.roi:+.1f}%",
                    f"¥{venue.profit_loss:+,.0f}"
                ])
            
            venue_table = Table(venue_data)
            venue_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(venue_table)
            story.append(Spacer(1, 20))
        
        # 推奨事項
        if recommendations and config.include_recommendations:
            rec_title = Paragraph("戦略最適化推奨事項", styles['Heading2'])
            story.append(rec_title)
            
            # 総合評価
            overall = Paragraph(f"<b>総合評価:</b> {recommendations['overall_assessment']}", styles['Normal'])
            story.append(overall)
            story.append(Spacer(1, 10))
            
            # 各カテゴリの推奨事項
            for category, items in recommendations.items():
                if category != 'overall_assessment' and items:
                    cat_title = Paragraph(f"<b>{category}:</b>", styles['Normal'])
                    story.append(cat_title)
                    
                    for item in items:
                        item_text = Paragraph(f"• {item}", styles['Normal'])
                        story.append(item_text)
                    
                    story.append(Spacer(1, 10))
        
        # チャート生成・挿入
        if config.include_charts and time_series.daily_pnl:
            chart_path = self._generate_performance_chart(time_series, report_name)
            if chart_path.exists():
                chart_title = Paragraph("パフォーマンス推移", styles['Heading2'])
                story.append(chart_title)
                
                img = Image(str(chart_path), width=6*inch, height=4*inch)
                story.append(img)
        
        # PDF生成
        doc.build(story)
        
        return str(pdf_path)
    
    def _generate_excel_report(self, report_name: str, performance_metrics: PerformanceMetrics,
                              venue_analysis: List[VenueAnalysis], time_series, 
                              recommendations, basic_stats: Dict) -> str:
        """Excel レポート生成"""
        excel_path = self.output_dir / f"{report_name}.xlsx"
        
        with pd.ExcelWriter(str(excel_path), engine='openpyxl') as writer:
            # サマリーシート
            summary_df = pd.DataFrame([
                ['分析期間', f'{basic_stats.get("total_bets", 0)}日間'],
                ['総投資額', basic_stats.get('total_stake', 0)],
                ['総払戻額', basic_stats.get('total_payout', 0)],
                ['総損益', basic_stats.get('total_profit', 0)],
                ['的中率', basic_stats.get('win_rate', 0)],
                ['ROI', basic_stats.get('roi', 0)],
                ['シャープレシオ', performance_metrics.sharpe_ratio],
                ['最大ドローダウン', performance_metrics.max_drawdown],
                ['ボラティリティ', performance_metrics.volatility]
            ], columns=['項目', '値'])
            summary_df.to_excel(writer, sheet_name='サマリー', index=False)
            
            # 会場別分析シート
            if venue_analysis:
                venue_df = pd.DataFrame([asdict(v) for v in venue_analysis])
                venue_df.to_excel(writer, sheet_name='会場別分析', index=False)
            
            # 時系列データシート
            if time_series.daily_pnl:
                ts_df = pd.DataFrame({
                    '日付': time_series.dates,
                    '日次損益': time_series.daily_pnl,
                    '累積損益': time_series.cumulative_pnl,
                    'ローリングシャープ': time_series.rolling_sharpe
                })
                ts_df.to_excel(writer, sheet_name='時系列分析', index=False)
            
            # 生データシート
            conn = sqlite3.connect(self.db_path)
            raw_df = pd.read_sql_query('SELECT * FROM bet_records ORDER BY timestamp DESC', conn)
            conn.close()
            raw_df.to_excel(writer, sheet_name='生データ', index=False)
        
        return str(excel_path)
    
    def _export_csv_data(self, report_name: str, days: int) -> str:
        """CSV データエクスポート"""
        csv_path = self.output_dir / f"{report_name}_data.csv"
        
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT * FROM bet_records 
            WHERE timestamp >= date('now', '-{} days')
            ORDER BY timestamp DESC
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        df.to_csv(str(csv_path), index=False, encoding='utf-8-sig')
        return str(csv_path)
    
    def _export_json_data(self, report_name: str, performance_metrics: PerformanceMetrics,
                         venue_analysis: List[VenueAnalysis], time_series, 
                         recommendations, basic_stats: Dict) -> str:
        """JSON データエクスポート"""
        json_path = self.output_dir / f"{report_name}_analysis.json"
        
        data = {
            'generated_at': datetime.now().isoformat(),
            'basic_statistics': basic_stats,
            'performance_metrics': asdict(performance_metrics),
            'venue_analysis': [asdict(v) for v in venue_analysis],
            'time_series_analysis': {
                'daily_pnl': time_series.daily_pnl,
                'cumulative_pnl': time_series.cumulative_pnl,
                'rolling_sharpe': time_series.rolling_sharpe,
                'dates': time_series.dates,
                'trend_direction': time_series.trend_direction,
                'momentum': time_series.momentum
            },
            'recommendations': recommendations
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        return str(json_path)
    
    def _generate_performance_chart(self, time_series, report_name: str) -> Path:
        """パフォーマンスチャート生成"""
        chart_path = self.output_dir / f"{report_name}_chart.png"
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # 累積損益
        dates = pd.to_datetime(time_series.dates)
        ax1.plot(dates, time_series.cumulative_pnl, linewidth=2, color='blue')
        ax1.set_title('累積損益推移', fontsize=14, fontweight='bold')
        ax1.set_ylabel('損益 (円)')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # ローリングシャープレシオ
        ax2.plot(dates, time_series.rolling_sharpe, linewidth=2, color='green')
        ax2.set_title('ローリングシャープレシオ（7日間）', fontsize=14, fontweight='bold')
        ax2.set_ylabel('シャープレシオ')
        ax2.set_xlabel('日付')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='良好基準')
        ax2.legend()
        
        # フォーマット調整
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(str(chart_path), dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def get_available_reports(self) -> List[Dict]:
        """利用可能なレポート一覧"""
        reports = []
        
        for file_path in self.output_dir.glob("investment_report_*"):
            if file_path.suffix in ['.pdf', '.xlsx', '.csv', '.json']:
                stat = file_path.stat()
                reports.append({
                    'filename': file_path.name,
                    'path': str(file_path),
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'format': file_path.suffix[1:]
                })
        
        return sorted(reports, key=lambda x: x['created_at'], reverse=True)


if __name__ == "__main__":
    # テスト実行
    generator = InvestmentReportGenerator()
    
    # サンプルレポート生成
    config = ReportConfig(
        period_days=30,
        include_charts=True,
        include_venue_analysis=True,
        include_recommendations=True,
        export_format='all'
    )
    
    print("投資レポート生成テスト実行中...")
    files = generator.generate_comprehensive_report(config)
    
    for format_type, file_path in files.items():
        print(f"{format_type.upper()} レポート生成: {file_path}")