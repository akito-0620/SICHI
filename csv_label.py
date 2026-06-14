import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def process_eda_data_with_visualization(input_filename=                 'csv/k4.csv', 
                                        output_csv_filename='label/1/k_events_4.csv',
                                        output_plot_filename          ='img/1_4.png'):
    """
    EDAセンサーの時系列データからイベントを検出し、特徴量を抽出し、
    ラベルを付けて教師データを作成します。
    さらに、検出したイベント区間を元のデータ上にプロットして保存します。

    Args:
        input_filename (str): 元のEDAデータが格納された入力CSVファイル名。
        output_csv_filename (str): 処理結果のラベル付きイベントデータが保存される出力CSVファイル名。
        output_plot_filename (str): イベント区間を可視化したグラフの保存ファイル名。
    """
    print(f"'{input_filename}' の処理を開始します...")

    # --- 0. データの読み込み ---
    try:
        df = pd.read_csv(input_filename)
        print("ステップ0: データの読み込みが完了しました。")
    except FileNotFoundError:
        print(f"エラー: 入力ファイル '{input_filename}' が見つかりません。")
        return

    # --- 1. トリガーの計算 ---
    df['eda_pct_change'] = df['eda'].pct_change().fillna(0)
    df['pct_change_sum_4step'] = df['eda_pct_change'].rolling(window=4).sum().fillna(0)
    print("ステップ1: トリガーとなる変化率の移動合計を計算しました。")

    # --- 2. イベントの検出と特徴量抽出 ---
    rolling_sum_threshold = 0.02
    frame_size = 40

    events = []
    detected_indices = df.index[df['pct_change_sum_4step'] > rolling_sum_threshold]

    last_event_end = -1
    for idx in detected_indices:
        if idx <= last_event_end:
            continue

        start_index = max(0, idx - 4 + 1)
        end_index = min(start_index + frame_size, len(df))
        frame = df.iloc[start_index:end_index]
        
        last_event_end = end_index - 1

        if not frame.empty:
            events.append({
                'start_time': df.iloc[start_index]['time'],
                # 可視化のために終了時刻も保存
                'end_time': df.iloc[end_index - 1]['time'],
                'max_pct_change': frame['eda_pct_change'].max(),
                'mean_pct_change': frame['eda_pct_change'].mean(),
                'std_eda_original': frame['eda'].std(),
                'duration': (frame['eda_pct_change'] > 0).sum()
            })

    events_df = pd.DataFrame(events)
    print(f"ステップ2: {len(events_df)}個のイベントを検出し、特徴量を抽出しました。")

    # --- 3. ラベリング ---
    events_df['label'] = 1
    print("ステップ3: すべてのイベントに「偽」のラベル（0）を付けました。")
    # print("ステップ3: すべてのイベントに「真」\のラベル（1）を付けました。")

    # --- 4. 可視化とグラフの保存 ---
    plt.figure(figsize=(15, 7))
    plt.plot(df['time'], df['eda'], label='Original EDA Data', color='skyblue', zorder=1)

    for index, event in events_df.iterrows():
        # 凡例が重複しないように、最初の1回だけラベルを付ける
        if index == 0:
            plt.axvline(x=event['start_time'], color='red', linestyle='--', label='Event Start')
            plt.axvline(x=event['end_time'], color='blue', linestyle='--', label='Event End')
        else:
            plt.axvline(x=event['start_time'], color='red', linestyle='--')
            plt.axvline(x=event['end_time'], color='blue', linestyle='--')

    plt.title('EDA Data with Detected Event Frames')
    plt.xlabel('Time (seconds)')
    plt.ylabel('EDA Value')
    plt.legend()
    plt.grid(True)
    
    plt.savefig(output_plot_filename)
    print(f"ステップ4: イベント区間を可視化したグラフを '{output_plot_filename}' として保存しました。")
    
    # --- 5. 結果のCSV保存 ---
    # 可視化に使ったend_time列は最終的な特徴量ではないので削除
    events_df_to_save = events_df
    events_df_to_save.to_csv(output_csv_filename, index=False)
    print(f"ステップ5: 最終的な教師データを '{output_csv_filename}' として保存しました。")
    print("\n--- 処理完了 ---")
    print("生成されたデータ:")
    print(events_df_to_save)


# --- メイン処理の実行 ---
if __name__ == '__main__':
    process_eda_data_with_visualization()