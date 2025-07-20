#!/usr/bin/env python3
"""
自然語言導航模組 (Navigation NLG Module)

實作 Phase 1-2 功能：
- Route Analyzer: 轉向偵測、分段距離、Landmark 擇選
- Rule Formatter: 中文導航文字生成
"""

import json
import math
import os
import sys
import yaml
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from pathlib import Path

@dataclass
class NavigationConfig:
    """導航系統配置"""
    
    # 地標檢測配置
    landmark_detection: Dict = None
    
    # 序列選擇配置  
    sequence_selection: Dict = None
    
    # 方位計算配置
    side_calculation: Dict = None
    
    def __post_init__(self):
        if self.landmark_detection is None:
            self.landmark_detection = {
                "search_radius": 3,
                "distance_filter": 2
            }
        
        if self.sequence_selection is None:
            self.sequence_selection = {
                "max_landmarks_per_side": 3,
                "coverage_weight": 1.0,
                "min_coverage_threshold": 0.2,  # 最低覆蓋率閾值 20%
                "use_front_fallback": True  # 低覆蓋率時使用前方landmark
            }
        
        if self.side_calculation is None:
            self.side_calculation = {
                "long_segment_threshold": 5,  # units, 超過此閾值使用segment幾何
                "front_angle_threshold": 0.966,  # cos(15°), 更嚴格的前方判斷
                "use_hybrid_method": True  # 是否啟用混合方法
            }
    
    @classmethod
    def from_yaml(cls, yaml_file: str) -> 'NavigationConfig':
        """從 YAML 文件載入配置"""
        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"配置文件不存在: {yaml_file}")
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 創建配置實例
        config = cls()
        
        # 更新配置
        if 'landmark_detection' in config_data:
            config.landmark_detection.update(config_data['landmark_detection'])
        
        if 'sequence_selection' in config_data:
            config.sequence_selection.update(config_data['sequence_selection'])
        
        if 'side_calculation' in config_data:
            config.side_calculation.update(config_data['side_calculation'])
        
        return config
    
    def to_yaml(self, yaml_file: str):
        """儲存配置到 YAML 文件"""
        config_data = {
            'landmark_detection': self.landmark_detection,
            'sequence_selection': self.sequence_selection,
            'side_calculation': self.side_calculation
        }
        
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, indent=2)

# 將專案根目錄加到 Python 路徑中（供直接執行使用）
if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)

try:
    from .grid import Cell, load_grid, load_grid_meta
    from .pathfinder import RouteResult
except ImportError:
    from core.grid import Cell, load_grid, load_grid_meta
    from core.pathfinder import RouteResult


@dataclass
class LandmarkInfo:
    """地標資訊"""
    idx: int
    name: str
    side: str  # "left", "right", "front", "behind"

@dataclass
class LandmarkWithCoverage:
    """帶覆蓋率的地標資訊"""
    cell: Dict
    side: str
    coverage_ratio: float  # 覆蓋率 (0.0 - 1.0)
    path_positions: List[int]  # 在路徑上出現的位置列表


@dataclass
class NavigationStep:
    """單一導航步驟"""
    step_id: int
    action: str  # "orient", "continue", "turn_left", "turn_right", "arrive"
    distance_units: int  # 距離（unit 單位）
    landmark: Optional[LandmarkInfo] = None
    direction: Optional[str] = None  # "north", "east", "south", "west"


class RouteAnalyzer:
    """路徑分析器 - Phase 1"""
    
    def __init__(self, grid_data: List[Dict], grid_types: Dict, config: NavigationConfig = None):
        """
        初始化路徑分析器
        
        Args:
            grid_data: 從 grid.json 載入的格子資料
            grid_types: 從 grid_types.json 載入的類型定義
            config: 導航配置
        """
        self.grid_data = grid_data
        self.grid_types = grid_types
        self.config = config or NavigationConfig()
        
        # 建立索引映射
        self.idx_to_cell = {cell['idx']: cell for cell in grid_data}
        
        # 建立 unit 座標到 cell 的映射（用於地標搜尋）
        self.unit_to_cells = {}
        for cell in grid_data:
            # 計算該 cell 佔據的所有 unit 座標
            for row_offset in range(cell.get('unit_h', 1)):
                for col_offset in range(cell.get('unit_w', 1)):
                    unit_pos = (cell['col'] + col_offset, cell['row'] + row_offset)
                    if unit_pos not in self.unit_to_cells:
                        self.unit_to_cells[unit_pos] = []
                    self.unit_to_cells[unit_pos].append(cell)
    
    def is_landmark(self, cell: Dict) -> bool:
        """判斷格子是否為地標（支援多種類型）"""
        landmark_types = ['booth', 'exp hall', 'stage', 'Lounge']
        return cell.get('type') in landmark_types
    
    def is_good_landmark(self, cell: Dict) -> bool:
        """判斷是否為品質良好的地標（有意義的名稱）"""
        # 大型區域（exp hall, stage, Lounge）總是好地標
        if cell.get('type') in ['exp hall', 'stage', 'Lounge']:
            return True
            
        # booth需要檢查名稱品質
        name = cell.get('name')
        if not name or name.strip() == '':
            return False
        # 排除純數字名稱
        if name.isdigit():
            return False
        # 排除全數字的名稱（如 "432"）
        if name.replace(' ', '').isdigit():
            return False
        return True
    
    def calculate_landmark_area(self, cell: Dict) -> int:
        """計算地標面積（用於優先級排序）"""
        unit_w = cell.get('unit_w', 1)
        unit_h = cell.get('unit_h', 1)
        return unit_w * unit_h
    
    def get_landmark_priority(self, cell: Dict) -> int:
        """獲取地標優先級（數字越小優先級越高）"""
        cell_type = cell.get('type', '')
        area = self.calculate_landmark_area(cell)
        
        # 基礎優先級 (類型)
        if cell_type == 'exp hall':
            base_priority = 100
        elif cell_type == 'stage':
            base_priority = 200  
        elif cell_type == 'Lounge':
            base_priority = 300
        elif cell_type == 'booth':
            base_priority = 400
        else:
            base_priority = 500
            
        # 面積越大，優先級越高（減去面積值）
        return base_priority - area
    
    def find_intermediate_landmarks_with_coverage(self, start_pos: Tuple[int, int], 
                                                end_pos: Tuple[int, int], 
                                                search_radius: int = None,
                                                exclude_cell_ids: set = None) -> List[LandmarkWithCoverage]:
        """
        搜尋直線段中的中繼地標（帶覆蓋率）
        
        Args:
            start_pos: 起點位置
            end_pos: 終點位置
            search_radius: 搜尋半徑（使用配置值）
            exclude_cell_ids: 要排除的cell idx集合（如起點、終點）
            
        Returns:
            List of LandmarkWithCoverage，帶覆蓋率信息
        """
        if search_radius is None:
            search_radius = self.config.landmark_detection["search_radius"]
        
        # 計算移動方向向量
        move_dir = (end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
        move_length = max(abs(move_dir[0]), abs(move_dir[1]))
        
        if move_length == 0:
            return []
        
        # 記錄每個地標在路徑上的所有出現位置
        landmark_appearances = {}  # idx -> {side, positions, distances}
        
        for i in range(move_length + 1):
            # 線性插值計算當前位置
            t = i / move_length
            current_pos = (
                int(start_pos[0] + t * move_dir[0]),
                int(start_pos[1] + t * move_dir[1])
            )
            
            # 搜尋當前位置周圍的地標
            for dx in range(-search_radius, search_radius + 1):
                for dy in range(-search_radius, search_radius + 1):
                    if dx == 0 and dy == 0:  # 跳過當前位置
                        continue
                        
                    search_pos = (current_pos[0] + dx, current_pos[1] + dy)
                    
                    if search_pos in self.unit_to_cells:
                        for cell in self.unit_to_cells[search_pos]:
                            if (self.is_landmark(cell) and self.is_good_landmark(cell) and 
                                (exclude_cell_ids is None or cell['idx'] not in exclude_cell_ids)):
                                
                                idx = cell['idx']
                                
                                # 計算地標的實際unit座標
                                landmark_unit_pos = (cell['col'], cell['row'])
                                
                                # 使用混合方位計算方法
                                segment_length = move_length
                                is_long_segment = (self.config.side_calculation["use_hybrid_method"] and 
                                                 segment_length >= self.config.side_calculation["long_segment_threshold"])
                                
                                side = self.calculate_landmark_side_hybrid(
                                    start_pos, end_pos, landmark_unit_pos,
                                    is_long_segment=is_long_segment, 
                                    is_turn_context=False
                                )
                                
                                distance_to_path = max(abs(dx), abs(dy))
                                
                                if idx not in landmark_appearances:
                                    landmark_appearances[idx] = {
                                        'cell': cell,
                                        'side': side,
                                        'positions': [],
                                        'distances': []
                                    }
                                
                                landmark_appearances[idx]['positions'].append(i)
                                landmark_appearances[idx]['distances'].append(distance_to_path)
        
        # 計算覆蓋率並創建LandmarkWithCoverage對象
        landmarks_with_coverage = []
        distance_filter = self.config.landmark_detection["distance_filter"]
        
        for idx, data in landmark_appearances.items():
            # 過濾距離太遠的位置
            valid_positions = []
            for pos, dist in zip(data['positions'], data['distances']):
                if dist <= distance_filter:
                    valid_positions.append(pos)
            
            if not valid_positions:
                continue
            
            # 計算覆蓋率：連續段的總長度 / 路徑總長度
            valid_positions.sort()
            coverage_length = self._calculate_coverage_length(valid_positions)
            coverage_ratio = coverage_length / move_length
            
            landmark_with_coverage = LandmarkWithCoverage(
                cell=data['cell'],
                side=data['side'],
                coverage_ratio=coverage_ratio,
                path_positions=valid_positions
            )
            landmarks_with_coverage.append(landmark_with_coverage)
        
        return landmarks_with_coverage
    
    def _calculate_coverage_length(self, positions: List[int]) -> int:
        """計算位置列表的覆蓋長度（考慮連續段）"""
        if not positions:
            return 0
        
        positions = sorted(set(positions))  # 去重並排序
        
        # 計算連續段的總長度
        total_length = 0
        start = positions[0]
        end = positions[0]
        
        for i in range(1, len(positions)):
            if positions[i] == end + 1:  # 連續
                end = positions[i]
            else:  # 不連續，開始新段
                total_length += (end - start + 1)
                start = positions[i]
                end = positions[i]
        
        # 加上最後一段
        total_length += (end - start + 1)
        
        return total_length

    def find_intermediate_landmarks(self, start_pos: Tuple[int, int], 
                                  end_pos: Tuple[int, int], 
                                  search_radius: int = 3,
                                  exclude_cell_ids: set = None) -> List[Tuple[Dict, str]]:
        """
        搜尋直線段中的中繼地標（向後相容版本）
        
        Args:
            start_pos: 起點位置
            end_pos: 終點位置
            search_radius: 搜尋半徑
            exclude_cell_ids: 要排除的cell idx集合（如起點、終點）
            
        Returns:
            List of (cell, side) tuples，按優先級排序
        """
        # 使用新的帶覆蓋率方法
        landmarks_with_coverage = self.find_intermediate_landmarks_with_coverage(
            start_pos, end_pos, search_radius, exclude_cell_ids
        )
        
        # 轉換為舊格式（按覆蓋率排序）
        landmarks_with_coverage.sort(key=lambda x: (-x.coverage_ratio, self.get_landmark_priority(x.cell)))
        
        return [(lm.cell, lm.side) for lm in landmarks_with_coverage]
    
    def generate_three_sequences(self, start_pos: Tuple[int, int], 
                                end_pos: Tuple[int, int], 
                                exclude_cell_ids: set = None) -> Dict[str, List[LandmarkWithCoverage]]:
        """
        生成三個地標序列：穿越/左側/右側
        
        Args:
            start_pos: 起點位置
            end_pos: 終點位置
            exclude_cell_ids: 要排除的cell idx集合
            
        Returns:
            {"crossing": [...], "left": [...], "right": [...]}
        """
        # 獲取所有帶覆蓋率的地標
        all_landmarks = self.find_intermediate_landmarks_with_coverage(
            start_pos, end_pos, exclude_cell_ids=exclude_cell_ids
        )
        
        # 檢查穿越地標（這裡需要特殊處理，穿越地標通常是大型區域）
        crossing_landmarks = []
        # TODO: 實現穿越地標檢測邏輯
        
        # 按側邊分組
        left_landmarks = [lm for lm in all_landmarks if lm.side == "left"]
        right_landmarks = [lm for lm in all_landmarks if lm.side == "right"]
        front_landmarks = [lm for lm in all_landmarks if lm.side == "front"]
        
        # front地標保持獨立，不合併到left/right
        
        # 處理每個序列：覆蓋率排序 → Top-K → 路徑順序重排
        max_landmarks = self.config.sequence_selection["max_landmarks_per_side"]
        
        left_sequence = self._process_landmark_sequence(left_landmarks, max_landmarks)
        right_sequence = self._process_landmark_sequence(right_landmarks, max_landmarks)
        front_sequence = self._process_landmark_sequence(front_landmarks, max_landmarks)
        crossing_sequence = self._process_landmark_sequence(crossing_landmarks, max_landmarks)
        
        return {
            "crossing": crossing_sequence,
            "left": left_sequence,
            "right": right_sequence,
            "front": front_sequence
        }
    
    def _process_landmark_sequence(self, landmarks: List[LandmarkWithCoverage], 
                                  max_count: int) -> List[LandmarkWithCoverage]:
        """
        處理地標序列：覆蓋率排序 → Top-K → 路徑順序重排
        
        Args:
            landmarks: 原始地標列表
            max_count: 最大保留數量
            
        Returns:
            處理後的地標序列
        """
        if not landmarks:
            return []
        
        # 1. 按覆蓋率排序（從高到低）
        landmarks.sort(key=lambda x: -x.coverage_ratio)
        
        # 2. Top-K選擇
        top_landmarks = landmarks[:max_count]
        
        # 3. 按路徑順序重排（使用第一個出現位置）
        top_landmarks.sort(key=lambda x: min(x.path_positions))
        
        return top_landmarks

    def find_landmarks_same_side(self, start_pos: Tuple[int, int], 
                                end_pos: Tuple[int, int], 
                                max_count: int = 3,
                                exclude_cell_ids: set = None) -> List[Tuple[Dict, str]]:
        """
        搜尋同側的多個中繼地標
        
        Args:
            start_pos: 起點位置
            end_pos: 終點位置
            max_count: 最大地標數量
            exclude_cell_ids: 要排除的cell idx集合（如起點、終點）
            
        Returns:
            同側的地標列表，按優先級排序
        """
        all_landmarks = self.find_intermediate_landmarks(start_pos, end_pos, exclude_cell_ids=exclude_cell_ids)
        
        if not all_landmarks:
            return []
        
        # 按側邊分組
        left_landmarks = [l for l in all_landmarks if l[1] == "left"]
        right_landmarks = [l for l in all_landmarks if l[1] == "right"]
        front_landmarks = [l for l in all_landmarks if l[1] == "front"]
        
        # 選擇地標最多的一側，或者優先級最高的一側
        candidates = []
        if left_landmarks:
            candidates.append(left_landmarks[:max_count])
        if right_landmarks:
            candidates.append(right_landmarks[:max_count])
        if front_landmarks:
            candidates.append(front_landmarks[:max_count])
        
        if not candidates:
            return []
        
        # 選擇地標數量最多的一側
        best_side = max(candidates, key=len)
        
        # 如果數量相同，選擇優先級最高的一側
        if len(best_side) == len(candidates[0]):
            best_side = min(candidates, key=lambda side: self.get_landmark_priority(side[0][0]) if side else 999)
        
        return best_side
    
    def detect_crossing_landmarks(self, start_pos: Tuple[int, int], 
                                 end_pos: Tuple[int, int]) -> List[Dict]:
        """
        檢測路徑是否穿越大型地標
        
        Args:
            start_pos: 起點位置
            end_pos: 終點位置
            
        Returns:
            被穿越的地標列表
        """
        crossing_landmarks = []
        
        # 計算移動方向向量
        move_dir = (end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
        move_length = max(abs(move_dir[0]), abs(move_dir[1]))
        
        if move_length == 0:
            return crossing_landmarks
        
        # 遍歷路徑上的點
        seen_idx = set()
        for i in range(move_length + 1):
            if move_length == 0:
                current_pos = start_pos
            else:
                # 線性插值計算當前位置
                t = i / move_length
                current_pos = (
                    int(start_pos[0] + t * move_dir[0]),
                    int(start_pos[1] + t * move_dir[1])
                )
            
            # 檢查當前位置是否在大型地標內
            if current_pos in self.unit_to_cells:
                for cell in self.unit_to_cells[current_pos]:
                    if (cell.get('type') in ['exp hall', 'stage', 'Lounge'] and 
                        cell['idx'] not in seen_idx):
                        crossing_landmarks.append(cell)
                        seen_idx.add(cell['idx'])
        
        # 按優先級排序
        crossing_landmarks.sort(key=self.get_landmark_priority)
        
        return crossing_landmarks
    
    def detect_turn_direction(self, p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int]) -> str:
        """
        使用向量外積偵測轉向
        注意：由於row軸向下增加，需反轉外積判斷
        
        Args:
            p1, p2, p3: 連續三個 unit 座標點
            
        Returns:
            "left", "right", "straight"
        """
        # 向量 p1->p2 和 p2->p3
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # 外積（叉積的 z 分量）
        cross_product = v1[0] * v2[1] - v1[1] * v2[0]
        
        # 修正座標系：row軸向下，需反轉判斷
        if cross_product > 0:
            return "right"  # 修正：原左轉改為右轉
        elif cross_product < 0:
            return "left"   # 修正：原右轉改為左轉
        else:
            return "straight"
    
    def get_direction_name(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> str:
        """獲取方向名稱（north/east/south/west）"""
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        
        if abs(dx) > abs(dy):
            return "east" if dx > 0 else "west"
        else:
            return "south" if dy > 0 else "north"
    
    def find_nearby_landmarks(self, current_pos: Tuple[int, int], 
                            next_pos: Tuple[int, int], 
                            search_radius: int = 2) -> List[Tuple[Dict, str]]:
        """
        在轉彎點附近搜尋地標，按優先級分區
        
        Args:
            current_pos: 當前位置
            next_pos: 下一個位置
            search_radius: 搜尋半徑
            
        Returns:
            List of (cell, side) tuples，按優先級排序
        """
        landmarks = []
        
        # 計算移動方向向量
        move_dir = (next_pos[0] - current_pos[0], next_pos[1] - current_pos[1])
        
        # 搜尋周圍格子
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                if dx == 0 and dy == 0:  # 跳過當前位置
                    continue
                    
                search_pos = (current_pos[0] + dx, current_pos[1] + dy)
                
                if search_pos in self.unit_to_cells:
                    for cell in self.unit_to_cells[search_pos]:
                        if self.is_landmark(cell) and self.is_good_landmark(cell):
                            # 計算地標相對於移動方向的位置
                            landmark_dir = (dx, dy)
                            side = self.calculate_relative_side(move_dir, landmark_dir)
                            landmarks.append((cell, side))
        
        # 去重（同一個landmark可能佔多個unit）
        unique_landmarks = []
        seen_idx = set()
        for cell, side in landmarks:
            if cell['idx'] not in seen_idx:
                unique_landmarks.append((cell, side))
                seen_idx.add(cell['idx'])
        
        # 按優先級排序：front > left/right > behind
        priority_order = {"front": 0, "left": 1, "right": 1, "behind": 2}
        unique_landmarks.sort(key=lambda x: priority_order.get(x[1], 3))
        
        return unique_landmarks
    
    def calculate_relative_side_segment_based(self, segment_start: Tuple[int, int], 
                                            segment_end: Tuple[int, int], 
                                            landmark_pos: Tuple[int, int]) -> str:
        """基於segment幾何關係計算地標方位"""
        
        # 計算segment方向向量
        segment_dir = (segment_end[0] - segment_start[0], segment_end[1] - segment_start[1])
        segment_length = math.sqrt(segment_dir[0]**2 + segment_dir[1]**2)
        
        if segment_length == 0:
            return "unknown"
        
        # 計算landmark相對於segment起點的向量
        landmark_dir = (landmark_pos[0] - segment_start[0], landmark_pos[1] - segment_start[1])
        landmark_length = math.sqrt(landmark_dir[0]**2 + landmark_dir[1]**2)
        
        if landmark_length == 0:
            return "unknown"
        
        # 內積判斷前後
        dot = (segment_dir[0] * landmark_dir[0] + segment_dir[1] * landmark_dir[1]) / (segment_length * landmark_length)
        
        # 前方區域：內積 >= cos(15°) ≈ 0.966 (±15度內) - 更嚴格的前方判斷
        if dot >= 0.966:
            return "front"
        
        # 外積判斷左右（修正座標系）
        cross = segment_dir[0] * landmark_dir[1] - segment_dir[1] * landmark_dir[0]
        
        if cross > 0:
            return "right"  # 修正：原左改為右
        elif cross < 0:
            return "left"   # 修正：原右改為左
        else:
            return "behind"
    
    def calculate_landmark_side_hybrid(self, segment_start: Tuple[int, int], 
                                     segment_end: Tuple[int, int], 
                                     landmark_pos: Tuple[int, int],
                                     is_long_segment: bool = True, 
                                     is_turn_context: bool = False) -> str:
        """混合方位計算：短距離用點對點，長距離用segment幾何"""
        
        if is_turn_context or not is_long_segment:
            # 短距離/轉向：使用點對點（原有邏輯）
            move_dir = (segment_end[0] - segment_start[0], segment_end[1] - segment_start[1])
            landmark_dir = (landmark_pos[0] - segment_start[0], landmark_pos[1] - segment_start[1])
            return self.calculate_relative_side(move_dir, landmark_dir)
        else:
            # 長距離直線：使用segment幾何
            return self.calculate_relative_side_segment_based(segment_start, segment_end, landmark_pos)

    def calculate_relative_side(self, move_dir: Tuple[int, int], 
                              landmark_dir: Tuple[int, int]) -> str:
        """計算地標相對於移動方向的側邊，實現三分區邏輯"""
        # 歸一化向量
        move_length = math.sqrt(move_dir[0]**2 + move_dir[1]**2)
        landmark_length = math.sqrt(landmark_dir[0]**2 + landmark_dir[1]**2)
        
        if move_length == 0 or landmark_length == 0:
            return "unknown"
        
        # 內積判斷前後
        dot = (move_dir[0] * landmark_dir[0] + move_dir[1] * landmark_dir[1]) / (move_length * landmark_length)
        
        # 前方區域：內積 >= cos(45°) ≈ 0.707 (±45度內)
        if dot >= 0.707:
            return "front"
        
        # 外積判斷左右（修正座標系）
        cross = move_dir[0] * landmark_dir[1] - move_dir[1] * landmark_dir[0]
        
        if cross > 0:
            return "right"  # 修正：原左改為右
        elif cross < 0:
            return "left"   # 修正：原右改為左
        else:
            return "behind"
    
    def analyze_route(self, route_result: RouteResult) -> List[NavigationStep]:
        """
        分析路徑並生成導航步驟（改進版：合併連續直線段）
        
        Args:
            route_result: pathfinder 計算出的路徑結果
            
        Returns:
            導航步驟列表
        """
        unit_path = route_result.unit_path
        steps = []
        
        if len(unit_path) < 2:
            # 起點即終點
            steps.append(NavigationStep(
                step_id=1,
                action="arrive",
                distance_units=0
            ))
            return steps
        
        # 先找出所有轉彎點
        turn_points = []
        for i in range(1, len(unit_path) - 1):
            turn_dir = self.detect_turn_direction(
                unit_path[i-1], unit_path[i], unit_path[i+1]
            )
            if turn_dir != "straight":
                turn_points.append((i, turn_dir))
        
        step_id = 1
        current_pos = 0
        
        # 生成起步指令（如果有長距離直線段）
        if turn_points:
            first_turn_pos = turn_points[0][0]
            if first_turn_pos > 3:  # 起步段較長時加入定位指令
                # 搜尋起步地標
                start_landmarks = self.find_nearby_landmarks(unit_path[0], unit_path[1])
                start_landmark = None
                if start_landmarks:
                    # 優先選擇前方地標
                    front_landmarks = [l for l in start_landmarks if l[1] == "front"]
                    if front_landmarks:
                        start_landmark = front_landmarks[0]
                    else:
                        start_landmark = start_landmarks[0]
                
                if start_landmark:
                    steps.append(NavigationStep(
                        step_id=step_id,
                        action="orient",
                        distance_units=0,
                        landmark=LandmarkInfo(
                            idx=start_landmark[0]['idx'],
                            name=start_landmark[0].get('name', f"格子 {start_landmark[0]['idx']}"),
                            side=start_landmark[1]
                        )
                    ))
                    step_id += 1
        
        # 處理每個轉彎點
        for turn_pos, turn_dir in turn_points:
            # 生成到轉彎點的直線段
            distance = turn_pos - current_pos
            
            if distance > 0:
                direction = self.get_direction_name(
                    unit_path[current_pos], unit_path[turn_pos]
                )
                
                steps.append(NavigationStep(
                    step_id=step_id,
                    action="continue",
                    distance_units=distance,
                    direction=direction
                ))
                step_id += 1
            
            # 搜尋轉彎點地標
            landmarks = self.find_nearby_landmarks(unit_path[turn_pos-1], unit_path[turn_pos])
            best_landmark = None
            
            if landmarks:
                # 優先選擇前方地標，其次選擇同轉向側地標
                front_landmarks = [l for l in landmarks if l[1] == "front"]
                same_side_landmarks = [l for l in landmarks if l[1] == turn_dir]
                
                if front_landmarks:
                    best_landmark = front_landmarks[0]
                elif same_side_landmarks:
                    best_landmark = same_side_landmarks[0]
                else:
                    best_landmark = landmarks[0]
            
            # 生成轉彎指令
            landmark_info = None
            if best_landmark:
                landmark_info = LandmarkInfo(
                    idx=best_landmark[0]['idx'],
                    name=best_landmark[0].get('name', f"格子 {best_landmark[0]['idx']}"),
                    side=best_landmark[1]
                )
            
            steps.append(NavigationStep(
                step_id=step_id,
                action=f"turn_{turn_dir}",
                distance_units=0,
                landmark=landmark_info
            ))
            step_id += 1
            current_pos = turn_pos
        
        # 處理最後一段
        final_distance = len(unit_path) - 1 - current_pos
        
        if final_distance > 0:
            direction = self.get_direction_name(
                unit_path[current_pos], unit_path[-1]
            )
            
            steps.append(NavigationStep(
                step_id=step_id,
                action="continue",
                distance_units=final_distance,
                direction=direction
            ))
            step_id += 1
        
        # 最終到達步驟 - 添加目的地方位判斷
        arrival_landmark = None
        if len(unit_path) >= 2:
            # 獲取目的地格子
            target_idx = route_result.route[-1] if route_result.route else None
            target_cell = self.idx_to_cell.get(target_idx) if target_idx else None
            
            if target_cell:
                # 計算最後移動方向
                last_move_dir = (unit_path[-1][0] - unit_path[-2][0], unit_path[-1][1] - unit_path[-2][1])
                
                # 搜尋目的地附近的位置，判斷目的地相對方位
                target_pos = unit_path[-1]
                target_landmarks = self.find_nearby_landmarks(unit_path[-2], target_pos, search_radius=1)
                
                # 查找目的地本身的方位
                for landmark, side in target_landmarks:
                    if landmark['idx'] == target_idx:
                        arrival_landmark = LandmarkInfo(
                            idx=target_cell['idx'],
                            name=target_cell.get('name', f"格子 {target_cell['idx']}"),
                            side=side
                        )
                        break
                
                # 如果沒找到，直接計算目的地相對方位
                if not arrival_landmark and len(unit_path) >= 2:
                    # 假設目的地就在最後位置，計算其相對方位
                    landmark_dir = (0, 0)  # 目的地就在當前位置
                    # 由於是到達目的地，我們認為目的地在"前方"
                    arrival_landmark = LandmarkInfo(
                        idx=target_cell['idx'],
                        name=target_cell.get('name', f"格子 {target_cell['idx']}"),
                        side="front"
                    )
        
        steps.append(NavigationStep(
            step_id=step_id,
            action="arrive",
            distance_units=0,
            landmark=arrival_landmark
        ))
        
        return steps
    
    def select_best_sequence_with_fallback(self, sequences: Dict[str, List[LandmarkWithCoverage]]) -> Tuple[str, List[LandmarkWithCoverage], bool]:
        """
        新的序列選擇策略：優先比較穿越/左右方，低覆蓋率時回退到前方landmark
        
        Args:
            sequences: {"crossing": [...], "left": [...], "right": [...], "front": [...]}
            
        Returns:
            (sequence_name, sequence, is_fallback)
        """
        min_threshold = self.config.sequence_selection["min_coverage_threshold"]
        use_fallback = self.config.sequence_selection["use_front_fallback"]
        
        # 第一階段：只比較穿越/左右方序列
        primary_sequences = {k: v for k, v in sequences.items() if k in ["crossing", "left", "right"]}
        
        best_score = -1
        best_name = None
        best_sequence = []
        
        for name, sequence in primary_sequences.items():
            if not sequence:
                continue
            
            # 計算平均覆蓋率
            avg_coverage = sum(lm.coverage_ratio for lm in sequence) / len(sequence)
            
            if avg_coverage > best_score:
                best_score = avg_coverage
                best_name = name
                best_sequence = sequence
        
        # 檢查是否需要回退到前方landmark
        if use_fallback and best_score < min_threshold and "front" in sequences and sequences["front"]:
            # 使用前方landmark作為指引
            # 從primary序列中選擇一個最好的作為"經過"對象
            if best_sequence:
                # 組合策略：經過[低覆蓋率landmark] + 走至[前方landmark]
                return self._create_combined_sequence(best_sequence, sequences["front"], best_name)
            else:
                # 如果primary序列都為空，直接使用前方landmark
                return "front", sequences["front"], True
        
        return best_name, best_sequence, False
    
    def _create_combined_sequence(self, low_coverage_sequence: List[LandmarkWithCoverage], 
                                front_sequence: List[LandmarkWithCoverage], 
                                primary_side: str) -> Tuple[str, List[LandmarkWithCoverage], bool]:
        """
        創建組合序列：經過低覆蓋率landmark + 走至前方landmark
        
        Args:
            low_coverage_sequence: 低覆蓋率的左/右/穿越序列
            front_sequence: 前方landmark序列
            primary_side: 主要側邊名稱
            
        Returns:
            (sequence_name, combined_sequence, is_fallback)
        """
        # 選擇覆蓋率最高的低覆蓋landmark（作為"經過"對象）
        primary_landmark = max(low_coverage_sequence, key=lambda x: x.coverage_ratio)
        
        # 選擇優先級最高的前方landmark（作為目標）
        target_landmark = max(front_sequence, key=lambda x: self.get_landmark_priority(x.cell))
        
        # 標記組合序列類型
        combined_name = f"{primary_side}_to_front"
        
        # 創建組合序列：[經過的landmark, 目標landmark]
        combined_sequence = [primary_landmark, target_landmark]
        
        return combined_name, combined_sequence, True


class RuleFormatter:
    """規則式格式化器 - Phase 2"""
    
    def __init__(self):
        """初始化格式化器"""
        pass
    
    def units_to_booth_count(self, units: int) -> int:
        """將 units 轉換為攤位數量（粗略估算：1 攤位 ≈ 2-3 units）"""
        return max(1, round(units / 2.5))
    
    def count_passed_booths(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int], 
                           analyzer: 'RouteAnalyzer') -> int:
        """計算直線段實際經過的攤位數量"""
        # 計算移動方向
        move_dir = (end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
        if move_dir == (0, 0):
            return 0
        
        booth_count = 0
        seen_booths = set()
        
        # 遍歷路徑上的每個點
        steps = max(abs(move_dir[0]), abs(move_dir[1]))
        for i in range(steps + 1):
            if steps == 0:
                current_pos = start_pos
            else:
                # 線性插值計算當前位置
                t = i / steps
                current_pos = (
                    int(start_pos[0] + t * move_dir[0]),
                    int(start_pos[1] + t * move_dir[1])
                )
            
            # 搜尋當前位置左右兩側的攤位
            for side_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                check_pos = (current_pos[0] + side_offset[0], current_pos[1] + side_offset[1])
                
                if check_pos in analyzer.unit_to_cells:
                    for cell in analyzer.unit_to_cells[check_pos]:
                        if (cell.get('type') == 'booth' and 
                            cell['idx'] not in seen_booths and
                            analyzer.is_good_landmark(cell)):
                            seen_booths.add(cell['idx'])
                            booth_count += 1
        
        return booth_count
    
    def format_distance(self, units: int, start_pos: Tuple[int, int] = None, 
                        end_pos: Tuple[int, int] = None, analyzer: 'RouteAnalyzer' = None,
                        exclude_cell_ids: set = None) -> str:
        """格式化距離描述（新版：支援中繼地標）"""
        if units == 0:
            return ""
        
        # 嘗試使用精確攤位計數
        booth_count = None
        if start_pos and end_pos and analyzer:
            try:
                booth_count = self.count_passed_booths(start_pos, end_pos, analyzer)
            except:
                pass  # 如果精確計數失敗，退回到估算
        
        # 如果沒有精確計數，使用估算
        if booth_count is None:
            booth_count = self.units_to_booth_count(units)
        
        # 新的距離分級策略
        if units <= 3:
            # 短距離：僅攤位計數
            if booth_count == 0:
                return "走過一小段距離"
            return f"走過 {booth_count} 個攤位"
            
        elif units <= 15:
            # 中距離：使用中繼地標 + 攤位計數
            if start_pos and end_pos and analyzer:
                return self.format_with_intermediate_landmarks(
                    units, start_pos, end_pos, analyzer, booth_count, exclude_cell_ids
                )
            else:
                return f"直走約 {booth_count} 個攤位"
                
        else:  # units > 15
            # 長距離：使用多地標（最多3個，同側優先）
            if start_pos and end_pos and analyzer:
                return self.format_with_multiple_landmarks(
                    units, start_pos, end_pos, analyzer, exclude_cell_ids
                )
            else:
                return "直走較長距離，約 2 分鐘"
    
    def format_with_intermediate_landmarks(self, units: int, start_pos: Tuple[int, int], 
                                         end_pos: Tuple[int, int], analyzer: 'RouteAnalyzer',
                                         booth_count: int, exclude_cell_ids: set = None) -> str:
        """使用單個中繼地標格式化距離"""
        # 檢查穿越地標
        crossing = analyzer.detect_crossing_landmarks(start_pos, end_pos)
        if crossing:
            landmark = crossing[0]  # 選擇最重要的穿越地標
            if booth_count <= 1:
                return f"直走穿越{landmark.get('name', '大型區域')}"
            return f"直走穿越{landmark.get('name', '大型區域')}，約 {booth_count} 個攤位"
        
        # 使用新的覆蓋率系統搜尋中繼地標
        landmarks_with_coverage = analyzer.find_intermediate_landmarks_with_coverage(
            start_pos, end_pos, exclude_cell_ids=exclude_cell_ids
        )
        if landmarks_with_coverage:
            # 選擇覆蓋率最高的地標
            best_landmark = max(landmarks_with_coverage, key=lambda x: x.coverage_ratio)
            side_text = self.get_side_text(best_landmark.side)
            if booth_count <= 1:
                return f"直走經過{side_text}的{best_landmark.cell.get('name', '地標')}"
            return f"直走經過{side_text}的{best_landmark.cell.get('name', '地標')}，約 {booth_count} 個攤位"
        
        # 沒有找到地標，使用原來的格式
        return f"直走約 {booth_count} 個攤位"
    
    def format_with_multiple_landmarks(self, units: int, start_pos: Tuple[int, int], 
                                     end_pos: Tuple[int, int], analyzer: 'RouteAnalyzer',
                                     exclude_cell_ids: set = None) -> str:
        """使用多個地標格式化長距離（基於覆蓋率的三序列選擇）"""
        
        # 生成三個候選序列
        sequences = analyzer.generate_three_sequences(start_pos, end_pos, exclude_cell_ids)
        
        # 使用新的序列選擇策略：優先比較穿越/左右方，低覆蓋率時回退到前方landmark
        best_sequence_name, best_sequence, is_fallback = analyzer.select_best_sequence_with_fallback(sequences)
        
        if not best_sequence:
            return "直走到底，約 2 分鐘"
        
        # 格式化描述
        if is_fallback and "_to_front" in best_sequence_name:
            # 組合序列：經過[低覆蓋率landmark] → 走至[前方landmark]
            if len(best_sequence) >= 2:
                pass_by = best_sequence[0].cell.get('name', '地標')
                target = best_sequence[1].cell.get('name', '地標')
                primary_side = best_sequence_name.split('_to_front')[0]
                side_text = self.get_side_text(primary_side)
                return f"直走經過{side_text}的{pass_by}，走至{target}前，約 2 分鐘"
            else:
                # 回退情況：只有前方landmark
                target = best_sequence[0].cell.get('name', '地標')
                return f"直走走至{target}前，約 2 分鐘"
        elif best_sequence_name == "crossing":
            names = [lm.cell.get('name', '區域') for lm in best_sequence]
            if len(names) == 1:
                return f"直走穿越{names[0]}，約 2 分鐘"
            else:
                return f"直走穿越{self.join_landmarks(names)}，約 2 分鐘"
        elif best_sequence_name == "front":
            # 純前方landmark指引
            names = [lm.cell.get('name', '地標') for lm in best_sequence]
            return f"直走走至{self.join_landmarks(names)}前，約 2 分鐘"
        else:
            # 傳統的左右方landmark
            side_text = self.get_side_text(best_sequence_name)
            names = [lm.cell.get('name', '地標') for lm in best_sequence]
            return f"直走經過{side_text}的{self.join_landmarks(names)}，約 2 分鐘"
    
    def select_best_sequence_by_coverage(self, sequences: Dict[str, List[LandmarkWithCoverage]]) -> Tuple[str, List[LandmarkWithCoverage]]:
        """
        基於平均覆蓋率選擇最佳序列
        
        Args:
            sequences: {"crossing": [...], "left": [...], "right": [...]}
            
        Returns:
            (best_sequence_name, best_sequence)
        """
        best_score = -1
        best_name = None
        best_sequence = []
        
        for name, sequence in sequences.items():
            if not sequence:
                continue
            
            # 計算平均覆蓋率
            avg_coverage = sum(lm.coverage_ratio for lm in sequence) / len(sequence)
            
            if avg_coverage > best_score:
                best_score = avg_coverage
                best_name = name
                best_sequence = sequence
        
        return best_name, best_sequence
    
    def select_best_landmark_sequence(self, candidates: List[Tuple[str, List[Tuple[Dict, str]]]]) -> Tuple[str, List[Tuple[Dict, str]]]:
        """
        選擇最佳地標序列
        
        Args:
            candidates: [(side, landmarks), ...] 候選方案列表
            
        Returns:
            (best_side, best_landmarks) 最佳方案
        """
        if not candidates:
            return None, []
        
        if len(candidates) == 1:
            return candidates[0]
        
        # 計算每個候選方案的得分
        best_score = -1
        best_candidate = candidates[0]
        
        for side, landmarks in candidates:
            if not landmarks:
                continue
                
            # 計算平均面積（area越大越好）
            total_area = 0
            valid_landmarks = 0
            for landmark, _ in landmarks:
                area = landmark.get('unit_w', 1) * landmark.get('unit_h', 1)
                total_area += area
                valid_landmarks += 1
            
            if valid_landmarks == 0:
                continue
                
            avg_area = total_area / valid_landmarks
            
            # 距離合理性評分（這裡假設都已經通過距離過濾，所以都是合理的）
            distance_score = 1.0
            
            # 地標數量得分（更多地標更好，但最多3個）
            count_score = min(len(landmarks) / 3.0, 1.0)
            
            # 總得分 = 平均面積 * 0.5 + 距離得分 * 0.3 + 數量得分 * 0.2
            total_score = avg_area * 0.5 + distance_score * 0.3 + count_score * 0.2
            
            if total_score > best_score:
                best_score = total_score
                best_candidate = (side, landmarks)
        
        return best_candidate
    
    def get_side_text(self, side: str) -> str:
        """獲取方位文字"""
        side_map = {
            "left": "左手邊",
            "right": "右手邊", 
            "front": "前方",
            "behind": "後方"
        }
        return side_map.get(side, "附近")
    
    def join_landmarks(self, names: List[str]) -> str:
        """連接多個地標名稱"""
        if len(names) == 1:
            return names[0]
        elif len(names) == 2:
            return f"{names[0]}、{names[1]}"
        else:
            return f"{names[0]}、{names[1]}、{names[2]}"
    
    def format_landmark(self, landmark: LandmarkInfo) -> str:
        """格式化地標描述"""
        side_map = {
            "left": "左手邊",
            "right": "右手邊", 
            "front": "前方",
            "behind": "後方"
        }
        side_text = side_map.get(landmark.side, "附近")
        return f"{side_text}的 {landmark.name}"
    
    def format_action(self, action: str) -> str:
        """格式化動作描述"""
        action_map = {
            "orient": "面向",
            "turn_left": "左轉",
            "turn_right": "右轉",
            "continue": "繼續直走",
            "arrive": "到達目的地"
        }
        return action_map.get(action, action)
    
    def generate_navigation_text(self, steps: List[NavigationStep], 
                                  unit_path: List[Tuple[int, int]] = None,
                                  analyzer: 'RouteAnalyzer' = None,
                                  route_cells: List[int] = None) -> List[str]:
        """
        生成中文導航指令（改進版：更自然的句型）
        
        Args:
            steps: 導航步驟列表
            unit_path: 單位路徑（用於精確攤位計數）
            analyzer: 路徑分析器（用於精確攤位計數）
            route_cells: 路徑經過的cell序列（用於排除起終點）
            
        Returns:
            中文指令列表
        """
        instructions = []
        path_index = 0  # 追蹤路徑位置
        
        # 建立排除的cell IDs集合（起點和終點）
        exclude_cell_ids = set()
        if route_cells and len(route_cells) >= 2:
            exclude_cell_ids.add(route_cells[0])   # 起點
            exclude_cell_ids.add(route_cells[-1])  # 終點
        
        for step in steps:
            if step.action == "orient":
                if step.landmark:
                    landmark_text = self.format_landmark(step.landmark)
                    if step.landmark.side == "front":
                        instructions.append(f"面向{step.landmark.name}攤位，準備出發。")
                    else:
                        instructions.append(f"以{landmark_text}為參考點，準備出發。")
            
            elif step.action == "arrive":
                if step.landmark:
                    instructions.append(f"目的地就在{self.format_landmark(step.landmark)}。")
                else:
                    instructions.append("已到達目的地。")
            
            elif step.action == "continue":
                # 計算路徑段的起點和終點
                start_pos = None
                end_pos = None
                if unit_path and path_index < len(unit_path):
                    start_pos = unit_path[path_index]
                    end_index = min(path_index + step.distance_units, len(unit_path) - 1)
                    end_pos = unit_path[end_index]
                    path_index = end_index
                
                distance_text = self.format_distance(step.distance_units, start_pos, end_pos, analyzer, exclude_cell_ids)
                if distance_text:
                    instructions.append(f"{distance_text}。")
            
            elif step.action in ["turn_left", "turn_right"]:
                action_text = self.format_action(step.action)
                
                if step.landmark:
                    landmark_text = self.format_landmark(step.landmark)
                    if step.landmark.side == "front":
                        instructions.append(f"走到{step.landmark.name}前{action_text}。")
                    else:
                        instructions.append(f"看到{landmark_text}後{action_text}。")
                else:
                    instructions.append(f"在此處{action_text}。")
        
        return instructions


class NavigationGenerator:
    """導航生成器 - 整合 Analyzer 和 Formatter"""
    
    def __init__(self, grid_file: str = "data/grid.json", 
                 grid_types_file: str = "data/grid_types.json",
                 config: NavigationConfig = None):
        """初始化導航生成器"""
        # 載入資料
        with open(grid_file, 'r', encoding='utf-8') as f:
            self.grid_data = json.load(f)
        
        with open(grid_types_file, 'r', encoding='utf-8') as f:
            self.grid_types = json.load(f)
        
        # 初始化組件
        self.analyzer = RouteAnalyzer(self.grid_data, self.grid_types, config)
        self.formatter = RuleFormatter()
    
    def generate_from_route_result(self, route_result: RouteResult) -> Dict:
        """
        從路徑結果生成導航指令
        
        Args:
            route_result: pathfinder 計算的路徑結果
            
        Returns:
            包含步驟和指令的字典
        """
        # 分析路徑
        steps = self.analyzer.analyze_route(route_result)
        
        # 生成中文指令
        instructions = self.formatter.generate_navigation_text(steps, route_result.unit_path, self.analyzer, route_result.route)
        
        # 轉換步驟為字典格式（用於 JSON 輸出）
        steps_dict = []
        for step in steps:
            step_dict = {
                "step_id": step.step_id,
                "action": step.action,
                "distance_units": step.distance_units
            }
            
            if step.landmark:
                step_dict["landmark"] = {
                    "idx": step.landmark.idx,
                    "name": step.landmark.name,
                    "side": step.landmark.side
                }
            
            if step.direction:
                step_dict["direction"] = step.direction
            
            steps_dict.append(step_dict)
        
        return {
            "steps": steps_dict,
            "instructions": instructions,
            "metadata": {
                "total_steps": len(steps),
                "total_distance_units": route_result.length,
                "estimated_booths": self.formatter.units_to_booth_count(int(route_result.length))
            }
        }
    
    def generate_from_route_file(self, route_file: str, start_idx: int, end_idx: int) -> Dict:
        """
        從路徑檔案生成導航指令
        
        Args:
            route_file: 路徑 JSON 檔案路徑
            start_idx: 起點格子 idx
            end_idx: 終點格子 idx
            
        Returns:
            包含步驟和指令的字典
        """
        with open(route_file, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        # 找到對應的路徑
        target_key = str(end_idx)
        if target_key not in route_data['targets']:
            raise ValueError(f"找不到從 {start_idx} 到 {end_idx} 的路徑")
        
        target_data = route_data['targets'][target_key]
        
        # 構造 RouteResult 對象
        route_result = RouteResult(
            route=target_data['route'],
            unit_path=[(pos[0], pos[1]) for pos in target_data['unit_path']],
            steps=target_data['steps'],
            length=target_data['length'],
            total_cost=target_data['total_cost']
        )
        
        return self.generate_from_route_result(route_result)


def main():
    """命令行介面測試"""
    if len(sys.argv) < 3:
        print("用法: python core/navigation.py <start_idx> <end_idx> [route_file]")
        print("範例: python core/navigation.py 52 10 routes/52_to_all.json")
        return
    
    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    route_file = sys.argv[3] if len(sys.argv) > 3 else f"routes/{start_idx}_to_all.json"
    
    try:
        generator = NavigationGenerator()
        result = generator.generate_from_route_file(route_file, start_idx, end_idx)
        
        print(f"\n=== 從攤位 {start_idx} 到攤位 {end_idx} 的導航指令 ===")
        print(f"總距離: {result['metadata']['total_distance_units']:.1f} units")
        print(f"約等於: {result['metadata']['estimated_booths']} 個攤位")
        print(f"總步驟: {result['metadata']['total_steps']}")
        
        print("\n導航指令:")
        for i, instruction in enumerate(result['instructions'], 1):
            print(f"{i}. {instruction}")
        
        print("\n詳細步驟 (JSON):")
        print(json.dumps(result['steps'], ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"錯誤: {e}")


if __name__ == "__main__":
    main() 