import tkinter as tk
from PIL import Image, ImageTk
import pygame
import os
import random
import threading
import time
import serial
import pandas as pd
import numpy as np
from collections import deque
from sklearn.ensemble import RandomForestClassifier
from bitalino import BITalino

# ===================================================================
# ===== 1. ファイルパスとゲーム設定 =====
# ===================================================================
GAME_WINDOW_WIDTH = 960
GAME_WINDOW_HEIGHT = 540

# --- 時間設定 ---
WIN_TIME = 40
COUNTER_INTERVAL = 10
END_BGM_DURATION = 5000
FINISH_SE_DURATION = 2000
START_SE_DURATION = 800

# --- 画像ファイル ---
IMG_BACKGROUND = "img_f/std.png" # 背景画像
IMG_ATTACK = "img_f/atc.png"
IMG_DEFENSE = "img_f/df.png"
IMG_COUNTER = "img_f/counter.png"
IMG_LOSE = "img_f/lose.png"
IMG_WIN = "img_f/win.png"

# --- 音楽ファイル ---
BGM_FILES = ["music/3.mp3", "music/4.mp3",  "music/6.mp3"]
BGM_WIN = "music/win.mp3"
BGM_LOSE = "music/lose.mp3"
ATTACK_FILES = ["se/p1.mp3", "se/p2.mp3"]
COUNTER_FILES = ["se/atc1.mp3", "se/atc2.mp3"]
DEFENSE_FILE = "se/df1.mp3"
SE_START = "se/start.mp3"
SE_FINISH = "se/fin.mp3"

# --- HP設定 ---
initial_player_hp = 4
initial_chili_hp = WIN_TIME // COUNTER_INTERVAL

# ===================================================================
# ===== 2. BITalino & 分析パラメータ設定 =====
# ===================================================================
BITALINO_MAC_ADDRESS = "98:D3:11:FE:02:2B"
SAMPLING_RATE = 10
ACQ_CHANNELS = [2]
N_SAMPLES = 1
ROLLING_WINDOW_SIZE = 4
ROLLING_SUM_THRESHOLD = 0.012
FRAME_SIZE = 40
DATA_BUFFER_SIZE = 200

# ===================================================================
# ===== 3. Arduino & シリアル通信設定 =====
# ===================================================================
SERIAL_PORT = "COM3"
BAUD_RATE = 9600

# ===================================================================
# ===== 4. グローバル変数 (プログラム全体で共有) =====
# ===================================================================
# --- 制御用変数 ---
bitalino_device = None
is_recording = False
eda_thread = None
model = None
data_buffer = deque(maxlen=DATA_BUFFER_SIZE)
last_event_time = 0
ser = None
is_game_over = False
current_bgm_index = 0
fade_time = 300
player_hp = initial_player_hp
chili_hp = initial_chili_hp
game_start_time = 0
last_counter_time = 0

# --- GUIウィジェット変数 ---
root = None
connect_button, start_button, stop_button, disconnect_button = None, None, None, None
status_label, prediction_label = None, None
game_window, game_canvas = None, None
loaded_images = {}

# ===================================================================
# ===== 5. コア機能 (機械学習, 画像処理, 音楽再生, Arduino) =====
# ===================================================================
def train_and_get_model(teacher_data_filename='label/all_datas.csv'):
    global model
    try:
        df_teacher = pd.read_csv(teacher_data_filename)
        features = ['max_pct_change', 'mean_pct_change', 'std_eda_original', 'duration']
        X = df_teacher[features]
        y = df_teacher['label']
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        if status_label:
            status_label.config(text="モデル学習完了。BITalino接続待機中...", fg="blue")
        print("✅ モデルの学習が完了しました。")
    except Exception as e:
        if status_label:
            status_label.config(text=f"教師データ '{teacher_data_filename}' が見つかりません。", fg="red")
        print(f"⚠ モデル学習エラー: {e}")

def setup_arduino():
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("✅ Arduinoと接続しました")
    except Exception as e:
        print(f"⚠ Arduino接続失敗: {e}")

def send_hp_to_arduino(hp_value):
    if ser and ser.is_open:
        try:
            ser.write(f"{hp_value};".encode('utf-8'))
            ser.flush()
            print(f"➡ ArduinoへHP送信: {hp_value}")
        except Exception as e:
            print(f"⚠ シリアル送信エラー: {e}")

def load_images():
    image_paths = {
        "bg": IMG_BACKGROUND, "atc": IMG_ATTACK, "df": IMG_DEFENSE,
        "lose": IMG_LOSE, "win": IMG_WIN, "counter": IMG_COUNTER
    }
    for name, path in image_paths.items():
        if os.path.exists(path):
            img = Image.open(path)
            img = img.resize((GAME_WINDOW_WIDTH, GAME_WINDOW_HEIGHT), Image.Resampling.LANCZOS)
            loaded_images[name] = ImageTk.PhotoImage(img)
        else:
            print(f"⚠ 画像ファイルが見つかりません: {path}")

def update_game_image(image_name):
    if game_canvas and image_name in loaded_images:
        game_canvas.create_image(0, 0, anchor='nw', image=loaded_images[image_name])
        draw_hp_bars()
        game_window.update()

def draw_hp_bars():
    if not game_canvas: return
    game_canvas.delete("hp_bar")
    margin, bar_height, max_bar_width = 20, 20, (GAME_WINDOW_WIDTH / 2) - 30
    chili_hp_width = max_bar_width * (chili_hp / initial_chili_hp)
    game_canvas.create_rectangle(margin, margin, margin + max_bar_width, margin + bar_height, fill='#555', outline='white', tags="hp_bar")
    game_canvas.create_rectangle(margin, margin, margin + chili_hp_width, margin + bar_height, fill='green', outline='white', tags="hp_bar")
    game_canvas.create_text(margin + 10, margin + (bar_height/2), text=f"唐辛子HP: {chili_hp}", fill="white", anchor="w", tags="hp_bar", font=("Arial", 12, "bold"))
    player_hp_width = max_bar_width * (player_hp / initial_player_hp)
    right_edge = GAME_WINDOW_WIDTH - margin
    start_x = right_edge - player_hp_width
    game_canvas.create_rectangle(right_edge - max_bar_width, margin, right_edge, margin + bar_height, fill='#555', outline='white', tags="hp_bar")
    game_canvas.create_rectangle(start_x, margin, right_edge, margin + bar_height, fill='red', outline='white', tags="hp_bar")
    game_canvas.create_text(right_edge - 10, margin + (bar_height/2), text=f"人間HP: {player_hp}", fill="white", anchor="e", tags="hp_bar", font=("Arial", 12, "bold"))

def play_bgm(index, loop=-1):
    global current_bgm_index
    current_bgm_index = index
    bgm_file = BGM_FILES[index]
    if 0 <= index < len(BGM_FILES) and os.path.exists(bgm_file):
        pygame.mixer.music.load(bgm_file)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(loop)

def play_end_bgm(bgm_file):
    if os.path.exists(bgm_file):
        pygame.mixer.music.stop()
        pygame.mixer.music.load(bgm_file)
        pygame.mixer.music.set_volume(0.8)
        pygame.mixer.music.play(loops=0)
        root.after(END_BGM_DURATION, pygame.mixer.music.stop)

def play_effect_with_image_change(effect_file, image_name):
    if is_game_over or not os.path.exists(effect_file): return
    update_game_image(image_name)
    pygame.mixer.music.fadeout(fade_time)
    effect_sound = pygame.mixer.Sound(effect_file)
    effect_sound.play()
    def restore_after_effect():
        time.sleep(effect_sound.get_length())
        if not is_game_over:
            update_game_image("bg")
            play_bgm(current_bgm_index)
    threading.Thread(target=restore_after_effect, daemon=True).start()

def attack(probability):
    global current_bgm_index, player_hp
    if player_hp > 0 and not is_game_over:
        player_hp -= 1
        print(f"💥 攻撃イベント発生！ (確信度: {probability:.1f}%) 人間HP={player_hp}")
        send_hp_to_arduino(player_hp)
        draw_hp_bars()
        play_effect_with_image_change(random.choice(ATTACK_FILES), "atc")
        if player_hp == 0:
            root.after(int(fade_time * 3), show_game_over)
        elif player_hp <= 2: # HPが3以下でBGM変更
            current_bgm_index = min(current_bgm_index + 1, len(BGM_FILES) - 1)

def defense(probability):
    if not is_game_over:
        print(f"🛡 防御イベント発生 (確信度: {probability:.1f}%)")
        play_effect_with_image_change(DEFENSE_FILE, "df")

def counter():
    global chili_hp
    if not is_game_over and chili_hp > 0:
        chili_hp -= 1
        print(f"🔄 反撃イベント発生！ 唐辛子HP={chili_hp}")
        draw_hp_bars()
        play_effect_with_image_change(random.choice(COUNTER_FILES), "counter")
        if chili_hp <= 0:
            root.after(int(fade_time * 3), show_game_win)


def show_game_over():
    global is_game_over
    if is_game_over: return
    is_game_over = True
    print("GAME OVER")
    update_game_image("lose")
    
    # ★★★ 決着サウンドを再生してから敗北BGMへ ★★★
    finish_sound = pygame.mixer.Sound(SE_FINISH)
    pygame.mixer.music.stop()
    finish_sound.play(maxtime=FINISH_SE_DURATION)
    root.after(FINISH_SE_DURATION, lambda: play_end_bgm(BGM_LOSE))
    total_delay = FINISH_SE_DURATION 
    root.after(total_delay, lambda: display_end_text("LOSE", "blue"))

def show_game_win():
    global is_game_over
    if is_game_over: return
    is_game_over = True
    print("GAME WIN")
    update_game_image("win")
    
    # ★★★ 決着サウンドを再生してから勝利BGMへ ★★★
    finish_sound = pygame.mixer.Sound(SE_FINISH)
    pygame.mixer.music.stop()
    finish_sound.play(maxtime=FINISH_SE_DURATION)
    root.after(FINISH_SE_DURATION, lambda: play_end_bgm(BGM_WIN))
    total_delay = FINISH_SE_DURATION 
    root.after(total_delay, lambda: display_end_text("WIN", "red"))


def display_end_text(text, color):
    """ゲーム画面の中央に終了テキストを表示する"""
    if game_canvas:
        game_canvas.create_text(
            GAME_WINDOW_WIDTH / 2,
            GAME_WINDOW_HEIGHT / 2,
            text=text,
            fill=color,
            font=("Impact", 150, "bold"), # Impactフォントで見栄え良く
            anchor='center'
        )

# ===================================================================
# ===== 6. リアルタイム分析処理 =====
# ===================================================================
def analyze_realtime_data():
    global last_event_time
    if len(data_buffer) < FRAME_SIZE: return

    df = pd.DataFrame(list(data_buffer), columns=['time', 'eda'])
    df['eda_pct_change'] = df['eda'].pct_change().fillna(0)
    df['pct_change_sum_4step'] = df['eda_pct_change'].rolling(window=ROLLING_WINDOW_SIZE).sum().fillna(0)
    
    if df['pct_change_sum_4step'].iloc[-1] > ROLLING_SUM_THRESHOLD:
        if time.time() - last_event_time < 5: return
        last_event_time = time.time()
        print("イベントを検出。予測を実行します...")
        
        frame = df.iloc[-FRAME_SIZE:]
        features = np.array([[
            frame['eda_pct_change'].max(), frame['eda_pct_change'].mean(),
            frame['eda'].std(), (frame['eda_pct_change'] > 0).sum()
        ]])
        
        if model:
            # ★★★★★ 修正点②：predict_probaで確率を取得し、attack/defense関数に渡す ★★★★★
            prediction = model.predict(features)[0]
            probabilities = model.predict_proba(features)[0] # [クラス0の確率, クラス1の確率]

            if prediction == 1:
                confidence = probabilities[1] * 100 # クラス1(真)である確率
                # lambdaを使ってattack関数に確率の値を渡す
                root.after(0, lambda: attack(confidence))
                root.after(0, lambda: prediction_label.config(text=f"交感神経活動: 高 (攻撃！) {confidence:.1f}%", fg="red"))
            else:
                confidence = probabilities[0] * 100 # クラス0(偽)である確率
                # lambdaを使ってdefense関数に確率の値を渡す
                root.after(0, lambda: defense(confidence))
                root.after(0, lambda: prediction_label.config(text=f"状態: 平常時 (防御) {confidence:.1f}%", fg="green"))
            # -------------------------------------------------------------

def realtime_processing_thread():
    start_time = time.time()
    while is_recording:
        try:
            data = bitalino_device.read(N_SAMPLES)
            eda_raw = data[:, 5]
            for value in eda_raw:
                data_buffer.append([time.time() - start_time, value])
            analyze_realtime_data()
            # N_SAMPLES=1の場合、過度なCPU使用を防ぐため小さなsleepを入れる
            if N_SAMPLES == 1: time.sleep(0.01)
        except Exception as e:
            if is_recording: print(f"⚠ データ読み取りエラー: {e}")
            break
    print("🔌 計測スレッド終了")

def connect_bitalino():
    global bitalino_device
    if bitalino_device: return
    try:
        status_label.config(text=f"{BITALINO_MAC_ADDRESS}に接続中...", fg="orange")
        root.update_idletasks()
        bitalino_device = BITalino(BITALINO_MAC_ADDRESS)
        bitalino_device.start(SAMPLING_RATE, ACQ_CHANNELS)
        status_label.config(text="接続成功！計測を開始できます", fg="blue")
        connect_button.config(state=tk.DISABLED); disconnect_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)
    except Exception as e:
        bitalino_device = None
        status_label.config(text=f"接続エラー: {e}", fg="red")

def game_loop():
    if is_game_over: return
    current_time = time.time()
    global last_counter_time
    if current_time - last_counter_time > COUNTER_INTERVAL:
        counter()
        last_counter_time = current_time
    root.after(1000, game_loop)

def start_recording():
    global is_recording, eda_thread, game_window, game_canvas, game_start_time, last_counter_time, player_hp, chili_hp, is_game_over
    if not bitalino_device or is_recording: return
    
    if game_window is None or not game_window.winfo_exists():
        game_window = tk.Toplevel(root)
        game_window.title("Game Display")
        game_window.resizable(False, False)
        game_canvas = tk.Canvas(game_window, width=GAME_WINDOW_WIDTH, height=GAME_WINDOW_HEIGHT)
        game_canvas.pack()
    
    player_hp = initial_player_hp
    chili_hp = initial_chili_hp
    is_game_over = False
    
    update_game_image("bg")

    start_sound = pygame.mixer.Sound(SE_START)
    start_sound.play(maxtime=START_SE_DURATION)
    root.after(START_SE_DURATION, lambda: play_bgm(0))

    is_recording = True
    data_buffer.clear()
    prediction_label.config(text="反応を待っています...", fg="gray")
    eda_thread = threading.Thread(target=realtime_processing_thread, daemon=True)
    eda_thread.start()
    status_label.config(text="計測中...", fg="green")
    start_button.config(state=tk.DISABLED); stop_button.config(state=tk.NORMAL)
    disconnect_button.config(state=tk.DISABLED)
    
    game_start_time = time.time()
    last_counter_time = time.time()
    game_loop()


def stop_recording():
    global is_recording
    if is_recording:
        is_recording = False
        status_label.config(text="停止しました", fg="blue")
        if bitalino_device:
            start_button.config(state=tk.NORMAL)
            disconnect_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

def disconnect_bitalino():
    global bitalino_device
    if is_recording: return
    if bitalino_device:
        try:
            bitalino_device.stop(); bitalino_device.close()
            bitalino_device = None
            status_label.config(text="切断しました", fg="black")
            connect_button.config(state=tk.NORMAL); disconnect_button.config(state=tk.DISABLED)
            start_button.config(state=tk.DISABLED); stop_button.config(state=tk.DISABLED)
        except Exception as e:
            status_label.config(text=f"切断エラー: {e}", fg="red")

def on_closing():
    global is_recording
    is_recording = False
    time.sleep(0.5)
    if bitalino_device and bitalino_device.is_connected:
        disconnect_bitalino()
    if ser and ser.is_open: ser.close()
    pygame.mixer.quit()
    if root: root.destroy()

def create_gui():
    global root, connect_button, start_button, stop_button, disconnect_button, status_label, prediction_label
    root = tk.Tk()
    root.title("コントロールパネル")
    
    bitalino_frame = tk.LabelFrame(root, text="センサーコントロール", padx=10, pady=10)
    bitalino_frame.pack(pady=10, padx=10, fill="x")
    
    connect_button = tk.Button(bitalino_frame, text="1. 接続", command=connect_bitalino)
    connect_button.pack(side=tk.LEFT, expand=True, fill="x")
    start_button = tk.Button(bitalino_frame, text="2. 計測開始", command=start_recording, state=tk.DISABLED)
    start_button.pack(side=tk.LEFT, expand=True, fill="x")
    stop_button = tk.Button(bitalino_frame, text="3. 計測停止", command=stop_recording, state=tk.DISABLED)
    stop_button.pack(side=tk.LEFT, expand=True, fill="x")
    disconnect_button = tk.Button(bitalino_frame, text="4. 切断", command=disconnect_bitalino, state=tk.DISABLED)
    disconnect_button.pack(side=tk.LEFT, expand=True, fill="x")
    
    status_frame = tk.LabelFrame(root, text="ステータス", padx=10, pady=10)
    status_frame.pack(pady=10, padx=10, fill="x")
    status_label = tk.Label(status_frame, text="モデルを学習中...", fg="orange")
    status_label.pack()
    prediction_label = tk.Label(status_frame, text="---", fg="gray", font=("Arial", 14, "bold"))
    prediction_label.pack(pady=5)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)

if __name__ == "__main__":
    pygame.mixer.init()
    setup_arduino()
    create_gui()
    load_images()
    threading.Thread(target=train_and_get_model, daemon=True).start()
    send_hp_to_arduino(player_hp)
    root.mainloop()