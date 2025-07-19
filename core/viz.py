import json
import numpy as np
from PIL import Image, ImageDraw
import os
import math
from typing import List, Tuple, Dict, Any, Optional

class FloorPlanVisualizer:
    """Floor plan visualization with route drawing capabilities"""
    
    def __init__(self, grid_path: str = "data/grid.json", 
                 grid_meta_path: str = "data/grid_meta.json",
                 grid_types_path: str = "data/grid_types.json",
                 map_path: str = "large_map.png"):
        """Initialize visualizer with grid data and map"""
        
        # Load grid data
        with open(grid_path, 'r', encoding='utf-8') as f:
            self.grid_data = json.load(f)
        
        # Load grid metadata
        with open(grid_meta_path, 'r', encoding='utf-8') as f:
            self.grid_meta = json.load(f)
        
        # Load grid types
        with open(grid_types_path, 'r', encoding='utf-8') as f:
            self.grid_types = json.load(f)
        
        # Create cell lookup by idx
        self.cells_by_idx = {cell['idx']: cell for cell in self.grid_data}
        
        # Load base map
        self.base_map = Image.open(map_path)
        
        # Define type colors (fallback if not in grid_types.json)
        self.default_colors = {
            'booth': (255, 120, 120, 150),      # Light red with alpha
            'road': (120, 255, 120, 100),       # Light green with alpha
            'wall': (80, 80, 80, 200),          # Dark gray with alpha
            'exp hall': (255, 255, 120, 100),   # Light yellow with alpha
            'stage': (255, 180, 60, 150),       # Orange with alpha
            'Lounge': (150, 150, 255, 120),     # Light blue with alpha
            'door': (180, 100, 50, 150),        # Brown with alpha
            'desk': (220, 120, 180, 150),       # Pink with alpha
            'exit_far': (120, 220, 220, 150),   # Cyan with alpha
        }
        
        # Extract unit conversion info
        self.unit_w = self.grid_meta['unit_w']
        self.unit_h = self.grid_meta['unit_h'] 
        self.origin_x = self.grid_meta['origin_x']
        self.origin_y = self.grid_meta['origin_y']
    
    def get_type_color(self, cell_type: str) -> Tuple[int, int, int, int]:
        """Get color for a cell type with alpha"""
        # Try to get from grid_types.json display_color first
        if cell_type in self.grid_types:
            display_color = self.grid_types[cell_type].get('display_color', '')
            if display_color and display_color.startswith('#'):
                # Parse hex color
                hex_color = display_color[1:]
                if len(hex_color) == 6:
                    try:
                        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                        return (*rgb, 150)  # Add alpha
                    except ValueError:
                        pass
        
        # Fallback to default colors
        return self.default_colors.get(cell_type, (128, 128, 128, 150))  # Gray fallback
    
    def unit_to_pixel(self, unit_col: int, unit_row: int) -> Tuple[int, int]:
        """Convert unit coordinates to pixel coordinates"""
        pixel_x = self.origin_x + unit_col * self.unit_w
        pixel_y = self.origin_y + unit_row * self.unit_h
        return pixel_x, pixel_y
    
    def draw_route_on_map(self, route_data: Dict[str, Any], 
                         output_path: str,
                         line_width: int = None,
                         route_color: Tuple[int, int, int] = None,
                         show_grid: bool = None,
                         crop_padding: int = None) -> None:
        """Draw a single route on the map with optional cropping"""
        
        # Use default values if not provided
        line_width = line_width or getattr(self, 'default_line_width', 8)
        route_color = route_color or getattr(self, 'default_route_color', (255, 0, 255))
        show_grid = show_grid if show_grid is not None else getattr(self, 'default_show_grid', True)
        crop_padding = crop_padding if crop_padding is not None else getattr(self, 'default_crop_padding', 200)
        
        # Create a copy of the base map and convert to RGBA for transparency support
        img = self.base_map.copy().convert('RGBA')
        draw = ImageDraw.Draw(img)
        
        # Get route path in unit coordinates
        unit_path = route_data.get('unit_path', [])
        route_cells = route_data.get('route', [])
        
        if not unit_path or len(unit_path) < 2:
            print(f"Warning: Invalid or empty route path")
            return
        
        # Convert unit path to pixel coordinates
        pixel_path = []
        for unit_col, unit_row in unit_path:
            pixel_x, pixel_y = self.unit_to_pixel(unit_col, unit_row)
            pixel_path.append((pixel_x, pixel_y))
        
        # Draw grid cells if requested
        if show_grid:
            # Get start and end cell indices
            start_cell_idx = route_cells[0] if route_cells else None
            end_cell_idx = route_cells[-1] if route_cells else None
            self._draw_all_grid_cells(img, start_cell_idx, end_cell_idx)
        
        # Draw the route line
        if len(pixel_path) >= 2:
            for i in range(len(pixel_path) - 1):
                draw.line([pixel_path[i], pixel_path[i + 1]], 
                         fill=route_color, width=line_width)
        
        # Draw start and end markers
        if pixel_path:
            # Start marker (green circle)
            start_x, start_y = pixel_path[0]
            marker_size = line_width * 2
            draw.ellipse([start_x - marker_size, start_y - marker_size,
                         start_x + marker_size, start_y + marker_size],
                        fill=(0, 255, 0), outline=(0, 0, 0), width=2)
            
            # End marker (red circle)
            end_x, end_y = pixel_path[-1]
            draw.ellipse([end_x - marker_size, end_y - marker_size,
                         end_x + marker_size, end_y + marker_size],
                        fill=(255, 0, 0), outline=(0, 0, 0), width=2)
        
        # Crop the image to focus on the route area
        if crop_padding > 0:
            # Also consider start and end cells in cropping
            start_cell = self.cells_by_idx.get(start_cell_idx) if start_cell_idx else None
            end_cell = self.cells_by_idx.get(end_cell_idx) if end_cell_idx else None
            img = self._crop_to_route(img, pixel_path, crop_padding, start_cell, end_cell)
        
        # Save the result (convert back to RGB to avoid transparency in PNG)
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if path contains a directory
            os.makedirs(output_dir, exist_ok=True)
        # Create white background and paste RGBA image
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, (0, 0), img)
        rgb_img.save(output_path)
        print(f"Route visualization saved to: {output_path}")
    
    def _draw_all_grid_cells(self, img: Image, start_cell_idx: int = None, end_cell_idx: int = None) -> None:
        """Draw all grid cells with type-based colors and 30% transparency"""
        # Create overlay image for transparency
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for cell in self.grid_data:
            cell_idx = cell['idx']
            cell_type = cell.get('type', 'unknown')
            
            # Get cell color
            color = self.get_type_color(cell_type)
            rgb_color = color[:3]
            
            # Set transparency to 30% (77/255 ≈ 0.3)
            transparent_color = (*rgb_color, 77)
            
            # Draw cell rectangle
            x, y, w, h = cell['x'], cell['y'], cell['w'], cell['h']
            
            # Special highlight for start and end cells
            if cell_idx == start_cell_idx or cell_idx == end_cell_idx:
                # More opaque for start/end cells (60% opacity)
                highlight_color = (*rgb_color, 153)
                overlay_draw.rectangle([x, y, x + w, y + h], 
                                     fill=highlight_color, outline=(0, 0, 0), width=4)
            else:
                # Normal transparency for other cells
                overlay_draw.rectangle([x, y, x + w, y + h], 
                                     fill=transparent_color, outline=(100, 100, 100), width=1)
        
        # Composite overlay with base image
        img.paste(overlay, (0, 0), overlay)
    
    def _crop_to_route(self, img: Image, pixel_path: List[Tuple[int, int]], 
                      padding: int, start_cell: dict = None, end_cell: dict = None) -> Image:
        """Crop image to focus on the route area including start/end cells"""
        if not pixel_path:
            return img
        
        # Find bounding box of the route
        min_x = min(x for x, y in pixel_path) - padding
        max_x = max(x for x, y in pixel_path) + padding
        min_y = min(y for x, y in pixel_path) - padding
        max_y = max(y for x, y in pixel_path) + padding
        
        # Include start and end cells in bounding box
        for cell in [start_cell, end_cell]:
            if cell:
                cell_min_x = cell['x']
                cell_max_x = cell['x'] + cell['w']
                cell_min_y = cell['y']
                cell_max_y = cell['y'] + cell['h']
                
                min_x = min(min_x, cell_min_x - padding)
                max_x = max(max_x, cell_max_x + padding)
                min_y = min(min_y, cell_min_y - padding)
                max_y = max(max_y, cell_max_y + padding)
        
        # Clamp to image bounds
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(img.width, max_x)
        max_y = min(img.height, max_y)
        
        return img.crop((min_x, min_y, max_x, max_y))
    
    def visualize_routes_from_file(self, routes_file: str, 
                                  output_dir: str = "visualizations",
                                  limit: Optional[int] = None) -> None:
        """Generate visualizations for all routes in a file"""
        
        with open(routes_file, 'r', encoding='utf-8') as f:
            routes_data = json.load(f)
        
        start_idx = routes_data['start_idx']
        start_cell = routes_data['start_cell']
        targets = routes_data['targets']
        
        print(f"Generating visualizations from {start_cell['name']} (idx: {start_idx})")
        print(f"Total targets: {len(targets)}")
        
        count = 0
        for target_idx, route_data in targets.items():
            if limit and count >= limit:
                break
                
            target_info = route_data['target_info']
            
            # Generate filename
            filename = f"viz_{start_idx}_to_{target_idx}.png"
            output_path = os.path.join(output_dir, filename)
            
            # Draw the route
            self.draw_route_on_map(route_data, output_path)
            
            print(f"Generated: {filename} -> {target_info['name']}")
            count += 1
        
        print(f"Generated {count} route visualizations in {output_dir}/")


def main():
    """Demo function to test visualization"""
    viz = FloorPlanVisualizer()
    
    # Generate first route as test
    viz.visualize_routes_from_file("routes/1_to_all.json", 
                                  output_dir="visualizations",
                                  limit=1)

if __name__ == "__main__":
    main() 