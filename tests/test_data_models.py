"""
data.simple_models モジュールの単体テスト
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

from data.simple_models import (
    TeikokuRaceInfo,
    TeikokuRacerStats,
    TeikokuRacerInfo,
    TeikokuRaceDetail,
    TeikokuPrediction
)


class TestTeikokuRaceInfo:
    """レース情報モデルテスト"""
    
    @pytest.mark.unit
    def test_init_valid(self):
        """有効な初期化テスト"""
        race_info = TeikokuRaceInfo(
            race_id="2025_01_15_01_01",
            venue_id="1",
            venue_name="桐生",
            race_number=1,
            start_time=datetime(2025, 1, 15, 10, 30),
            date="2025-01-15",
            status="発売中"
        )
        
        assert race_info.race_id == "2025_01_15_01_01"
        assert race_info.venue_id == "1"
        assert race_info.venue_name == "桐生"
        assert race_info.race_number == 1
        assert race_info.start_time == datetime(2025, 1, 15, 10, 30)
        assert race_info.date == "2025-01-15"
        assert race_info.status == "発売中"
    
    @pytest.mark.unit
    def test_init_minimal(self):
        """最小限の初期化テスト"""
        race_info = TeikokuRaceInfo(
            race_id="2025_01_15_01_01",
            venue_id="1",
            venue_name="桐生",
            race_number=1,
            date="2025-01-15",
            status="発売中"
        )
        
        assert race_info.race_id == "2025_01_15_01_01"
        assert race_info.start_time is None
    
    @pytest.mark.unit
    def test_str_representation(self):
        """文字列表現テスト"""
        race_info = TeikokuRaceInfo(
            race_id="2025_01_15_01_01",
            venue_id="1",
            venue_name="桐生",
            race_number=1,
            start_time=datetime(2025, 1, 15, 10, 30),
            date="2025-01-15",
            status="発売中"
        )
        
        str_repr = str(race_info)
        assert "race_number=1" in str_repr
        assert "2025_01_15_01_01" in str_repr


class TestTeikokuRacerStats:
    """選手統計モデルテスト"""
    
    @pytest.mark.unit
    def test_init_all_fields(self, sample_racer_stats):
        """全フィールド初期化テスト"""
        stats = sample_racer_stats
        
        assert stats.total_races == 1000
        assert stats.win_rate == 15.5
        assert stats.place_rate == 32.1
        assert stats.show_rate == 48.7
        assert stats.course_1_rate == 55.2
        # current_course_rate属性は存在しない（削除）
        assert stats.average_st == 0.165
        assert stats.recent_form_score == 0.82
    
    @pytest.mark.unit
    def test_init_minimal(self):
        """最小限の初期化テスト"""
        stats = TeikokuRacerStats(
            total_races=100,
            win_rate=15.0,
            place_rate=30.0,
            show_rate=45.0
        )
        
        assert stats.total_races == 100
        assert stats.win_rate == 15.0
        # デフォルト値の確認
        assert stats.course_1_rate == 0.0
        assert stats.average_st == 0.0  # デフォルト値は0.0
    
    @pytest.mark.unit
    def test_rate_validation(self):
        """勝率等の妥当性テスト"""
        stats = TeikokuRacerStats(
            total_races=1000,
            win_rate=15.5,
            place_rate=32.1,
            show_rate=48.7
        )
        
        # 勝率 <= 連対率 <= 複勝率 の関係
        assert stats.win_rate <= stats.place_rate
        assert stats.place_rate <= stats.show_rate
        
        # パーセンテージ値の範囲
        assert 0 <= stats.win_rate <= 100
        assert 0 <= stats.place_rate <= 100
        assert 0 <= stats.show_rate <= 100


class TestTeikokuRacerInfo:
    """選手情報モデルテスト"""
    
    @pytest.mark.unit
    def test_init_with_stats(self, sample_racer_info):
        """統計付き初期化テスト"""
        racer = sample_racer_info
        
        assert racer.number == 1
        assert racer.name == "テスト選手1号"
        assert racer.estimated_strength == 75.5
        assert racer.lane_advantage == 0.85
        assert racer.stats is not None
        assert racer.stats.total_races == 1000
    
    @pytest.mark.unit
    def test_init_without_stats(self):
        """統計なし初期化テスト"""
        racer = TeikokuRacerInfo(
            racer_id="test_no_stats",
            number=1,
            name="テスト選手",
            estimated_strength=70.0,
            lane_advantage=0.8
        )
        
        assert racer.number == 1
        assert racer.name == "テスト選手"
        assert racer.stats is None
    
    @pytest.mark.unit
    def test_number_validation(self):
        """選手番号検証テスト"""
        # 有効な番号
        for i in range(1, 7):
            racer = TeikokuRacerInfo(
                racer_id=f"test_racer_{i}",
                number=i,
                name=f"選手{i}",
                estimated_strength=70.0,
                lane_advantage=0.8
            )
            assert racer.number == i
    
    @pytest.mark.unit
    def test_str_representation(self):
        """文字列表現テスト"""
        racer = TeikokuRacerInfo(
            racer_id="test_str_repr",
            number=1,
            name="テスト選手",
            estimated_strength=75.5,
            lane_advantage=0.85
        )
        
        str_repr = str(racer)
        assert "number=1" in str_repr
        assert "racer_id='test_str_repr'" in str_repr


class TestTeikokuRaceDetail:
    """レース詳細モデルテスト"""
    
    @pytest.mark.unit
    def test_init_valid(self, sample_race_detail):
        """有効な初期化テスト"""
        race_detail = sample_race_detail
        
        assert race_detail.race_info is not None
        assert race_detail.racers is not None
        assert len(race_detail.racers) == 6
        
        # 選手番号が1-6の連番
        racer_numbers = [racer.number for racer in race_detail.racers]
        assert racer_numbers == [1, 2, 3, 4, 5, 6]
    
    @pytest.mark.unit
    def test_racer_count_validation(self, sample_race_info):
        """選手数検証テスト"""
        # 正常な6人
        racers = []
        for i in range(1, 7):
            racer = TeikokuRacerInfo(
                racer_id=f"test_validation_{i}",
                number=i,
                name=f"選手{i}",
                estimated_strength=70.0,
                lane_advantage=0.8
            )
            racers.append(racer)
        
        race_detail = TeikokuRaceDetail(race_info=sample_race_info, racers=racers)
        assert len(race_detail.racers) == 6
    
    @pytest.mark.unit
    def test_str_representation(self, sample_race_detail):
        """文字列表現テスト"""
        str_repr = str(sample_race_detail)
        
        assert "race_info" in str_repr
        assert "racers" in str_repr
    
    @pytest.mark.unit
    def test_get_racer_by_number(self, sample_race_detail):
        """番号による選手取得テスト"""
        racer_1 = None
        racer_5 = None
        
        for racer in sample_race_detail.racers:
            if racer.number == 1:
                racer_1 = racer
            elif racer.number == 5:
                racer_5 = racer
        
        assert racer_1 is not None
        assert racer_1.number == 1
        assert racer_5 is not None
        assert racer_5.number == 5


class TestTeikokuPrediction:
    """予想結果モデルテスト"""
    
    @pytest.mark.unit
    def test_init_valid(self, sample_prediction):
        """有効な初期化テスト"""
        prediction = sample_prediction
        
        assert prediction.race_id == "2025_01_15_01_01"
        assert prediction.predictions == {1: 0.35, 2: 0.22, 3: 0.18, 4: 0.12, 5: 0.08, 6: 0.05}
        assert prediction.recommended_win == 1
        assert prediction.recommended_place == [1, 2, 3]
        assert prediction.confidence == 0.85
        assert prediction.confidence_breakdown is not None
    
    @pytest.mark.unit
    def test_predictions_sum(self, sample_prediction):
        """予想確率の合計テスト"""
        prediction = sample_prediction
        total_probability = sum(prediction.predictions.values())
        
        # 確率の合計は1.0に近い値であるべき
        assert abs(total_probability - 1.0) < 0.01
    
    @pytest.mark.unit
    def test_predictions_order(self, sample_prediction):
        """予想順序の整合性テスト"""
        prediction = sample_prediction
        
        # 推奨本命が最高確率であることを確認
        max_prob_racer = max(prediction.predictions.items(), key=lambda x: x[1])[0]
        assert max_prob_racer == prediction.recommended_win
        
        # 推奨連複が上位3位に含まれることを確認
        sorted_predictions = sorted(prediction.predictions.items(), key=lambda x: x[1], reverse=True)
        top_3_racers = [racer for racer, _ in sorted_predictions[:3]]
        
        for racer in prediction.recommended_place:
            assert racer in top_3_racers
    
    @pytest.mark.unit
    def test_confidence_range(self, sample_prediction):
        """信頼度範囲テスト"""
        prediction = sample_prediction
        
        # 信頼度は0.0-1.0の範囲
        assert 0.0 <= prediction.confidence <= 1.0
        
        # 信頼度内訳も同様
        if prediction.confidence_breakdown:
            for key, value in prediction.confidence_breakdown.items():
                if isinstance(value, (int, float)) and key.endswith('confidence'):
                    assert 0.0 <= value <= 1.0
    
    @pytest.mark.unit
    def test_str_representation(self, sample_prediction):
        """文字列表現テスト"""
        str_repr = str(sample_prediction)
        
        assert "2025_01_15_01_01" in str_repr
        assert "recommended_win=1" in str_repr  # 推奨本命
        assert "0.85" in str_repr or "85%" in str_repr  # 信頼度
    
    @pytest.mark.unit
    def test_init_minimal(self):
        """最小限の初期化テスト"""
        prediction = TeikokuPrediction(
            race_id="2025_01_15_01_01",
            predictions={1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1},
            recommended_win=1,
            recommended_place=[1, 2, 3],
            confidence=0.75
        )
        
        assert prediction.race_id == "2025_01_15_01_01"
        assert prediction.confidence == 0.75  # 設定値
        assert prediction.confidence_breakdown is None
    
    @pytest.mark.unit
    def test_to_dict(self, sample_prediction):
        """辞書変換テスト"""
        prediction = sample_prediction
        
        # オブジェクトに__dict__属性があることを確認
        assert hasattr(prediction, '__dict__')
        
        # 主要な属性が辞書に含まれることを確認
        obj_dict = prediction.__dict__
        assert 'race_id' in obj_dict
        assert 'predictions' in obj_dict
        assert 'recommended_win' in obj_dict
        assert 'confidence' in obj_dict


class TestModelIntegration:
    """モデル統合テスト"""
    
    @pytest.mark.unit
    def test_complete_race_workflow(self):
        """完全なレースワークフローテスト"""
        # 1. レース情報作成
        race_info = TeikokuRaceInfo(
            race_id="2025_01_15_01_01",
            venue_id="1",
            venue_name="桐生",
            race_number=1,
            start_time=datetime(2025, 1, 15, 10, 30),
            date="2025-01-15",
            status="発売中"
        )
        
        # 2. 選手情報作成
        racers = []
        for i in range(1, 7):
            stats = TeikokuRacerStats(
                total_races=1000,
                win_rate=15.0 + i,
                place_rate=30.0 + i,
                show_rate=45.0 + i
            )
            
            racer = TeikokuRacerInfo(
                racer_id=f"test_comprehensive_{i}",
                number=i,
                name=f"選手{i}",
                estimated_strength=70.0 + i,
                lane_advantage=0.8 - i * 0.1,
                stats=stats
            )
            racers.append(racer)
        
        # 3. レース詳細作成
        race_detail = TeikokuRaceDetail(race_info=race_info, racers=racers)
        
        # 4. 予想結果作成
        predictions = {}
        for i in range(1, 7):
            predictions[i] = (7 - i) / 21.0  # 1号艇が最高確率
        
        prediction = TeikokuPrediction(
            race_id=race_info.race_id,
            predictions=predictions,
            recommended_win=1,
            recommended_place=[1, 2, 3],
            confidence=0.85
        )
        
        # 5. 整合性確認
        assert race_detail.race_info.race_id == prediction.race_id
        assert len(race_detail.racers) == len(prediction.predictions)
        
        # 各選手の予想確率が存在することを確認
        for racer in race_detail.racers:
            assert racer.number in prediction.predictions
    
    @pytest.mark.unit
    def test_model_equality(self):
        """モデル等価性テスト"""
        # 同じデータでオブジェクト作成
        race_info1 = TeikokuRaceInfo(
            race_id="2025_01_15_01_01",
            venue_id="1",
            venue_name="桐生",
            race_number=1,
            date="2025-01-15",
            status="発売中"
        )
        
        race_info2 = TeikokuRaceInfo(
            race_id="2025_01_15_01_01",
            venue_id="1",
            venue_name="桐生",
            race_number=1,
            date="2025-01-15",
            status="発売中"
        )
        
        # 属性が同じであることを確認
        assert race_info1.race_id == race_info2.race_id
        assert race_info1.venue_id == race_info2.venue_id
        assert race_info1.venue_name == race_info2.venue_name
        assert race_info1.race_number == race_info2.race_number
        assert race_info1.status == race_info2.status