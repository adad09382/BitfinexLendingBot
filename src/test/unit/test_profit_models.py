"""
收益模型單元測試

測試新創建的放貸收益相關模型功能
"""

import unittest
from datetime import datetime, date
from decimal import Decimal

from src.main.python.models.lending_order import LendingOrder, OrderStatus
from src.main.python.models.interest_payment import InterestPayment, PaymentType
from src.main.python.models.profit_report import ProfitReport, ProfitMetrics, ReportPeriod
from src.main.python.models.portfolio_stats import (
    PortfolioStats, CurrencyAllocation, PeriodAllocation, 
    StrategyAllocation, RiskMetrics
)


class TestLendingOrder(unittest.TestCase):
    """放貸訂單模型測試"""
    
    def setUp(self):
        """設置測試數據"""
        self.order = LendingOrder(
            order_id=12345,
            symbol="fUSD",
            amount=Decimal('1000.0'),
            rate=Decimal('0.0001'),
            period=7
        )
    
    def test_order_creation(self):
        """測試訂單創建"""
        self.assertEqual(self.order.order_id, 12345)
        self.assertEqual(self.order.symbol, "fUSD")
        self.assertEqual(self.order.amount, Decimal('1000.0'))
        self.assertEqual(self.order.rate, Decimal('0.0001'))
        self.assertEqual(self.order.period, 7)
        self.assertEqual(self.order.status, OrderStatus.PENDING)
        self.assertIsNone(self.order.id)
    
    def test_order_status_checks(self):
        """測試訂單狀態檢查"""
        # 初始狀態
        self.assertTrue(self.order.is_active())
        self.assertFalse(self.order.is_completed())
        
        # 執行狀態
        self.order.status = OrderStatus.EXECUTED
        self.assertFalse(self.order.is_active())
        self.assertTrue(self.order.is_completed())
        
        # 取消狀態
        self.order.status = OrderStatus.CANCELLED
        self.assertFalse(self.order.is_active())
        self.assertTrue(self.order.is_completed())
    
    def test_expected_interest_calculation(self):
        """測試預期利息計算"""
        expected = self.order.calculate_expected_interest()
        # 1000 * 0.0001 * 7 = 0.7
        self.assertEqual(expected, Decimal('0.7'))
    
    def test_duration_calculation(self):
        """測試持續時間計算"""
        # 未執行時應返回 None
        self.assertIsNone(self.order.get_duration_days())
        
        # 設置執行和完成時間
        from datetime import timedelta
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        self.order.executed_at = base_time
        self.order.completed_at = base_time + timedelta(days=3)
        
        duration = self.order.get_duration_days()
        self.assertEqual(duration, 3)


class TestInterestPayment(unittest.TestCase):
    """利息收入模型測試"""
    
    def setUp(self):
        """設置測試數據"""
        self.payment = InterestPayment(
            currency="USD",
            amount=Decimal('5.50'),
            paid_at=datetime.now(),
            fee_amount=Decimal('0.50'),
            principal_amount=Decimal('1000.0')
        )
    
    def test_payment_creation(self):
        """測試支付記錄創建"""
        self.assertEqual(self.payment.currency, "USD")
        self.assertEqual(self.payment.amount, Decimal('5.50'))
        self.assertEqual(self.payment.fee_amount, Decimal('0.50'))
        self.assertEqual(self.payment.payment_type, PaymentType.DAILY_INTEREST)
    
    def test_net_amount_calculation(self):
        """測試淨收益計算"""
        net = self.payment.calculate_net_amount()
        self.assertEqual(net, Decimal('5.00'))  # 5.50 - 0.50
    
    def test_effective_rate_calculation(self):
        """測試實際收益率計算"""
        rate = self.payment.calculate_effective_rate()
        self.assertEqual(rate, Decimal('0.005'))  # 5.00 / 1000.0
    
    def test_fee_deduction_check(self):
        """測試手續費扣款檢查"""
        # 正常支付
        self.assertFalse(self.payment.is_fee_deduction())
        
        # 負金額
        self.payment.amount = Decimal('-1.0')
        self.assertTrue(self.payment.is_fee_deduction())
        
        # 懲罰類型
        self.payment.amount = Decimal('1.0')
        self.payment.payment_type = PaymentType.PENALTY
        self.assertTrue(self.payment.is_fee_deduction())


class TestProfitReport(unittest.TestCase):
    """收益報告模型測試"""
    
    def setUp(self):
        """設置測試數據"""
        self.metrics = ProfitMetrics(
            total_interest=Decimal('100.0'),
            total_fees=Decimal('10.0'),
            net_profit=Decimal('90.0'),
            annualized_return=Decimal('0.12'),
            total_orders=10,
            successful_orders=8,
            cancelled_orders=2
        )
        
        self.report = ProfitReport(
            currency="USD",
            period_type=ReportPeriod.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            metrics=self.metrics
        )
    
    def test_report_creation(self):
        """測試報告創建"""
        self.assertEqual(self.report.currency, "USD")
        self.assertEqual(self.report.period_type, ReportPeriod.MONTHLY)
        self.assertEqual(self.report.metrics.net_profit, Decimal('90.0'))
    
    def test_period_days_calculation(self):
        """測試報告期間天數計算"""
        days = self.report.get_period_days()
        self.assertEqual(days, 31)  # 1月有31天
    
    def test_daily_avg_profit_calculation(self):
        """測試日均收益計算"""
        daily_avg = self.report.calculate_daily_avg_profit()
        expected = Decimal('90.0') / 31  # 90 / 31 days
        self.assertAlmostEqual(daily_avg, expected, places=4)
    
    def test_success_rate_calculation(self):
        """測試成功率計算"""
        success_rate = self.report.get_success_rate()
        self.assertEqual(success_rate, Decimal('0.8'))  # 8/10
    
    def test_benchmark_comparison(self):
        """測試基準比較"""
        # 無基準時
        self.assertIsNone(self.report.is_outperforming_benchmark())
        
        # 跑贏基準
        self.report.benchmark_return = Decimal('0.10')
        self.assertTrue(self.report.is_outperforming_benchmark())
        
        # 跑輸基準
        self.report.benchmark_return = Decimal('0.15')
        self.assertFalse(self.report.is_outperforming_benchmark())


class TestPortfolioStats(unittest.TestCase):
    """投資組合統計模型測試"""
    
    def setUp(self):
        """設置測試數據"""
        self.currency_allocs = [
            CurrencyAllocation(
                currency="USD",
                total_amount=Decimal('5000'),
                deployed_amount=Decimal('4500'),
                available_amount=Decimal('500'),
                allocation_percentage=Decimal('50'),
                avg_rate=Decimal('0.0001'),
                total_orders=5
            ),
            CurrencyAllocation(
                currency="BTC", 
                total_amount=Decimal('3000'),
                deployed_amount=Decimal('2800'),
                available_amount=Decimal('200'),
                allocation_percentage=Decimal('30'),
                avg_rate=Decimal('0.0002'),
                total_orders=3
            )
        ]
        
        self.portfolio = PortfolioStats(
            snapshot_date=date.today(),
            total_portfolio_value=Decimal('10000'),
            total_deployed=Decimal('8000'),
            total_available=Decimal('2000'),
            overall_utilization=Decimal('80'),
            target_utilization=Decimal('90'),
            currency_allocations=self.currency_allocs
        )
    
    def test_portfolio_creation(self):
        """測試投資組合創建"""
        self.assertEqual(self.portfolio.total_portfolio_value, Decimal('10000'))
        self.assertEqual(self.portfolio.overall_utilization, Decimal('80'))
        self.assertEqual(len(self.portfolio.currency_allocations), 2)
    
    def test_diversification_score(self):
        """測試分散化評分"""
        score = self.portfolio.get_diversification_score()
        self.assertGreater(score, Decimal('0'))
        self.assertLessEqual(score, Decimal('100'))
    
    def test_efficiency_score(self):
        """測試效率評分"""
        score = self.portfolio.get_efficiency_score()
        # 80/90 * 100 = 88.89
        expected = Decimal('80') / Decimal('90') * 100
        self.assertAlmostEqual(score, expected, places=1)
    
    def test_most_profitable_strategy(self):
        """測試最盈利策略識別"""
        # 無策略分配時
        self.assertIsNone(self.portfolio.get_most_profitable_strategy())
        
        # 添加策略分配
        strategies = [
            StrategyAllocation(
                strategy_name="laddering",
                total_amount=Decimal('5000'),
                allocation_percentage=Decimal('50'),
                order_count=5,
                success_rate=Decimal('0.8'),
                avg_return=Decimal('0.12'),
                last_used=datetime.now()
            ),
            StrategyAllocation(
                strategy_name="market_taker",
                total_amount=Decimal('3000'),
                allocation_percentage=Decimal('30'), 
                order_count=3,
                success_rate=Decimal('0.9'),
                avg_return=Decimal('0.15'),
                last_used=datetime.now()
            )
        ]
        self.portfolio.strategy_allocations = strategies
        
        best = self.portfolio.get_most_profitable_strategy()
        self.assertEqual(best, "market_taker")
    
    def test_risk_level_assessment(self):
        """測試風險級別評估"""
        # 低風險
        self.portfolio.risk_metrics.risk_score = Decimal('10')
        self.assertEqual(self.portfolio.get_risk_level(), "Low Risk")
        
        # 高風險
        self.portfolio.risk_metrics.risk_score = Decimal('85')
        self.assertEqual(self.portfolio.get_risk_level(), "High Risk")
    
    def test_rebalancing_need(self):
        """測試重新平衡需求"""
        # 正常情況
        self.assertFalse(self.portfolio.needs_rebalancing())
        
        # 利用率偏離太多
        self.portfolio.overall_utilization = Decimal('70')  # 偏離目標20%
        self.assertTrue(self.portfolio.needs_rebalancing())
        
        # 重置並測試過度集中
        self.portfolio.overall_utilization = Decimal('85')
        self.portfolio.currency_allocations[0].allocation_percentage = Decimal('80')
        self.assertTrue(self.portfolio.needs_rebalancing())


if __name__ == '__main__':
    # 運行測試
    unittest.main() 