## 模組化實作規劃

整體流程將以 Jupyter Notebook (`notebooks/01_workflow.ipynb`) 為主控，串接各個功能模組 (`core/*.py`)。所有核心邏輯都會寫在 `.py` 檔案中，方便重複使用與測試。

### 核心資料流
`bboxes_*.json` (偵測原始資料) -> `data/grid.json` (權威網格檔) -> `routes/*.json` (預運算路徑)

---

### 階段一：Grid 建立與管理 (`core/grid.py`)
1.  **合併與轉換**：
    -   讀取 `detect.ipynb` 產出的多個 `bboxes_*.json`。
    -   合併、去重後，轉換成統一的網格化資料結構。
    -   以自增的 `idx` 作為每個格子的唯一識別碼。
2.  **權威資料檔**：
    -   所有網格資料統一儲存於 `data/grid.json`。
    -   `Cell` 資料結構包含：`idx`, `col`, `row`, `(x,y,w,h)`, `type`, `name`, `booth_id`。
3.  **可視化**：
    -   提供 `overlay_grid()` 函式，能將 `grid.json` 的格線繪製在 `large_map.png` 上，並在 Notebook 中顯示。
    -   可根據 `type` 為不同格子自訂顏色。

### 階段二：手動標註與修正 (`core/annotate.py`)
-   基於 `select_bounding_box.py` 改寫的 GUI 工具。
-   **功能**：
    1.  **新增**：處理自動偵測遺漏的格子（如走道、特殊區塊），滑鼠框選後可手動指定 `type` 與 `name`。
    2.  **修改**：點擊現有格子，可修改其所有屬性。
    3.  **刪除**：移除錯誤的格子。
-   直接讀寫 `data/grid.json`，是確保資料品質的關鍵。

### 階段三：OCR (`core/ocr_ollama.py`)
-   **Ollama 整合**：
    -   針對 `type` 為 `booth` 或 `unknown` 的格子進行裁切 (`crops/cell_{idx}.png`)。
    -   呼叫 Ollama 視覺模型 (`gemma3n:e4b`) 進行 OCR。
    -   利用 Ollama 的 JSON Schema 功能，強制模型回傳結構化資料 (`{name: str, booth_id: str | None}`)，提升辨識穩定性。
-   **批次處理**：提供 `scripts/ocr_batch.py`，可一次性處理所有需要 OCR 的格子。

### 階段四：路徑計算 (`core/pathfinder.py`)
1.  **建立可行走 (walkable) 與成本 (cost) 矩陣**
    -   讀取 `data/grid.json`，依 `cell.type` 參照 `data/grid_types.json` 生成：
        * `walkable`: `np.ndarray[bool]` – `is_walkable=True` 為 True，其餘 False。
        * `cost`: `np.ndarray[float]` – 取 `grid_types.json.cost` 欄位，若缺省則預設 1.0。
    -   `allow_enter_area=True` 時，可將 `exp hall`、`stage` 等「大區域」暫時視為可行走並給予較高 cost。
    -   Cell 可能佔多個 unit (`unit_w`, `unit_h`)，需展開填入矩陣。

2.  **起點／終點映射策略**
    -   `booth` 自身視為障礙，但需計算路徑起終點：
        1. 先取 booth 幾何中心(unit 座標)。
        2. 以 8 向 BFS 搜尋最近 `walkable==True` 的 unit 作為實際 A* 起點／終點。
    -   預留未來多入口或手動 `entry_points` 擴充。

3.  **A* 尋路演算法 (支援斜向)**
    -   鄰接點採 8 向；若兩側直向格皆為障礙，該斜向移動無效 (corner-cutting)。
    -   移動成本 = 目標單元 `cost` × (直向 1 或斜向 √2)。
    -   回傳 `route`: Cell `idx` 序列 (含起終點) 及 `meta`: `{steps, length, total_cost}`。

4.  **批次 1 → All 預運算**
    -   `scripts/precompute_routes.py`：給定 `start_idx`，遍歷所有 `type=="booth"` 目標。
    -   共用鄰接表與成本矩陣，以 NumPy 加速多次 A* 計算。
    -   結果輸出 `routes/{start}_to_all.json`，含 `unreachable` 清單。

5.  **路徑語意標註**
    -   `through`: 路徑實際穿越的格子。
    -   `pass_by`: 與路徑相鄰且 `is_landmark=True` 之格子。
    -   `start` / `end`: 起點與終點格子。

### 階段五：可視化與導航 (`core/viz.py`)
-   **路徑繪製**：
    -   提供 `show_route()` 函式，將計算出的路徑與語意標註視覺化。
    -   在地圖上繪製路徑（連線）、`through` 格子（高亮）、`pass_by` 地標（外框）。
-   **文字導航**（未來實作）：
    -   根據語意標註的路徑，生成自然語言的導航指令。

## 目前進度 (2025-01-09)
1. Grid 建立
   - `data/grid.json`：完整格子資料 (pixel 與 grid 座標)
   - `data/grid_meta.json`：unit 大小與原點
2. 手動標註
   - `core/annotate.py`：支援縮放、平移、框選/刪除/編輯格子
3. 格子類型統計與維護
   - `scripts/check_grid_types.py`：列出各 type 數量，少於閾值詳細列出 idx/name
   - `scripts/build_type_metadata.py`：掃描 grid.json，自動建立/更新 `data/grid_types.json`
   - `data/grid_types.json`：type metadata（description / is_walkable / display_color / **cost**）
4. **OCR 模組** ✅ **已完成**
   - `core/ocr_ollama.py`：使用 Ollama qwen2.5vl:7b 進行 booth 資訊識別
   - `scripts/ocr_batch.py`：批次處理腳本，支援續傳和錯誤重試
   - `scripts/test_ocr.py`：OCR 功能測試腳本
   - `docs/OCR_USAGE.md`：完整使用說明文檔
5. **Path-finding 模組** ✅ **已完成**
   - `core/pathfinder.py`：完整的 A* 路徑計算模組，支援 8 向移動
   - `scripts/precompute_routes.py`：批次預運算腳本，從一點到所有 booth
   - `routes/1_to_all.json`：完整預運算結果（100% 成功率，92 條路徑）
   - **矩陣建立邏輯**：預設可行走，標記障礙物（`not walkable` 優先）
   - **RouteResult 結構**：同時提供語意路徑（Cell idx）和幾何路徑（unit 座標）
6. **Path-finding 2.0** ✅ **已完成**
   - 支援「多邊界候選」起點/終點，並實作 multi-source & multi-target A*。
   - `allow_diag` 參數化（預設為 `False`，僅 4 向移動）。
   - `turn_weight` 轉彎成本納入計算。
   - 新增 `PathfindingOptions` dataclass 統一管理路徑參數。
   - `find_route()` / `find_route_from_files()` 介面已調整。
   - `scripts/precompute_routes.py` 已更新以呼叫新 API。
7. **自動化腳本** ✅ **已完成**
   - 新增 `run_routes.bat` 批次檔，整合預運算與視覺化流程。

## 後續實作方向
1. **自然語言導航**
   - 先以模板，之後可接 LLM

---
_以下為已完成項目，僅供參考_
- **視覺化** ✅ **已完成**
  - `core/viz.py` 已提供強大的路徑繪製功能。
  - `scripts/batch_visualize.py` 支援按類型分組輸出和自訂顏色。 