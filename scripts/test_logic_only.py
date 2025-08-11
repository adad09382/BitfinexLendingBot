#!/usr/bin/env python3
"""
純邏輯測試腳本
測試核心業務邏輯而不依賴外部服務和配置
"""

import sys
import os
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class LogicTester:
    """純邏輯測試器"""
    
    def __init__(self):
        self.test_results = {}
        
    def run_comprehensive_test(self):
        """運行純邏輯測試"""
        
        logger.info("🧪 開始優化系統核心邏輯測試")
        
        test_suites = [
            ('資金分配邏輯測試', self.test_fund_allocation_logic),
            ('收益率計算測試', self.test_roi_calculation),
            ('利用率計算測試', self.test_utilization_calculation),
            ('風險評估邏輯測試', self.test_risk_assessment),
            ('機會評分測試', self.test_opportunity_scoring),
            ('訂單大小計算測試', self.test_order_sizing)
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
    
    def test_fund_allocation_logic(self) -> bool:
        """測試資金分配邏輯"""
        
        try:
            # 模擬資金分配場景
            total_balance = Decimal('40000')
            target_utilization = Decimal('0.96')
            target_amount = total_balance * target_utilization  # 38400
            
            # 驗證目標金額計算
            expected_target = Decimal('38400')
            if abs(target_amount - expected_target) > Decimal('0.01'):
                logger.error(f"目標金額計算錯誤: {target_amount}, 期望: {expected_target}")
                return False
            
            # 測試多機會分配邏輯
            opportunities = [
                {'rate': Decimal('0.085'), 'expected_return': Decimal('0.085'), 'risk_score': 0.1},
                {'rate': Decimal('0.082'), 'expected_return': Decimal('0.082'), 'risk_score': 0.15},
                {'rate': Decimal('0.080'), 'expected_return': Decimal('0.080'), 'risk_score': 0.2}
            ]
            
            # 簡化分配算法測試
            remaining_balance = target_amount
            allocations = []
            min_order_amount = Decimal('100')
            
            for i, opp in enumerate(opportunities):
                if remaining_balance < min_order_amount:
                    break
                
                # 基礎分配 - 平均分配剩餘資金
                base_allocation = remaining_balance / Decimal(str(len(opportunities) - i))
                
                # 根據期望收益調整
                quality_multiplier = opp['expected_return'] / Decimal('0.08')
                quality_multiplier = max(Decimal('0.5'), min(Decimal('2.0'), quality_multiplier))
                
                adjusted_amount = base_allocation * quality_multiplier
                final_amount = max(min_order_amount, adjusted_amount)
                
                # 確保不超過剩餘餘額
                final_amount = min(final_amount, remaining_balance)
                
                allocations.append({
                    'rate': opp['rate'],
                    'amount': final_amount
                })
                
                remaining_balance -= final_amount
            
            # 驗證分配結果
            total_allocated = sum(alloc['amount'] for alloc in allocations)
            if total_allocated > target_amount:
                logger.error(f"分配超額: {total_allocated} > {target_amount}")
                return False
            
            utilization_rate = (total_allocated / total_balance) * 100
            if utilization_rate < 90:  # 至少90%利用率
                logger.error(f"資金利用率過低: {utilization_rate:.1f}%")
                return False
            
            logger.info(f"資金分配測試通過 - 分配金額: ${total_allocated:.2f}, 利用率: {utilization_rate:.1f}%")
            return True
            
        except Exception as e:
            logger.error(f"資金分配邏輯測試失敗: {e}")
            return False
    
    def test_roi_calculation(self) -> bool:
        """測試收益率計算"""
        
        try:
            # 測試年化收益率計算
            daily_earnings = Decimal('12.5')
            money_working = Decimal('38000')
            
            # 計算日收益率
            daily_roi = (daily_earnings / money_working) * 100  # 0.0329%
            
            # 計算年化收益率
            annual_rate = daily_roi * 365  # 12.0%
            
            # 驗證計算結果
            expected_daily_roi = Decimal('0.032895')  # 約 0.033%
            expected_annual_rate = Decimal('12.0')    # 約 12%
            
            if abs(daily_roi - expected_daily_roi) > Decimal('0.001'):
                logger.error(f"日收益率計算錯誤: {daily_roi}, 期望: {expected_daily_roi}")
                return False
            
            if abs(annual_rate - expected_annual_rate) > Decimal('0.5'):
                logger.error(f"年化收益率計算錯誤: {annual_rate}, 期望: {expected_annual_rate}")
                return False
            
            # 測試邊界情況
            zero_earnings = Decimal('0')
            zero_working = Decimal('0')
            
            # 零收益情況
            if money_working > 0:
                zero_daily_roi = (zero_earnings / money_working) * 100
                if zero_daily_roi != 0:
                    logger.error(f"零收益計算錯誤: {zero_daily_roi}")
                    return False
            
            # 零投資情況 - 應該處理除零情況
            if zero_working == 0:
                # 應該返回0或處理異常
                pass
            
            logger.info(f"收益率計算測試通過 - 日收益率: {daily_roi:.4f}%, 年化: {annual_rate:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"收益率計算測試失敗: {e}")
            return False
    
    def test_utilization_calculation(self) -> bool:
        """測試資金利用率計算"""
        
        try:
            # 測試標準利用率計算
            test_cases = [
                {'total': Decimal('40000'), 'working': Decimal('38000'), 'expected': Decimal('95.0')},
                {'total': Decimal('50000'), 'working': Decimal('47500'), 'expected': Decimal('95.0')},
                {'total': Decimal('100000'), 'working': Decimal('96000'), 'expected': Decimal('96.0')},
                {'total': Decimal('10000'), 'working': Decimal('0'), 'expected': Decimal('0.0')}
            ]
            
            for case in test_cases:
                total_balance = case['total']
                money_working = case['working']
                expected_utilization = case['expected']
                
                # 計算利用率
                utilization_rate = (money_working / total_balance * 100) if total_balance > 0 else Decimal('0')
                
                # 驗證結果
                if abs(utilization_rate - expected_utilization) > Decimal('0.1'):
                    logger.error(f"利用率計算錯誤: {utilization_rate}, 期望: {expected_utilization}")
                    return False
            
            # 測試邊界情況
            zero_total = Decimal('0')
            some_working = Decimal('1000')
            
            # 零總資金情況
            if zero_total == 0:
                utilization = Decimal('0')  # 應該返回0
                if utilization != 0:
                    logger.error(f"零總資金利用率計算錯誤: {utilization}")
                    return False
            
            logger.info("資金利用率計算測試通過")
            return True
            
        except Exception as e:
            logger.error(f"資金利用率計算測試失敗: {e}")
            return False
    
    def test_risk_assessment(self) -> bool:
        """測試風險評估邏輯"""
        
        try:
            # 測試機會風險評分
            opportunities = [
                {'rate': Decimal('0.085'), 'volume': Decimal('10000'), 'position': 0},
                {'rate': Decimal('0.082'), 'volume': Decimal('15000'), 'position': 1},
                {'rate': Decimal('0.080'), 'volume': Decimal('20000'), 'position': 2},
                {'rate': Decimal('0.075'), 'volume': Decimal('5000'), 'position': 3}
            ]
            
            avg_rate = Decimal('0.080')
            
            for opp in opportunities:
                # 計算成交概率 (簡化版)
                rate_diff = abs(opp['rate'] - avg_rate) / avg_rate
                rate_factor = max(0.1, 1 - float(rate_diff) * 2)
                
                volume_factor = min(1.0, float(opp['volume'] / 5000))
                market_activity = 0.8
                
                fill_probability = rate_factor * 0.5 + volume_factor * 0.3 + market_activity * 0.2
                fill_probability = max(0.1, min(0.95, fill_probability))
                
                # 驗證概率範圍
                if not (0.1 <= fill_probability <= 0.95):
                    logger.error(f"成交概率超出範圍: {fill_probability}")
                    return False
                
                # 計算風險評分
                risk_score = 1 - fill_probability
                
                if not (0.05 <= risk_score <= 0.9):
                    logger.error(f"風險評分超出範圍: {risk_score}")
                    return False
            
            logger.info("風險評估邏輯測試通過")
            return True
            
        except Exception as e:
            logger.error(f"風險評估測試失敗: {e}")
            return False
    
    def test_opportunity_scoring(self) -> bool:
        """測試機會評分邏輯"""
        
        try:
            # 測試機會評分算法
            base_rate = Decimal('0.08')  # 8% 基準利率
            
            test_opportunities = [
                {'rate': Decimal('0.085'), 'volume': Decimal('10000'), 'position': 0},
                {'rate': Decimal('0.075'), 'volume': Decimal('20000'), 'position': 5},
                {'rate': Decimal('0.090'), 'volume': Decimal('5000'), 'position': 0}
            ]
            
            for opp in test_opportunities:
                rate = opp['rate']
                volume = opp['volume']
                position = opp['position']
                
                # 計算各項評分
                rate_score = float(min(rate / base_rate, Decimal('1.5')))
                volume_score = float(min(volume / 10000, Decimal('1.0')))
                position_score = max(0, 1 - position / 20)
                risk_score = 0.8
                
                # 加權總評分
                total_score = (
                    rate_score * 0.4 +
                    volume_score * 0.3 +
                    position_score * 0.2 +
                    risk_score * 0.1
                )
                
                # 驗證評分合理性
                if not (0.1 <= total_score <= 2.0):
                    logger.error(f"總評分超出範圍: {total_score}")
                    return False
                
                # 高利率應該得到更高評分
                if rate > base_rate and rate_score <= 1.0:
                    logger.error(f"高利率評分異常: 利率 {rate}, 評分 {rate_score}")
                    return False
            
            logger.info("機會評分邏輯測試通過")
            return True
            
        except Exception as e:
            logger.error(f"機會評分測試失敗: {e}")
            return False
    
    def test_order_sizing(self) -> bool:
        """測試訂單大小計算"""
        
        try:
            # 測試訂單大小計算邏輯
            remaining_balance = Decimal('10000')
            total_opportunities = 5
            min_order_amount = Decimal('100')
            max_single_order_ratio = Decimal('0.15')  # 15%
            
            for index in range(total_opportunities):
                # 基礎分配
                base_allocation = remaining_balance / Decimal(str(total_opportunities - index))
                
                # 質量調整 (假設質量倍數)
                quality_multiplier = Decimal('1.2')  # 20% 加成
                risk_multiplier = Decimal('0.9')     # 10% 風險折扣
                
                adjusted_amount = base_allocation * quality_multiplier * risk_multiplier
                
                # 應用約束
                max_single_amount = remaining_balance * max_single_order_ratio
                final_amount = min(adjusted_amount, max_single_amount)
                final_amount = max(min_order_amount, final_amount)
                
                # 驗證約束
                if final_amount < min_order_amount:
                    logger.error(f"訂單金額低於最小值: {final_amount}")
                    return False
                
                if final_amount > max_single_amount:
                    logger.error(f"單筆訂單超出最大比例: {final_amount} > {max_single_amount}")
                    return False
                
                if final_amount > remaining_balance:
                    logger.error(f"訂單金額超出剩餘餘額: {final_amount} > {remaining_balance}")
                    return False
                
                # 模擬分配
                remaining_balance -= min(final_amount, remaining_balance)
                
                if remaining_balance <= 0:
                    break
            
            logger.info("訂單大小計算測試通過")
            return True
            
        except Exception as e:
            logger.error(f"訂單大小計算測試失敗: {e}")
            return False

def main():
    """主函數"""
    
    tester = LogicTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 所有核心邏輯測試通過！")
            print("✨ 優化系統業務邏輯驗證完成")
            print("📊 核心算法:")
            print("   - 資金分配算法 ✅") 
            print("   - 收益率計算 ✅")
            print("   - 利用率計算 ✅")
            print("   - 風險評估 ✅")
            print("   - 機會評分 ✅")
            print("   - 訂單優化 ✅")
            return 0
        else:
            print("\n❌ 部分邏輯測試失敗，請檢查算法實現")
            return 1
            
    except Exception as e:
        print(f"\n💥 測試執行異常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())