"""
OCR 模組 - 使用 Ollama 視覺模型進行 booth 資訊識別
支援 JSON Schema 輸出，確保結構化資料品質
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict
import logging

import cv2
import numpy as np
from PIL import Image
import ollama

from .grid import Cell, load_grid, save_grid

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRResult:
    """OCR 識別結果"""
    def __init__(self, name: Optional[str] = None, booth_id: Optional[str] = None, 
                 confidence: float = 0.0, error: Optional[str] = None):
        self.name = name
        self.booth_id = booth_id
        self.confidence = confidence
        self.error = error

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "booth_id": self.booth_id,
            "confidence": self.confidence,
            "error": self.error
        }


class OllamaOCR:
    """Ollama OCR 處理器"""
    
    def __init__(self, model_name: str = "qwen2.5vl:7b", crops_dir: str = "crops"):
        self.model_name = model_name
        self.crops_dir = Path(crops_dir)
        self.crops_dir.mkdir(exist_ok=True)
        
        # JSON Schema 定義
        self.json_schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Booth 或展位的名稱，如公司名稱或產品名稱"
                },
                "booth_id": {
                    "type": ["string", "null"],
                    "description": "Booth 編號或展位編號，可能包含字母和數字"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "識別信心度，0.0-1.0 之間"
                }
            },
            "required": ["name", "confidence"],
            "additionalProperties": False
        }
        
        # 檢查 Ollama 連線
        self._check_ollama_connection()

    def _check_ollama_connection(self) -> bool:
        """檢查 Ollama 服務是否可用"""
        try:
            models = ollama.list()
            available_models = [model['name'] for model in models.get('models', [])]
            
            if self.model_name not in available_models:
                logger.warning(f"模型 {self.model_name} 不在可用模型列表中: {available_models}")
                logger.info(f"請執行: ollama pull {self.model_name}")
                return False
            
            logger.info(f"Ollama 連線成功，使用模型: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Ollama 連線失敗: {e}")
            return False

    def crop_cell_image(self, cell: Cell, source_image_path: str = "large_map.png") -> Optional[str]:
        """
        從大圖中裁切指定格子的區域
        
        Args:
            cell: 要裁切的格子
            source_image_path: 來源圖片路徑
            
        Returns:
            裁切後的圖片檔案路徑，失敗時返回 None
        """
        try:
            # 讀取來源圖片
            image = cv2.imread(source_image_path)
            if image is None:
                logger.error(f"無法讀取圖片: {source_image_path}")
                return None
            
            # 裁切區域 (加一些邊距提高識別效果)
            margin = 10
            x1 = max(0, cell.x - margin)
            y1 = max(0, cell.y - margin)
            x2 = min(image.shape[1], cell.x + cell.w + margin)
            y2 = min(image.shape[0], cell.y + cell.h + margin)
            
            cropped = image[y1:y2, x1:x2]
            
            # 保存裁切圖片
            crop_filename = f"cell_{cell.idx}.png"
            crop_path = self.crops_dir / crop_filename
            
            cv2.imwrite(str(crop_path), cropped)
            logger.debug(f"已裁切格子 {cell.idx} 圖片: {crop_path}")
            
            return str(crop_path)
            
        except Exception as e:
            logger.error(f"裁切格子 {cell.idx} 時發生錯誤: {e}")
            return None

    def _enhance_image(self, image_path: str) -> str:
        """
        優化圖片以提高 OCR 識別效果
        
        Args:
            image_path: 原始圖片路徑
            
        Returns:
            優化後圖片路徑
        """
        try:
            # 讀取圖片
            image = cv2.imread(image_path)
            if image is None:
                return image_path
            
            # 轉為灰階
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 去噪
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # 自適應二值化
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 放大圖片以提高解析度
            height, width = binary.shape
            if width < 200 or height < 200:
                scale_factor = max(200 / width, 200 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                binary = cv2.resize(binary, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # 保存優化後圖片
            enhanced_path = image_path.replace('.png', '_enhanced.png')
            cv2.imwrite(enhanced_path, binary)
            
            return enhanced_path
            
        except Exception as e:
            logger.warning(f"圖片優化失敗: {e}")
            return image_path

    def recognize_cell(self, cell: Cell, source_image_path: str = "large_map.png") -> OCRResult:
        """
        識別單個格子的內容
        
        Args:
            cell: 要識別的格子
            source_image_path: 來源圖片路徑
            
        Returns:
            OCR 識別結果
        """
        try:
            # 裁切圖片
            crop_path = self.crop_cell_image(cell, source_image_path)
            if not crop_path:
                return OCRResult(error="圖片裁切失敗")
            
            # 優化圖片
            enhanced_path = self._enhance_image(crop_path)
            
            # 準備 prompt
            system_prompt = """你是一個專業的 OCR 系統，專門識別展場地圖中的 booth 資訊。
請仔細觀察圖片中的文字內容，提取出：
1. Booth 名稱（公司名稱、產品名稱等）
2. Booth 編號（如 A01, B-12, 123 等）
3. 評估識別的信心度

請只識別清晰可見的文字，不要推測或編造內容。
如果圖片中沒有清晰的文字或只有背景圖案，請將 name 設為 null。"""

            user_prompt = f"""請識別這個 booth 區域的資訊。
返回 JSON 格式，包含：
- name: booth 名稱（字符串，如果沒有清晰文字則為 null）
- booth_id: booth 編號（字符串或 null）
- confidence: 識別信心度（0.0-1.0）

格子資訊：位置 ({cell.x}, {cell.y})，大小 {cell.w}x{cell.h}，類型：{cell.type}"""

            # 呼叫 Ollama API
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                        "images": [os.path.abspath(enhanced_path)]
                    }
                ],
                format=self.json_schema,
                options={
                    "temperature": 0.1,  # 低溫度確保一致性
                    "top_p": 0.9
                }
            )
            
            # 解析回應
            try:
                result_text = response['message']['content']
                result_data = json.loads(result_text)
                
                return OCRResult(
                    name=result_data.get('name'),
                    booth_id=result_data.get('booth_id'),
                    confidence=result_data.get('confidence', 0.0)
                )
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"解析 OCR 回應失敗: {e}")
                logger.error(f"原始回應: {response}")
                return OCRResult(error=f"回應解析失敗: {e}")
                
        except Exception as e:
            logger.error(f"OCR 識別格子 {cell.idx} 時發生錯誤: {e}")
            return OCRResult(error=str(e))
        
        finally:
            # 清理暫存檔案
            try:
                if 'enhanced_path' in locals() and enhanced_path != crop_path:
                    os.remove(enhanced_path)
            except:
                pass

    def process_cells(self, cells: List[Cell], target_types: List[str] = None, 
                     source_image_path: str = "large_map.png") -> Dict[int, OCRResult]:
        """
        批次處理多個格子
        
        Args:
            cells: 要處理的格子列表
            target_types: 要處理的格子類型，None 表示處理 booth 和 unknown
            source_image_path: 來源圖片路徑
            
        Returns:
            格子 idx 到 OCR 結果的映射
        """
        if target_types is None:
            target_types = ["booth", "unknown"]
        
        # 過濾需要處理的格子
        target_cells = [cell for cell in cells if cell.type in target_types]
        
        logger.info(f"開始處理 {len(target_cells)} 個格子 (類型: {target_types})")
        
        results = {}
        
        for i, cell in enumerate(target_cells, 1):
            logger.info(f"處理進度: {i}/{len(target_cells)} - 格子 {cell.idx} (類型: {cell.type})")
            
            result = self.recognize_cell(cell, source_image_path)
            results[cell.idx] = result
            
            # 輸出結果
            if result.error:
                logger.warning(f"格子 {cell.idx} 識別失敗: {result.error}")
            else:
                logger.info(f"格子 {cell.idx} 識別結果: name='{result.name}', booth_id='{result.booth_id}', confidence={result.confidence:.2f}")
        
        return results

    def update_grid_with_ocr_results(self, cells: List[Cell], ocr_results: Dict[int, OCRResult]) -> List[Cell]:
        """
        使用 OCR 結果更新格子資料
        
        Args:
            cells: 原始格子列表
            ocr_results: OCR 識別結果
            
        Returns:
            更新後的格子列表
        """
        updated_cells = []
        updated_count = 0
        
        for cell in cells:
            if cell.idx in ocr_results:
                result = ocr_results[cell.idx]
                
                if not result.error and result.name and result.confidence > 0.3:
                    # 更新格子資訊
                    cell.name = result.name
                    if result.booth_id:
                        cell.booth_id = result.booth_id
                    updated_count += 1
                    logger.debug(f"已更新格子 {cell.idx}: name='{cell.name}', booth_id='{cell.booth_id}'")
            
            updated_cells.append(cell)
        
        logger.info(f"成功更新 {updated_count} 個格子的資訊")
        return updated_cells

    def save_ocr_results(self, ocr_results: Dict[int, OCRResult], output_path: str = "data/ocr_results.json"):
        """
        保存 OCR 結果到檔案
        
        Args:
            ocr_results: OCR 識別結果
            output_path: 輸出檔案路徑
        """
        # 轉換為可序列化的格式
        serializable_results = {
            idx: result.to_dict() for idx, result in ocr_results.items()
        }
        
        # 確保目錄存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存結果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OCR 結果已保存到: {output_path}")

    def load_ocr_results(self, input_path: str = "data/ocr_results.json") -> Dict[int, OCRResult]:
        """
        從檔案載入 OCR 結果
        
        Args:
            input_path: 輸入檔案路徑
            
        Returns:
            OCR 識別結果
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = {}
            for idx_str, result_data in data.items():
                idx = int(idx_str)
                results[idx] = OCRResult(
                    name=result_data.get('name'),
                    booth_id=result_data.get('booth_id'),
                    confidence=result_data.get('confidence', 0.0),
                    error=result_data.get('error')
                )
            
            logger.info(f"從 {input_path} 載入了 {len(results)} 個 OCR 結果")
            return results
            
        except FileNotFoundError:
            logger.warning(f"OCR 結果檔案不存在: {input_path}")
            return {}
        except Exception as e:
            logger.error(f"載入 OCR 結果失敗: {e}")
            return {}


def main():
    """主函數 - 示例用法"""
    # 載入格子資料
    cells = load_grid()
    if not cells:
        logger.error("無法載入格子資料")
        return
    
    # 建立 OCR 處理器
    ocr = OllamaOCR()
    
    # 只處理前 5 個 booth 格子進行測試
    booth_cells = [cell for cell in cells if cell.type == "booth"][:5]
    
    if not booth_cells:
        logger.warning("沒有找到 booth 類型的格子")
        return
    
    logger.info(f"測試處理 {len(booth_cells)} 個 booth 格子")
    
    # 執行 OCR 識別
    results = ocr.process_cells(booth_cells)
    
    # 保存結果
    ocr.save_ocr_results(results)
    
    # 更新格子資料
    updated_cells = ocr.update_grid_with_ocr_results(cells, results)
    
    # 保存更新後的格子資料
    save_grid(updated_cells)
    
    logger.info("OCR 處理完成")


if __name__ == "__main__":
    main() 