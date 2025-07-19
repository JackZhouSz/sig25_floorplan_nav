#!/usr/bin/env python3
"""
建立或更新 grid_types.json 的腳本。
掃描 grid.json 中所有的 type，確保每個 type 都有對應的 metadata。
"""

import json
from pathlib import Path

def build_type_metadata():
    # 路徑設定
    data_dir = Path("data")
    grid_file = data_dir / "grid.json"
    types_file = data_dir / "grid_types.json"
    
    # 讀取現有的 grid.json
    print(f"讀取 {grid_file}...")
    with open(grid_file, 'r', encoding='utf-8') as f:
        cells = json.load(f)
    
    # 收集所有的 type
    all_types = set()
    for cell in cells:
        if 'type' in cell and cell['type']:
            all_types.add(cell['type'])
    
    print(f"發現 {len(all_types)} 種類型: {sorted(all_types)}")
    
    # 讀取現有的 types 檔案（如果存在）
    existing_types = {}
    if types_file.exists():
        print(f"讀取現有的 {types_file}...")
        with open(types_file, 'r', encoding='utf-8') as f:
            existing_types = json.load(f)
    
    # 預設值設定
    default_metadata = {
        "description": "",
        "is_walkable": False,
        "cost": 1.0
    }
    
    # 特殊類型的預設值
    walkable_types = {
        "road": True,
        "exp hall": True,
        "Lounge": True
    }
    
    # 為每個 type 建立或更新 metadata
    updated_types = {}
    for type_name in sorted(all_types):
        if type_name in existing_types:
            # 更新現有的 metadata
            metadata = existing_types[type_name].copy()
            
            # 確保必要欄位存在
            if "cost" not in metadata:
                metadata["cost"] = 1.0
            if "is_walkable" not in metadata:
                metadata["is_walkable"] = walkable_types.get(type_name, False)
            if "description" not in metadata:
                metadata["description"] = f"描述 {type_name} 類型的區域。"
            if "display_color" not in metadata:
                metadata["display_color"] = ""
        else:
            # 建立新的 metadata
            metadata = default_metadata.copy()
            metadata["description"] = f"描述 {type_name} 類型的區域。"
            metadata["is_walkable"] = walkable_types.get(type_name, False)
            print(f"新增類型: {type_name}")
        
        updated_types[type_name] = metadata
    
    # 寫回檔案
    print(f"寫入 {types_file}...")
    with open(types_file, 'w', encoding='utf-8') as f:
        json.dump(updated_types, f, ensure_ascii=False, indent=4)
    
    print("完成！")
    
    # 顯示統計資訊
    walkable_count = sum(1 for meta in updated_types.values() if meta["is_walkable"])
    print(f"\n統計資訊:")
    print(f"  總類型數: {len(updated_types)}")
    print(f"  可行走類型: {walkable_count}")
    print(f"  障礙類型: {len(updated_types) - walkable_count}")

if __name__ == "__main__":
    build_type_metadata() 