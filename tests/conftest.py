"""
pytest設定とフィクスチャー定義
"""
import os
import sys
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# テスト用データモデル
from data.simple_models import (
    TeikokuRaceInfo, TeikokuRacerInfo, TeikokuRacerStats, 
    TeikokuRaceDetail, TeikokuPrediction
)


@pytest.fixture
def temp_dir():
    """一時ディレクトリフィクスチャー"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_race_info():
    """サンプルレース情報フィクスチャー"""
    return TeikokuRaceInfo(
        race_id="2025_01_15_01_01",
        venue_id="1",
        venue_name="桐生",
        race_number=1,
        start_time=datetime(2025, 1, 15, 10, 30),
        date="2025-01-15",
        status="発売中"
    )


@pytest.fixture
def sample_racer_stats():
    """サンプル選手統計フィクスチャー"""
    return TeikokuRacerStats(
        total_races=1000,
        total_wins=155,
        win_rate=15.5,
        place_rate=32.1,
        show_rate=48.7,
        course_1_rate=55.2,
        course_2_rate=14.8,
        course_3_rate=12.3,
        course_4_rate=9.7,
        course_5_rate=6.1,
        course_6_rate=1.9,
        local_races=150,
        local_wins=27,
        local_win_rate=18.2,
        sg_win_rate=12.1,
        g1_win_rate=13.5,
        general_win_rate=15.8,
        current_series_races=5,
        current_series_wins=1,
        current_series_win_rate=20.0,
        average_st=0.165,
        flying_rate=2.1,
        late_rate=5.3,
        start_timing_score=0.75,
        motor_number=15,
        motor_win_rate=16.4,
        motor_place_rate=35.2,
        boat_number=22,
        boat_win_rate=14.9,
        boat_place_rate=33.8,
        recent_form_score=0.82,
        consistency_score=0.65,
        trend_score=0.73
    )


@pytest.fixture
def sample_racer_info(sample_racer_stats):
    """サンプル選手情報フィクスチャー"""
    return TeikokuRacerInfo(
        racer_id="test_racer_001",
        number=1,
        name="テスト選手1号",
        estimated_strength=75.5,
        lane_advantage=0.85,
        stats=sample_racer_stats
    )


@pytest.fixture
def sample_race_detail(sample_race_info):
    """サンプルレース詳細フィクスチャー"""
    racers = []
    for i in range(1, 7):
        stats = TeikokuRacerStats(
            total_races=1000 + i * 100,
            total_wins=int((1000 + i * 100) * (15.0 + i) / 100),
            win_rate=15.0 + i,
            place_rate=30.0 + i * 2,
            show_rate=45.0 + i * 3,
            course_1_rate=50.0 if i == 1 else 15.0 - i,
            course_2_rate=15.0 if i == 2 else 10.0,
            course_3_rate=12.0 if i == 3 else 8.0,
            course_4_rate=10.0 if i == 4 else 6.0,
            course_5_rate=8.0 if i == 5 else 4.0,
            course_6_rate=5.0 if i == 6 else 2.0,
            local_races=100 + i * 10,
            local_wins=int((100 + i * 10) * (15.0 + i) / 100),
            local_win_rate=15.0 + i,
            general_win_rate=15.0 + i,
            current_series_races=3 + i,
            current_series_wins=1 if i <= 3 else 0,
            current_series_win_rate=15.0 + i * 2,
            average_st=0.15 + i * 0.01,
            start_timing_score=0.5 + i * 0.05,
            motor_number=10 + i,
            motor_win_rate=15.0 + i,
            boat_number=20 + i,
            boat_win_rate=15.0 + i,
            recent_form_score=0.5 + i * 0.05
        )
        
        racer = TeikokuRacerInfo(
            racer_id=f"test_racer_{i:03d}",
            number=i,
            name=f"テスト選手{i}号",
            estimated_strength=70.0 + i * 2,
            lane_advantage=0.8 - i * 0.1,
            stats=stats
        )
        racers.append(racer)
    
    return TeikokuRaceDetail(race_info=sample_race_info, racers=racers)


@pytest.fixture
def sample_prediction():
    """サンプル予想結果フィクスチャー"""
    return TeikokuPrediction(
        race_id="2025_01_15_01_01",
        predictions={1: 0.35, 2: 0.22, 3: 0.18, 4: 0.12, 5: 0.08, 6: 0.05},
        recommended_win=1,
        recommended_place=[1, 2, 3],
        confidence=0.85,
        confidence_breakdown={
            'base_confidence': 0.75,
            'ensemble_bonus': 0.05,
            'real_data_bonus': 0.05,
            'final_confidence': 0.85
        }
    )


@pytest.fixture
def mock_weather_data():
    """モック気象データフィクスチャー"""
    return {
        'wind_speed': 5.2,
        'wind_direction': 'NE',
        'wind_gust': 7.1,
        'temperature': 25.5,
        'humidity': 65,
        'pressure': 1013.2,
        'weather': 'sunny'
    }


@pytest.fixture
def mock_database_connection():
    """モックデータベース接続フィクスチャー"""
    conn = Mock()
    conn.execute = Mock()
    conn.fetchone = Mock()
    conn.fetchall = Mock()
    conn.commit = Mock()
    conn.close = Mock()
    conn.__enter__ = Mock(return_value=conn)
    conn.__exit__ = Mock(return_value=False)
    return conn


@pytest.fixture
def mock_logging():
    """ログ出力のモックフィクスチャー"""
    with patch('logging.getLogger') as mock_logger:
        logger_instance = Mock()
        mock_logger.return_value = logger_instance
        yield logger_instance


@pytest.fixture(autouse=True)
def setup_test_environment(temp_dir, monkeypatch):
    """テスト環境の自動セットアップ"""
    # 環境変数設定
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setenv('TEST_DATA_DIR', temp_dir)
    
    # テスト用ディレクトリ作成
    cache_dir = Path(temp_dir) / 'cache'
    model_dir = Path(temp_dir) / 'models'
    cache_dir.mkdir(exist_ok=True)
    model_dir.mkdir(exist_ok=True)
    
    # テスト開始・終了のログ
    print(f"テスト環境セットアップ完了: {temp_dir}")
    yield
    print("テスト環境クリーンアップ完了")


# テスト用のカスタムマーカー
def pytest_configure(config):
    """pytestの設定"""
    config.addinivalue_line(
        "markers", "slow: マークされたテストは実行に時間がかかります"
    )
    config.addinivalue_line(
        "markers", "integration: 統合テストを示します"
    )
    config.addinivalue_line(
        "markers", "unit: 単体テストを示します"
    )
    config.addinivalue_line(
        "markers", "smoke: スモークテストを示します"
    )