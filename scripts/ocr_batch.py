#!/usr/bin/env python3
"""
OCR 批次處理腳本
一次性處理所有需要 OCR 的格子，支援續傳和錯誤重試
"""

import argparse
import sys
import os
from pathlib import Path
import logging
from typing import List, Dict, Optional

# 添加項目根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.grid import load_grid, save_grid, Cell
from core.ocr_ollama import OllamaOCR, OCRResult

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ocr_batch.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO"):
    """設定日誌級別"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    logging.getLogger().setLevel(numeric_level)
    
    # 確保日誌目錄存在
    os.makedirs('logs', exist_ok=True)


def filter_cells_for_ocr(cells: List[Cell], target_types: List[str] = None, 
                        skip_processed: bool = True) -> List[Cell]:
    """
    過濾需要進行 OCR 的格子
    
    Args:
        cells: 所有格子
        target_types: 目標格子類型
        skip_processed: 是否跳過已處理的格子（已有 name 和 booth_id）
        
    Returns:
        需要進行 OCR 的格子列表
    """
    if target_types is None:
        target_types = ["booth", "unknown"]
    
    # 基本類型過濾
    filtered_cells = [cell for cell in cells if cell.type in target_types]
    
    if skip_processed:
        # 跳過已經有名稱的格子
        unprocessed_cells = []
        for cell in filtered_cells:
            if not cell.name or cell.name.strip() == "":
                unprocessed_cells.append(cell)
            else:
                logger.debug(f"跳過已處理的格子 {cell.idx}: {cell.name}")
        filtered_cells = unprocessed_cells
    
    return filtered_cells


def print_summary(cells: List[Cell], target_types: List[str] = None):
    """打印格子統計摘要"""
    if target_types is None:
        target_types = ["booth", "unknown"]
    
    total_cells = len(cells)
    target_cells = [cell for cell in cells if cell.type in target_types]
    processed_cells = [cell for cell in target_cells if cell.name and cell.name.strip()]
    unprocessed_cells = [cell for cell in target_cells if not cell.name or cell.name.strip() == ""]
    
    print("\n" + "="*50)
    print("格子統計摘要")
    print("="*50)
    print(f"總格子數: {total_cells}")
    print(f"目標類型格子數 ({', '.join(target_types)}): {len(target_cells)}")
    print(f"已處理格子數: {len(processed_cells)}")
    print(f"待處理格子數: {len(unprocessed_cells)}")
    print("="*50 + "\n")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="OCR 批次處理腳本")
    parser.add_argument("--model", default="qwen2.5vl:7b", help="Ollama 模型名稱")
    parser.add_argument("--types", nargs="+", default=["booth", "unknown"], 
                       help="要處理的格子類型")
    parser.add_argument("--source-image", default="large_map.png", 
                       help="來源圖片路徑")
    parser.add_argument("--grid-file", default="data/grid.json", 
                       help="格子資料檔案路徑")
    parser.add_argument("--output-dir", default="data", 
                       help="輸出目錄")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日誌級別")
    parser.add_argument("--force", action="store_true", 
                       help="強制重新處理所有格子（忽略已處理的）")
    parser.add_argument("--dry-run", action="store_true", 
                       help="模擬運行，不實際執行 OCR")
    parser.add_argument("--limit", type=int, default=None, 
                       help="限制處理的格子數量（用於測試）")
    parser.add_argument("--resume", action="store_true", 
                       help="從之前的 OCR 結果續傳")
    
    args = parser.parse_args()
    
    # 設定日誌
    setup_logging(args.log_level)
    
    try:
        # 載入格子資料
        logger.info(f"載入格子資料: {args.grid_file}")
        cells = load_grid(args.grid_file)
        if not cells:
            logger.error("無法載入格子資料")
            return 1
        
        # 打印統計摘要
        print_summary(cells, args.types)
        
        # 過濾需要處理的格子
        skip_processed = not args.force
        target_cells = filter_cells_for_ocr(cells, args.types, skip_processed)
        
        if not target_cells:
            logger.info("沒有需要處理的格子")
            return 0
        
        # 限制處理數量（用於測試）
        if args.limit:
            target_cells = target_cells[:args.limit]
            logger.info(f"限制處理數量: {args.limit}")
        
        logger.info(f"將處理 {len(target_cells)} 個格子")
        
        if args.dry_run:
            logger.info("模擬運行模式，列出待處理格子:")
            for i, cell in enumerate(target_cells[:10], 1):  # 只顯示前 10 個
                print(f"  {i}. 格子 {cell.idx} (類型: {cell.type}, 位置: {cell.x},{cell.y})")
            if len(target_cells) > 10:
                print(f"  ... 還有 {len(target_cells) - 10} 個格子")
            return 0
        
        # 確認處理
        if not args.force and len(target_cells) > 10:
            response = input(f"確定要處理 {len(target_cells)} 個格子嗎? (y/N): ")
            if response.lower() != 'y':
                logger.info("使用者取消處理")
                return 0
        
        # 建立 OCR 處理器
        logger.info(f"初始化 OCR 處理器，模型: {args.model}")
        ocr = OllamaOCR(model_name=args.model)
        
        # 載入之前的結果（如果有的話）
        ocr_results = {}
        if args.resume:
            ocr_results_file = os.path.join(args.output_dir, "ocr_results.json")
            if os.path.exists(ocr_results_file):
                ocr_results = ocr.load_ocr_results(ocr_results_file)
                logger.info(f"載入了 {len(ocr_results)} 個之前的 OCR 結果")
        
        # 過濾出需要重新處理的格子
        if args.resume and ocr_results:
            new_target_cells = []
            for cell in target_cells:
                if cell.idx not in ocr_results or ocr_results[cell.idx].error:
                    new_target_cells.append(cell)
                else:
                    logger.debug(f"跳過已有結果的格子 {cell.idx}")
            target_cells = new_target_cells
            logger.info(f"續傳模式：剩餘 {len(target_cells)} 個格子需要處理")
        
        if not target_cells:
            logger.info("沒有需要處理的格子（續傳模式）")
            return 0
        
        # 執行 OCR 處理
        logger.info("開始 OCR 批次處理...")
        try:
            new_results = ocr.process_cells(
                target_cells, 
                args.types, 
                args.source_image
            )
            
            # 合併結果
            ocr_results.update(new_results)
            
        except KeyboardInterrupt:
            logger.warning("使用者中斷處理，保存已完成的結果...")
        except Exception as e:
            logger.error(f"OCR 處理時發生錯誤: {e}")
            return 1
        
        # 保存 OCR 結果
        ocr_results_file = os.path.join(args.output_dir, "ocr_results.json")
        ocr.save_ocr_results(ocr_results, ocr_results_file)
        
        # 統計結果
        successful_results = sum(1 for r in ocr_results.values() if not r.error and r.name)
        failed_results = sum(1 for r in ocr_results.values() if r.error)
        empty_results = sum(1 for r in ocr_results.values() if not r.error and not r.name)
        
        logger.info(f"OCR 處理完成統計:")
        logger.info(f"  成功識別: {successful_results} 個")
        logger.info(f"  識別為空: {empty_results} 個")
        logger.info(f"  處理失敗: {failed_results} 個")
        
        # 更新格子資料
        if successful_results > 0:
            logger.info("更新格子資料...")
            updated_cells = ocr.update_grid_with_ocr_results(cells, ocr_results)
            
            # 保存更新後的格子資料
            backup_file = args.grid_file + ".backup"
            if os.path.exists(args.grid_file):
                import shutil
                shutil.copy2(args.grid_file, backup_file)
                logger.info(f"已備份原始格子資料: {backup_file}")
            
            save_grid(updated_cells, args.grid_file)
            logger.info(f"已更新格子資料: {args.grid_file}")
        
        # 生成處理報告
        report_file = os.path.join(args.output_dir, "ocr_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("OCR 批次處理報告\n")
            f.write("=" * 30 + "\n\n")
            f.write(f"處理時間: {logger.handlers[0].formatter.formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}\n")
            f.write(f"使用模型: {args.model}\n")
            f.write(f"來源圖片: {args.source_image}\n")
            f.write(f"處理類型: {', '.join(args.types)}\n\n")
            f.write(f"總處理格子數: {len(ocr_results)}\n")
            f.write(f"成功識別: {successful_results} 個\n")
            f.write(f"識別為空: {empty_results} 個\n")
            f.write(f"處理失敗: {failed_results} 個\n\n")
            
            if failed_results > 0:
                f.write("處理失敗的格子:\n")
                for idx, result in ocr_results.items():
                    if result.error:
                        f.write(f"  格子 {idx}: {result.error}\n")
                f.write("\n")
            
            if successful_results > 0:
                f.write("成功識別的格子:\n")
                for idx, result in ocr_results.items():
                    if not result.error and result.name:
                        f.write(f"  格子 {idx}: {result.name}")
                        if result.booth_id:
                            f.write(f" (ID: {result.booth_id})")
                        f.write(f" [信心度: {result.confidence:.2f}]\n")
        
        logger.info(f"處理報告已保存: {report_file}")
        logger.info("OCR 批次處理完成!")
        
        return 0
        
    except Exception as e:
        logger.error(f"程式執行失敗: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 