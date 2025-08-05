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
        """選手の基本能力を評価"""
        ability_score = 0.0
        
        # 級班による基礎点
        ability_score += self.class_points.get(rider.class_rank.value, 50)
        
        # 勝率による補正
        if rider.stats:
            win_rate_bonus = rider.stats.win_rate * 100
            place_rate_bonus = rider.stats.place_rate * 50
            ability_score += win_rate_bonus + place_rate_bonus
        
        # 年齢による補正（ピーク年齢28-35歳）
        age_factor = 1.0
        if 28 <= rider.age <= 35:
            age_factor = 1.1
        elif rider.age > 40:
            age_factor = 0.9
        elif rider.age < 25:
            age_factor = 0.95
        
        return ability_score * age_factor

    def _evaluate_recent_form(self, rider: RiderInfo) -> float:
        """直近の調子を評価"""
        if not rider.stats or not rider.stats.recent_results:
            return 50.0  # デフォルト値
        
        recent_results = rider.stats.recent_results[-5:]  # 直近5走
        form_score = 0.0
        weight_decay = [1.0, 0.8, 0.6, 0.4, 0.2]  # 新しい結果ほど重視
        
        for i, result in enumerate(recent_results):
            weight = weight_decay[i] if i < len(weight_decay) else 0.1
            
            if result.finish_position == 1:
                form_score += 20 * weight
            elif result.finish_position <= 3:
                form_score += 10 * weight
            elif result.finish_position <= 6:
                form_score += 5 * weight
            else:
                form_score += 1 * weight
        
        return form_score

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
        """予想全体の信頼度を計算"""
        if not scores:
            return 0.0
        
        # 上位3名のスコア差を見る
        sorted_scores = sorted(scores.values(), key=lambda x: x.total_score, reverse=True)
        
        if len(sorted_scores) < 3:
            return 0.5
        
        # 1位と2位の差
        score_diff_1_2 = sorted_scores[0].total_score - sorted_scores[1].total_score
        # 2位と3位の差
        score_diff_2_3 = sorted_scores[1].total_score - sorted_scores[2].total_score
        
        # スコア差が大きいほど信頼度が高い
        confidence = min(1.0, (score_diff_1_2 + score_diff_2_3) / 50)
        return max(0.3, confidence)

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