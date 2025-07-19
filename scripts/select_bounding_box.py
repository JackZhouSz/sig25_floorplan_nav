import cv2
import numpy as np

# 全域變數來儲存選取框的起點和終點，以及繪圖狀態
ref_point_display = [] # 儲存顯示圖片上的選取點
drawing_bbox = False
panning = False
start_pan_x, start_pan_y = -1, -1

# 圖片相關的全域變數
original_image = None
current_display_image = None # 實際顯示在視窗上的圖像
zoom_factor = 1.0
pan_offset_x, pan_offset_y = 0, 0

# 最大顯示尺寸 (用於初始縮放和視窗大小)
MAX_DISPLAY_WIDTH = 1200
MAX_DISPLAY_HEIGHT = 800

def redraw_image():
    global original_image, current_display_image, zoom_factor, pan_offset_x, pan_offset_y, ref_point_display, drawing_bbox

    if original_image is None:
        return

    # 1. 應用縮放
    scaled_width = int(original_image.shape[1] * zoom_factor)
    scaled_height = int(original_image.shape[0] * zoom_factor)

    # 確保縮放後的尺寸至少為 1x1
    scaled_width = max(1, scaled_width)
    scaled_height = max(1, scaled_height)

    scaled_image = cv2.resize(original_image, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR)

    # 2. 應用平移 (裁剪或填充到顯示視窗大小)
    # 限制平移範圍，防止圖像移出顯示區域太多
    pan_offset_x = int(np.clip(pan_offset_x, -(scaled_width - 1), MAX_DISPLAY_WIDTH - 1))
    pan_offset_y = int(np.clip(pan_offset_y, -(scaled_height - 1), MAX_DISPLAY_HEIGHT - 1))

    # 創建一個空白的畫布作為顯示區域
    current_display_image = np.zeros((MAX_DISPLAY_HEIGHT, MAX_DISPLAY_WIDTH, 3), dtype=np.uint8)

    # 計算從 scaled_image 中提取的區域和在 current_display_image 中貼上的位置
    # 源圖像的裁剪區域 (從 scaled_image 中取的部分)
    src_x1 = max(0, -pan_offset_x)
    src_y1 = max(0, -pan_offset_y)
    src_x2 = min(scaled_width, MAX_DISPLAY_WIDTH - pan_offset_x)
    src_y2 = min(scaled_height, MAX_DISPLAY_HEIGHT - pan_offset_y)

    # 目標畫布的貼上區域 (在 current_display_image 中貼上的位置)
    dst_x1 = max(0, pan_offset_x)
    dst_y1 = max(0, pan_offset_y)
    dst_x2 = dst_x1 + (src_x2 - src_x1)
    dst_y2 = dst_y1 + (src_y2 - src_y1)
    
    # 進行複製操作，將 scaled_image 的部分內容貼到 current_display_image 上
    if src_x2 > src_x1 and src_y2 > src_y1:
        current_display_image[dst_y1:dst_y2, dst_x1:dst_x2] = \
            scaled_image[src_y1:src_y2, src_x1:src_x2]

    # 如果正在繪製 bounding box，繪製預覽框
    if drawing_bbox and len(ref_point_display) == 2:
        pt1 = ref_point_display[0]
        pt2 = ref_point_display[1]
        cv2.rectangle(current_display_image, pt1, pt2, (0, 255, 0), 2)

    cv2.imshow("image", current_display_image)

def mouse_callback(event, x, y, flags, param):
    global ref_point_display, drawing_bbox, panning, start_pan_x, start_pan_y
    global zoom_factor, pan_offset_x, pan_offset_y, original_image

    # ====== 左鍵：Bounding Box 選擇處理 ====== #
    if event == cv2.EVENT_LBUTTONDOWN:
        ref_point_display = [(x, y)]
        drawing_bbox = True

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing_bbox:
            # 繪製臨時預覽框
            temp_display_image = current_display_image.copy()
            cv2.rectangle(temp_display_image, ref_point_display[0], (x, y), (0, 255, 0), 2)
            cv2.imshow("image", temp_display_image)

    elif event == cv2.EVENT_LBUTTONUP:
        ref_point_display.append((x, y))
        drawing_bbox = False

        # 繪製最終選取框並印出坐標
        redraw_image() # 繪製最終框，因為移動時是繪製在 copy 上

        x1_display, y1_display = ref_point_display[0]
        x2_display, y2_display = ref_point_display[1]

        # 確保坐標是左上角和右下角
        min_x_display = min(x1_display, x2_display)
        max_x_display = max(x1_display, x2_display)
        min_y_display = min(y1_display, y2_display)
        max_y_display = max(y1_display, y2_display)

        # 將顯示坐標轉換回原始圖片坐標 (考慮平移和縮放)
        original_min_x = int((min_x_display - pan_offset_x) / zoom_factor)
        original_min_y = int((min_y_display - pan_offset_y) / zoom_factor)
        original_max_x = int((max_x_display - pan_offset_x) / zoom_factor)
        original_max_y = int((max_y_display - pan_offset_y) / zoom_factor)
        
        # 計算寬度和高度
        original_width = original_max_x - original_min_x
        original_height = original_max_y - original_min_y

        print(f"選取的 bounding box 坐標 (基於原始圖片，格式: x, y, 寬度, 高度):")
        print(f"  ({original_min_x}, {original_min_y}, {original_width}, {original_height})")
        print("\n請關閉圖片視窗以結束程式。")

    # ====== 右鍵：平移處理 ====== #
    elif event == cv2.EVENT_RBUTTONDOWN:
        panning = True
        start_pan_x, start_pan_y = x, y

    elif event == cv2.EVENT_MOUSEMOVE and panning:
        dx = x - start_pan_x
        dy = y - start_pan_y
        pan_offset_x += dx
        pan_offset_y += dy
        start_pan_x, start_pan_y = x, y
        redraw_image()

    elif event == cv2.EVENT_RBUTTONUP:
        panning = False

    # ====== 滾輪：縮放處理 ====== #
    elif event == cv2.EVENT_MOUSEWHEEL:
        old_zoom_factor = zoom_factor
        # flags // 120 判斷滾輪方向 (120 為向上，-120 為向下)
        if flags > 0: # 滾輪向上放大
            zoom_factor *= 1.1
        else: # 滾輪向下縮小
            zoom_factor /= 1.1
        
        # 限制縮放範圍，防止過度縮放
        zoom_factor = max(0.1, min(10.0, zoom_factor)) # 最小 0.1 倍，最大 10 倍

        # 調整 pan_offset 以實現以滑鼠游標為中心的縮放
        pan_offset_x = x - ((x - pan_offset_x) / old_zoom_factor) * zoom_factor
        pan_offset_y = y - ((y - pan_offset_y) / old_zoom_factor) * zoom_factor
        
        redraw_image()

if __name__ == "__main__":
    image_path = 'large_map.png' # 您的大張照片
    original_image = cv2.imread(image_path)

    if original_image is None:
        print(f"錯誤：無法載入圖片: {image_path}")
    else:
        # 根據圖片大小初始化 zoom_factor 和 pan_offset
        (h_orig, w_orig) = original_image.shape[:2]

        if w_orig > MAX_DISPLAY_WIDTH or h_orig > MAX_DISPLAY_HEIGHT:
            r_width = MAX_DISPLAY_WIDTH / float(w_orig)
            r_height = MAX_DISPLAY_HEIGHT / float(h_orig)
            zoom_factor = min(r_width, r_height)
            print(f"圖片過大，已初始縮放為 {zoom_factor:.2f} 倍以適應螢幕顯示。")
        else:
            zoom_factor = 1.0
            print("圖片大小適中，無需初始縮放。")
        
        # 初始平移量，使圖片居中顯示
        scaled_width_initial = int(w_orig * zoom_factor)
        scaled_height_initial = int(h_orig * zoom_factor)

        pan_offset_x = (MAX_DISPLAY_WIDTH - scaled_width_initial) // 2
        pan_offset_y = (MAX_DISPLAY_HEIGHT - scaled_height_initial) // 2

        cv2.namedWindow("image")
        cv2.setMouseCallback("image", mouse_callback)

        redraw_image() # 第一次繪製圖像

        cv2.waitKey(0)
        cv2.destroyAllWindows() 