import logging
from typing import Optional

from src.main.python.services.database_manager import DatabaseManager, handle_database_errors
from src.main.python.models.daily_profit import DailyProfit

log = logging.getLogger(__name__)

class DailyProfitRepository:
    """
    管理 DailyProfit 對象的數據庫操作。
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._create_table_if_not_exists()

    @handle_database_errors
    def _create_table_if_not_exists(self):
        """
        如果 daily_profits 表不存在，則創建它。
        """
        query = """
        CREATE TABLE IF NOT EXISTS daily_profits (
            id SERIAL PRIMARY KEY,
            currency VARCHAR(10) NOT NULL,
            interest_income NUMERIC(20, 10) NOT NULL,
            total_loan NUMERIC(20, 10) NOT NULL,
            type VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(currency, date, type)
        );
        """
        self.db_manager.execute_query(query)
        log.info("Table 'daily_profits' is ready.")

    @handle_database_errors
    def save_daily_profit(self, profit: DailyProfit) -> Optional[DailyProfit]:
        """
        保存單個每日收益記錄。如果記錄已存在（基於 currency, date, type），則更新它。
        
        Args:
            profit: 要保存的 DailyProfit 對象。
            
        Returns:
            如果插入或更新成功，返回帶有數據庫 id 的 DailyProfit 對象，否則返回 None。
        """
        query = """
        INSERT INTO daily_profits (currency, interest_income, total_loan, type, date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (currency, date, type) DO UPDATE SET
            interest_income = EXCLUDED.interest_income,
            total_loan = EXCLUDED.total_loan
        RETURNING id;
        """
        params = (
            profit.currency,
            profit.interest_income,
            profit.total_loan,
            profit.type,
            profit.date
        )
        
        result = self.db_manager.execute_query(query, params, fetch='one')
        
        if result:
            profit.id = result[0]
            log.info(f"Saved daily profit for {profit.currency} on {profit.date}")
            return profit
        else:
            log.warning(f"Failed to save daily profit for {profit.currency} on {profit.date}")
            return None
