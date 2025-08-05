"""
競輪予想エンジン
"""
import logging
from typing import List, Dict, Tuple
from datetime import datetime

from data.models import (
    RaceDetail, RiderInfo, PredictionResult, PredictionScore,
    BetRecommendation, LineInfo, RacingStyle, RiderClass
)
from config.settings import PREDICTION_WEIGHTS, CLASS_POINTS


class KeirinPredictor:
    """競輪予想エンジン"""

    def __init__(self):
        self.weights = PREDICTION_WEIGHTS
        self.class_points = CLASS_POINTS
        self.logger = logging.getLogger(__name__)

    def predict_race(self, race_data: RaceDetail) -> PredictionResult:
        """レース予想を実行"""
        self.logger.info(f"予想開始: {race_data.race_info.race_id}")
        
        # 各選手のスコア計算
        scores = {}
        for rider in race_data.riders:
            score = self._calculate_total_score(rider, race_data)
            scores[rider.number] = score

        # ランキング作成
        rankings = sorted(scores.keys(), key=lambda x: scores[x].total_score, reverse=True)
        
        # 信頼度計算
        confidence = self._calculate_confidence(scores)
        
        # 買い目推奨生成
        betting_recommendations = self._generate_betting_recommendations(rankings, scores, race_data)
        
        result = PredictionResult(
            race_id=race_data.race_info.race_id,
            rankings=rankings,
            scores=scores,
            confidence=confidence,
            betting_recommendations=betting_recommendations
        )
        
        self.logger.info(f"予想完了: 1位予想 {rankings[0]}番")
        return result

    def _calculate_total_score(self, rider: RiderInfo, race_data: RaceDetail) -> PredictionScore:
        """選手の総合スコアを計算"""
        # 各評価項目のスコア計算
        ability_score = self._evaluate_rider_ability(rider)
        form_score = self._evaluate_recent_form(rider)
        track_score = self._evaluate_track_compatibility(rider, race_data.race_info.venue)
        line_score = self._evaluate_line_strategy(rider, race_data)
        external_score = self._evaluate_external_factors(rider, race_data)
        
        # 重み付き合計
        total_score = (
            ability_score * self.weights['rider_ability'] +
            form_score * self.weights['recent_form'] +
            track_score * self.weights['track_compatibility'] +
            line_score * self.weights['line_strategy'] +
            external_score * self.weights['external_factors']
        )
        
        # 信頼度計算
        confidence = self._calculate_rider_confidence(
            ability_score, form_score, track_score, line_score, external_score
        )
        
        return PredictionScore(
            rider_number=rider.number,
            total_score=total_score,
            ability_score=ability_score,
            form_score=form_score,
            track_score=track_score,
            line_score=line_score,
            external_score=external_score,
            confidence=confidence
        )

    def _evaluate_rider_ability(self, rider: RiderInfo) -> float:
        """選手の基本能力を評価（改善版）"""
        ability_score = 0.0
        
        # 級班による基礎点（強化）
        class_score = self.class_points.get(rider.class_rank.value, 50)
        ability_score += class_score
        
        # 勝率による補正（より詳細な分析）
        if rider.stats:
            # 勝率の非線形評価（上位選手はより高評価）
            win_rate_factor = 1 + (rider.stats.win_rate * 2) ** 1.5
            place_rate_factor = 1 + (rider.stats.place_rate * 1.5) ** 1.2
            show_rate_factor = 1 + (rider.stats.show_rate * 1.2) ** 1.1
            
            ability_score *= (win_rate_factor + place_rate_factor + show_rate_factor) / 3
            
            # 総レース数による信頼度調整
            experience_factor = min(1.2, 1 + (rider.stats.total_races / 500))
            ability_score *= experience_factor
        
        # 年齢による補正（より詳細なピーク分析）
        age_factor = self._calculate_age_performance_factor(rider.age)
        ability_score *= age_factor
        
        # 級班と成績の整合性チェック
        consistency_factor = self._evaluate_class_consistency(rider)
        ability_score *= consistency_factor
        
        return ability_score

    def _calculate_age_performance_factor(self, age: int) -> float:
        """年齢による能力係数を詳細計算"""
        if age < 20:
            return 0.8  # 経験不足
        elif 20 <= age < 25:
            return 0.9 + (age - 20) * 0.04  # 0.9-1.1の線形上昇
        elif 25 <= age <= 32:
            return 1.1  # ピーク期間
        elif 33 <= age <= 37:
            return 1.1 - (age - 32) * 0.02  # 1.1-1.0の緩やかな下降
        elif 38 <= age <= 42:
            return 1.0 - (age - 37) * 0.03  # 1.0-0.85の下降
        else:
            return max(0.7, 0.85 - (age - 42) * 0.02)  # 更なる下降、最低0.7

    def _evaluate_class_consistency(self, rider: RiderInfo) -> float:
        """級班と成績の整合性を評価"""
        if not rider.stats:
            return 1.0
        
        # 級班に期待される勝率
        expected_win_rates = {
            "S1": 0.25, "S2": 0.20, "A1": 0.15, "A2": 0.12, "A3": 0.08
        }
        
        expected_rate = expected_win_rates.get(rider.class_rank.value, 0.10)
        actual_rate = rider.stats.win_rate
        
        # 実際の勝率が期待より高い場合は上昇期、低い場合は下降期
        if actual_rate > expected_rate:
            return min(1.3, 1 + (actual_rate - expected_rate) * 2)
        else:
            return max(0.8, 1 - (expected_rate - actual_rate) * 1.5)

    def _evaluate_recent_form(self, rider: RiderInfo) -> float:
        """直近の調子を評価（改善版）"""
        if not rider.stats or not rider.stats.recent_results:
            return 50.0  # デフォルト値
        
        # 直近10走まで拡張
        recent_results = rider.stats.recent_results[-10:]
        if not recent_results:
            return 50.0
        
        # より詳細な重み付け（指数減衰）
        form_score = 0.0
        total_weight = 0.0
        trend_score = 0.0
        
        for i, result in enumerate(recent_results):
            # 指数減衰重み（最新の結果により大きな重み）
            weight = 0.9 ** i
            total_weight += weight
            
            # 順位による得点計算
            position_score = self._calculate_position_score(result.finish_position)
            form_score += position_score * weight
            
            # トレンド分析（直近3走の傾向）
            if i < 3:
                trend_score += position_score * (3 - i)  # 最新ほど重視
        
        # 平均化
        if total_weight > 0:
            form_score = form_score / total_weight
        
        # トレンド補正
        trend_factor = self._calculate_trend_factor(recent_results[:3])
        form_score *= trend_factor
        
        # 安定性評価
        stability_factor = self._calculate_stability_factor(recent_results)
        form_score *= stability_factor
        
        return form_score

    def _calculate_position_score(self, position: int) -> float:
        """順位による得点計算"""
        if position == 1:
            return 100
        elif position == 2:
            return 80
        elif position == 3:
            return 65
        elif position <= 5:
            return 40
        elif position <= 7:
            return 20
        else:
            return 5

    def _calculate_trend_factor(self, recent_results: list) -> float:
        """直近のトレンドを分析"""
        if len(recent_results) < 2:
            return 1.0
        
        # 順位の推移を分析
        positions = [result.finish_position for result in recent_results]
        trend = 0
        
        for i in range(1, len(positions)):
            if positions[i-1] > positions[i]:  # 順位向上
                trend += 1
            elif positions[i-1] < positions[i]:  # 順位悪化
                trend -= 1
        
        # トレンド係数
        if trend > 0:  # 上昇トレンド
            return 1.0 + (trend * 0.1)
        elif trend < 0:  # 下降トレンド
            return max(0.8, 1.0 + (trend * 0.1))
        else:  # 安定
            return 1.0

    def _calculate_stability_factor(self, results: list) -> float:
        """成績の安定性を評価"""
        if len(results) < 3:
            return 1.0
        
        positions = [result.finish_position for result in results]
        avg_position = sum(positions) / len(positions)
        variance = sum((pos - avg_position) ** 2 for pos in positions) / len(positions)
        
        # 分散が小さいほど安定している
        stability = 1.0 + (5.0 - variance) * 0.02
        return max(0.9, min(1.1, stability))

    def _evaluate_track_compatibility(self, rider: RiderInfo, venue: str) -> float:
        """バンクとの相性を評価"""
        if not rider.stats:
            return 50.0
        
        # 当場での成績
        venue_stats = rider.stats.venue_stats.get(venue, {})
        venue_win_rate = venue_stats.get('win_rate', rider.stats.win_rate)
        venue_place_rate = venue_stats.get('place_rate', rider.stats.place_rate)
        
        compatibility_score = venue_win_rate * 100 + venue_place_rate * 50
        
        # バンクの特徴による補正
        track_features = self._get_track_features(venue)
        
        # 選手の脚質とバンクの相性
        style_bonus = self._calculate_style_compatibility(rider.racing_style, track_features)
        compatibility_score += style_bonus
        
        return compatibility_score

    def _evaluate_line_strategy(self, rider: RiderInfo, race_data: RaceDetail) -> float:
        """ライン戦略による評価"""
        line = race_data.get_line_by_rider(rider.number)
        if not line:
            return 40.0  # 単騎の場合
        
        line_score = 0.0
        
        # ライン内での役割による評価
        if line.leader_number == rider.number:
            # ライン先頭
            line_score += 25
        elif rider.number in line.members[:2]:
            # 番手
            line_score += 20
        else:
            # 3番手以降
            line_score += 15
        
        # ライン全体の強さ
        line_score += line.strength * 30
        
        # ライン人数による補正
        line_size = len(line.members)
        if line_size == 3:
            line_score += 10  # 理想的なライン
        elif line_size == 2:
            line_score += 5
        elif line_size == 1:
            line_score -= 5   # 単騎は不利
        
        return line_score

    def _evaluate_external_factors(self, rider: RiderInfo, race_data: RaceDetail) -> float:
        """外部要因による評価"""
        external_score = 50.0  # ベーススコア
        
        # 天候による影響
        if race_data.weather == "雨" and hasattr(rider, 'wet_performance'):
            if rider.wet_performance > 0.7:
                external_score += 10
            elif rider.wet_performance < 0.3:
                external_score -= 10
        
        # 風による影響
        if race_data.wind_speed > 5.0:
            # 逃げ・先行タイプは向かい風に不利
            if rider.racing_style in [RacingStyle.SPRINTER, RacingStyle.LEADER]:
                external_score -= 5
        
        # オッズによる市場評価（人気薄は穴狙い）
        if race_data.odds and rider.number in race_data.odds.win_odds:
            odds = race_data.odds.win_odds[rider.number]
            if 3.0 <= odds <= 8.0:  # 中穴
                external_score += 5
            elif odds > 15.0:  # 大穴
                external_score += 3
        
        return external_score

    def _get_track_features(self, venue: str) -> Dict[str, bool]:
        """バンクの特徴を取得"""
        # 開催場ごとの特徴（実際の競輪場の特徴を反映）
        track_features_map = {
            "平塚": {"sprint_favorable": True, "wind_prone": True},
            "川崎": {"endurance_favorable": True, "tight_turns": True},
            "小田原": {"sprint_favorable": True, "short_straight": True},
            "静岡": {"balanced": True},
        }
        
        return track_features_map.get(venue, {"balanced": True})

    def _calculate_style_compatibility(self, style: RacingStyle, features: Dict[str, bool]) -> float:
        """脚質とバンクの相性を計算"""
        bonus = 0.0
        
        if style == RacingStyle.SPRINTER and features.get('sprint_favorable'):
            bonus += 15
        elif style == RacingStyle.LEADER and features.get('sprint_favorable'):
            bonus += 10
        elif style == RacingStyle.TRACKER and features.get('endurance_favorable'):
            bonus += 15
        elif style == RacingStyle.SWEEPER and features.get('endurance_favorable'):
            bonus += 12
        
        return bonus

    def _calculate_rider_confidence(self, *scores) -> float:
        """選手スコアの信頼度を計算"""
        # スコアのばらつきから信頼度を算出
        avg_score = sum(scores) / len(scores)
        variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
        
        # 分散が小さいほど信頼度が高い
        confidence = max(0.3, 1.0 - (variance / 1000))
        return min(1.0, confidence)

    def _calculate_confidence(self, scores: Dict[int, PredictionScore]) -> float:
        """予想全体の信頼度を計算（改善版）"""
        if not scores:
            return 0.0
        
        sorted_scores = sorted(scores.values(), key=lambda x: x.total_score, reverse=True)
        
        if len(sorted_scores) < 3:
            return 0.4
        
        # 複数の要素から信頼度を計算
        confidence_factors = []
        
        # 1. スコア分離度（上位選手と他の差）
        top_score = sorted_scores[0].total_score
        avg_score = sum(score.total_score for score in sorted_scores) / len(sorted_scores)
        separation_factor = min(1.0, (top_score - avg_score) / 30.0)
        confidence_factors.append(separation_factor)
        
        # 2. 上位陣の安定性（1-3位のスコア差）
        score_diff_1_2 = sorted_scores[0].total_score - sorted_scores[1].total_score
        score_diff_2_3 = sorted_scores[1].total_score - sorted_scores[2].total_score
        stability_factor = min(1.0, (score_diff_1_2 + score_diff_2_3) / 40.0)
        confidence_factors.append(stability_factor)
        
        # 3. 個別選手の信頼度平均
        individual_confidence = sum(score.confidence for score in sorted_scores[:3]) / 3
        confidence_factors.append(individual_confidence)
        
        # 4. データ充実度
        data_completeness = self._calculate_data_completeness(scores)
        confidence_factors.append(data_completeness)
        
        # 重み付き平均で最終信頼度を計算
        weights = [0.3, 0.25, 0.25, 0.2]  # 各要素の重み
        final_confidence = sum(factor * weight for factor, weight in zip(confidence_factors, weights))
        
        return max(0.4, min(0.95, final_confidence))

    def _calculate_data_completeness(self, scores: Dict[int, PredictionScore]) -> float:
        """データの充実度を評価"""
        completeness_score = 0.0
        total_riders = len(scores)
        
        for score in scores.values():
            # 各評価項目が適切に計算されているかチェック
            if score.ability_score > 0:
                completeness_score += 0.25
            if score.form_score > 0:
                completeness_score += 0.25
            if score.track_score > 0:
                completeness_score += 0.25
            if score.line_score > 0:
                completeness_score += 0.25
        
        return completeness_score / total_riders if total_riders > 0 else 0.0

    def _generate_betting_recommendations(
        self, rankings: List[int], scores: Dict[int, PredictionScore], race_data: RaceDetail
    ) -> List[BetRecommendation]:
        """買い目推奨を生成"""
        recommendations = []
        
        if len(rankings) < 3:
            return recommendations
        
        top_3 = rankings[:3]
        confidence = self._calculate_confidence(scores)
        
        # 3連単推奨（高配当狙い）
        if confidence > 0.7:
            trifecta_combination = f"{top_3[0]}-{top_3[1]}-{top_3[2]}"
            expected_odds = self._estimate_trifecta_odds(top_3, race_data)
            
            recommendations.append(BetRecommendation(
                bet_type="3連単",
                combination=trifecta_combination,
                expected_odds=expected_odds,
                confidence="A" if confidence > 0.8 else "B",
                expected_value=self._calculate_expected_value(expected_odds, confidence),
                investment_ratio=0.4
            ))
        
        # 3連複推奨（安定重視）
        trio_combination = f"{top_3[0]}-{top_3[1]}-{top_3[2]}"
        trio_odds = self._estimate_trio_odds(top_3, race_data)
        
        recommendations.append(BetRecommendation(
            bet_type="3連複",
            combination=trio_combination,
            expected_odds=trio_odds,
            confidence="B",
            expected_value=self._calculate_expected_value(trio_odds, confidence * 0.8),
            investment_ratio=0.6
        ))
        
        # 穴狙い推奨
        if len(rankings) >= 5 and confidence > 0.6:
            hole_pick = rankings[3:5]  # 4-5位の選手
            if len(hole_pick) >= 2:
                hole_combination = f"{top_3[0]}-{hole_pick[0]}-{hole_pick[1]}"
                hole_odds = self._estimate_trifecta_odds([top_3[0], hole_pick[0], hole_pick[1]], race_data)
                
                recommendations.append(BetRecommendation(
                    bet_type="3連単(穴)",
                    combination=hole_combination,
                    expected_odds=hole_odds,
                    confidence="C",
                    expected_value=self._calculate_expected_value(hole_odds, confidence * 0.5),
                    investment_ratio=0.2
                ))
        
        return recommendations

    def _estimate_trifecta_odds(self, combination: List[int], race_data: RaceDetail) -> float:
        """3連単オッズを推定"""
        if not race_data.odds or not race_data.odds.win_odds:
            return 15.0  # デフォルト値
        
        # 単勝オッズから3連単オッズを概算
        odds_product = 1.0
        for rider_num in combination:
            rider_odds = race_data.odds.win_odds.get(rider_num, 5.0)
            odds_product *= rider_odds
        
        # 3連単オッズは単勝オッズの積の約1/3程度
        estimated_odds = odds_product * 0.3
        return max(5.0, min(999.9, estimated_odds))

    def _estimate_trio_odds(self, combination: List[int], race_data: RaceDetail) -> float:
        """3連複オッズを推定"""
        trifecta_odds = self._estimate_trifecta_odds(combination, race_data)
        # 3連複は3連単の約1/6
        return max(2.0, trifecta_odds / 6.0)

    def _calculate_expected_value(self, odds: float, win_probability: float) -> float:
        """期待値を計算"""
        expected_return = odds * win_probability
        expected_value = (expected_return - 1.0) * 100  # パーセンテージ
        return round(expected_value, 1)