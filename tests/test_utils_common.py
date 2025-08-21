"""
utils.common モジュールの単体テスト
"""
import pytest
import tempfile
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from utils.common import (
    ensure_directory,
    safe_file_operation,
    calculate_md5_hash,
    serialize_object,
    deserialize_object,
    safe_get_config_value,
    format_datetime,
    parse_datetime,
    safe_division,
    normalize_percentage,
    validate_race_id,
    validate_racer_number,
    clamp_value,
    SafeJsonEncoder,
    safe_json_dumps,
    safe_json_loads,
    create_database_connection,
    safe_database_operation,
    measure_execution_time,
    retry_on_failure,
    batch_process,
    VENUE_NAMES,
    GRADE_NAMES
)


class TestDirectoryOperations:
    """ディレクトリ操作テスト"""
    
    @pytest.mark.unit
    def test_ensure_directory(self, temp_dir):
        """ディレクトリ作成テスト"""
        test_path = Path(temp_dir) / "test" / "nested" / "directory"
        
        # ディレクトリが存在しない場合
        assert not test_path.exists()
        ensure_directory(test_path)
        assert test_path.exists()
        assert test_path.is_dir()
        
        # 既存ディレクトリの場合（エラーが発生しない）
        ensure_directory(test_path)
        assert test_path.exists()


class TestFileOperations:
    """ファイル操作テスト"""
    
    @pytest.mark.unit
    def test_safe_file_operation_success(self, temp_dir):
        """安全なファイル操作（成功）テスト"""
        test_file = Path(temp_dir) / "test.txt"
        
        def write_operation():
            with open(test_file, 'w') as f:
                f.write("test content")
            return "success"
        
        success, result, error = safe_file_operation(write_operation)
        
        assert success is True
        assert result == "success"
        assert error is None
        assert test_file.exists()
    
    @pytest.mark.unit
    def test_safe_file_operation_failure(self):
        """安全なファイル操作（失敗）テスト"""
        def failing_operation():
            raise ValueError("Test error")
        
        success, result, error = safe_file_operation(failing_operation)
        
        assert success is False
        assert result is None
        assert "Test error" in error


class TestHashAndSerialization:
    """ハッシュ・シリアル化テスト"""
    
    @pytest.mark.unit
    def test_calculate_md5_hash_string(self):
        """文字列のMD5ハッシュテスト"""
        test_string = "test string"
        hash_result = calculate_md5_hash(test_string)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32
        # 同じ入力には同じハッシュ
        assert calculate_md5_hash(test_string) == hash_result
    
    @pytest.mark.unit
    def test_calculate_md5_hash_bytes(self):
        """バイト列のMD5ハッシュテスト"""
        test_bytes = b"test bytes"
        hash_result = calculate_md5_hash(test_bytes)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32
    
    @pytest.mark.unit
    def test_serialize_deserialize_object(self):
        """オブジェクトのシリアル化・デシリアル化テスト"""
        test_obj = {"key": "value", "number": 42, "list": [1, 2, 3]}
        
        # シリアル化
        serialized = serialize_object(test_obj)
        assert isinstance(serialized, bytes)
        
        # デシリアル化
        deserialized = deserialize_object(serialized)
        assert deserialized == test_obj


class TestConfigHandling:
    """設定値処理テスト"""
    
    @pytest.mark.unit
    def test_safe_get_config_value_exists(self):
        """設定値が存在する場合のテスト"""
        config = {"key1": "value1", "key2": 42}
        
        assert safe_get_config_value(config, "key1") == "value1"
        assert safe_get_config_value(config, "key2") == 42
    
    @pytest.mark.unit
    def test_safe_get_config_value_not_exists(self):
        """設定値が存在しない場合のテスト"""
        config = {"key1": "value1"}
        
        assert safe_get_config_value(config, "key2") is None
        assert safe_get_config_value(config, "key2", "default") == "default"
    
    @pytest.mark.unit
    def test_safe_get_config_value_type_check(self):
        """型チェック付き設定値取得テスト"""
        config = {"string_key": "value", "int_key": 42}
        
        # 正しい型
        assert safe_get_config_value(config, "string_key", expected_type=str) == "value"
        assert safe_get_config_value(config, "int_key", expected_type=int) == 42
        
        # 間違った型
        with patch('logging.warning') as mock_log:
            result = safe_get_config_value(config, "string_key", "default", expected_type=int)
            assert result == "default"
            mock_log.assert_called_once()


class TestDateTimeHandling:
    """日時処理テスト"""
    
    @pytest.mark.unit
    def test_format_datetime_valid(self):
        """有効なdatetimeのフォーマットテスト"""
        dt = datetime(2025, 1, 15, 10, 30, 45)
        
        # デフォルトフォーマット
        assert format_datetime(dt) == "2025-01-15 10:30:45"
        
        # カスタムフォーマット
        assert format_datetime(dt, "%Y/%m/%d") == "2025/01/15"
    
    @pytest.mark.unit
    def test_format_datetime_none(self):
        """None値のフォーマットテスト"""
        assert format_datetime(None) == "未設定"
    
    @pytest.mark.unit
    def test_parse_datetime_valid(self):
        """有効な日時文字列のパーステスト"""
        date_str = "2025-01-15 10:30:45"
        result = parse_datetime(date_str)
        
        assert result == datetime(2025, 1, 15, 10, 30, 45)
    
    @pytest.mark.unit
    def test_parse_datetime_invalid(self):
        """無効な日時文字列のパーステスト"""
        assert parse_datetime("invalid date") is None
        assert parse_datetime("") is None


class TestMathOperations:
    """数学的操作テスト"""
    
    @pytest.mark.unit
    def test_safe_division_normal(self):
        """通常の割り算テスト"""
        assert safe_division(10, 2) == 5.0
        assert safe_division(7, 3) == pytest.approx(2.333, rel=1e-3)
    
    @pytest.mark.unit
    def test_safe_division_by_zero(self):
        """ゼロ除算テスト"""
        assert safe_division(10, 0) == 0.0
        assert safe_division(0, 0) == 0.0
    
    @pytest.mark.unit
    def test_normalize_percentage(self):
        """パーセンテージ正規化テスト"""
        assert normalize_percentage(50, 100) == 0.5
        assert normalize_percentage(150, 100) == 1.0  # 上限クランプ
        assert normalize_percentage(-10, 100) == 0.0  # 下限クランプ
    
    @pytest.mark.unit
    def test_clamp_value(self):
        """値クランプテスト"""
        assert clamp_value(5, 0, 10) == 5
        assert clamp_value(-1, 0, 10) == 0
        assert clamp_value(15, 0, 10) == 10


class TestValidation:
    """検証機能テスト"""
    
    @pytest.mark.unit
    def test_validate_race_id_valid(self):
        """有効なレースID検証テスト"""
        assert validate_race_id("2025_01_15_01_01") is True
        assert validate_race_id("2024_12_31_24_20") is True
    
    @pytest.mark.unit
    def test_validate_race_id_invalid(self):
        """無効なレースID検証テスト"""
        assert validate_race_id("") is False
        assert validate_race_id("invalid_format") is False
        assert validate_race_id("2025_13_01_01_01") is False  # 無効な月
        assert validate_race_id("2025_01_32_01_01") is False  # 無効な日
        assert validate_race_id("2025_01_01_25_01") is False  # 無効な会場
        assert validate_race_id("2025_01_01_01_21") is False  # 無効なレース番号
    
    @pytest.mark.unit
    def test_validate_racer_number(self):
        """選手番号検証テスト"""
        # 有効な番号
        for i in range(1, 7):
            assert validate_racer_number(i) is True
        
        # 無効な番号
        assert validate_racer_number(0) is False
        assert validate_racer_number(7) is False
        assert validate_racer_number("1") is False


class TestJsonHandling:
    """JSON処理テスト"""
    
    @pytest.mark.unit
    def test_safe_json_encoder_datetime(self):
        """datetime含むJSONエンコードテスト"""
        encoder = SafeJsonEncoder()
        dt = datetime(2025, 1, 15, 10, 30)
        
        result = encoder.default(dt)
        assert result == "2025-01-15T10:30:00"
    
    @pytest.mark.unit
    def test_safe_json_dumps(self):
        """安全なJSON文字列化テスト"""
        data = {
            "datetime": datetime(2025, 1, 15),
            "string": "テスト",
            "number": 42
        }
        
        result = safe_json_dumps(data)
        assert isinstance(result, str)
        assert "2025-01-15T00:00:00" in result
        assert "テスト" in result
    
    @pytest.mark.unit
    def test_safe_json_loads_valid(self):
        """有効なJSON解析テスト"""
        json_str = '{"key": "value", "number": 42}'
        result = safe_json_loads(json_str)
        
        assert result == {"key": "value", "number": 42}
    
    @pytest.mark.unit
    def test_safe_json_loads_invalid(self):
        """無効なJSON解析テスト"""
        assert safe_json_loads("invalid json") is None
        assert safe_json_loads("invalid json", {"default": True}) == {"default": True}


class TestDatabaseOperations:
    """データベース操作テスト"""
    
    @pytest.mark.unit
    def test_create_database_connection(self, temp_dir):
        """データベース接続作成テスト"""
        db_path = os.path.join(temp_dir, "test.db")
        
        conn = create_database_connection(db_path)
        assert conn is not None
        
        # 設定確認
        cursor = conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0] == "wal"
        
        conn.close()
    
    @pytest.mark.unit
    def test_safe_database_operation_success(self, temp_dir):
        """安全なデータベース操作（成功）テスト"""
        db_path = os.path.join(temp_dir, "test.db")
        
        def create_table(conn):
            conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'test')")
            return "success"
        
        success, result, error = safe_database_operation(db_path, create_table)
        
        assert success is True
        assert result == "success"
        assert error is None
        
        # テーブルが作成されていることを確認
        def check_table(conn):
            cursor = conn.execute("SELECT * FROM test")
            return cursor.fetchall()
        
        success, result, error = safe_database_operation(db_path, check_table)
        assert len(result) == 1
    
    @pytest.mark.unit
    def test_safe_database_operation_failure(self, temp_dir):
        """安全なデータベース操作（失敗）テスト"""
        db_path = os.path.join(temp_dir, "test.db")
        
        def failing_operation(conn):
            conn.execute("INVALID SQL QUERY")
        
        success, result, error = safe_database_operation(db_path, failing_operation)
        
        assert success is False
        assert result is None
        assert error is not None


class TestDecorators:
    """デコレータテスト"""
    
    @pytest.mark.unit
    def test_measure_execution_time(self):
        """実行時間測定デコレータテスト"""
        @measure_execution_time
        def test_function():
            return "test result"
        
        with patch('logging.info') as mock_log:
            result = test_function()
            
        assert result == "test result"
        mock_log.assert_called()
        
        # ログメッセージに実行時間が含まれていることを確認
        log_call = mock_log.call_args[0][0]
        assert "test_function実行時間" in log_call
    
    @pytest.mark.unit
    def test_retry_on_failure_success(self):
        """リトライデコレータ（成功）テスト"""
        @retry_on_failure(max_retries=3, delay=0.01)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    @pytest.mark.unit
    def test_retry_on_failure_eventual_success(self):
        """リトライデコレータ（最終的に成功）テスト"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.01)
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        with patch('logging.warning'):
            result = eventually_successful_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.unit
    def test_retry_on_failure_max_retries(self):
        """リトライデコレータ（最大リトライ到達）テスト"""
        @retry_on_failure(max_retries=2, delay=0.01)
        def always_failing_function():
            raise ValueError("Always fails")
        
        with patch('logging.warning'), patch('logging.error'):
            with pytest.raises(ValueError, match="Always fails"):
                always_failing_function()


class TestBatchProcessing:
    """バッチ処理テスト"""
    
    @pytest.mark.unit
    def test_batch_process_success(self):
        """バッチ処理（成功）テスト"""
        items = list(range(10))
        
        def processor(batch):
            return [x * 2 for x in batch]
        
        result = batch_process(items, batch_size=3, processor=processor)
        expected = [x * 2 for x in items]
        
        assert result == expected
    
    @pytest.mark.unit
    def test_batch_process_with_errors(self):
        """バッチ処理（エラー含む）テスト"""
        items = list(range(10))
        
        def processor(batch):
            if 5 in batch:
                raise ValueError("Error in batch")
            return [x * 2 for x in batch]
        
        with patch('logging.error'):
            result = batch_process(items, batch_size=3, processor=processor)
        
        # エラーが発生したバッチ以外は処理される
        assert len(result) < len(items) * 2


class TestConstants:
    """定数テスト"""
    
    @pytest.mark.unit
    def test_venue_names(self):
        """会場名定数テスト"""
        assert VENUE_NAMES[1] == "桐生"
        assert VENUE_NAMES[24] == "大村"
        assert len(VENUE_NAMES) == 24
    
    @pytest.mark.unit
    def test_grade_names(self):
        """グレード名定数テスト"""
        assert GRADE_NAMES['SG'] == "スペシャルグレード"
        assert GRADE_NAMES['G1'] == "グレード1"
        assert GRADE_NAMES['一般'] == "一般戦"