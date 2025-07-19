import cv2
import numpy as np
import tkinter as tk
from tkinter import simpledialog, messagebox
from functools import partial

from grid import Cell, load_grid, save_grid, get_by_idx, load_grid_meta, grid_to_pixel, pixel_to_grid

# 全域變數
original_image = None
display_image = None
cells = []
next_idx = 1
grid_meta = {}

# 視窗與繪圖狀態
drawing_bbox = False
ref_point_display = []
zoom_factor = 1.0
pan_offset_x, pan_offset_y = 0, 0
panning = False
start_pan_x, start_pan_y = -1, -1

# 顯示設定
MAX_DISPLAY_WIDTH = 1600
MAX_DISPLAY_HEIGHT = 900
WINDOW_NAME = "Grid Annotator - Left: Select/Draw | Right: Pan | Wheel: Zoom | 's' to save"

def redraw_image():
    global display_image, zoom_factor, pan_offset_x, pan_offset_y

    if original_image is None:
        return

    scaled_width = int(original_image.shape[1] * zoom_factor)
    scaled_height = int(original_image.shape[0] * zoom_factor)
    scaled_image = cv2.resize(original_image, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR)

    display_image = np.zeros((MAX_DISPLAY_HEIGHT, MAX_DISPLAY_WIDTH, 3), dtype=np.uint8)

    src_x1 = max(0, int(-pan_offset_x))
    src_y1 = max(0, int(-pan_offset_y))
    src_x2 = min(scaled_width, int(MAX_DISPLAY_WIDTH - pan_offset_x))
    src_y2 = min(scaled_height, int(MAX_DISPLAY_HEIGHT - pan_offset_y))

    dst_x1 = max(0, int(pan_offset_x))
    dst_y1 = max(0, int(pan_offset_y))
    dst_x2 = dst_x1 + (src_x2 - src_x1)
    dst_y2 = dst_y1 + (src_y2 - src_y1)

    if src_x2 > src_x1 and src_y2 > src_y1:
        display_image[dst_y1:dst_y2, dst_x1:dst_x2] = scaled_image[src_y1:src_y2, src_x1:src_x2]

    # Draw existing cells
    for cell in cells:
        draw_cell(display_image, cell)

    cv2.imshow(WINDOW_NAME, display_image)

def draw_cell(image, cell):
    # 使用 grid 座標系統計算位置
    pixel_x, pixel_y = grid_to_pixel(cell.col, cell.row, grid_meta)
    pixel_w = cell.unit_w * grid_meta["unit_w"]
    pixel_h = cell.unit_h * grid_meta["unit_h"]
    
    # Transform to display coordinates
    disp_x1 = int(pixel_x * zoom_factor + pan_offset_x)
    disp_y1 = int(pixel_y * zoom_factor + pan_offset_y)
    disp_x2 = int((pixel_x + pixel_w) * zoom_factor + pan_offset_x)
    disp_y2 = int((pixel_y + pixel_h) * zoom_factor + pan_offset_y)

    # 將線條粗細從 1 改為 2
    cv2.rectangle(image, (disp_x1, disp_y1), (disp_x2, disp_y2), (0, 255, 0), 2)
    
    # Put text
    text = f"{cell.idx}:{cell.type}({cell.col},{cell.row})"
    # 將文字顏色改為黑色 (0, 0, 0)，字體粗細改為 2
    cv2.putText(image, text, (disp_x1 + 5, disp_y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)


def get_cell_at_coords(x_disp, y_disp):
    """Find which cell is at the clicked display coordinates."""
    # Convert display coordinates to original image coordinates
    orig_x = (x_disp - pan_offset_x) / zoom_factor
    orig_y = (y_disp - pan_offset_y) / zoom_factor

    for cell in reversed(cells): # Search from top-most rendered
        if cell.x <= orig_x < (cell.x + cell.w) and cell.y <= orig_y < (cell.y + cell.h):
            return cell
    return None

def edit_cell_dialog(cell):
    """Opens a dialog to edit cell properties or delete."""
    root = tk.Tk()
    root.withdraw() # Hide the main window

    response = messagebox.askyesnocancel(
        "Edit/Delete Cell",
        f"編輯 Cell {cell.idx} (Type: {cell.type}, Name: {cell.name or '無'})\n\n按下 '是' 編輯，'否' 刪除，'取消' 關閉。",
        icon='question'
    )

    if response is True: # Yes, edit
        new_type = simpledialog.askstring("Edit Cell", "Enter new type:", initialvalue=cell.type)
        if new_type is not None:
            cell.type = new_type
        
        new_name = simpledialog.askstring("Edit Cell", "Enter new name:", initialvalue=cell.name or "")
        if new_name is not None:
            cell.name = new_name if new_name else None
        
        # Optionally, allow editing col/row/unit_w/unit_h if needed
        # For now, these are derived from initial bboxes or manual drawing.
        
    elif response is False: # No, delete
        if messagebox.askyesno("Confirm Delete", f"確定要刪除 Cell {cell.idx} 嗎？", icon='warning'):
            global cells
            cells = [c for c in cells if c.idx != cell.idx]
            messagebox.showinfo("Deleted", f"Cell {cell.idx} 已刪除。")
    
    # Redraw in any case to reflect changes (or lack thereof)
    redraw_image()
    root.destroy()

def mouse_callback(event, x, y, flags, param):
    global ref_point_display, drawing_bbox, panning, start_pan_x, start_pan_y
    global zoom_factor, pan_offset_x, pan_offset_y, next_idx

    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_cell = get_cell_at_coords(x, y)
        if clicked_cell:
            edit_cell_dialog(clicked_cell)
        else:
            ref_point_display = [(x, y)]
            drawing_bbox = True

    elif event == cv2.EVENT_LBUTTONUP:
        if drawing_bbox:
            drawing_bbox = False
            ref_point_display.append((x, y))

            x1_disp, y1_disp = ref_point_display[0]
            x2_disp, y2_disp = ref_point_display[1]

            # 轉換為像素座標
            pixel_x1 = (min(x1_disp, x2_disp) - pan_offset_x) / zoom_factor
            pixel_y1 = (min(y1_disp, y2_disp) - pan_offset_y) / zoom_factor
            pixel_x2 = (max(x1_disp, x2_disp) - pan_offset_x) / zoom_factor
            pixel_y2 = (max(y1_disp, y2_disp) - pan_offset_y) / zoom_factor
            
            # 轉換為 grid 座標並對齊到格子邊界
            grid_col1, grid_row1 = pixel_to_grid(pixel_x1, pixel_y1, grid_meta)
            grid_col2, grid_row2 = pixel_to_grid(pixel_x2, pixel_y2, grid_meta)
            
            # 確保是有效的矩形
            min_col, max_col = min(grid_col1, grid_col2), max(grid_col1, grid_col2)
            min_row, max_row = min(grid_row1, grid_row2), max(grid_row1, grid_row2)
            
            # 計算最終的 grid 尺寸
            unit_w = max_col - min_col + 1
            unit_h = max_row - min_row + 1
            
            # 轉換回像素座標存儲
            final_pixel_x, final_pixel_y = grid_to_pixel(min_col, min_row, grid_meta)

            new_cell = Cell(
                idx=next_idx,
                x=int(final_pixel_x), y=int(final_pixel_y),
                w=unit_w * grid_meta["unit_w"],
                h=unit_h * grid_meta["unit_h"],
                col=min_col, row=min_row,
                unit_w=unit_w, unit_h=unit_h
            )
            cells.append(new_cell)
            next_idx += 1
            edit_cell_dialog(new_cell) # Open dialog for the new cell

    elif event == cv2.EVENT_RBUTTONDOWN:
        panning = True
        start_pan_x, start_pan_y = x, y

    elif event == cv2.EVENT_RBUTTONUP:
        panning = False

    elif event == cv2.EVENT_MOUSEWHEEL:
        old_zoom = zoom_factor
        if flags > 0: zoom_factor *= 1.1
        else: zoom_factor /= 1.1
        zoom_factor = max(0.1, min(10.0, zoom_factor))
        
        pan_offset_x = x - (x - pan_offset_x) * (zoom_factor / old_zoom)
        pan_offset_y = y - (y - pan_offset_y) * (zoom_factor / old_zoom)
        redraw_image()

    elif event == cv2.EVENT_MOUSEMOVE: # Corrected: single MOUSEMOVE check
        if drawing_bbox:
            temp_display_image = display_image.copy()
            cv2.rectangle(temp_display_image, ref_point_display[0], (x, y), (0, 0, 255), 2)
            cv2.imshow(WINDOW_NAME, temp_display_image)
        elif panning: # Now correctly an elif inside MOUSEMOVE block
            dx = x - start_pan_x
            dy = y - start_pan_y
            pan_offset_x += dx
            pan_offset_y += dy
            start_pan_x, start_pan_y = x, y
            redraw_image()


def main(image_path, grid_path):
    global original_image, cells, next_idx, zoom_factor, pan_offset_x, pan_offset_y, grid_meta

    original_image = cv2.imread(image_path)
    if original_image is None:
        print(f"Error: Cannot load image at {image_path}")
        return

    # 載入 grid 和 meta 資料
    cells = load_grid(grid_path)
    grid_meta = load_grid_meta(grid_path.replace('grid.json', 'grid_meta.json'))
    print(f"Grid meta: {grid_meta}")
    
    if cells:
        next_idx = max(c.idx for c in cells) + 1 if cells else 1

    h, w = original_image.shape[:2]
    if w > MAX_DISPLAY_WIDTH or h > MAX_DISPLAY_HEIGHT:
        zoom_factor = min(MAX_DISPLAY_WIDTH / w, MAX_DISPLAY_HEIGHT / h)

    pan_offset_x = (MAX_DISPLAY_WIDTH - int(w * zoom_factor)) // 2
    pan_offset_y = (MAX_DISPLAY_HEIGHT - int(h * zoom_factor)) // 2

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    redraw_image()

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_grid(cells, grid_path)
            print(f"Grid saved to {grid_path}")
            
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grid Annotation Tool")
    parser.add_argument("image", help="Path to the large map image.")
    parser.add_argument("--grid", default="data/grid.json", help="Path to the grid JSON file.")
    args = parser.parse_args()
    
    main(args.image, args.grid) 