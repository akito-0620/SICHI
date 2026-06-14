import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
import os

def train_and_evaluate_model(data_filename='label/all_datas.csv', 
                               plot_filename='confusion_matrix.png'):
    """
    結合されたイベントデータを読み込み、ランダムフォレストモデルを学習させ、
    その性能を評価して混合行列を保存します。

    Args:
        data_filename (str): 学習に使用するCSVファイル名。
        plot_filename (str): 保存する混合行列の画像ファイル名。
    """
    print("モデルの学習と評価を開始します...")

    # --- 1. データの読み込み ---
    try:
        df = pd.read_csv(data_filename)
        print(f"ステップ1: '{data_filename}' の読み込みが完了しました。")
        print(f"合計 {len(df)} 件のイベントデータがあります。")
    except FileNotFoundError:
        print(f"エラー: データファイル '{data_filename}' が見つかりません。")
        print("前のステップで all_datas.csv を作成したか確認してください。")
        return

    # --- 2. データの準備 ---
    # 特徴量 (X) とラベル (y) を定義
    # start_timeとend_timeはイベントの特定には使うが、モデルの直接の特徴量からは除外
    features = ['max_pct_change', 'mean_pct_change', 'std_eda_original', 'duration']
    X = df[features]
    y = df['label']

    # データを学習用(70%)とテスト用(30%)に分割
    # stratify=y は、元のデータのラベルの比率を保ったまま分割するオプション
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    print("ステップ2: データを学習用とテスト用に分割しました。")

    # --- 3. モデルの学習 ---
    # ランダムフォレスト分類器を初期化して学習
    model = RandomForestClassifier(n_estimators=100, random_state=7)
    model.fit(X_train, y_train)
    print("ステップ3: ランダムフォレストモデルの学習が完了しました。")

    # --- 4. 予測と評価 ---
    # テストデータを使って予測
    y_pred = model.predict(X_test)

    print("\n--- 評価結果 ---")
    # classification_reportで適合率、再現率、F1スコアなどを表示
    print("▼分類レポート:")
    print(classification_report(y_test, y_pred, target_names=['Class 0 (n)', 'Class 1 (k)']))
    
    # 混合行列を作成
    cm = confusion_matrix(y_test, y_pred)
    
    # --- 5. 混合行列の可視化と保存 ---
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Predicted 0 (n)', 'Predicted 1 (k)'], 
                yticklabels=['Actual 0 (n)', 'Actual 1 (k)'])
    plt.title('Confusion Matrix')
    plt.ylabel('Actual Label')
    plt.xlabel('Predicted Label')

    plt.savefig(plot_filename)
    print(f"\nステップ5: 混合行列を '{plot_filename}' として保存しました。")
    print("--- 処理完了 ---")

# --- メイン処理の実行 ---
if __name__ == '__main__':
    train_and_evaluate_model()