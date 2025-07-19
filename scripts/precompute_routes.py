#!/usr/bin/env python3
"""
批次路徑預運算腳本

計算從指定起點到所有 booth 的路徑，並將結果保存到 routes/ 目錄。
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# 將專案根目錄加到 Python 路徑中
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.pathfinder import find_route, load_grid_types, PathfindingGrid
from core.grid import load_grid


def precompute_routes(
    start_idx: int,
    grid_path: str = "data/grid.json",
    grid_types_path: str = "data/grid_types.json",
    output_dir: str = "routes",
    allow_enter_area: bool = False
):
    """
    計算從 start_idx 到所有 booth 的路徑
    
    Args:
        start_idx: 起點 Cell idx
        grid_path: 網格資料檔案路徑
        grid_types_path: 網格類型定義檔案路徑
        output_dir: 輸出目錄
        allow_enter_area: 是否允許進入大區域
    """
    print(f"=== 批次路徑預運算：起點 {start_idx} ===")
    
    # 載入資料
    cells = load_grid(grid_path)
    if not cells:
        print(f"錯誤：無法載入 {grid_path}")
        return
    
    grid_types = load_grid_types(grid_types_path)
    
    # 建立 Cell 索引
    cell_by_idx = {cell.idx: cell for cell in cells}
    
    # 檢查起點是否存在
    if start_idx not in cell_by_idx:
        print(f"錯誤：起點 {start_idx} 不存在")
        return
    
    start_cell = cell_by_idx[start_idx]
    print(f"起點：Cell {start_idx} ({start_cell.name or start_cell.type}) at ({start_cell.col},{start_cell.row})")
    
    # 找到所有 booth 類型的目標
    booth_cells = [cell for cell in cells if cell.type == "booth" and cell.idx != start_idx]
    print(f"找到 {len(booth_cells)} 個目標 booth")
    
    # 建立路徑計算網格（共用以提升效率）
    pathfinding_grid = PathfindingGrid(cells, grid_types, allow_enter_area)
    
    # 預先計算起點的可行走位置
    start_pos = pathfinding_grid.find_walkable_near_booth(start_idx)
    if start_pos is None:
        print(f"錯誤：無法找到起點 {start_idx} 附近的可行走位置")
        return
    
    print(f"起點可行走位置：{start_pos}")
    
    # 結果收集
    results = {
        "start_idx": start_idx,
        "start_cell": {
            "idx": int(start_cell.idx),
            "type": start_cell.type,
            "name": start_cell.name,
            "position": (int(start_cell.col), int(start_cell.row))
        },
        "targets": {},
        "unreachable": [],
        "statistics": {
            "total_targets": len(booth_cells),
            "successful": 0,
            "failed": 0
        }
    }
    
    # 批次計算路徑
    print("\n開始計算路徑...")
    for i, target_cell in enumerate(booth_cells, 1):
        target_idx = target_cell.idx
        print(f"進度 [{i}/{len(booth_cells)}] 計算到 Cell {target_idx} ({target_cell.name or target_cell.type})", end="... ")
        
        try:
            # 找到目標的可行走位置
            end_pos = pathfinding_grid.find_walkable_near_booth(target_idx)
            if end_pos is None:
                print("無法找到可行走位置")
                results["unreachable"].append(target_idx)
                results["statistics"]["failed"] += 1
                continue
            
            # 執行 A* 搜尋
            path_result = pathfinding_grid.astar(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
            
            if path_result is None:
                print("無路徑")
                results["unreachable"].append(target_idx)
                results["statistics"]["failed"] += 1
            else:
                # 確保起終點包含在路徑中
                route = path_result.route[:]
                if start_idx not in route:
                    route.insert(0, start_idx)
                if target_idx not in route:
                    route.append(target_idx)
                
                results["targets"][str(target_idx)] = {
                    "route": [int(x) for x in route],  # 確保為Python int
                    "unit_path": [(int(x), int(y)) for x, y in path_result.unit_path],  # 轉換numpy類型
                    "steps": int(path_result.steps),
                    "length": round(float(path_result.length), 2),
                    "total_cost": round(float(path_result.total_cost), 2),
                    "target_info": {
                        "idx": int(target_cell.idx),
                        "type": target_cell.type,
                        "name": target_cell.name,
                        "position": (int(target_cell.col), int(target_cell.row))
                    }
                }
                results["statistics"]["successful"] += 1
                print(f"成功 ({path_result.steps} 步, 成本 {path_result.total_cost:.1f})")
                
        except Exception as e:
            print(f"錯誤: {e}")
            results["unreachable"].append(target_idx)
            results["statistics"]["failed"] += 1
    
    # 保存結果
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    output_file = output_path / f"{start_idx}_to_all.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 輸出統計
    print(f"\n=== 預運算完成 ===")
    print(f"成功路徑：{results['statistics']['successful']}")
    print(f"失敗路徑：{results['statistics']['failed']}")
    print(f"無法到達：{results['unreachable']}")
    print(f"結果已保存到：{output_file}")


def main():
    parser = argparse.ArgumentParser(description="批次計算從指定起點到所有booth的路徑")
    parser.add_argument("start_idx", type=int, help="起點 Cell idx")
    parser.add_argument("--grid", default="data/grid.json", help="網格資料檔案路徑")
    parser.add_argument("--grid-types", default="data/grid_types.json", help="網格類型定義檔案路徑")
    parser.add_argument("--output-dir", default="routes", help="輸出目錄")
    parser.add_argument("--allow-enter-area", action="store_true", help="允許進入大區域（如 exp hall）")
    
    args = parser.parse_args()
    
    precompute_routes(
        start_idx=args.start_idx,
        grid_path=args.grid,
        grid_types_path=args.grid_types,
        output_dir=args.output_dir,
        allow_enter_area=args.allow_enter_area
    )


if __name__ == "__main__":
    main() 