
import os
import json
from datetime import datetime, timedelta
import sys

# scripts/modulesディレクトリへのパスを追加
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
if module_path not in sys.path:
    sys.path.append(module_path)

from api_fetcher import SimpleOpenAPIFetcher

def collect_past_data(start_date_str, end_date_str):
    """
    指定された期間の過去のレース結果と出走表データを収集し、マージしてファイルに保存する。
    """
    fetcher = SimpleOpenAPIFetcher()
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    all_merged_data = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Fetching data for {date_str}...")

        # 出走表データと結果データを取得
        daily_programs = fetcher.get_programs_for_date(date_str)
        daily_results = fetcher.get_results_for_date(date_str)

        if not daily_results or not daily_programs:
            current_date += timedelta(days=1)
            continue

        # 結果データを辞書に変換（高速アクセスのため）
        results_dict = {
            (r['race_stadium_number'], r['race_number']): r 
            for r in daily_results if r
        }

        # プログラムデータと結果データをマージ
        for program in daily_programs:
            if not program: continue
            race_key = (program.get('race_stadium_number'), program.get('race_number'))
            if race_key in results_dict:
                result_data = results_dict[race_key]
                # `boats` 情報をプログラムから、`payoffs` を結果からマージ
                merged_race = program.copy()
                merged_race['payoffs'] = result_data.get('payoffs')
                if merged_race['payoffs']: # payoffがnullでないものだけ追加
                    all_merged_data.append(merged_race)

        current_date += timedelta(days=1)

    # 'data'ディレクトリがなければ作成
    if not os.path.exists('data'):
        os.makedirs('data')

    # データをJSONファイルに保存
    file_path = 'data/training_data_merged.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_merged_data, f, ensure_ascii=False, indent=2)

    print(f"Data collection complete. {len(all_merged_data)} merged races saved to {file_path}")

if __name__ == "__main__":
    # 2024年1月のデータを収集
    collect_past_data('2024-01-01', '2024-01-31')
