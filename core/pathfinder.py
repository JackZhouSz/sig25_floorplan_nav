#!/usr/bin/env python3
"""
路徑計算模組 (Path-finding Module)

提供基於 A* 演算法的路徑計算功能，支援：
- 建立 walkable 與 cost 矩陣
- 起點/終點映射策略
- 8 向 A* 尋路（支援斜向移動）
- 路徑語意標註
"""

import json
import numpy as np
import heapq
import sys
import os
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from pathlib import Path

# 將專案根目錄加到 Python 路徑中（供直接執行使用）
if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)

try:
    from .grid import Cell, load_grid, load_grid_meta
except ImportError:
    from core.grid import Cell, load_grid, load_grid_meta


@dataclass
class PathfindingOptions:
    """路徑計算選項配置"""
    allow_diag: bool = False        # 是否允許斜向移動（預設為 False，僅 4 向）
    turn_weight: float = 0.0        # 轉彎額外成本（預設 0，不加彎折成本）
    allow_enter_area: bool = False  # 是否允許進入大區域（沿用舊邏輯）


@dataclass
class RouteResult:
    """路徑計算結果"""
    route: List[int]                  # 語意路徑 (Cell idx 序列)
    unit_path: List[Tuple[int, int]]  # 幾何路徑 (unit 座標序列)
    steps: int                        # 總步數
    length: float                     # 幾何長度（unit 單位）
    total_cost: float                 # 加權總成本


class PathfindingGrid:
    """路徑計算網格類別"""
    
    def __init__(self, cells: List[Cell], grid_types: dict, options: PathfindingOptions = None):
        self.cells = cells
        self.grid_types = grid_types
        self.options = options or PathfindingOptions()
        
        # 向後相容性
        self.allow_enter_area = self.options.allow_enter_area
        
        # 建立 idx 到 Cell 的對應
        self.cell_by_idx = {cell.idx: cell for cell in cells}
        
        # 計算網格範圍
        self._calculate_grid_bounds()
        
        # 建立矩陣
        self.walkable, self.cost, self.cell_map = self._build_matrices()
    
    def _calculate_grid_bounds(self):
        """計算網格邊界"""
        all_cols = []
        all_rows = []
        
        for cell in self.cells:
            # 計算該 cell 佔據的所有 unit 格
            for dc in range(cell.unit_w):
                for dr in range(cell.unit_h):
                    all_cols.append(cell.col + dc)
                    all_rows.append(cell.row + dr)
        
        self.min_col = min(all_cols) if all_cols else 0
        self.max_col = max(all_cols) if all_cols else 0
        self.min_row = min(all_rows) if all_rows else 0
        self.max_row = max(all_rows) if all_rows else 0
        
        self.grid_width = self.max_col - self.min_col + 1
        self.grid_height = self.max_row - self.min_row + 1
        
        print(f"Grid bounds: col [{self.min_col}, {self.max_col}], row [{self.min_row}, {self.max_row}]")
        print(f"Grid size: {self.grid_width} x {self.grid_height}")
    
    def _build_matrices(self):
        """建立 walkable, cost, cell_map 矩陣"""
        # 初始化矩陣
        walkable = np.ones((self.grid_height, self.grid_width), dtype=bool) # 預設為可行走
        cost = np.ones((self.grid_height, self.grid_width), dtype=float)
        cell_map = np.full((self.grid_height, self.grid_width), -1, dtype=int)  # -1 表示無 cell
        
        # 填入每個 cell 的資訊
        for cell in self.cells:
            cell_type = cell.type
            type_info = self.grid_types.get(cell_type, {})
            
            # 取得基本屬性
            is_walkable = type_info.get('is_walkable', True)  # 預設可行走
            cell_cost = type_info.get('cost', 1.0)
            
            # 如果 allow_enter_area=True，特定區域可行走但成本較高
            if self.allow_enter_area and cell_type in ['exp hall', 'stage', 'Lounge']:
                is_walkable = True
                cell_cost = max(cell_cost, 2.0)  # 至少 2.0 的成本
            
            # 填入該 cell 佔據的所有 unit 格
            for dc in range(cell.unit_w):
                for dr in range(cell.unit_h):
                    grid_col = cell.col + dc - self.min_col
                    grid_row = cell.row + dr - self.min_row
                    
                    if 0 <= grid_col < self.grid_width and 0 <= grid_row < self.grid_height:
                        # 只有明確標記為不可行走的才設為 False
                        if not is_walkable:
                            walkable[grid_row, grid_col] = False
                        cost[grid_row, grid_col] = cell_cost
                        cell_map[grid_row, grid_col] = cell.idx
        
        return walkable, cost, cell_map
    
    def grid_to_matrix(self, col: int, row: int) -> Tuple[int, int]:
        """將網格座標轉換為矩陣索引"""
        matrix_col = col - self.min_col
        matrix_row = row - self.min_row
        return matrix_row, matrix_col
    
    def matrix_to_grid(self, matrix_row: int, matrix_col: int) -> Tuple[int, int]:
        """將矩陣索引轉換為網格座標"""
        col = matrix_col + self.min_col
        row = matrix_row + self.min_row
        return col, row
    
    def find_walkable_candidates(self, booth_idx: int) -> List[Tuple[int, int]]:
        """找出 booth 周圍所有可行走的邊界點"""
        if booth_idx not in self.cell_by_idx:
            return []
        
        booth = self.cell_by_idx[booth_idx]
        candidates = []
        
        # booth 佔據的範圍
        min_col, max_col = booth.col, booth.col + booth.unit_w - 1
        min_row, max_row = booth.row, booth.row + booth.unit_h - 1
        
        # 檢查 booth 四周的相鄰格子
        for col in range(min_col - 1, max_col + 2):
            for row in range(min_row - 1, max_row + 2):
                # 跳過 booth 內部的格子
                if min_col <= col <= max_col and min_row <= row <= max_row:
                    continue
                
                # 轉換為矩陣座標並檢查是否可行走
                matrix_row, matrix_col = self.grid_to_matrix(col, row)
                if (0 <= matrix_row < self.grid_height and 
                    0 <= matrix_col < self.grid_width and 
                    self.walkable[matrix_row, matrix_col]):
                    candidates.append((col, row))
        
        return candidates
    
    def find_walkable_near_booth(self, booth_idx: int) -> Optional[Tuple[int, int]]:
        """找到 booth 附近最近的可行走點（8向BFS）"""
        if booth_idx not in self.cell_by_idx:
            return None
        
        booth = self.cell_by_idx[booth_idx]
        
        # 先檢查 booth 周圍的所有邊界點
        candidates = []
        
        # booth 佔據的範圍
        min_col, max_col = booth.col, booth.col + booth.unit_w - 1
        min_row, max_row = booth.row, booth.row + booth.unit_h - 1
        
        # 檢查 booth 四周的相鄰格子
        for col in range(min_col - 1, max_col + 2):
            for row in range(min_row - 1, max_row + 2):
                # 跳過 booth 內部的格子
                if min_col <= col <= max_col and min_row <= row <= max_row:
                    continue
                
                # 轉換為矩陣座標並檢查是否可行走
                matrix_row, matrix_col = self.grid_to_matrix(col, row)
                if (0 <= matrix_row < self.grid_height and 
                    0 <= matrix_col < self.grid_width and 
                    self.walkable[matrix_row, matrix_col]):
                    
                    # 計算到 booth 中心的距離
                    center_col = booth.col + booth.unit_w / 2
                    center_row = booth.row + booth.unit_h / 2
                    distance = ((col - center_col) ** 2 + (row - center_row) ** 2) ** 0.5
                    candidates.append((distance, col, row))
        
        if candidates:
            # 回傳距離最近的可行走點
            candidates.sort()
            _, closest_col, closest_row = candidates[0]
            return closest_col, closest_row
        
        # 如果沒有找到相鄰的可行走點，使用較大範圍的 BFS
        center_col = booth.col + booth.unit_w // 2
        center_row = booth.row + booth.unit_h // 2
        start_matrix_row, start_matrix_col = self.grid_to_matrix(center_col, center_row)
        
        # 8 向搜尋
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        queue = [(start_matrix_row, start_matrix_col, 0)]  # (row, col, distance)
        visited = set()
        
        while queue:
            curr_row, curr_col, dist = queue.pop(0)
            
            if (curr_row, curr_col) in visited:
                continue
            visited.add((curr_row, curr_col))
            
            # 檢查邊界
            if not (0 <= curr_row < self.grid_height and 0 <= curr_col < self.grid_width):
                continue
            
            # 如果是可行走的，回傳網格座標
            if self.walkable[curr_row, curr_col]:
                grid_col, grid_row = self.matrix_to_grid(curr_row, curr_col)
                return grid_col, grid_row
            
            # 擴展鄰居
            for dr, dc in directions:
                new_row, new_col = curr_row + dr, curr_col + dc
                if (new_row, new_col) not in visited:
                    queue.append((new_row, new_col, dist + 1))
        
        return None
    
    def astar_multi(self, start_nodes: List[Tuple[int, int]], goal_set: set) -> Optional[RouteResult]:
        """
        多源多目標 A* 演算法，支援轉彎成本
        
        Args:
            start_nodes: 起點候選列表 [(col, row), ...]
            goal_set: 終點候選集合 {(col, row), ...}
        
        Returns:
            RouteResult 或 None
        """
        if not start_nodes or not goal_set:
            return None
        
        # 轉換為矩陣座標
        start_matrix_nodes = []
        goal_matrix_set = set()
        
        for col, row in start_nodes:
            matrix_row, matrix_col = self.grid_to_matrix(col, row)
            if (0 <= matrix_row < self.grid_height and 
                0 <= matrix_col < self.grid_width and 
                self.walkable[matrix_row, matrix_col]):
                start_matrix_nodes.append((matrix_row, matrix_col))
        
        for col, row in goal_set:
            matrix_row, matrix_col = self.grid_to_matrix(col, row)
            if (0 <= matrix_row < self.grid_height and 
                0 <= matrix_col < self.grid_width and 
                self.walkable[matrix_row, matrix_col]):
                goal_matrix_set.add((matrix_row, matrix_col))
        
        if not start_matrix_nodes or not goal_matrix_set:
            return None
        
        # A* 演算法初始化
        open_set = []
        came_from = {}  # (row, col) -> (prev_row, prev_col, prev_dir)
        g_score = {}
        f_score = {}
        
        # 初始化所有起點
        for matrix_row, matrix_col in start_matrix_nodes:
            pos = (matrix_row, matrix_col)
            g_score[pos] = 0
            f_score[pos] = self._heuristic_to_goal_set(matrix_row, matrix_col, goal_matrix_set)
            heapq.heappush(open_set, (f_score[pos], matrix_row, matrix_col))
        
        # 決定移動方向
        if self.options.allow_diag:
            # 8 向移動
            directions = [
                (-1,-1, np.sqrt(2)), (-1,0, 1), (-1,1, np.sqrt(2)),
                (0,-1, 1),                      (0,1, 1),
                (1,-1, np.sqrt(2)),  (1,0, 1),  (1,1, np.sqrt(2))
            ]
        else:
            # 4 向移動
            directions = [
                (-1,0, 1), (0,-1, 1), (0,1, 1), (1,0, 1)
            ]
        
        while open_set:
            current_f, current_row, current_col = heapq.heappop(open_set)
            current_pos = (current_row, current_col)
            
            # 找到目標
            if current_pos in goal_matrix_set:
                path = self._reconstruct_path_with_direction(came_from, current_pos)
                return self._path_to_route_result(path)
            
            for dr, dc, move_cost_multiplier in directions:
                neighbor_row, neighbor_col = current_row + dr, current_col + dc
                neighbor_pos = (neighbor_row, neighbor_col)
                
                # 檢查邊界
                if not (0 <= neighbor_row < self.grid_height and 0 <= neighbor_col < self.grid_width):
                    continue
                
                # 檢查是否可行走
                if not self.walkable[neighbor_row, neighbor_col]:
                    continue
                
                # 檢查 corner-cutting（僅在斜向移動時）
                if self.options.allow_diag and move_cost_multiplier == np.sqrt(2):
                    side1_row, side1_col = current_row + dr, current_col
                    side2_row, side2_col = current_row, current_col + dc
                    
                    side1_blocked = (not (0 <= side1_row < self.grid_height and 0 <= side1_col < self.grid_width) or 
                                   not self.walkable[side1_row, side1_col])
                    side2_blocked = (not (0 <= side2_row < self.grid_height and 0 <= side2_col < self.grid_width) or 
                                   not self.walkable[side2_row, side2_col])
                    
                    if side1_blocked and side2_blocked:
                        continue  # 禁止 corner-cutting
                
                # 計算移動成本
                neighbor_cost = self.cost[neighbor_row, neighbor_col]
                tentative_g_score = g_score[current_pos] + neighbor_cost * move_cost_multiplier
                
                # 計算轉彎成本
                if self.options.turn_weight > 0 and current_pos in came_from:
                    prev_row, prev_col, prev_dir = came_from[current_pos]
                    curr_dir = (dr, dc)
                    if prev_dir != curr_dir:  # 發生轉彎
                        tentative_g_score += self.options.turn_weight
                
                if neighbor_pos not in g_score or tentative_g_score < g_score[neighbor_pos]:
                    came_from[neighbor_pos] = (current_row, current_col, (dr, dc))
                    g_score[neighbor_pos] = tentative_g_score
                    f_score[neighbor_pos] = tentative_g_score + self._heuristic_to_goal_set(neighbor_row, neighbor_col, goal_matrix_set)
                    heapq.heappush(open_set, (f_score[neighbor_pos], neighbor_row, neighbor_col))
        
        return None  # 無法找到路徑
    
    def astar(self, start_col: int, start_row: int, end_col: int, end_row: int) -> Optional[RouteResult]:
        """A* 路徑搜尋"""
        # 轉換為矩陣座標
        start_matrix_row, start_matrix_col = self.grid_to_matrix(start_col, start_row)
        end_matrix_row, end_matrix_col = self.grid_to_matrix(end_col, end_row)
        
        # 檢查起終點是否在範圍內且可行走
        if not (0 <= start_matrix_row < self.grid_height and 0 <= start_matrix_col < self.grid_width):
            return None
        if not (0 <= end_matrix_row < self.grid_height and 0 <= end_matrix_col < self.grid_width):
            return None
        if not (self.walkable[start_matrix_row, start_matrix_col] and self.walkable[end_matrix_row, end_matrix_col]):
            return None
        
        # A* 演算法
        open_set = []
        heapq.heappush(open_set, (0, start_matrix_row, start_matrix_col))
        
        came_from = {}
        g_score = {(start_matrix_row, start_matrix_col): 0}
        f_score = {(start_matrix_row, start_matrix_col): self._heuristic(start_matrix_row, start_matrix_col, end_matrix_row, end_matrix_col)}
        
        # 8 向移動
        directions = [
            (-1,-1, np.sqrt(2)), (-1,0, 1), (-1,1, np.sqrt(2)),
            (0,-1, 1),                      (0,1, 1),
            (1,-1, np.sqrt(2)),  (1,0, 1),  (1,1, np.sqrt(2))
        ]
        
        while open_set:
            current_f, current_row, current_col = heapq.heappop(open_set)
            
            # 找到目標
            if current_row == end_matrix_row and current_col == end_matrix_col:
                path = self._reconstruct_path(came_from, (current_row, current_col))
                return self._path_to_route_result(path)
            
            for dr, dc, move_cost_multiplier in directions:
                neighbor_row, neighbor_col = current_row + dr, current_col + dc
                
                # 檢查邊界
                if not (0 <= neighbor_row < self.grid_height and 0 <= neighbor_col < self.grid_width):
                    continue
                
                # 檢查是否可行走
                if not self.walkable[neighbor_row, neighbor_col]:
                    continue
                
                # 檢查 corner-cutting：斜向移動時兩側直向不能都是障礙
                if move_cost_multiplier == np.sqrt(2):  # 斜向移動
                    side1_row, side1_col = current_row + dr, current_col
                    side2_row, side2_col = current_row, current_col + dc
                    
                    side1_blocked = (not (0 <= side1_row < self.grid_height and 0 <= side1_col < self.grid_width) or 
                                   not self.walkable[side1_row, side1_col])
                    side2_blocked = (not (0 <= side2_row < self.grid_height and 0 <= side2_col < self.grid_width) or 
                                   not self.walkable[side2_row, side2_col])
                    
                    if side1_blocked and side2_blocked:
                        continue  # 禁止 corner-cutting
                
                # 計算移動成本
                neighbor_cost = self.cost[neighbor_row, neighbor_col]
                tentative_g_score = g_score[(current_row, current_col)] + neighbor_cost * move_cost_multiplier
                
                neighbor_pos = (neighbor_row, neighbor_col)
                if neighbor_pos not in g_score or tentative_g_score < g_score[neighbor_pos]:
                    came_from[neighbor_pos] = (current_row, current_col)
                    g_score[neighbor_pos] = tentative_g_score
                    f_score[neighbor_pos] = tentative_g_score + self._heuristic(neighbor_row, neighbor_col, end_matrix_row, end_matrix_col)
                    heapq.heappush(open_set, (f_score[neighbor_pos], neighbor_row, neighbor_col))
        
        return None  # 無法找到路徑
    
    def _heuristic(self, row1: int, col1: int, row2: int, col2: int) -> float:
        """A* 啟發式函數（歐幾里得距離）"""
        return np.sqrt((row1 - row2)**2 + (col1 - col2)**2)
    
    def _heuristic_to_goal_set(self, row: int, col: int, goal_set: set) -> float:
        """計算到目標集合中最近點的啟發式距離"""
        if not goal_set:
            return 0.0
        
        min_dist = float('inf')
        for goal_row, goal_col in goal_set:
            dist = self._heuristic(row, col, goal_row, goal_col)
            if dist < min_dist:
                min_dist = dist
        
        return min_dist
    
    def _reconstruct_path(self, came_from: dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """重建路徑"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def _reconstruct_path_with_direction(self, came_from: dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """重建路徑（處理包含方向資訊的 came_from）"""
        path = [current]
        while current in came_from:
            prev_row, prev_col, prev_dir = came_from[current]
            current = (prev_row, prev_col)
            path.append(current)
        path.reverse()
        return path
    
    def _path_to_route_result(self, path: List[Tuple[int, int]]) -> RouteResult:
        """將矩陣路徑轉換為 RouteResult"""
        route_cells = []
        unit_path = []
        total_cost = 0.0
        total_length = 0.0
        
        for i, (matrix_row, matrix_col) in enumerate(path):
            # 轉換矩陣座標為 unit 座標
            grid_col, grid_row = self.matrix_to_grid(matrix_row, matrix_col)
            unit_path.append((grid_col, grid_row))
            
            # 取得該位置的 cell idx
            cell_idx = self.cell_map[matrix_row, matrix_col]
            if cell_idx != -1 and (not route_cells or route_cells[-1] != cell_idx):
                route_cells.append(cell_idx)
            
            # 計算移動成本和距離
            if i > 0:
                prev_row, prev_col = path[i-1]
                curr_row, curr_col = matrix_row, matrix_col
                
                # 移動距離
                dr, dc = curr_row - prev_row, curr_col - prev_col
                if abs(dr) == 1 and abs(dc) == 1:  # 斜向
                    move_distance = np.sqrt(2)
                else:  # 直向
                    move_distance = 1.0
                
                # 移動成本
                move_cost = self.cost[curr_row, curr_col] * move_distance
                
                total_length += move_distance
                total_cost += move_cost
        
        return RouteResult(
            route=route_cells,
            unit_path=unit_path,
            steps=len(path) - 1,
            length=total_length,
            total_cost=total_cost
        )


def load_grid_types(path: str = "data/grid_types.json") -> dict:
    """載入網格類型定義"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {path} not found, using default grid types")
        return {}


def find_route(
    cells: List[Cell], 
    start_idx: int, 
    end_idx: int,
    grid_types: Optional[dict] = None,
    options: Optional[PathfindingOptions] = None,
    # 向後相容性參數
    diag: Optional[bool] = None,
    allow_enter_area: Optional[bool] = None
) -> Optional[RouteResult]:
    """
    計算兩個 booth 之間的路徑
    
    Args:
        cells: Cell 列表
        start_idx: 起點 Cell idx
        end_idx: 終點 Cell idx
        grid_types: 網格類型定義（若為 None 則自動載入）
        options: 路徑計算選項（若為 None 則使用預設）
        diag: 向後相容性參數，是否允許斜向移動
        allow_enter_area: 向後相容性參數，是否允許進入大區域
    
    Returns:
        RouteResult: 包含路徑資訊的結果物件，若無法找到路徑則為 None
    """
    if grid_types is None:
        grid_types = load_grid_types()
    
    # 處理向後相容性：如果有舊參數，建立對應的 options
    if options is None:
        options = PathfindingOptions()
        if diag is not None:
            options.allow_diag = diag
        if allow_enter_area is not None:
            options.allow_enter_area = allow_enter_area
    
    # 建立路徑計算網格
    pathfinding_grid = PathfindingGrid(cells, grid_types, options)
    
    # 使用新的多邊界演算法
    start_candidates = pathfinding_grid.find_walkable_candidates(start_idx)
    end_candidates = pathfinding_grid.find_walkable_candidates(end_idx)
    
    if not start_candidates:
        print(f"Warning: Cannot find walkable candidates near start booth {start_idx}")
        # 降級到舊方法
        start_pos = pathfinding_grid.find_walkable_near_booth(start_idx)
        if start_pos is None:
            return None
        start_candidates = [start_pos]
    
    if not end_candidates:
        print(f"Warning: Cannot find walkable candidates near end booth {end_idx}")
        # 降級到舊方法
        end_pos = pathfinding_grid.find_walkable_near_booth(end_idx)
        if end_pos is None:
            return None
        end_candidates = [end_pos]
    
    # 執行多源多目標 A* 搜尋
    result = pathfinding_grid.astar_multi(start_candidates, set(end_candidates))
    
    if result is None:
        return None
    
    # 確保起終點包含在路徑中
    route = result.route[:]
    if start_idx not in route:
        route.insert(0, start_idx)
    if end_idx not in route:
        route.append(end_idx)
    
    # 返回完整的結果物件
    return RouteResult(
        route=route,
        unit_path=result.unit_path,
        steps=result.steps,
        length=result.length,
        total_cost=result.total_cost
    )


# 主要 API 函數
def find_route_from_files(
    start_idx: int,
    end_idx: int,
    grid_path: str = "data/grid.json",
    grid_types_path: str = "data/grid_types.json",
    options: Optional[PathfindingOptions] = None,
    # 向後相容性參數
    diag: Optional[bool] = None,
    allow_enter_area: Optional[bool] = None
) -> Optional[RouteResult]:
    """
    從檔案載入資料並計算路徑
    """
    cells = load_grid(grid_path)
    if not cells:
        print(f"Error: Cannot load grid from {grid_path}")
        return None
    
    grid_types = load_grid_types(grid_types_path)
    
    return find_route(cells, start_idx, end_idx, grid_types, options, diag, allow_enter_area)


if __name__ == "__main__":
    # 測試用例
    import argparse
    
    parser = argparse.ArgumentParser(description="Test pathfinding between two booths")
    parser.add_argument("start", type=int, help="Start booth idx")
    parser.add_argument("end", type=int, help="End booth idx")
    parser.add_argument("--allow-enter-area", action="store_true", help="Allow entering large areas")
    
    args = parser.parse_args()
    
    result = find_route_from_files(args.start, args.end, allow_enter_area=args.allow_enter_area)
    
    if result is None:
        print("No route found")
    else:
        print(f"Route: {result.route}")
        print(f"Unit path: {result.unit_path}")
        print(f"Steps: {result.steps}, Length: {result.length:.2f}, Cost: {result.total_cost:.2f}") 