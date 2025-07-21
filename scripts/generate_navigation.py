#!/usr/bin/env python3
"""
導航指令生成腳本 - Phase 2 CLI

支援功能：
- 單一路徑導航指令生成
- 批次處理多個目標
- 輸出格式選擇（文字/JSON）
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 將專案根目錄加到 Python 路徑中
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.navigation import NavigationGenerator, NavigationConfig


def load_booth_data():
    """載入攤位詳細資料"""
    booth_data_path = "booth_data_detailed.json"
    grid_data_path = "data/grid.json"
    
    if not os.path.exists(booth_data_path):
        return {}, {}
    
    with open(booth_data_path, 'r', encoding='utf-8') as f:
        booth_data = json.load(f)
    
    with open(grid_data_path, 'r', encoding='utf-8') as f:
        grid_data = json.load(f)
    
    # 建立 booth_id 到廠商列表的映射
    booth_id_to_companies = {}
    for company in booth_data:
        booth_id = company.get('booth_id', '')
        if booth_id:
            if booth_id not in booth_id_to_companies:
                booth_id_to_companies[booth_id] = []
            booth_id_to_companies[booth_id].append(company)
    
    # 建立 idx 到 grid cell 的映射
    idx_to_cell = {cell['idx']: cell for cell in grid_data}
    
    return booth_id_to_companies, idx_to_cell


def get_booth_info(idx: int, booth_id_to_companies: dict, idx_to_cell: dict):
    """獲取攤位資訊"""
    if idx not in idx_to_cell:
        return None
    
    cell = idx_to_cell[idx]
    booth_id = cell.get('booth_id', '')
    grid_name = cell.get('name', f'攤位 {idx}')
    
    companies = booth_id_to_companies.get(booth_id, [])
    
    # 生成 display name
    if companies:
        company_names = [company['name'] for company in companies]
        display_name = f"{grid_name}: {' | '.join(company_names)}"
    else:
        display_name = grid_name
    
    return {
        'idx': idx,
        'booth_id': booth_id,
        'grid_name': grid_name,
        'display_name': display_name,
        'companies': companies
    }


def generate_single_navigation(start_idx: int, end_idx: int, 
                             route_file: str = None, 
                             output_format: str = "text",
                             output_file: str = None,
                             coverage_threshold: float = None,
                             config_file: str = None):
    """
    生成單一路徑的導航指令
    
    Args:
        start_idx: 起點格子 idx
        end_idx: 終點格子 idx
        route_file: 路徑檔案路徑（可選）
        output_format: 輸出格式 ("text" 或 "json")
        output_file: 輸出檔案路徑（可選）
    """
    try:
        # 載入攤位資料
        booth_id_to_companies, idx_to_cell = load_booth_data()
        
        # 初始化導航生成器
        # 創建配置
        if config_file:
            # 從 YAML 文件載入配置
            config = NavigationConfig.from_yaml(config_file)
            # 命令列參數覆蓋配置文件參數
            if coverage_threshold is not None:
                config.sequence_selection["min_coverage_threshold"] = coverage_threshold
        else:
            # 使用默認配置
            config = NavigationConfig()
            if coverage_threshold is not None:
                config.sequence_selection["min_coverage_threshold"] = coverage_threshold
            
        generator = NavigationGenerator(config=config)
        
        # 確定路徑檔案
        if route_file is None:
            route_file = f"routes/{start_idx}_to_all.json"
        
        if not os.path.exists(route_file):
            print(f"錯誤: 找不到路徑檔案 {route_file}")
            return False
        
        # 生成導航指令
        result = generator.generate_from_route_file(route_file, start_idx, end_idx)
        
        # 獲取起點和終點攤位資訊
        start_info = get_booth_info(start_idx, booth_id_to_companies, idx_to_cell)
        end_info = get_booth_info(end_idx, booth_id_to_companies, idx_to_cell)
        
        # 格式化輸出
        if output_format == "text":
            output_text = format_text_output(result, start_info, end_info)
        elif output_format == "json":
            # 添加目標資訊到 JSON
            if end_info:
                result['target_info'] = end_info
            output_text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            print(f"錯誤: 不支援的輸出格式 {output_format}")
            return False
        
        # 輸出結果
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"導航指令已儲存至: {output_file}")
        else:
            print(output_text)
        
        return True
        
    except Exception as e:
        print(f"錯誤: {e}")
        return False


def format_text_output(result: dict, start_info: dict, end_info: dict) -> str:
    """格式化文字輸出"""
    lines = []
    
    # 標題 - 使用 display name
    start_name = start_info['display_name'] if start_info else f"攤位 {result.get('start_idx', '?')}"
    end_name = end_info['display_name'] if end_info else f"攤位 {result.get('end_idx', '?')}"
    lines.append(f"=== 從 {start_name} 到 {end_name} 的導航指令 ===")
    lines.append("")
    
    # 導航指令 (移除統計資訊)
    lines.append("導航指令:")
    for i, instruction in enumerate(result['instructions'], 1):
        lines.append(f"{i}. {instruction}")
    
    return "\n".join(lines)


def generate_batch_navigation(start_idx: int, 
                            target_indices: list = None,
                            route_file: str = None,
                            output_dir: str = "navigation_results",
                            output_format: str = "text",
                            coverage_threshold: float = None,
                            config_file: str = None):
    """
    批次生成多個目標的導航指令
    
    Args:
        start_idx: 起點格子 idx
        target_indices: 目標格子 idx 列表（可選，預設使用路徑檔案中的所有目標）
        route_file: 路徑檔案路徑（可選）
        output_dir: 輸出目錄
        output_format: 輸出格式
    """
    try:
        # 載入攤位資料
        booth_id_to_companies, idx_to_cell = load_booth_data()
        
        # 初始化導航生成器
        # 創建配置
        if config_file:
            # 從 YAML 文件載入配置
            config = NavigationConfig.from_yaml(config_file)
            # 命令列參數覆蓋配置文件參數
            if coverage_threshold is not None:
                config.sequence_selection["min_coverage_threshold"] = coverage_threshold
        else:
            # 使用默認配置
            config = NavigationConfig()
            if coverage_threshold is not None:
                config.sequence_selection["min_coverage_threshold"] = coverage_threshold
            
        generator = NavigationGenerator(config=config)
        
        # 確定路徑檔案
        if route_file is None:
            route_file = f"routes/{start_idx}_to_all.json"
        
        if not os.path.exists(route_file):
            print(f"錯誤: 找不到路徑檔案 {route_file}")
            return False
        
        # 讀取路徑資料
        with open(route_file, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        # 確定目標列表
        if target_indices is None:
            target_indices = [int(k) for k in route_data['targets'].keys()]
        
        # 建立輸出目錄
        Path(output_dir).mkdir(exist_ok=True)
        
        # 批次處理
        success_count = 0
        total_count = len(target_indices)
        
        for end_idx in target_indices:
            try:
                result = generator.generate_from_route_file(route_file, start_idx, end_idx)
                
                # 獲取起點和終點攤位資訊
                start_info = get_booth_info(start_idx, booth_id_to_companies, idx_to_cell)
                end_info = get_booth_info(end_idx, booth_id_to_companies, idx_to_cell)
                
                # 確定輸出檔案
                file_ext = "txt" if output_format == "text" else "json"
                output_file = os.path.join(output_dir, f"nav_{start_idx}_to_{end_idx}.{file_ext}")
                
                # 格式化並儲存
                if output_format == "text":
                    output_text = format_text_output(result, start_info, end_info)
                else:
                    # 添加目標資訊到 JSON
                    if end_info:
                        result['target_info'] = end_info
                    output_text = json.dumps(result, ensure_ascii=False, indent=2)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                
                success_count += 1
                print(f"✓ 已生成: {output_file}")
                
            except Exception as e:
                print(f"✗ 生成失敗 {start_idx} -> {end_idx}: {e}")
        
        print(f"\n批次處理完成: {success_count}/{total_count} 成功")
        print(f"結果儲存於: {output_dir}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"批次處理錯誤: {e}")
        return False


def main():
    """命令行介面"""
    parser = argparse.ArgumentParser(
        description="展場地圖導航指令生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 生成單一路徑導航指令
  python scripts/generate_navigation.py --start 52 --end 10
  
  # 輸出為 JSON 格式
  python scripts/generate_navigation.py --start 52 --end 10 --format json
  
  # 儲存到檔案
  python scripts/generate_navigation.py --start 52 --end 10 --output nav_52_to_10.txt
  
  # 批次生成所有目標的導航指令
  python scripts/generate_navigation.py --start 52 --batch
  
  # 批次生成指定目標
  python scripts/generate_navigation.py --start 52 --batch --targets 10,20,30
        """
    )
    
    parser.add_argument("--start", type=int, required=True,
                       help="起點格子 idx")
    
    parser.add_argument("--end", type=int,
                       help="終點格子 idx（單一路徑模式必須）")
    
    parser.add_argument("--batch", action="store_true",
                       help="批次處理模式")
    
    parser.add_argument("--targets", type=str,
                       help="批次模式的目標列表（逗號分隔）")
    
    parser.add_argument("--route-file", type=str,
                       help="路徑檔案路徑（預設: routes/{start}_to_all.json）")
    
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="輸出格式（預設: text）")
    
    parser.add_argument("--output", type=str,
                       help="輸出檔案路徑（單一路徑模式）")
    
    parser.add_argument("--output-dir", type=str, default="navigation_results",
                       help="批次模式輸出目錄（預設: navigation_results）")
    
    parser.add_argument("--coverage-threshold", type=float, default=None,
                       help="覆蓋率閾值 (0.0-1.0)，低於此值使用前方landmark回退策略")
    
    parser.add_argument("--config", type=str, default=None,
                       help="YAML配置文件路徑 (例: config/high_precision.yaml)")
    
    args = parser.parse_args()
    
    # 驗證參數
    if not args.batch and args.end is None:
        parser.error("單一路徑模式需要指定 --end 參數")
    
    if args.batch and args.end is not None:
        parser.error("批次模式不能同時指定 --end 參數")
    
    # 執行對應模式
    if args.batch:
        # 批次模式
        target_indices = None
        if args.targets:
            try:
                target_indices = [int(x.strip()) for x in args.targets.split(',')]
            except ValueError:
                parser.error("--targets 必須是逗號分隔的整數列表")
        
        success = generate_batch_navigation(
            start_idx=args.start,
            target_indices=target_indices,
            route_file=args.route_file,
            output_dir=args.output_dir,
            output_format=args.format,
            coverage_threshold=args.coverage_threshold,
            config_file=args.config
        )
    else:
        # 單一路徑模式
        success = generate_single_navigation(
            start_idx=args.start,
            end_idx=args.end,
            route_file=args.route_file,
            output_format=args.format,
            output_file=args.output,
            coverage_threshold=args.coverage_threshold,
            config_file=args.config
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 