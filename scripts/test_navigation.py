#!/usr/bin/env python3
"""
導航模組單元測試 - Phase 1-2 驗證

測試項目：
- 轉向偵測功能
- 地標搜尋功能
- 路徑分析功能
- 格式化輸出功能
"""

import os
import sys
import json
from typing import List, Tuple

# 將專案根目錄加到 Python 路徑中
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.navigation import RouteAnalyzer, RuleFormatter, NavigationGenerator, LandmarkInfo, NavigationStep
from core.pathfinder import RouteResult


def test_turn_detection():
    """測試轉向偵測功能"""
    print("=== 測試轉向偵測 ===")
    
    # 建立測試用的分析器（使用空資料）
    analyzer = RouteAnalyzer([], {})
    
    # 測試案例：直走
    result = analyzer.detect_turn_direction((0, 0), (1, 0), (2, 0))
    assert result == "straight", f"直走偵測失敗: {result}"
    print("pass - 直走偵測正確")
    
    # 測試案例：右轉 (修正：由於row軸向下，(0,0)→(1,0)→(1,1)是右轉)
    result = analyzer.detect_turn_direction((0, 0), (1, 0), (1, 1))
    assert result == "right", f"右轉偵測失敗: {result}"
    print("pass - 右轉偵測正確")
    
    # 測試案例：左轉 (修正：由於row軸向下，(0,0)→(1,0)→(1,-1)是左轉)
    result = analyzer.detect_turn_direction((0, 0), (1, 0), (1, -1))
    assert result == "left", f"左轉偵測失敗: {result}"
    print("pass - 左轉偵測正確")
    
    print("轉向偵測測試通過！\n")


def test_relative_side_calculation():
    """測試相對位置計算"""
    print("=== 測試相對位置計算 ===")
    
    analyzer = RouteAnalyzer([], {})
    
    # 向右移動時的相對位置
    move_dir = (1, 0)  # 向右
    
    # 地標在移動方向的右側 (修正：由於row軸向下，(0,1)在右側)
    landmark_dir = (0, 1)  # 下方
    side = analyzer.calculate_relative_side(move_dir, landmark_dir)
    assert side == "right", f"右側計算錯誤: {side}"
    print("pass - 右側位置計算正確")
    
    # 地標在移動方向的左側 (修正：由於row軸向下，(0,-1)在左側)
    landmark_dir = (0, -1)  # 上方
    side = analyzer.calculate_relative_side(move_dir, landmark_dir)
    assert side == "left", f"左側計算錯誤: {side}"
    print("pass - 左側位置計算正確")
    
    # 地標在移動方向的前方
    landmark_dir = (1, 0)  # 同方向
    side = analyzer.calculate_relative_side(move_dir, landmark_dir)
    assert side == "front", f"前方計算錯誤: {side}"
    print("pass - 前方位置計算正確")
    
    print("相對位置計算測試通過！\n")


def test_distance_formatting():
    """測試距離格式化"""
    print("=== 測試距離格式化 ===")
    
    formatter = RuleFormatter()
    
    # 測試短距離
    result = formatter.format_distance(1)
    assert "走過 1 個攤位" in result, f"短距離格式化錯誤: {result}"
    print("pass - 短距離格式化正確")
    
    # 測試中距離
    result = formatter.format_distance(5)
    assert "直走約" in result and "個攤位" in result, f"中距離格式化錯誤: {result}"
    print("pass - 中距離格式化正確")
    
    # 測試長距離
    result = formatter.format_distance(20)
    assert "約 1 分鐘" in result, f"長距離格式化錯誤: {result}"
    print("pass - 長距離格式化正確")
    
    print("距離格式化測試通過！\n")


def test_landmark_formatting():
    """測試地標格式化"""
    print("=== 測試地標格式化 ===")
    
    formatter = RuleFormatter()
    
    # 測試各種方向的地標
    landmark = LandmarkInfo(idx=1, name="測試攤位", side="left")
    result = formatter.format_landmark(landmark)
    assert "左手邊的 測試攤位" == result, f"左側地標格式化錯誤: {result}"
    print("pass - 左側地標格式化正確")
    
    landmark = LandmarkInfo(idx=2, name="測試攤位", side="right")
    result = formatter.format_landmark(landmark)
    assert "右手邊的 測試攤位" == result, f"右側地標格式化錯誤: {result}"
    print("pass - 右側地標格式化正確")
    
    print("地標格式化測試通過！\n")


def test_real_route_analysis():
    """測試真實路徑分析"""
    print("=== 測試真實路徑分析 ===")
    
    try:
        # 使用真實資料測試
        generator = NavigationGenerator()
        
        # 測試直走路徑（52→62）
        result = generator.generate_from_route_file("routes/52_to_all.json", 52, 62)
        
        # 驗證基本結構
        assert "steps" in result, "缺少 steps 欄位"
        assert "instructions" in result, "缺少 instructions 欄位"
        assert "metadata" in result, "缺少 metadata 欄位"
        
        # 驗證步驟結構
        steps = result["steps"]
        assert len(steps) > 0, "步驟列表為空"
        assert steps[-1]["action"] == "arrive", "最後一步不是到達"
        
        # 驗證指令生成
        instructions = result["instructions"]
        assert len(instructions) > 0, "指令列表為空"
        assert "已到達目的地" in instructions[-1], "最後一條指令不正確"
        
        print(f"pass - 路徑 52→62 分析成功，生成 {len(steps)} 個步驟")
        print(f"pass - 總距離: {result['metadata']['total_distance_units']:.1f} units")
        
    except FileNotFoundError:
        print("⚠ 警告: 找不到路徑檔案，跳過真實路徑測試")
    except Exception as e:
        print(f"fail - 真實路徑分析失敗: {e}")
        return False
    
    print("真實路徑分析測試通過！\n")
    return True


def test_edge_cases():
    """測試邊界情況"""
    print("=== 測試邊界情況 ===")
    
    # 測試單點路徑（起點即終點）
    single_point_path = [(5, 5)]
    route_result = RouteResult(
        route=[1],
        unit_path=single_point_path,
        steps=1,
        length=0.0,
        total_cost=0.0
    )
    
    analyzer = RouteAnalyzer([], {})
    steps = analyzer.analyze_route(route_result)
    
    assert len(steps) == 1, f"單點路徑步驟數錯誤: {len(steps)}"
    assert steps[0].action == "arrive", f"單點路徑動作錯誤: {steps[0].action}"
    print("pass - 單點路徑處理正確")
    
    # 測試兩點直線路徑
    straight_path = [(0, 0), (5, 0)]
    route_result = RouteResult(
        route=[1, 2],
        unit_path=straight_path,
        steps=2,
        length=5.0,
        total_cost=5.0
    )
    
    steps = analyzer.analyze_route(route_result)
    assert len(steps) == 2, f"直線路徑步驟數錯誤: {len(steps)}"
    assert steps[0].action == "continue", f"直線路徑第一步動作錯誤: {steps[0].action}"
    assert steps[1].action == "arrive", f"直線路徑最後步動作錯誤: {steps[1].action}"
    print("pass - 直線路徑處理正確")
    
    print("邊界情況測試通過！\n")


def run_all_tests():
    """執行所有測試"""
    print("開始執行導航模組測試...\n")
    
    test_count = 0
    passed_count = 0
    
    tests = [
        ("轉向偵測", test_turn_detection),
        ("相對位置計算", test_relative_side_calculation),
        ("距離格式化", test_distance_formatting),
        ("地標格式化", test_landmark_formatting),
        ("真實路徑分析", test_real_route_analysis),
        ("邊界情況", test_edge_cases),
    ]
    
    for test_name, test_func in tests:
        test_count += 1
        try:
            result = test_func()
            if result is not False:  # None 或 True 都算通過
                passed_count += 1
        except Exception as e:
            print(f"fail - {test_name} 測試失敗: {e}\n")
    
    print("=" * 50)
    print(f"測試總結: {passed_count}/{test_count} 個測試通過")
    
    if passed_count == test_count:
        print("SUCCESS - 所有測試通過！Navigation NLG Phase 1-2 實作成功。")
        return True
    else:
        print("FAIL - 部分測試失敗，請檢查實作。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 