import sys
import os

# 將專案根目錄加到 Python 路徑中
# 這樣 scripts 資料夾內的腳本才能正確 import core 模組
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

import json
from collections import defaultdict
from core.grid import load_grid, Cell

def check_grid_types(grid_path="data/grid.json", threshold=3):
    """
    檢查 grid.json 中各 type 的數量，並顯示數量少於閾值的 cell 資訊。
    """
    cells = load_grid(grid_path)
    if not cells:
        print(f"錯誤：找不到 {grid_path} 或檔案為空。")
        return

    type_counts = defaultdict(list)
    for cell in cells:
        type_counts[cell.type].append(cell)

    print(f"--- Grid Type 檢查報告 ({grid_path}) ---")
    for cell_type, cell_list in type_counts.items():
        count = len(cell_list)
        print(f"類型 '{cell_type}': 總計 {count} 個")

        if count < threshold:
            print(f"  注意：類型 '{cell_type}' 數量過少 (小於 {threshold} 個)。詳細資訊：")
            for cell in cell_list:
                name_info = f", Name: '{cell.name}'" if cell.name else ""
                print(f"    - Cell idx: {cell.idx} (Col: {cell.col}, Row: {cell.row}){name_info}")
    print("---------------------------------------")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check grid.json types and list details for low-count types.")
    parser.add_argument("--grid", default="../data/grid.json", help="Path to the grid JSON file.")
    parser.add_argument("--threshold", type=int, default=3, help="Threshold for listing detailed cell info.")
    args = parser.parse_args()
    
    check_grid_types(args.grid, args.threshold) 