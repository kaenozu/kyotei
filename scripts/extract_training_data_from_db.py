
import sqlite3
import json
import pandas as pd

def extract_data():
    """
    accuracy_tracker.dbから訓練データを抽出し、JSONファイルとして保存する。
    """
    db_path = 'scripts/cache/accuracy_tracker.db'
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        
        # 予測データと結果データを読み込む
        # race_results には winning_boat があるので、これを正解ラベルとして利用する
        query = """
        SELECT 
            p.race_date, 
            p.venue_id, 
            p.race_number, 
            p.prediction_data, 
            r.winning_boat
        FROM predictions p
        JOIN race_results r 
        ON p.race_date = r.race_date AND p.venue_id = r.venue_id AND p.race_number = r.race_number
        WHERE r.winning_boat IS NOT NULL
        """
        df = pd.read_sql_query(query, conn)

        if df.empty:
            print("データベースから有効な訓練データが見つかりませんでした。")
            return

        # train_model.pyが期待する形式に変換
        training_data = []
        for _, row in df.iterrows():
            try:
                prediction_data = json.loads(row['prediction_data'])
                # racers情報がない、またはリストでない場合はスキップ
                if 'racers' not in prediction_data or not isinstance(prediction_data['racers'], list):
                    continue

                # train_model.pyの入力形式に合わせる
                race_record = {
                    'race_stadium_number': row['venue_id'],
                    'race_number': row['race_number'],
                    'race_date': row['race_date'],
                    'boats': [],
                    # 正解ラベルとして1着の艇番を格納
                    'winning_boat': row['winning_boat']
                }

                for racer in prediction_data['racers']:
                    # 必要なキーが揃っているか確認
                    required_keys = ['number', 'national_win_rate', 'local_win_rate', 'motor_rate', 'boat_rate']
                    if not all(key in racer for key in required_keys):
                        continue

                    race_record['boats'].append({
                        'boat_number': racer['number'],
                        # train_model.pyで使われるキー名に合わせる
                        'win_rate': racer['national_win_rate'],
                        'local_win_rate': racer['local_win_rate'],
                        'motor_2_rate': racer['motor_rate'],
                        'boat_2_rate': racer['boat_rate'],
                        'racer_rank': 'A1' # ダミー値。必要であればprediction_dataから取得
                    })
                
                # boat情報が一つでもあれば追加
                if race_record['boats']:
                    training_data.append(race_record)

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Skipping record due to data error: {e}")
                continue

        # データをJSONファイルに保存
        output_path = 'data/training_data_from_db.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)

        print(f"Data extraction complete. {len(training_data)} races saved to {output_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    extract_data()
