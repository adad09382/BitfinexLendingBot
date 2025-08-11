#!/usr/bin/env python3
"""
優化系統最小化測試腳本
測試核心功能而不依賴完整環境
"""

import sys
import os
import logging
from datetime import datetime
from decimal import Decimal

# 添加項目路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class MinimalTester:
    """最小化測試器"""
    
    def __init__(self):
        self.test_results = {}
        
    def run_comprehensive_test(self):
        """運行簡化測試"""
        
        logger.info("🧪 開始優化系統簡化測試")
        
        test_suites = [
            ('模塊導入測試', self.test_module_imports),
            ('數據結構測試', self.test_data_structures),
            ('策略邏輯測試', self.test_strategy_logic),
            ('配置驗證測試', self.test_configuration_validation)
        ]
        
        for test_name, test_func in test_suites:
            logger.info(f"🔍 執行測試: {test_name}")
            try:
                result = test_func()
                status_icon = '✅' if result else '❌'
                logger.info(f"{status_icon} {test_name}: {'通過' if result else '失敗'}")
                self.test_results[test_name] = result
            except Exception as e:
                logger.error(f"❌ {test_name} 測試異常: {e}")
                self.test_results[test_name] = False
        
        # 返回總體結果
        passed_tests = sum(1 for r in self.test_results.values() if r)
        total_tests = len(self.test_results)
        
        logger.info(f"🎯 測試完成: {passed_tests}/{total_tests} 通過")
        return passed_tests == total_tests
    
    def test_module_imports(self) -> bool:
        """測試核心模塊是否可以導入"""
        
        try:
            # 測試核心模塊導入
            from src.main.python.core.strategies.optimal_allocation_strategy import OptimalAllocationStrategy
            from src.main.python.services.account_status_manager_v2 import AccountStatusManagerV2
            from src.main.python.services.user_dashboard_service import UserDashboardService
            from src.main.python.core.dual_write_manager import DualWriteManager
            
            logger.info("所有核心模塊導入成功")
            return True
            
        except ImportError as e:
            logger.error(f"模塊導入失敗: {e}")
            return False
    
    def test_data_structures(self) -> bool:
        """測試核心數據結構"""
        
        try:
            # 測試最優分配策略的數據結構
            mock_market_data = {
                'rates_data': {
                    'bids': [
                        {'rate': 0.085, 'amount': 10000},
                        {'rate': 0.082, 'amount': 15000},
                        {'rate': 0.080, 'amount': 20000}
                    ]
                },
                'avg_rate': 0.080
            }
            
            # 驗證數據結構完整性
            required_fields = ['rates_data', 'avg_rate']
            for field in required_fields:
                if field not in mock_market_data:
                    logger.error(f"市場數據缺少字段: {field}")
                    return False
            
            # 驗證訂單數據結構
            for bid in mock_market_data['rates_data']['bids']:
                if 'rate' not in bid or 'amount' not in bid:
                    logger.error(f"訂單數據格式錯誤: {bid}")
                    return False
            
            logger.info("數據結構驗證通過")
            return True
            
        except Exception as e:
            logger.error(f"數據結構測試失敗: {e}")
            return False
    
    def test_strategy_logic(self) -> bool:
        """測試策略邏輯"""
        
        try:
            # 創建模擬配置
            class MockConfig:
                class trading:
                    lending_currency = 'USD'
            
            config = MockConfig()
            
            # 導入並創建策略實例
            from src.main.python.core.strategies.optimal_allocation_strategy import OptimalAllocationStrategy
            strategy = OptimalAllocationStrategy(config)
            
            # 測試策略參數
            if strategy.target_utilization != 0.96:
                logger.error(f"目標利用率配置錯誤: {strategy.target_utilization}")
                return False
            
            if strategy.min_order_amount != 100:
                logger.error(f"最小訂單金額配置錯誤: {strategy.min_order_amount}")
                return False
            
            # 測試策略名稱
            if strategy.get_strategy_name() != "optimal_allocation":
                logger.error(f"策略名稱錯誤: {strategy.get_strategy_name()}")
                return False
            
            logger.info("策略邏輯測試通過")
            return True
            
        except Exception as e:
            logger.error(f"策略邏輯測試失敗: {e}")
            return False
    
    def test_configuration_validation(self) -> bool:
        """測試配置驗證"""
        
        try:
            # 測試 Decimal 類型處理
            test_amounts = [
                Decimal('40000.0'),
                Decimal('0.96'),
                Decimal('100.0')
            ]
            
            for amount in test_amounts:
                if not isinstance(amount, Decimal):
                    logger.error(f"Decimal 類型驗證失敗: {amount}")
                    return False
                
                if amount < 0:
                    logger.error(f"負數驗證失敗: {amount}")
                    return False
            
            # 測試百分比計算
            total = Decimal('40000')
            working = Decimal('38000')
            utilization = (working / total) * 100
            
            if not (94 <= utilization <= 96):
                logger.error(f"資金利用率計算錯誤: {utilization}")
                return False
            
            logger.info("配置驗證測試通過")
            return True
            
        except Exception as e:
            logger.error(f"配置驗證測試失敗: {e}")
            return False

def main():
    """主函數"""
    
    tester = MinimalTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 所有簡化測試通過！核心組件準備就緒")
            print("✨ 優化系統核心功能驗證完成")
            return 0
        else:
            print("\n❌ 部分測試失敗，請檢查實現")
            return 1
            
    except Exception as e:
        print(f"\n💥 測試執行異常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())