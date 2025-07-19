import json
import os
import sys

# 將專案根目錄加到 Python 路徑中
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.grid import load_grid

def build_type_metadata(grid_path="data/grid.json", type_meta_path="data/grid_types.json"):
    """
    掃描 grid.json 中的所有 type，並更新/建立 type_metadata.json。
    """
    cells = load_grid(grid_path)
    if not cells:
        print(f"錯誤：找不到 {grid_path} 或檔案為空，無法建立 type metadata。")
        return

    # 1. 收集 grid.json 中所有的 unique types
    unique_types = set()
    for cell in cells:
        unique_types.add(cell.type)

    print(f"從 {grid_path} 掃描到以下 unique types: {unique_types}")

    # 2. 載入現有的 type_metadata.json (如果存在)
    existing_metadata = {}
    if os.path.exists(type_meta_path):
        try:
            with open(type_meta_path, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
            print(f"成功載入現有的 type metadata 從 {type_meta_path}。")
        except json.JSONDecodeError:
            print(f"警告：{type_meta_path} 檔案格式錯誤，將會重新建立。")
            existing_metadata = {}
    else:
        print(f"{type_meta_path} 不存在，將建立新檔案。")

    # 3. 合併新舊資料
    # 遍歷所有 unique_types，如果不存在於 existing_metadata，則新增，
    # 否則保持現有資訊不變。
    updated_metadata = existing_metadata.copy() # 保持原有資料
    for cell_type in unique_types:
        if cell_type not in updated_metadata:
            # 新增 type，給予預設值
            updated_metadata[cell_type] = {
                "description": f"描述 {cell_type} 類型的區域。",
                "is_walkable": True if cell_type == "walkway" else False, # 預設 walkway 可走
                "display_color": "" # 可以從 grid.py 的 def_colors 拿，但這裡先留空
            }
            print(f"新增類型 '{cell_type}' 到 metadata。")
        else:
            print(f"類型 '{cell_type}' 已存在於 metadata，保持不變。")

    # 4. 儲存更新後的 type_metadata.json
    try:
        with open(type_meta_path, 'w', encoding='utf-8') as f:
            json.dump(updated_metadata, f, indent=4, ensure_ascii=False)
        print(f"\n成功更新 type metadata 到 {type_meta_path}。")
    except Exception as e:
        print(f"儲存 type metadata 到 {type_meta_path} 時發生錯誤: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build or update type metadata from grid.json.")
    parser.add_argument("--grid", default="data/grid.json", help="Path to the grid JSON file.")
    parser.add_argument("--output", default="data/grid_types.json", help="Path to the output type metadata JSON file.")
    args = parser.parse_args()
    
    build_type_metadata(args.grid, args.output) 