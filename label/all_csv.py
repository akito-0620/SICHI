import os
import pandas as pd

def combine_csv_files(base_folder='label', output_filename='all_datas.csv'):
    """
    指定されたベースフォルダ内のサブフォルダ（'0', '1'）にある
    全てのCSVファイルを1つのCSVファイルに結合します。

    Args:
        base_folder (str): サブフォルダが含まれる親フォルダ名。
        output_filename (str): 出力する結合後CSVファイル名。
    """
    # 結合したデータを格納するための空のDataFrameを準備
    all_data_df = pd.DataFrame()
    
    # ベースフォルダのパスを構築
    base_path = base_folder
    output_filepath = os.path.join(base_path, output_filename)

    print(f"'{base_path}' フォルダの処理を開始します...")

    # '0'と'1'のサブフォルダをループ処理
    for sub_folder in ['0', '1']:
        folder_path = os.path.join(base_path, sub_folder)

        # フォルダが存在するか確認
        if not os.path.isdir(folder_path):
            print(f"警告: '{folder_path}' が見つかりません。スキップします。")
            continue

        # フォルダ内の全ファイルを取得
        for filename in os.listdir(folder_path):
            # ファイルがCSVファイルの場合のみ処理
            if filename.endswith('.csv'):
                file_path = os.path.join(folder_path, filename)
                try:
                    # CSVファイルを読み込む
                    df = pd.read_csv(file_path)
                    
                    # データを結合用のDataFrameに追加
                    all_data_df = pd.concat([all_data_df, df], ignore_index=True)
                    
                    print(f" - '{file_path}' を読み込みました。")
                except Exception as e:
                    print(f"エラー: '{file_path}' の読み込み中に問題が発生しました: {e}")

    # 結合したデータが空でないか確認
    if not all_data_df.empty:
        # 最終的なCSVファイルとして保存
        all_data_df.to_csv(output_filepath, index=False)
        print(f"\nすべてのCSVデータを結合し、'{output_filepath}' として保存しました。")
        print(f"合計 {len(all_data_df)} 件のイベントデータが保存されました。")
    else:
        print("\n処理対象のCSVファイルが見つからなかったため、ファイルは作成されませんでした。")


# --- メイン処理の実行 ---
if __name__ == '__main__':
    combine_csv_files()