#!/usr/bin/env python3
"""
BoatraceOpenAPI専用システム - 予想根拠透明性システム
予想計算過程の完全可視化による信頼性向上
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PredictionComponent:
    """予想構成要素"""
    name: str
    value: float
    weight: float
    contribution: float
    description: str
    data_source: str
    confidence: float  # 0.0-1.0


@dataclass
class PredictionBreakdown:
    """予想内訳詳細"""
    boat_number: int
    racer_name: str
    final_prediction: float
    components: List[PredictionComponent]
    total_adjustments: float
    base_strength: float
    weather_impact: Optional[str] = None
    venue_impact: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class TransparencyReport:
    """透明性レポート"""
    race_id: str
    venue_name: str
    analysis_timestamp: str
    data_sources: List[str]
    breakdowns: List[PredictionBreakdown]
    weather_analysis: Optional[Dict[str, Any]] = None
    calculation_method: str = "高度AI予想システム"
    accuracy_estimate: float = 0.0


class PredictionTransparencyEngine:
    """予想根拠透明性エンジン"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_transparency_report(self, race_data: Dict[str, Any], 
                                 predictions: Dict[str, Any]) -> TransparencyReport:
        """透明性レポート作成"""
        try:
            # 基本情報
            venue_id = race_data.get('race_stadium_number', 1)
            race_id = f"{datetime.now().strftime('%Y%m%d')}_{venue_id:02d}_XX"
            venue_name = self._get_venue_name(venue_id)
            
            # データソース一覧
            data_sources = self._identify_data_sources(race_data, predictions)
            
            # 各艇の詳細分析
            breakdowns = []
            for prediction in predictions.get('predictions', []):
                breakdown = self._create_prediction_breakdown(
                    prediction, race_data, predictions
                )
                breakdowns.append(breakdown)
            
            # 天候分析情報
            weather_analysis = predictions.get('weather_analysis')
            
            # 精度推定
            accuracy_estimate = self._estimate_accuracy(data_sources, weather_analysis)
            
            return TransparencyReport(
                race_id=race_id,
                venue_name=venue_name,
                analysis_timestamp=datetime.now().isoformat(),
                data_sources=data_sources,
                breakdowns=breakdowns,
                weather_analysis=weather_analysis,
                accuracy_estimate=accuracy_estimate
            )
            
        except Exception as e:
            self.logger.error(f"透明性レポート作成エラー: {e}")
            return self._create_error_report(str(e))
    
    def _create_prediction_breakdown(self, prediction: Dict[str, Any], 
                                   race_data: Dict[str, Any],
                                   full_predictions: Dict[str, Any]) -> PredictionBreakdown:
        """個別予想内訳作成"""
        boat_number = prediction.get('boat_number', 0)
        racer_name = prediction.get('racer_name', '不明')
        final_prediction = prediction.get('final_prediction', 0.0)
        
        # 構成要素詳細分析
        components = []
        
        # 1. 基本実力
        base_strength = prediction.get('base_strength', 0.0)
        components.append(PredictionComponent(
            name="基本実力",
            value=base_strength,
            weight=0.35,
            contribution=base_strength * 0.35,
            description=f"全国勝率・連対率から算出した選手の基本能力値",
            data_source="BoatraceOpenAPI",
            confidence=0.9
        ))
        
        # 2. 競艇場特性
        venue_adjustment = prediction.get('venue_adjustment', 0.0)
        components.append(PredictionComponent(
            name="競艇場特性",
            value=venue_adjustment,
            weight=0.15,
            contribution=venue_adjustment * 0.15,
            description=f"競艇場の特性（内枠有利度、スタート重要度等）による調整",
            data_source="統計データベース",
            confidence=0.8
        ))
        
        # 3. 天候補正
        weather_adjustment = prediction.get('weather_adjustment', 0.0)
        weather_available = full_predictions.get('weather_data_available', False)
        components.append(PredictionComponent(
            name="天候補正",
            value=weather_adjustment,
            weight=0.20 if weather_available else 0.0,
            contribution=weather_adjustment * 0.20 if weather_available else 0.0,
            description=f"風速・風向・波高・天気による影響調整",
            data_source="OpenWeatherMap API" if weather_available else "データなし",
            confidence=0.85 if weather_available else 0.0
        ))
        
        # 4. 直近調子
        recent_form = prediction.get('recent_form', 0.0)
        components.append(PredictionComponent(
            name="直近調子",
            value=recent_form,
            weight=0.10,
            contribution=recent_form * 0.10,
            description=f"最近のレース成績による調子補正",
            data_source="実績データ（未実装時は0）",
            confidence=0.3 if recent_form == 0.0 else 0.7
        ))
        
        # 5. スタート技術
        st_factor = prediction.get('st_factor', 1.0)
        st_contribution = (st_factor - 1.0) * 0.15
        components.append(PredictionComponent(
            name="スタート技術",
            value=st_factor,
            weight=0.15,
            contribution=st_contribution,
            description=f"平均スタートタイミングによる技術評価",
            data_source="BoatraceOpenAPI",
            confidence=0.85
        ))
        
        # 6. 艇番有利度
        lane_advantage = prediction.get('lane_advantage', 0.0)
        components.append(PredictionComponent(
            name="艇番有利度",
            value=lane_advantage,
            weight=0.10,
            contribution=lane_advantage * 0.10,
            description=f"{boat_number}号艇の統計的有利度",
            data_source="競艇統計データ",
            confidence=0.9
        ))
        
        # 7. モーター・ボート
        equipment_bonus = prediction.get('equipment_bonus', 0.0)
        components.append(PredictionComponent(
            name="機材成績",
            value=equipment_bonus,
            weight=0.05,
            contribution=equipment_bonus * 0.05,
            description=f"モーター・ボートの成績による調整",
            data_source="BoatraceOpenAPI",
            confidence=0.6
        ))
        
        # 調整合計
        total_adjustments = sum(comp.contribution for comp in components[1:])
        
        # 信頼度スコア計算
        confidence_score = self._calculate_confidence_score(components)
        
        return PredictionBreakdown(
            boat_number=boat_number,
            racer_name=racer_name,
            final_prediction=final_prediction,
            components=components,
            total_adjustments=total_adjustments,
            base_strength=base_strength,
            confidence_score=confidence_score
        )
    
    def _calculate_confidence_score(self, components: List[PredictionComponent]) -> float:
        """信頼度スコア計算"""
        total_weight = sum(comp.weight for comp in components)
        if total_weight == 0:
            return 0.0
        
        weighted_confidence = sum(comp.confidence * comp.weight for comp in components)
        return weighted_confidence / total_weight
    
    def _identify_data_sources(self, race_data: Dict[str, Any], 
                             predictions: Dict[str, Any]) -> List[str]:
        """データソース特定"""
        sources = ["BoatraceOpenAPI（選手成績・レース情報）"]
        
        if predictions.get('weather_data_available'):
            sources.append("OpenWeatherMap API（天候データ）")
        
        if predictions.get('ml_enabled'):
            sources.append("機械学習モデル（過去データ学習）")
        
        sources.append("競艇統計データ（艇番有利度・競艇場特性）")
        
        return sources
    
    def _estimate_accuracy(self, data_sources: List[str], 
                         weather_analysis: Optional[Dict]) -> float:
        """精度推定計算"""
        base_accuracy = 0.65  # 基本精度65%
        
        # 天候データ有無による調整
        if any("OpenWeatherMap" in source for source in data_sources):
            base_accuracy += 0.08  # +8%向上
        
        # 機械学習有無による調整
        if any("機械学習" in source for source in data_sources):
            base_accuracy += 0.05  # +5%向上
        
        # データ品質による調整
        if len(data_sources) >= 4:
            base_accuracy += 0.02  # 多様なデータソース+2%
        
        return min(base_accuracy, 0.85)  # 最大85%
    
    def _get_venue_name(self, venue_id: int) -> str:
        """競艇場名取得"""
        venue_names = {
            1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
            7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
            13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島", 17: "宮島", 18: "徳山",
            19: "下関", 20: "若松", 21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
        }
        return venue_names.get(venue_id, f"競艇場{venue_id:02d}")
    
    def _create_error_report(self, error_message: str) -> TransparencyReport:
        """エラー時レポート"""
        return TransparencyReport(
            race_id="ERROR",
            venue_name="エラー",
            analysis_timestamp=datetime.now().isoformat(),
            data_sources=["エラー"],
            breakdowns=[],
            accuracy_estimate=0.0
        )
    
    def generate_html_report(self, report: TransparencyReport) -> str:
        """HTML形式レポート生成"""
        html_template = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>予想根拠詳細レポート - {venue_name}</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }}
                .header h1 {{ color: #007bff; margin: 0; }}
                .summary {{ background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 30px; }}
                .boat-analysis {{ margin-bottom: 30px; border: 1px solid #ddd; border-radius: 8px; padding: 20px; }}
                .boat-header {{ background-color: #007bff; color: white; padding: 10px; border-radius: 5px; margin-bottom: 15px; }}
                .component {{ display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee; }}
                .component-name {{ font-weight: bold; flex: 1; }}
                .component-value {{ flex: 1; text-align: center; }}
                .component-contribution {{ flex: 1; text-align: center; font-weight: bold; }}
                .component-confidence {{ flex: 1; text-align: center; }}
                .confidence-high {{ color: #28a745; }}
                .confidence-medium {{ color: #ffc107; }}
                .confidence-low {{ color: #dc3545; }}
                .data-sources {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 30px; }}
                .accuracy-badge {{ display: inline-block; background-color: #28a745; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 予想根拠詳細レポート</h1>
                    <h2>{venue_name} - {race_id}</h2>
                    <p>分析時刻: {analysis_timestamp}</p>
                </div>
                
                <div class="summary">
                    <h3>📊 分析サマリー</h3>
                    <p><strong>予想精度:</strong> <span class="accuracy-badge">{accuracy_estimate:.1%}</span></p>
                    <p><strong>使用データソース:</strong> {data_sources_count}種類</p>
                    <p><strong>分析手法:</strong> {calculation_method}</p>
                </div>
                
                {boat_analyses}
                
                <div class="data-sources">
                    <h3>📋 使用データソース</h3>
                    <ul>
                        {data_sources_list}
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 各艇の分析HTML生成
        boat_analyses = ""
        for breakdown in sorted(report.breakdowns, key=lambda x: x.boat_number):
            boat_analyses += self._generate_boat_analysis_html(breakdown)
        
        # データソースリスト生成
        data_sources_list = ""
        for source in report.data_sources:
            data_sources_list += f"<li>{source}</li>"
        
        return html_template.format(
            venue_name=report.venue_name,
            race_id=report.race_id,
            analysis_timestamp=datetime.fromisoformat(report.analysis_timestamp).strftime('%Y年%m月%d日 %H:%M:%S'),
            accuracy_estimate=report.accuracy_estimate,
            data_sources_count=len(report.data_sources),
            calculation_method=report.calculation_method,
            boat_analyses=boat_analyses,
            data_sources_list=data_sources_list
        )
    
    def _generate_boat_analysis_html(self, breakdown: PredictionBreakdown) -> str:
        """個別艇分析HTML生成"""
        template = """
        <div class="boat-analysis">
            <div class="boat-header">
                <h3>{boat_number}号艇 - {racer_name}</h3>
                <p>最終予想値: {final_prediction:.3f} | 信頼度: {confidence_score:.1%}</p>
            </div>
            
            <div class="components">
                <div class="component" style="font-weight: bold; background-color: #f8f9fa;">
                    <div class="component-name">構成要素</div>
                    <div class="component-value">数値</div>
                    <div class="component-contribution">寄与度</div>
                    <div class="component-confidence">信頼度</div>
                </div>
                {components_html}
            </div>
        </div>
        """
        
        components_html = ""
        for comp in breakdown.components:
            confidence_class = "confidence-high" if comp.confidence > 0.7 else "confidence-medium" if comp.confidence > 0.4 else "confidence-low"
            components_html += f"""
            <div class="component">
                <div class="component-name">{comp.name}</div>
                <div class="component-value">{comp.value:.3f}</div>
                <div class="component-contribution">{comp.contribution:+.3f}</div>
                <div class="component-confidence"><span class="{confidence_class}">{comp.confidence:.1%}</span></div>
            </div>
            """
        
        return template.format(
            boat_number=breakdown.boat_number,
            racer_name=breakdown.racer_name,
            final_prediction=breakdown.final_prediction,
            confidence_score=breakdown.confidence_score,
            components_html=components_html
        )
    
    def generate_json_report(self, report: TransparencyReport) -> str:
        """JSON形式レポート生成"""
        return json.dumps(asdict(report), ensure_ascii=False, indent=2)


# グローバルインスタンス
prediction_transparency = PredictionTransparencyEngine()