# 展場地圖導航專案

本專案旨在建立一個展場地圖的數位化解決方案，最終目標是能提供從特定起點（如 Dell booth）到其他展位或區域的文字導航。

## 專案目標與前提

-   **目標**: 建立一個數位化的展場地圖，提供展位間的文字導航。
-   **前提**:
    -   原始地圖 (https://siggraph25.mapyourshow.com/8_0/exhview/index.cfm) 為網路 Canvas Render 格式，無法直接提取展位資訊。
    -   該地圖 Canvas 在 Hover 會 Hightlight booth，利用這特性偵測
    -   地圖上的展位佈局是網格對齊的。
    -   利用電腦視覺 (CV) 與光學字元辨識 (OCR) 技術來解析地圖。

## ✨ 任務進度 (TODOs)

-   [x] **網格建立與管理**: 將地圖轉換為結構化的網格資料 (`data/grid.json`)。
-   [x] **手動標註工具**: 提供 GUI 工具 (`core/annotate.py`) 進行人工新增、修改、刪除網格。
-   [x] **OCR 資訊擷取**: 自動識別展位名稱與編號，並填入網格資料中。
-   [ ] **路徑計算**: 開發尋路演算法 (如 A*)，計算展位間的路徑。
-   [ ] **路徑可視化**: 將計算出的路徑繪製在地圖上。
-   [ ] **文字導航生成**: 將路徑轉換為自然語言的導航指令。

> 詳細的技術規劃與歷史進度請參閱：[`task.md`](./task.md)

---

## 📸 前置步驟 (資料準備)

在開始建立網格前，我們需要從線上地圖獲取原始的展位數據。

1.  **錄影線上地圖**: 在網頁上錄製地圖影片，並逐一 hover 過所有展位，使其 highlight。
    > **注意**: 地圖可能太大，需要分多次錄影來涵蓋所有區域。

2.  **處理單個影片**: 使用 `notebooks/single_detect.ipynb` 處理每個錄製的影片，將影片中所有 highlight 的展位區域轉換為在地圖大圖上的網格框 (grid box)，並將結果儲存為 `bboxed_{i}.json`。
    ```
    notebooks/single_detect.ipynb
    ```

3.  **合併與計算網格單位**: 使用 `notebooks/01_build_grid.ipynb` 合併來自多個影片的網格框數據，並計算出統一的網格單位。這將生成 `data/grid.json` 作為主要的網格資料來源。
    ```
    notebooks/01_build_grid.ipynb
    ```

---

## 🚀 主要工作流程

本專案的工作流程設計為幾個獨立但環環相扣的步驟，讓您可以循序漸進地從一張地圖圖片，最終產出完整的導航資訊。

### 步驟 1: 建立與修正網格
在完成前置步驟生成初始網格數據後，使用手動工具進行精細調整與補充。

1.  **手動標註與修正**: 使用 GUI 工具進行精細調整。這是確保資料品質最關鍵的一步。
    ```bash
    python core/annotate.py
    ```
    -   **操作**: 滑鼠左鍵拖曳新增格子，右鍵點擊進行修改或刪除。
    -   **目標**: 確保所有展位、走道、公共區域都被正確標記。

2.  **建立類型元數據**: 掃描 `grid.json` 中已有的 `type` 欄位，自動建立或更新 `data/grid_types.json`。
    ```bash
    python scripts/build_type_metadata.py
    ```
    > **重要**: `data/grid_types.json` 定義了每種格子的屬性（如是否可行走、顯示顏色等），是路徑計算的基礎，請務必在開始 OCR 或路徑計算前執行此步驟。

### 步驟 2: 執行 OCR 識別
網格建立完成後，執行 OCR 來自動填寫展位名稱與編號。

1.  **執行批次 OCR**: 此腳本會處理所有需要識別的格子。
    ```bash
    python scripts/ocr_batch.py
    ```
    > **提示**: 首次執行或格子數量多時，此過程可能需要一些時間。腳本支援 `--limit` 參數進行測試。

2.  **人工審核與修正**:
    -   開啟 `data/ocr_results.json` 檔案。
    -   人工檢查並修正模型識別錯誤的 `name` 或 `booth_id`。

3.  **套用修正結果**: 將修正後的結果寫回主要的 `grid.json` 檔案。
    ```bash
    python scripts/apply_ocr_results.py --backup
    ```

> 關於 OCR 模組更詳細的說明，請參閱：[`docs/OCR_USAGE.md`](./docs/OCR_USAGE.md)

---

## 🔧 環境安裝

1.  **複製專案**:
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **安裝 Python 依賴**:
    建議使用虛擬環境 (如 `venv` 或 `conda`)。
    ```bash
    # 建立虛擬環境
    python -m venv venv
    # 啟用虛擬環境
    source venv/bin/activate  # on Windows: venv\Scripts\activate
    
    # 安裝核心依賴
    pip install opencv-python numpy Pillow
    ```

3.  **安裝與設定 Ollama (OCR 功能所需)**:
    ```bash
    # 1. 安裝 Ollama (若尚未安裝)
    curl -fsSL https://ollama.com/install.sh | sh

    # 2. 啟動 Ollama 服務 (通常會自動啟動)
    ollama serve

    # 3. 下載 OCR 所需的視覺模型
    ollama pull qwen2.5vl:7b
    
    # 4. 安裝 Ollama Python 客戶端
    pip install ollama
    ```

## 📚 詳細文件

-   [**技術任務與規劃** (`task.md`)](./task.md): 深入了解每個模組的設計細節、資料流與歷史進度。
-   [**OCR 模組使用手冊** (`docs/OCR_USAGE.md`)](./docs/OCR_USAGE.md): 包含 OCR 模組的詳細參數設定、故障排除與進階用法。