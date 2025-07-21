# 展場地圖導航專案

## 🎯 系統示範

### 導航範例：從攤位 52 到攤位 1

**路徑視覺化呈現：**

![導航路徑視覺化](result_f10/booth/viz_52_to_1.png)

**生成的導航指令（中文）：**

```
=== 從攤位 52 到攤位 1 的導航指令 ===

總距離: 46.0 units
約等於: 18 個攤位
總步驟: 7

導航指令:
1. 面向Abstract Group攤位，準備出發。
2. 直走經過右手邊的XIMEA、XGRIDS、Connection Lounge，約 3 個攤位。
3. 走到Connection Lounge前右轉。
4. 直走經過左手邊的Odyssey，走至Bria Visual AI Platform前，約 2 個攤位。
5. 走到Bria Visual AI Platform前左轉。
6. 直走經過右手邊的SKY ENGINE AI。
7. 目的地就在前方的 Luma AI。
```

這個範例展示了：
- **精確路徑視覺化**：清楚的路徑視覺化，標示起點與終點
- **自然語言指令**：人性化的中文導航，包含地標參考
- **語意一致性**：攤位數量與地標描述一致（如「約 3 個攤位」對應 3 個地標）
- **空間感知能力**：基於移動分析的準確左右前方向判斷

---

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
-   [x] **路徑計算**: 已實作 A* 演算法 (`core/pathfinder.py`) 與批次預運算腳本 (`scripts/precompute_routes.py`)。
-   [x] **路徑可視化**: 新增視覺化模組 (`core/viz.py`) 與輔助腳本 (`scripts/visualize_routes.py`, `scripts/batch_visualize.py`)。
-   [] **文字導航生成**: 將路徑轉換為自然語言的導航指令，支援覆蓋率導向的地標選擇與中文自然語言生成。

> 詳細的技術規劃與歷史進度請參閱：[`task.md`](./task.md)

---

## 📸 前置步驟 (資料準備)

在開始建立網格前，我們需要從線上地圖獲取原始的展位數據。

1.  **錄影線上地圖**: 在網頁上錄製地圖影片，並逐一 hover 過所有展位，使其 highlight。
    > **注意**: 地圖可能太大，需要分多次錄影來涵蓋所有區域。
    
    **錄影範例：**
    
    ![Hover 錄影示範](assets/input_video.gif)
    
    *示範 hover 錄影，展示攤位高亮偵測過程*

2.  **處理單個影片**: 使用 `notebooks/single_detect.ipynb` 處理每個錄製的影片，將影片中所有 highlight 的展位區域轉換為在地圖大圖上的網格框 (grid box)，並將結果儲存為 `bboxed_{i}.json`。
    ```
    notebooks/single_detect.ipynb
    ```

3.  **合併與計算網格單位**: 使用 `notebooks/01_build_grid.ipynb` 合併來自多個影片的網格框數據，並計算出統一的網格單位。這將生成 `data/grid.json` 作為主要的網格資料來源。
    ```
    notebooks/01_build_grid.ipynb
    ```

4.  **提取攤位詳細資訊 (可選)**: 從線上展覽目錄中提取額外的參展商資訊，以增強導航內容。
    
    **流程：**
    1. 造訪 `https://siggraph25.mapyourshow.com/8_0/explore/exhibitor-gallery.cfm`
    2. 展開所有參展商以顯示完整清單
    3. 將 HTML 頁面儲存為 `booth.html`
    4. 執行攤位詳細資訊提取腳本：
    ```bash
    # 從 HTML 解析基本攤位資料
    python scripts/booth_detail/parse_booth_data.py
    
    # 取得詳細描述與分類資訊
    python scripts/booth_detail/fetch_booth_details.py
    ```
    
    **輸出**: `booth_data_detailed.json` 包含所有 92+ 家參展商的攤位名稱、網址、描述與分類。
    
    > 詳細使用方法請見 [`scripts/booth_detail/README.md`](scripts/booth_detail/README.md)

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

### 步驟 3: 路徑計算與預運算（Path-finding 2.0）

路徑計算模組已升級為 **Path-finding 2.0**，提供更彈性且精確的路徑搜尋：
-   **多邊界候選 A***：不再只取單一入口，演算法會自動考慮 booth 所有可行走邊界，找出最佳路徑。
-   **可參數化移動**：支援 4 向（預設）與 8 向（斜向）移動。
-   **轉彎成本**：可設定每次轉彎的額外成本（預設為 0），讓路徑更直。

```bash
# 批次預運算：從指定展位到所有展位（可加參數）
# --allow-diag：啟用 8 向移動
# --turn-weight：設定轉彎成本
python scripts/precompute_routes.py --start 1 --allow-diag
```

### 步驟 4: 路徑可視化（NEW）

1. **快速預覽（生成少量路徑）**
   ```bash
   python scripts/visualize_routes.py routes/1_to_all.json --limit 3
   ```
2. **完整生成（依類型分組，推薦）**
   ```bash
   python scripts/batch_visualize.py routes/1_to_all.json --show-stats
   ```
   - 輸出至 `visualizations_by_type/{type}/viz_{src}_to_{dst}.png`
   - 全域格子以 30 % 透明度顯示，起 / 終點格子 60 % 不透明度高亮

### 步驟 5: 自然語言導航生成（NEW）

系統已支援將路徑轉換為符合中文使用習慣的自然語言導航指引：

1. **單一路徑導航生成**
   ```bash
   python scripts/generate_navigation.py --start 52 --end 10
   ```

2. **批次導航生成**
   ```bash
   python scripts/generate_navigation.py --start 52 --batch
   ```

3. **自訂配置導航**
   ```bash
   python scripts/generate_navigation.py --start 52 --end 10 --config config/high_precision.yaml
   ```

**導航特色**:
- **覆蓋率導向地標選擇**: 確保「經過」的地標確實在路徑上有足夠可見度
- **序列攤位計數**: 攤位數量與地標描述保持語意一致
- **智能距離分級**: 
  - ≤3單位: 「走過2個攤位」
  - 4-15單位: 「直走經過左手邊的Art Gallery，約5個攤位」
  - >15單位: 「直走經過前方的Maxon、Blender、Puget Systems，約2分鐘」

### 步驟 6: 自動化執行

為方便操作，專案提供 `run_routes.bat` 批次腳本，可一鍵完成路徑預運算與視覺化：

```bat
:: 預設起點 1，預設資料夾
run_routes.bat 1

:: 指定起點 52，輸出到 my_output 資料夾，並啟用斜向移動
run_routes.bat 52 my_output true
```
> 詳細參數與用法請參閱 `run_routes.bat` 內註解。

> 其他參數（`--crop-padding`, `--route-color`, `--line-width`, `--uniform-color` 等）可透過 `-h` 查看說明。

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

-   [**系統架構文檔** (`arch.md`)](./arch.md): 完整的系統架構說明，包含設計理念、技術決策和實作邏輯。
-   [**技術任務與規劃** (`task.md`)](./task.md): 深入了解每個模組的設計細節、資料流與歷史進度。
-   [**OCR 模組使用手冊** (`docs/OCR_USAGE.md`)](./docs/OCR_USAGE.md): 包含 OCR 模組的詳細參數設定、故障排除與進階用法。

## 🌟 系統特色

### 導航品質改進
- **覆蓋率系統**: 解決傳統系統中「說5個攤位但只提到2個地標」的語意不一致問題
- **序列計數**: 攤位數量直接對應地標序列，確保描述準確
- **智能地標選擇**: 基於地標在路徑上的實際可見度選擇最佳描述

### 技術亮點
- **多源多標A***: 支援多入口攤位的最佳路徑計算
- **配置驅動**: YAML配置系統支援不同場景的參數調整
- **模組化架構**: 各組件獨立可測試，便於維護和擴展

## 📊 系統性能

- **路徑規劃成功率**: 100% (92/92條路徑)
- **OCR識別準確率**: >90%
- **導航文字自然度**: 通過人工評估，符合中文使用習慣

## 🔄 最新更新

### Phase 1.2 - 序列攤位計數系統
- 移除四方向路徑掃描邏輯，採用序列基礎計數
- 解決攤位數量與地標描述不一致問題
- 提升導航文字的語意準確性

範例改進:
- **改進前**: "直走經過左手邊的RapidPipeline，約5個攤位" (只提到1個地標，卻說5個攤位)
- **改進後**: "直走經過前方的RapidPipeline，約1個攤位" (數量與描述一致)