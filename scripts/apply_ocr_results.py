#!/usr/bin/env python3
"""
將人工修正後的 OCR 結果套用回 grid.json 的腳本。
"""

import argparse
import sys
import os
import shutil
from pathlib import Path
import logging

# 添加項目根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.grid import load_grid, save_grid
from core.ocr_ollama import OllamaOCR # 引入 OllamaOCR 以使用其中的更新邏輯

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="將人工修正後的 OCR 結果套用回 grid.json。")
    parser.add_argument("--grid-file", default="data/grid.json", 
                       help="要更新的 grid.json 檔案路徑")
    parser.add_argument("--ocr-results-file", default="data/ocr_results.json", 
                       help="人工修正後的 OCR 結果檔案路徑")
    parser.add_argument("--backup", action="store_true", 
                       help="在更新前備份原始的 grid.json 檔案")
    
    args = parser.parse_args()
    
    try:
        # 載入原始格子資料
        logger.info(f"載入原始格子資料: {args.grid_file}")
        cells = load_grid(args.grid_file)
        if not cells:
            logger.error(f"無法載入格子資料，請檢查檔案是否存在: {args.grid_file}")
            return 1
        
        # 載入人工修正後的 OCR 結果
        logger.info(f"載入人工修正後的 OCR 結果: {args.ocr_results_file}")
        ocr_processor = OllamaOCR(check_connection=False) # 實例化時不檢查連線
        ocr_results = ocr_processor.load_ocr_results(args.ocr_results_file)
        
        if not ocr_results:
            logger.warning("沒有載入任何 OCR 結果，無需更新 grid.json。")
            return 0
            
        # 檢查載入的 OCR 結果概況
        null_name_count = sum(1 for r in ocr_results.values() if not r.name or r.name.strip() == "")
        null_booth_id_count = sum(1 for r in ocr_results.values() if not r.booth_id or str(r.booth_id).strip() == "")
        error_count = sum(1 for r in ocr_results.values() if r.error)
        
        if null_name_count > 0:
            logger.info(f"載入的 OCR 結果中，有 {null_name_count} 個格子的 'name' 欄位為空或 null。")
        if null_booth_id_count > 0:
            null_booth_ids = [idx for idx, r in ocr_results.items() if not r.booth_id or str(r.booth_id).strip() == ""]
            logger.warning(
                f"警告：載入的 OCR 結果中，有 {null_booth_id_count} 個格子的 'booth_id' 欄位為空或 null。\n"
                f"受影響的格子 idx: {null_booth_ids}"
            )
        if error_count > 0:
            logger.warning(f"警告：載入的 OCR 結果中，有 {error_count} 個格子存在識別錯誤 (error 欄位不為 null)。")
        
        logger.info(f"共載入 {len(ocr_results)} 個 OCR 結果，將嘗試套用至 grid.json。")

        # 備份原始 grid.json (如果指定)
        if args.backup:
            backup_path = args.grid_file + ".bak"
            shutil.copy2(args.grid_file, backup_path)
            logger.info(f"已備份原始 grid.json 到: {backup_path}")
            
        # 使用 OCR 模組的邏輯更新格子資料
        logger.info("開始將 OCR 結果套用回格子資料...")
        updated_cells = ocr_processor.update_grid_with_ocr_results(cells, ocr_results)
        
        # 保存更新後的格子資料
        save_grid(updated_cells, args.grid_file)
        logger.info(f"已成功將 OCR 結果套用回: {args.grid_file}")
        logger.info("更新完成!")
        
    except FileNotFoundError as e:
        logger.error(f"檔案未找到: {e}")
        return 1
    except Exception as e:
        logger.error(f"執行失敗: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 