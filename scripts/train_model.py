import json
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

def train_model():
    """
    抽出された訓練データを使用してモデルを訓練し、保存します。
    """
    # --- 1. データの読み込み ---
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'training_data_from_db.json')
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            all_races = json.load(f)
    except FileNotFoundError:
        print(f"訓練データファイルが見つかりません: {data_path}")
        return

    if not all_races:
        print("訓練データが空です。")
        return

    # --- 2. データフレームの作成 ---
    records = []
    for race in all_races:
        win_boat = race.get('winning_boat')
        if not win_boat or not race.get('boats'):
            continue

        for boat in race['boats']:
            # boatが辞書型であることを確認
            if not isinstance(boat, dict):
                continue
            
            record = {
                'race_stadium_number': race.get('race_stadium_number'),
                'race_number': race.get('race_number'),
                'boat_number': boat.get('boat_number'),
                'racer_rank': boat.get('racer_rank'),
                'win_rate': boat.get('win_rate'),
                'local_win_rate': boat.get('local_win_rate'),
                'motor_2_rate': boat.get('motor_2_rate'),
                'boat_2_rate': boat.get('boat_2_rate'),
                'is_winner': 1 if boat.get('boat_number') == win_boat else 0
            }
            records.append(record)

    if not records:
        print("処理可能なレコードがありませんでした。データの内容を確認してください。")
        return

    df = pd.DataFrame(records)
    
    # --- 3. 前処理 ---
    # is_winner以外の全てのNone/NaNを処理
    for col in df.columns:
        if col != 'is_winner':
            if df[col].dtype == 'object':
                df[col].fillna(df[col].mode()[0], inplace=True)
            else:
                df[col].fillna(df[col].median(), inplace=True)

    # --- 4. 特徴量とターゲットの定義 ---
    X = df.drop('is_winner', axis=1)
    y = df['is_winner']

    # 特徴量の型を定義
    numeric_features = ['win_rate', 'local_win_rate', 'motor_2_rate', 'boat_2_rate']
    categorical_features = ['race_stadium_number', 'race_number', 'boat_number', 'racer_rank']

    # --- 5. 前処理パイプラインの作成 ---
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ], remainder='passthrough')

    # --- 6. モデルの定義とパイプラインの結合 ---
    model = Pipeline(steps=[('preprocessor', preprocessor),
                            ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'))])

    # --- 7. 訓練データとテストデータに分割 ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # --- 8. モデルの訓練 ---
    print("モデルの訓練を開始します...")
    model.fit(X_train, y_train)
    print("モデルの訓練が完了しました。")

    # --- 9. モデルの評価 ---
    y_pred = model.predict(X_test)
    print("\n--- モデル評価結果 ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # --- 10. モデルと前処理器の保存 ---
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok=True)

    model_path = os.path.join(cache_dir, 'improved_ml_models.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model, f) # パイプライン全体を保存
    print(f"\nモデルパイプラインを {model_path} に保存しました。")


if __name__ == '__main__':
    train_model()
