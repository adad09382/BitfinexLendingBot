import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from src.main.python.repositories.lending_order_repository import LendingOrderRepository
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.repositories.daily_profit_repository import DailyProfitRepository
from src.main.python.repositories.profit_report_repository import ProfitReportRepository # Assuming this exists or will be created
from src.main.python.models.daily_profit import DailyProfit
from src.main.python.models.profit_report import ProfitReport, ProfitMetrics, ReportPeriod
from src.main.python.models.lending_order import OrderStatus

log = logging.getLogger(__name__)

class ProfitCalculationService:
    """
    負責計算和生成各種收益報告。
    """
    def __init__(self, 
                 lending_order_repo: LendingOrderRepository,
                 interest_payment_repo: InterestPaymentRepository,
                 daily_profit_repo: DailyProfitRepository,
                 profit_report_repo: ProfitReportRepository):
        self.lending_order_repo = lending_order_repo
        self.interest_payment_repo = interest_payment_repo
        self.daily_profit_repo = daily_profit_repo
        self.profit_report_repo = profit_report_repo

    def calculate_daily_profit(self, target_date: date, currency: str) -> DailyProfit:
        """
        計算指定日期和貨幣的每日收益。
        """
        log.info(f"Calculating daily profit for {target_date} in {currency}...")
        
        # 獲取當天所有已支付的利息
        payments_today = self.interest_payment_repo.get_payments_by_date(target_date, currency)
        total_interest_income = sum(p.amount for p in payments_today)

        # 獲取當天所有活躍或已完成的放貸訂單的總金額
        # 這需要更複雜的邏輯來判斷當天實際部署的資金量
        # 簡化處理：獲取當天所有已執行訂單的金額
        orders_executed_today = self.lending_order_repo.get_orders_executed_on_date(target_date, currency)
        total_loan_amount = sum(o.executed_amount or o.amount for o in orders_executed_today if o.executed_amount or o.amount)

        daily_profit = DailyProfit(
            currency=currency,
            interest_income=total_interest_income,
            total_loan=total_loan_amount,
            type="funding", # 假設為資金放貸收益
            date=target_date
        )
        
        self.daily_profit_repo.save_daily_profit(daily_profit)
        log.info(f"Daily profit for {target_date} ({currency}): Interest={total_interest_income:.8f}, Total Loan={total_loan_amount:.2f}")
        return daily_profit

    def generate_profit_report(self, 
                               currency: str, 
                               period_type: ReportPeriod, 
                               start_date: date, 
                               end_date: date) -> ProfitReport:
        """
        生成指定時間範圍和貨幣的綜合收益報告。
        """
        log.info(f"Generating {period_type.value} profit report for {currency} from {start_date} to {end_date}...")

        # 獲取所有相關的利息支付和放貸訂單
        all_payments = self.interest_payment_repo.get_payments_in_range(start_date, end_date, currency)
        all_orders = self.lending_order_repo.get_orders_in_range(start_date, end_date, currency)

        metrics = ProfitMetrics()
        metrics.total_interest = sum(p.amount for p in all_payments)
        # 假設沒有手續費，或者手續費已從 amount 中扣除
        metrics.net_profit = metrics.total_interest

        # 計算平均部署金額和利用率 (簡化)
        total_deployed_sum = Decimal('0')
        for order in all_orders:
            if order.status == OrderStatus.EXECUTED and order.executed_amount:
                total_deployed_sum += order.executed_amount
        metrics.avg_deployed_amount = total_deployed_sum / (end_date - start_date).days if (end_date - start_date).days > 0 else Decimal('0')
        # 利用率計算需要總資產，這裡無法獲取，暫時設為0
        metrics.utilization_rate = Decimal('0')

        # 計算平均放貸利率
        total_rate_amount_product = Decimal('0')
        total_executed_amount = Decimal('0')
        for order in all_orders:
            if order.status == OrderStatus.EXECUTED and order.executed_amount and order.executed_rate:
                total_rate_amount_product += order.executed_amount * order.executed_rate
                total_executed_amount += order.executed_amount
        metrics.avg_lending_rate = total_rate_amount_product / total_executed_amount if total_executed_amount > 0 else Decimal('0')

        # 交易統計
        metrics.total_orders = len(all_orders)
        metrics.successful_orders = len([o for o in all_orders if o.status == OrderStatus.EXECUTED])
        metrics.cancelled_orders = len([o for o in all_orders if o.status == OrderStatus.CANCELLED])
        metrics.avg_order_size = total_executed_amount / metrics.successful_orders if metrics.successful_orders > 0 else Decimal('0')

        # 填充日收益明細 (daily_profits)
        daily_profits_dict = {}
        current_date = start_date
        while current_date <= end_date:
            daily_profit_record = self.daily_profit_repo.get_daily_profit_by_date(current_date, currency)
            if daily_profit_record:
                daily_profits_dict[current_date.isoformat()] = daily_profit_record.interest_income
            else:
                daily_profits_dict[current_date.isoformat()] = Decimal('0')
            current_date += timedelta(days=1)

        # 創建 ProfitReport 實例
        profit_report = ProfitReport(
            currency=currency,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            daily_profits=daily_profits_dict,
            report_generated_at=datetime.now()
        )
        
        # 保存報告 (如果需要持久化)
        self.profit_report_repo.save_profit_report(profit_report)
        log.info(f"Generated {period_type.value} profit report for {currency}. Net Profit: {metrics.net_profit:.8f}")
        return profit_report

    def calculate_and_store_daily_profits_for_range(self, start_date: date, end_date: date, currency: str):
        """
        計算並存儲指定日期範圍內的每日收益。
        """
        log.info(f"Calculating and storing daily profits for {currency} from {start_date} to {end_date}...")
        current_date = start_date
        while current_date <= end_date:
            self.calculate_daily_profit(current_date, currency)
            current_date += timedelta(days=1)
        log.info("Finished calculating daily profits for the range.")
