import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import numpy as np
import cv2

@dataclass
class Cell:
    """Represents a single cell in the grid."""
    idx: int
    # Large map coordinates (absolute pixel positions)
    x: int
    y: int
    w: int
    h: int
    # Grid unit coordinates (from detect.ipynb unit field)
    col: int
    row: int
    unit_w: int = 1  # width in grid units
    unit_h: int = 1  # height in grid units
    # Cell properties
    type: str = "unknown"
    name: Optional[str] = None
    booth_id: Optional[str] = None

def_colors = {
    "booth": (128, 208, 128),      # Light green
    "walkway": (221, 221, 221),    # Light grey
    "area": (112, 192, 255),       # Sky blue
    "stage": (112, 192, 255),      # Sky blue
    "entrance": (112, 192, 255),   # Sky blue
    "unknown": (255, 176, 144),    # Pinkish orange
}

def load_grid(path: str = "data/grid.json") -> List[Cell]:
    """Loads grid data from a JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [Cell(**item) for item in data]
    except FileNotFoundError:
        return []

def save_grid(cells: List[Cell], path: str = "data/grid.json"):
    """Saves grid data to a JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump([asdict(c) for c in cells], f, indent=4)

def get_by_idx(cells: List[Cell], idx: int) -> Optional[Cell]:
    """Finds a cell by its index."""
    for cell in cells:
        if cell.idx == idx:
            return cell
    return None

def overlay_grid(image: np.ndarray, cells: List[Cell], show_idx: bool = True, color_map: dict = None) -> np.ndarray:
    """
    Draws the grid overlay on an image.
    Returns a new image with the overlay.
    """
    if color_map is None:
        color_map = def_colors

    overlay = image.copy()
    
    for cell in cells:
        color = color_map.get(cell.type, (0, 0, 255)) # Default to red if type not in map
        top_left = (cell.x, cell.y)
        bottom_right = (cell.x + cell.w, cell.y + cell.h)
        
        # Draw rectangle
        cv2.rectangle(overlay, top_left, bottom_right, color, 2)
        
        if show_idx:
            # Put text (idx) in the center of the box
            text = str(cell.idx)
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            text_x = cell.x + (cell.w - text_size[0]) // 2
            text_y = cell.y + (cell.h + text_size[1]) // 2
            cv2.putText(overlay, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            
    return overlay 

def load_grid_meta(path: str = "data/grid_meta.json") -> dict:
    """Loads grid metadata (unit size, origin, etc.)"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 預設值
        return {
            "unit_w": 186,
            "unit_h": 186, 
            "origin_x": 0,
            "origin_y": 0
        }

def grid_to_pixel(col, row, meta):
    """Convert grid coordinates to pixel coordinates"""
    return (
        meta["origin_x"] + col * meta["unit_w"],
        meta["origin_y"] + row * meta["unit_h"]
    )

def pixel_to_grid(x, y, meta):
    """Convert pixel coordinates to grid coordinates"""
    return (
        round((x - meta["origin_x"]) / meta["unit_w"]),
        round((y - meta["origin_y"]) / meta["unit_h"])
    ) 