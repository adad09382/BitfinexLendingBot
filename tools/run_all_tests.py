#!/usr/bin/env python3
"""
運行所有測試的腳本

包括：
- 配置管理器單元測試
- 主函數測試（可選，因為會進行真實 API 調用）
- 集成測試（可選，因為會進行真實 API 調用）
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 設置項目路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def run_command(cmd, description):
    """運行命令並處理結果"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"執行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            env={**os.environ, 'PYTHONPATH': str(PROJECT_ROOT)}
        )
        
        if result.stdout:
            print(f"輸出:\n{result.stdout}")
        
        if result.stderr:
            print(f"錯誤:\n{result.stderr}")
        
        if result.returncode == 0:
            print(f"✅ {description} 成功")
            return True
        else:
            print(f"❌ {description} 失敗 (退出碼: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ 執行 {description} 時發生異常: {e}")
        return False


def run_config_tests():
    """運行配置管理器測試"""
    tests = [
        ("src/test/unit/test_config_manager.py", "配置管理器單元測試"),
        ("src/test/unit/test_profit_models.py", "收益模型單元測試"),
    ]
    
    results = []
    for test_file, description in tests:
        cmd = [sys.executable, test_file]
        success = run_command(cmd, description)
        results.append(success)
    
    return all(results)


def run_main_function_tests(include_trading=False):
    """運行主函數測試"""
    # 安全測試（只讀操作）
    safe_tests = [
        ("src/test/unit/main_functions/test_get_available_balance.py", "獲取可用餘額測試"),
        ("src/test/unit/main_functions/test_analyze_funding_market.py", "市場分析測試"),
    ]
    
    # 交易測試（會進行真實交易）
    trading_tests = [
        ("src/test/unit/main_functions/test_place_lending_offer.py", "下單測試"),
        ("src/test/unit/main_functions/test_cancel_funding_offer.py", "取消訂單測試"),
        ("src/test/unit/main_functions/test_execute_aggressive_strategy.py", "積極策略測試"),
        ("src/test/unit/main_functions/test_execute_passive_strategy.py", "被動策略測試"),
        ("src/test/unit/main_functions/test_execute_split_strategy.py", "分割策略測試"),
    ]
    
    # 根據參數決定運行哪些測試
    tests = safe_tests
    if include_trading:
        tests.extend(trading_tests)
    
    results = []
    for test_file, description in tests:
        cmd = [sys.executable, test_file]
        success = run_command(cmd, description)
        results.append((description, success))
    
    return results


def run_integration_tests():
    """運行集成測試"""
    cmd = [sys.executable, "src/test/integration/test_funding_bid.py"]
    return run_command(cmd, "集成測試")


def main():
    parser = argparse.ArgumentParser(description="運行 Bitfinex Funding Bot 測試套件")
    parser.add_argument(
        "--include-trading", 
        action="store_true", 
        help="包含會進行真實交易的測試（請謹慎使用）"
    )
    parser.add_argument(
        "--config-only", 
        action="store_true", 
        help="只運行配置測試（最安全）"
    )
    parser.add_argument(
        "--safe-only", 
        action="store_true", 
        help="運行所有安全測試（配置+只讀API測試）"
    )
    
    args = parser.parse_args()
    
    print(f"""
🚀 Bitfinex Funding Bot 測試套件
{'='*60}
項目路徑: {PROJECT_ROOT}
Python 版本: {sys.version}
""")
    
    # 檢查虛擬環境
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 虛擬環境已激活")
    else:
        print("⚠️  建議在虛擬環境中運行測試")
    
    total_tests = 0
    passed_tests = 0
    
    # 1. 總是運行配置測試（安全）
    print(f"\n🔧 第一階段：配置系統測試")
    if run_config_tests():
        passed_tests += 1
    total_tests += 1
    
    if not args.config_only:
        # 2. 運行主函數測試
        if args.include_trading:
            print(f"\n📊 第二階段：主函數測試（包含交易測試）")
            print("⚠️  警告：這將包含會進行真實交易的測試！")
        else:
            print(f"\n📊 第二階段：主函數測試（僅安全測試）")
        
        main_results = run_main_function_tests(include_trading=args.include_trading)
        for description, success in main_results:
            total_tests += 1
            if success:
                passed_tests += 1
        
        # 3. 運行集成測試
        if args.include_trading:
            print(f"\n🔗 第三階段：集成測試")
            if run_integration_tests():
                passed_tests += 1
            total_tests += 1
        else:
            print(f"\n🔗 第三階段：集成測試（已跳過）")
            print("使用 --include-trading 參數來運行包含真實交易的測試")
    
    # 測試總結
    print(f"""
📋 測試總結
{'='*60}
總測試數: {total_tests}
通過測試: {passed_tests}
失敗測試: {total_tests - passed_tests}
成功率: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%

{'✅ 所有測試通過！' if passed_tests == total_tests else '❌ 部分測試失敗'}
""")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main()) 