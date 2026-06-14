# SICHI — 辛さ体験型 EDA連動ゲーム

BITalinoのEDAセンサーで辛い物を食べたときの発汗を検知し、発汗が検出されるとプレイヤーがダメージを受けるゲームです。  
ランダムフォレスト分類器でリアルタイムに「辛さ由来の発汗」と「平常時の発汗」を識別し、ゲームイベントに変換します。

## ゲームの概要

| 項目 | 内容 |
|---|---|
| プレイヤーHP | 4 |
| 唐辛子HP | 4（10秒ごとに自動減少） |
| 勝利条件 | 唐辛子HPが0になる（辛さに耐えきる） |
| 敗北条件 | プレイヤーHPが0になる（発汗しすぎる） |
| 発汗検知 → 攻撃 | プレイヤーHP -1、BGMが緊張感のある曲へ切り替わる |
| 平常時検知 → 防御 | 防御演出のみ（HPへの影響なし） |

## システム構成

```
BITalino (EDAセンサー)
    │ Bluetooth
    ▼
eda_game_v3.py  ─── RandomForest分類 ──▶ 攻撃 / 防御 イベント
    │                                        │
    │ シリアル通信 (COM3)                    │
    ▼                                        ▼
Arduino (HP表示)                       tkinter + pygame (ゲーム画面)
```

## ファイル構成

```
.
├── eda_game_v3.py      # メインゲーム（本番用）
├── make_karai.py       # 辛いデータ収集用 EDA レコーダー
├── make_normal.py      # 平常時データ収集用 EDA レコーダー
├── csv_label.py        # EDAデータからイベント検出・特徴量抽出・ラベル付け
├── model.py            # モデル学習・評価・混同行列出力
├── label/
│   ├── all_csv.py      # 個別CSVを結合して all_datas.csv を生成
│   └── all_datas.csv   # 学習用教師データ（辛い/平常時イベント）
├── img_f/              # ゲーム画面用背景画像
├── music/              # BGM（通常〜ピンチ、勝利、敗北）
└── se/                 # 効果音（攻撃、防御、開始、終了）
```

## 必要環境

- Python 3.8+
- BITalino デバイス（EDAセンサー, チャンネル3）
- Arduino（HP表示用、任意）

### パッケージインストール

```bash
pip install pillow pygame pyserial pandas numpy scikit-learn bitalino
```

## 使い方

### 1. ゲームを実行する

```bash
cd code
python eda_game_v3.py
```

起動後、コントロールパネルで操作します：

1. **接続** — BITalinoとBluetooth接続
2. **計測開始** — ゲームスタート（発汗検知開始）
3. **計測停止** — ゲーム一時停止
4. **切断** — BITalino切断

### 2. 教師データを収集する（再学習したい場合）

```bash
# 辛い食べ物を食べながら計測
python make_karai.py    # → csv/k*.csv に保存

# 平常時を計測
python make_normal.py   # → csv/n*.csv に保存

# イベント抽出・ラベル付け
python csv_label.py     # → label/1/ または label/0/ に保存

# CSVを結合
python label/all_csv.py # → label/all_datas.csv を更新

# モデル評価（オプション）
python model.py
```

## 設定の変更

`eda_game_v3.py` の上部にある定数を環境に合わせて変更してください：

```python
# BITalino の MACアドレス
BITALINO_MAC_ADDRESS = "98:D3:11:FE:02:2B"

# Arduino のシリアルポート
SERIAL_PORT = "COM3"

# ゲームバランス
WIN_TIME = 40           # 唐辛子の初期HP（秒換算）
COUNTER_INTERVAL = 10   # 唐辛子HPが減る間隔（秒）
initial_player_hp = 4   # プレイヤーの初期HP
```

## 機械学習モデルの詳細

| 項目 | 内容 |
|---|---|
| アルゴリズム | RandomForestClassifier（100本）|
| 特徴量 | `max_pct_change`, `mean_pct_change`, `std_eda_original`, `duration` |
| イベント検出 | EDA変化率の4ステップ移動合計 > 0.012 |
| クールダウン | イベント検出後5秒間は再検出しない |

## 依存関係

| ライブラリ | 用途 |
|---|---|
| `bitalino` | BITalinoデバイスとのBluetooth通信 |
| `pygame` | BGM・効果音の再生 |
| `tkinter` / `Pillow` | GUIとゲーム画像の描画 |
| `scikit-learn` | RandomForestによる発汗分類 |
| `pandas` / `numpy` | EDAデータの処理・特徴量計算 |
| `pyserial` | ArduinoへのHP送信 |
