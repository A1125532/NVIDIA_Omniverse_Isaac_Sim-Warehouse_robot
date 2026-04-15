# 巨量資料分析期末專題：Isaac Sim 倉儲叉車監控與控制系統

完整檔案：https://drive.google.com/drive/folders/1izmM1tDj53Wz2Foz9Cha8KURc7s638yV?usp=drive_link

本專案結合 **Isaac Sim 模擬腳本**、**FastAPI 後端** 與 **Web 即時儀表板**，用於展示倉儲場景中叉車（Forklift）移動、避障、任務觸發與位置回傳的完整流程。

核心目標是讓使用者能透過網頁端發出開始指令，並在 2D 面板上即時觀察 Isaac Sim 內叉車的位置與朝向變化。

---

## 功能總覽

- 讀取 USD 倉儲場景並在 Isaac Sim 建立多個區域標記（Zone 4/5/6/Prepare）
- 自動掃描場景樹，嘗試辨識 forklift、障礙物與箱子物件
- 叉車路徑規劃與動態避障（含重新規劃 waypoint）
- 透過 FastAPI 進行前後端通訊（開始、重置、姿態、指令）
- 前端儀表板即時顯示叉車位置（x, y）與朝向（yaw）
- 任務完成或超時後可自動重置執行旗標，支援再次執行

---

## 專案結構

```text
巨量資料分析期末專題/
├─ avg.py
├─ finish.py
├─ dashboard_server.py
├─ start_server.bat
├─ test.py
├─ requirements.txt
└─ frontend/
   └─ index.html
```

---

## 各檔案詳細說明

### `finish.py`（主要 Isaac Sim 任務腳本）

主要負責：

1. 啟動 `SimulationApp`
2. 載入倉儲 USD 場景
3. 建立 Zone 標記（4、5、6、Prepare）
4. 掃描場景並辨識：
   - 可能 forklift 物件
   - 障礙物（地面附近、排除結構物/貨架/車輛）
   - 箱體物件（box/crate/cargo/container/pallet/package）
5. 叉車運動控制流程：
   - 等待 API 開始信號
   - 裝載階段（前進）
   - 倒退回起始並後移
   - 主要移動階段（避障 + 目標停車）
6. 持續將姿態透過 `POST /api/pose` 發送給後端
7. 任務完成後呼叫 `POST /api/reset`，允許下一輪執行

> 這支腳本包含較完整狀態機與「貨物跟隨車身移動/旋轉」邏輯，通常可視為主版本。

---

### `avg.py`（另一版 Isaac Sim 腳本）

整體流程與 `finish.py` 類似，也有：

- 場景載入
- Zone 建立
- forklift 搜尋
- 避障與姿態回傳

差異是流程較簡化，且實作細節與參數設定不同（例如目標定位偏移、停止條件、路線固定行為）。

> 建議擇一腳本作為主執行腳本，避免版本混用造成行為差異。

---

### `dashboard_server.py`（FastAPI 後端）

負責：

- 提供 REST API 供前端與 Isaac Sim 溝通
- 維護共享狀態（姿態、開始旗標、指令）
- 掛載靜態前端頁面（`frontend/index.html`）

API 如下：

- `POST /api/start`：設定開始執行
- `GET /api/start`：查詢是否已開始
- `POST /api/reset`：重置執行狀態
- `POST /api/pose`：更新叉車姿態 `{x, y, yaw}`
- `GET /api/pose`：取得最新姿態
- `POST /api/command`：設定任務指令
- `GET /api/command`：讀取任務指令

---

### `frontend/index.html`（即時監控儀表板）

前端功能：

- 以 2D 平面圖顯示 Zone 範圍與叉車圖示
- 每 200ms 輪詢 `GET /api/pose` 更新畫面
- 按下「開始執行」時：
  1. `POST /api/command`
  2. `POST /api/start`
- 提供「重置」按鈕呼叫 `POST /api/reset`
- 透過簡單停車偵測（位置長時間不變）回復按鈕狀態

---

### `start_server.bat`

Windows 啟動腳本，會直接啟動：

```bash
python -m uvicorn dashboard_server:app --reload --host 127.0.0.1 --port 8000 --log-level warning
```

---

### `requirements.txt`

目前列出：

- `fastapi`
- `uvicorn`
- `requests`

---

### `test.py`

簡單 Python 測試檔，用於確認環境執行正常，與主系統邏輯無直接耦合。

---

## 系統架構與資料流

1. 使用者在前端輸入指令並按「開始執行」
2. 前端送出 `/api/command` 與 `/api/start`
3. Isaac Sim 腳本輪詢 `/api/start`，收到開始旗標後啟動任務
4. 腳本每幀（或週期性）將叉車姿態送往 `/api/pose`
5. 前端持續輪詢 `/api/pose` 並更新地圖上的叉車位置
6. 任務完成後 Isaac Sim 腳本呼叫 `/api/reset`，等待下一次任務

---

## 執行需求

## 1) Python 套件

- Python 3.9+（建議）
- 安裝 `requirements.txt` 內套件

## 2) Isaac Sim 環境

- 需能在 Isaac Sim Python 環境下執行 `finish.py` 或 `avg.py`
- 需可使用：
  - `from isaacsim import SimulationApp`
  - `omni.usd`
  - `pxr` 相關模組（`Usd`, `UsdGeom`, `UsdLux`, `UsdShade`, `Gf`, `Sdf`）

## 3) 場景檔（USD）

腳本內目前有硬編碼路徑，例如：

```python
warehouse_usd_path = r"D:\project_isaac\1.usd"
```

請先改成你的實際 USD 檔案路徑。

---

## 安裝與啟動教學（建議順序）

### 步驟 A：安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 步驟 B：啟動後端 + 前端

Windows 可直接雙擊：

- `start_server.bat`

或手動執行：

```bash
python -m uvicorn dashboard_server:app --reload --host 127.0.0.1 --port 8000
```

啟動後打開瀏覽器：

- <http://127.0.0.1:8000>

### 步驟 C：在 Isaac Sim 執行腳本

建議先執行 `finish.py`（主版本），確認以下可正常運作：

- 場景成功載入
- forklift 路徑辨識成功
- 等待 `/api/start` 後開始移動
- 位姿可回傳前端

### 步驟 D：在前端觸發任務

1. 在「指令」輸入框輸入任意內容
2. 按「開始執行」
3. 觀察地圖中叉車移動與姿態更新

---

## 可調參數（建議優先調整）

在 `finish.py` / `avg.py` 中常見可調項：

- `warehouse_usd_path`：USD 場景路徑
- `start_pos`：叉車起始位置
- `target_pos` 或區域中心偏移：最終停車點
- `max_speed`：最大速度
- `max_angular_velocity`：最大角速度
- `obstacle_detection_distance`：障礙物檢測距離
- `avoidance_distance`：繞行距離
- `safety_radius`：安全半徑
- `stop_distance`：到達判定距離
- `max_run_time`：超時保護

