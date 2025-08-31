
import os
import json
from datetime import datetime, timedelta
import sys

# scripts/modulesディレクトリへのパスを追加
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
if module_path not in sys.path:
    sys.path.append(module_path)

from api_fetcher import SimpleOpenAPIFetcher

def collect_past_data(days_to_collect):
    """
    指定された日数分の過去のレース結果データを収集し、ファイルに保存する。
    """
    fetcher = SimpleOpenAPIFetcher()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_collect)

    all_results = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Fetching data for {date_str}...")
        daily_results = fetcher.get_results_for_date(date_str)
        if daily_results:
            all_results.extend(daily_results)
        current_date += timedelta(days=1)

    # 'data'ディレクトリがなければ作成
    if not os.path.exists('data'):
        os.makedirs('data')

    # データをJSONファイルに保存
    file_path = 'data/training_data.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"Data collection complete. {len(all_results)} races saved to {file_path}")

if __name__ == "__main__":
    # 過去365日分のデータを収集
    collect_past_data(365)
