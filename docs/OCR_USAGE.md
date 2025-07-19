# OCR 模組使用說明

## 概述

OCR 模組使用 Ollama 的 `qwen2.5vl:7b` 視覺語言模型，自動識別展場地圖中的 booth 名稱和編號。支援 JSON Schema 輸出，確保結構化資料品質。

## 功能特點

- 🎯 **精準識別**: 專門針對展場地圖 booth 資訊最佳化
- 📄 **JSON Schema**: 結構化輸出，確保資料一致性
- 🔧 **批次處理**: 支援大量格子的批次 OCR 識別
- 💾 **續傳功能**: 支援中斷後續傳處理
- 🖼️ **圖片優化**: 自動優化圖片以提高識別效果
- 📊 **詳細報告**: 生成完整的處理報告

## 系統需求

### 必要條件

1. **Ollama 服務**: 需要本地運行 Ollama 服務
2. **qwen2.5vl:7b 模型**: 確保已下載此模型
3. **Python 依賴**:
   - `ollama` - Ollama Python 客戶端
   - `opencv-python` - 圖片處理
   - `numpy` - 數值計算
   - `Pillow` - 圖片操作

### 安裝步驟

```bash
# 1. 安裝 Ollama (如果尚未安裝)
curl -fsSL https://ollama.com/install.sh | sh

# 2. 下載 qwen2.5vl:7b 模型
ollama pull qwen2.5vl:7b

# 3. 安裝 Python 依賴
pip install ollama opencv-python numpy Pillow

# 4. 驗證安裝
ollama list  # 確認模型已下載
```

## 使用方法

### 1. 快速測試

```bash
# 執行測試腳本，驗證功能
python scripts/test_ocr.py
```

### 2. 批次處理所有格子

```bash
# 處理所有 booth 和 unknown 類型格子
python scripts/ocr_batch.py

# 只處理 booth 類型格子
python scripts/ocr_batch.py --types booth

# 測試模式 (限制處理 5 個格子)
python scripts/ocr_batch.py --limit 5

# 模擬運行 (不實際執行 OCR)
python scripts/ocr_batch.py --dry-run
```

### 3. 進階用法

```bash
# 使用不同模型
python scripts/ocr_batch.py --model qwen2.5vl:3b

# 從指定結果續傳
python scripts/ocr_batch.py --resume

# 強制重新處理所有格子
python scripts/ocr_batch.py --force

# 自訂來源圖片
python scripts/ocr_batch.py --source-image my_map.png

# 詳細日誌
python scripts/ocr_batch.py --log-level DEBUG
```

## 程式化使用

### 基本使用

```python
from core.grid import load_grid
from core.ocr_ollama import OllamaOCR

# 載入格子資料
cells = load_grid()

# 建立 OCR 處理器
ocr = OllamaOCR(model_name="qwen2.5vl:7b")

# 處理指定格子
booth_cells = [cell for cell in cells if cell.type == "booth"]
results = ocr.process_cells(booth_cells[:10])  # 處理前 10 個

# 更新格子資料
updated_cells = ocr.update_grid_with_ocr_results(cells, results)
```

### 單個格子處理

```python
from core.ocr_ollama import OllamaOCR

ocr = OllamaOCR()

# 處理單個格子
cell = cells[0]  # 假設這是一個 booth 格子
result = ocr.recognize_cell(cell)

if not result.error:
    print(f"名稱: {result.name}")
    print(f"編號: {result.booth_id}")
    print(f"信心度: {result.confidence}")
```

## 輸出格式

### OCR 結果 JSON

```json
{
  "1": {
    "name": "Dell Technologies",
    "booth_id": "A01", 
    "confidence": 0.85,
    "error": null
  },
  "2": {
    "name": null,
    "booth_id": null,
    "confidence": 0.0,
    "error": "圖片裁切失敗"
  }
}
```

### 處理報告

批次處理完成後會生成詳細報告 (`data/ocr_report.txt`):

```
OCR 批次處理報告
==============================

處理時間: 2025-01-09 14:30:15
使用模型: qwen2.5vl:7b
來源圖片: large_map.png
處理類型: booth, unknown

總處理格子數: 150
成功識別: 125 個
識別為空: 18 個
處理失敗: 7 個

處理失敗的格子:
  格子 45: 圖片裁切失敗
  格子 78: 回應解析失敗

成功識別的格子:
  格子 1: Dell Technologies (ID: A01) [信心度: 0.85]
  格子 2: NVIDIA Corporation (ID: B12) [信心度: 0.92]
  ...
```

## 故障排除

### 常見問題

1. **Ollama 連線失敗**
   ```
   錯誤: Ollama 連線失敗: Connection refused
   解決: 確認 Ollama 服務正在運行: ollama serve
   ```

2. **模型不存在**
   ```
   錯誤: 模型 qwen2.5vl:7b 不在可用模型列表中
   解決: 下載模型: ollama pull qwen2.5vl:7b
   ```

3. **圖片讀取失敗**
   ```
   錯誤: 無法讀取圖片: large_map.png
   解決: 確認圖片檔案存在且格式正確
   ```

4. **記憶體不足**
   ```
   解決: 使用較小的模型如 qwen2.5vl:3b 或分批處理
   ```

### 效能優化

1. **調整批次大小**: 根據系統記憶體調整一次處理的格子數量
2. **使用續傳功能**: 大量資料時使用 `--resume` 避免重複處理
3. **選擇合適模型**: 
   - `qwen2.5vl:3b` - 較快但精度稍低
   - `qwen2.5vl:7b` - 平衡效能和精度 (推薦)
   - `qwen2.5vl:32b` - 最高精度但需要更多資源

## 配置選項

### 模型參數

在 `core/ocr_ollama.py` 中可調整：

```python
# JSON Schema 定義
self.json_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "booth_id": {"type": ["string", "null"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
    }
}

# 模型推理參數
options = {
    "temperature": 0.1,  # 一致性 (0.0-1.0)
    "top_p": 0.9        # 多樣性控制
}
```

### 圖片處理參數

```python
# 圖片裁切邊距
margin = 10

# 最小圖片尺寸 (會自動放大)
min_size = 200

# 信心度閾值 (低於此值不更新格子)
confidence_threshold = 0.3
```

## 注意事項

1. **首次使用**: 第一次下載模型可能需要較長時間
2. **網路需求**: 初始模型下載需要網路連線，但識別過程完全在本地進行
3. **處理時間**: 每個格子約需 2-10 秒，具體取決於硬體配置
4. **資料備份**: 批次處理會自動備份原始 `grid.json` 檔案

## 擴展功能

### 自訂 Prompt

可以修改 `system_prompt` 和 `user_prompt` 來適應特定需求：

```python
system_prompt = """你是專門識別某特定展會格子的 OCR 系統..."""
```

### 支援其他模型

```python
# 其他視覺模型
ocr = OllamaOCR(model_name="llava:7b")
ocr = OllamaOCR(model_name="bakllava:7b")
```

### 結果後處理

```python
# 自訂結果處理邏輯
def custom_post_process(result):
    if result.name:
        # 清理名稱格式
        result.name = result.name.strip().title()
    return result
``` 