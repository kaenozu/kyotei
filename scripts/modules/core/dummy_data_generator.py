#!/usr/bin/env python3
"""
データ生成・フォーマット関数
API用のダミーデータ生成とデータフォーマット機能
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def format_race_data_for_api(races_data: List[Dict]) -> List[Dict]:
    """API用にレースデータをフォーマット"""
    try:
        if not races_data:
            return []
        
        formatted_races = []
        for race in races_data:
            formatted_race = {
                'venue_id': race.get('venue_id', 0),
                'venue_name': race.get('venue_name', '不明'),
                'race_number': race.get('race_number', 0),
                'race_title': race.get('race_title', ''),
                'start_time': race.get('start_time', ''),
                'status': race.get('status', 'unknown'),
                'boats': race.get('boats', []),
                'predictions': race.get('predictions', {}),
                'results': race.get('results', {}),
                'confidence': race.get('confidence', 0.0),
                'formatted_time': _format_display_time(race.get('start_time'))
            }
            formatted_races.append(formatted_race)
        
        logger.debug(f"API用データフォーマット完了: {len(formatted_races)}件")
        return formatted_races
        
    except Exception as e:
        logger.error(f"データフォーマットエラー: {e}")
        return []

def _format_display_time(time_str: Optional[str]) -> str:
    """表示用時間フォーマット"""
    if not time_str:
        return "時間未定"
    
    try:
        # HH:MM形式の場合はそのまま返す
        if ':' in time_str and len(time_str) <= 5:
            return time_str
            
        # ISO形式などの場合は時分のみ抽出
        if 'T' in time_str:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime('%H:%M')
            
        return time_str
        
    except Exception as e:
        logger.debug(f"時間フォーマット失敗: {time_str} -> {e}")
        return str(time_str)

def generate_dummy_race_data(venue_id: int = 1, race_count: int = 12) -> List[Dict]:
    """ダミーレースデータを生成（テスト用）"""
    
    venue_names = {
        1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川", 6: "浜名湖",
        7: "蒲郡", 8: "常滑", 9: "津", 10: "三国", 11: "びわこ", 12: "住之江"
    }
    
    dummy_races = []
    base_hour = 9
    
    for race_num in range(1, race_count + 1):
        race_time = f"{base_hour + (race_num * 25) // 60:02d}:{(base_hour * 60 + race_num * 25) % 60:02d}"
        
        dummy_race = {
            'venue_id': venue_id,
            'venue_name': venue_names.get(venue_id, f"会場{venue_id}"),
            'race_number': race_num,
            'race_title': f"第{race_num}レース",
            'start_time': race_time,
            'status': 'scheduled',
            'boats': [
                {'boat_number': i, 'player_name': f'選手{i}'} 
                for i in range(1, 7)
            ],
            'predictions': {
                'win': 1,
                'place': [1, 2, 3],
                'trifecta': [1, 2, 3]
            },
            'confidence': round(0.3 + (race_num % 5) * 0.1, 2)
        }
        dummy_races.append(dummy_race)
    
    logger.info(f"ダミーデータ生成完了: {len(dummy_races)}件")
    return dummy_races

def format_prediction_result(prediction: Dict, actual_result: Dict = None) -> Dict:
    """予想結果をフォーマット"""
    formatted = {
        'prediction': {
            'win': prediction.get('win'),
            'place': prediction.get('place', []),
            'trifecta': prediction.get('trifecta', [])
        },
        'confidence': prediction.get('confidence', 0.0),
        'timestamp': prediction.get('timestamp', datetime.now().isoformat())
    }
    
    if actual_result:
        formatted['result'] = {
            'win': actual_result.get('win'),
            'place': actual_result.get('place', []),
            'trifecta': actual_result.get('trifecta', [])
        }
        formatted['hit'] = _calculate_hit_status(prediction, actual_result)
    
    return formatted

def _calculate_hit_status(prediction: Dict, result: Dict) -> Dict:
    """的中状況を計算"""
    hit_status = {
        'win': False,
        'place': False,
        'trifecta': False
    }
    
    try:
        pred_win = prediction.get('win')
        result_win = result.get('win')
        result_place = result.get('place', [])
        
        if pred_win and result_win:
            # 単勝的中判定
            hit_status['win'] = pred_win == result_win
            
            # 複勝的中判定（1-3位内）
            hit_status['place'] = pred_win in result_place
        
        # 三連単的中判定
        pred_trifecta = prediction.get('trifecta', [])
        result_trifecta = result.get('trifecta', [])
        
        if len(pred_trifecta) >= 3 and len(result_trifecta) >= 3:
            hit_status['trifecta'] = pred_trifecta[:3] == result_trifecta[:3]
            
    except Exception as e:
        logger.error(f"的中判定エラー: {e}")
    
    return hit_status

if __name__ == '__main__':
    # テスト実行
    print("データ生成テスト:")
    
    # ダミーデータ生成テスト
    dummy_data = generate_dummy_race_data(venue_id=1, race_count=3)
    print(f"ダミーデータ: {len(dummy_data)}件")
    
    # フォーマットテスト
    formatted_data = format_race_data_for_api(dummy_data)
    print(f"フォーマットデータ: {len(formatted_data)}件")
    
    if formatted_data:
        print(f"サンプル: {formatted_data[0]}")