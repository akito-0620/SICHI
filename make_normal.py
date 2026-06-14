import tkinter as tk
import csv
import time
import threading
from bitalino import BITalino

# ==== BITalino設定 ====
macAddress = "98:D3:11:FE:02:2B"  # ご自身のデバイスのMACアドレス
samplingRate = 10
acqChannels = [2]
nSamples = 1
filename = "./csv/n12.csv"
# ==== グローバル変数 ====
device = None    # BITalinoデバイスオブジェクトを保持する
running = False  # 計測中かどうか
thread = None    # 計測スレッド

# --- 機能追加：BITalinoとの接続 ---
def connect_bitalino():
    """BITalinoデバイスとの接続を試みる"""
    global device
    if device is not None:
        status_label.config(text="すでに接続済みです", fg="blue")
        return

    try:
        status_label.config(text=f"{macAddress}に接続中...", fg="orange")
        root.update_idletasks() # ラベルの更新を即時反映
        
        device = BITalino(macAddress)
        device.start(samplingRate, acqChannels)
        
        status_label.config(text="接続成功！計測を開始できます", fg="blue")
        # ボタンの状態を更新
        connect_button.config(state=tk.DISABLED)
        disconnect_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)
        
    except Exception as e:
        device = None
        status_label.config(text=f"接続エラー: {e}", fg="red")

# --- 機能追加：BITalinoとの切断 ---
def disconnect_bitalino():
    """BITalinoデバイスとの接続を切断する"""
    global device
    if running:
        status_label.config(text="エラー: 先に計測を停止してください", fg="red")
        return

    if device:
        try:
            device.stop()
            device.close()
            device = None
            status_label.config(text="切断しました", fg="blue")
            # ボタンの状態を更新
            connect_button.config(state=tk.NORMAL)
            disconnect_button.config(state=tk.DISABLED)
            start_button.config(state=tk.DISABLED)
            stop_button.config(state=tk.DISABLED)
        except Exception as e:
            status_label.config(text=f"切断エラー: {e}", fg="red")


def record_eda():
    """EDAを取得してCSVに保存するスレッド処理"""
    
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "eda"])

        start_time = time.time()
        # 'running'がFalseになるまでループ
        while running:
            try:
                data = device.read(nSamples)
                eda_raw = data[:, 5]

                for value in eda_raw:
                    timestamp = time.time() - start_time
                    writer.writerow([timestamp, value])
                
                time.sleep(nSamples / samplingRate * 0.5)
            except Exception as e:
                print(f"データ読み取りエラー: {e}")
                break # エラーが発生したらループを抜ける
    print("計測スレッド終了")


def start_recording():
    """計測開始"""
    global running, thread
    if not device:
        status_label.config(text="エラー: BITalinoが接続されていません", fg="red")
        return

    if not running:
        running = True
        thread = threading.Thread(target=record_eda, daemon=True)
        thread.start()
        status_label.config(text="計測中...", fg="green")
        # ボタンの状態を更新
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
        disconnect_button.config(state=tk.DISABLED) # 計測中は切断不可


def stop_recording():
    """計測停止"""
    global running
    if running:
        running = False
        status_label.config(text="停止しました", fg="red")
        # ボタンの状態を更新
        if device:
            start_button.config(state=tk.NORMAL)
            disconnect_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

# --- 機能追加：ウィンドウを閉じる際の処理 ---
def on_closing():
    """ウィンドウが閉じられるときに実行される関数"""
    if running:
        stop_recording() # 計測中なら停止
    if device:
        disconnect_bitalino() # 接続中なら切断
    root.destroy()

# ==== GUI構築 ====
root = tk.Tk()
root.title("EDA Recorder")
root.geometry("300x250") # ウィンドウサイズを少し調整

# --- ボタンの順番と状態を変更 ---
connect_button = tk.Button(root, text="接続", command=connect_bitalino, width=15, height=2)
connect_button.pack(pady=5)

start_button = tk.Button(root, text="Start", command=start_recording, width=15, height=2, state=tk.DISABLED)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_recording, width=15, height=2, state=tk.DISABLED)
stop_button.pack(pady=5)

disconnect_button = tk.Button(root, text="切断", command=disconnect_bitalino, width=15, height=2, state=tk.DISABLED)
disconnect_button.pack(pady=5)

status_label = tk.Label(root, text="待機中 (最初に接続ボタンを押してください)", fg="blue", font=("Arial", 10))
status_label.pack(pady=10)

# ウィンドウの「×」ボタンに関数を割り当て
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()