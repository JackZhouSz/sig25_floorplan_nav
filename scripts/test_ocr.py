#!/usr/bin/env python3
"""
OCR 功能測試腳本
用於快速測試 OCR 模組的基本功能
"""

import sys
import os
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.grid import load_grid
from core.ocr_ollama import OllamaOCR


def test_connection():
    """測試 Ollama 連線"""
    print("測試 Ollama 連線...")
    ocr = OllamaOCR()
    print("✓ Ollama 連線測試完成")


def test_grid_loading():
    """測試格子資料載入"""
    print("\n測試格子資料載入...")
    cells = load_grid()
    print(f"✓ 成功載入 {len(cells)} 個格子")
    
    # 統計格子類型
    type_counts = {}
    for cell in cells:
        type_counts[cell.type] = type_counts.get(cell.type, 0) + 1
    
    print("格子類型統計:")
    for cell_type, count in sorted(type_counts.items()):
        print(f"  {cell_type}: {count} 個")
    
    return cells


def test_single_ocr(cells):
    """測試單個格子的 OCR 識別"""
    print("\n測試單個格子 OCR 識別...")
    
    # 找到第一個 booth 類型的格子
    booth_cells = [cell for cell in cells if cell.type == "booth"]
    if not booth_cells:
        print("❌ 沒有找到 booth 類型的格子")
        return
    
    test_cell = booth_cells[0]
    print(f"測試格子 {test_cell.idx} (位置: {test_cell.x}, {test_cell.y})")
    
    ocr = OllamaOCR()
    
    # 測試圖片裁切
    crop_path = ocr.crop_cell_image(test_cell)
    if crop_path:
        print(f"✓ 圖片裁切成功: {crop_path}")
    else:
        print("❌ 圖片裁切失敗")
        return
    
    # 測試 OCR 識別
    result = ocr.recognize_cell(test_cell)
    if result.error:
        print(f"❌ OCR 識別失敗: {result.error}")
    else:
        print(f"✓ OCR 識別成功:")
        print(f"  名稱: {result.name}")
        print(f"  編號: {result.booth_id}")
        print(f"  信心度: {result.confidence:.2f}")


def test_batch_ocr(cells, limit=3):
    """測試批次 OCR 處理"""
    print(f"\n測試批次 OCR 處理 (限制 {limit} 個格子)...")
    
    # 找到前幾個 booth 類型的格子
    booth_cells = [cell for cell in cells if cell.type == "booth"][:limit]
    if not booth_cells:
        print("❌ 沒有找到 booth 類型的格子")
        return
    
    print(f"將處理 {len(booth_cells)} 個格子")
    
    ocr = OllamaOCR()
    results = ocr.process_cells(booth_cells)
    
    print(f"✓ 批次處理完成，結果:")
    for idx, result in results.items():
        if result.error:
            print(f"  格子 {idx}: ❌ {result.error}")
        else:
            print(f"  格子 {idx}: ✓ '{result.name}' (信心度: {result.confidence:.2f})")


def main():
    """主函數"""
    print("OCR 功能測試")
    print("=" * 40)
    
    try:
        # 測試連線
        test_connection()
        
        # 測試格子載入
        cells = test_grid_loading()
        
        # 詢問是否進行 OCR 測試
        print("\n是否進行 OCR 測試? 這將需要 Ollama 服務運行中...")
        response = input("繼續測試? (y/N): ")
        
        if response.lower() != 'y':
            print("跳過 OCR 測試")
            return
        
        # 測試單個 OCR
        test_single_ocr(cells)
        
        # 詢問是否進行批次測試
        print("\n是否進行批次 OCR 測試?")
        response = input("這可能需要幾分鐘時間 (y/N): ")
        
        if response.lower() == 'y':
            test_batch_ocr(cells)
        
        print("\n✅ 所有測試完成!")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 