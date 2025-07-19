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
1.  **建立成本地圖**：
    -   讀取 `grid.json`，將其轉換為 2D 的可行走矩陣 (`occupancy matrix`)。
    -   `walkway` 為可走，`booth`, `stage` 等為障礙物。
    -   `area` 型別可透過參數 (`allow_enter_area`) 設定是否可穿越。
2.  **尋路演算法**：
    -   使用 A* 或 BFS 演算法計算指定起點 `idx` 到終點 `idx` 的最短路徑。
3.  **路徑語意標註**：
    -   對計算出的路徑（一系列 `Cell`）進行標註：
        -   `through`: 實際路徑**穿越**的格子。
        -   `pass_by`: 路徑**旁邊相鄰**的格子（地標）。
        -   `start` / `end`: 起點與終點。

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
   - `data/grid_types.json`：type metadata（description / is_walkable / display_color）
4. **OCR 模組 (新增)**
   - `core/ocr_ollama.py`：使用 Ollama qwen2.5vl:7b 進行 booth 資訊識別
   - `scripts/ocr_batch.py`：批次處理腳本，支援續傳和錯誤重試
   - `scripts/test_ocr.py`：OCR 功能測試腳本
   - `docs/OCR_USAGE.md`：完整使用說明文檔

## 後續實作方向
1. ~~OCR 模組（Ollama Vision + JSON Schema）~~ ✅ **已完成**
   - ~~讀取 `crops/`，自動填 `name`、`booth_id`~~ ✅
   - ~~失敗項目進 GUI 快速修正~~ (可通過批次腳本處理)
2. Path-finding
   - 依 `grid_types.json` 的 `is_walkable` 決定可走區域
   - A* / BFS，預先計算 Dell → 其他 booth 路徑
3. 自然語言導航
   - 先以模板，之後可接 LLM
4. 視覺化
   - `core/viz.py`: 顯示路徑、經過地標
5. 進一步優化
   - `grid_types.json` 增加顏色配置，供 overlay 使用
   - Scripts 自動同步 def_colors → type metadata 