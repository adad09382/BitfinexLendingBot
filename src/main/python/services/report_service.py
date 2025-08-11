import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from src.main.python.repositories.profit_report_repository import ProfitReportRepository
from src.main.python.repositories.daily_profit_repository import DailyProfitRepository
from src.main.python.models.profit_report import ProfitReport, ReportPeriod
from src.main.python.models.daily_profit import DailyProfit

log = logging.getLogger(__name__)

class ReportService:
    """
    負責從數據庫中檢索和提供各種報告數據。
    """
    def __init__(self, profit_report_repo: ProfitReportRepository, daily_profit_repo: DailyProfitRepository):
        self.profit_report_repo = profit_report_repo
        self.daily_profit_repo = daily_profit_repo

    def get_latest_profit_report(self, currency: str, period_type: ReportPeriod) -> Optional[ProfitReport]:
        """
        獲取最新生成的指定類型和貨幣的收益報告。
        """
        log.info(f"Fetching latest {period_type.value} profit report for {currency}...")
        return self.profit_report_repo.get_latest_report(currency, period_type)

    def get_profit_reports_in_range(self, currency: str, period_type: ReportPeriod, start_date: date, end_date: date) -> List[ProfitReport]:
        """
        獲取指定時間範圍內的所有收益報告。
        """
        log.info(f"Fetching {period_type.value} profit reports for {currency} from {start_date} to {end_date}...")
        return self.profit_report_repo.get_reports_in_range(currency, period_type, start_date, end_date)

    def get_daily_profits_for_chart(self, currency: str, days: int = 30) -> Dict[str, Decimal]:
        """
        獲取用於圖表顯示的每日收益數據。
        :return: 字典，鍵為日期字符串 (YYYY-MM-DD)，值為每日利息收入
        """
        log.info(f"Fetching last {days} days of daily profits for {currency}...")
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        daily_profits_records = self.daily_profit_repo.get_daily_profits_in_range(start_date, end_date, currency)
        
        chart_data = {} 
        current_date = start_date
        while current_date <= end_date:
            found_profit = next((dp for dp in daily_profits_records if dp.date == current_date), None)
            chart_data[current_date.isoformat()] = found_profit.interest_income if found_profit else Decimal('0')
            current_date += timedelta(days=1)
            
        return chart_data

    # 可以添加更多獲取其他報告數據的方法，例如：
    # - get_portfolio_stats_history
    # - get_strategy_performance_breakdown
