import logging
from typing import Optional
from src.main.python.services.database_manager import DatabaseManager, handle_database_errors
from src.main.python.models.lending_order import LendingOrder, OrderStatus

log = logging.getLogger(__name__)

class LendingOrderRepository:
    """
    管理 LendingOrder 對象的數據庫操作。
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._create_table_if_not_exists()

    @handle_database_errors
    def _create_table_if_not_exists(self):
        """
        如果 lending_orders 表不存在，則創建它。
        """
        query = """
        CREATE TABLE IF NOT EXISTS lending_orders (
            id SERIAL PRIMARY KEY,
            order_id BIGINT UNIQUE NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            amount NUMERIC(20, 10) NOT NULL,
            rate NUMERIC(20, 10) NOT NULL,
            period INT NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            executed_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            executed_amount NUMERIC(20, 10),
            executed_rate NUMERIC(20, 10),
            strategy_name VARCHAR(50),
            strategy_params JSONB
        );
        """
        self.db_manager.execute_query(query)
        log.info("Table 'lending_orders' is ready.")

    @handle_database_errors
    def save(self, order: LendingOrder) -> Optional[LendingOrder]:
        """
        保存或更新一個 LendingOrder 記錄。
        如果記錄已存在（基於 order_id），則更新它。
        """
        query = """
        INSERT INTO lending_orders (
            order_id, symbol, amount, rate, period, status, created_at, 
            executed_at, cancelled_at, completed_at, executed_amount, 
            executed_rate, strategy_name, strategy_params
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO UPDATE SET
            status = EXCLUDED.status,
            executed_at = EXCLUDED.executed_at,
            cancelled_at = EXCLUDED.cancelled_at,
            completed_at = EXCLUDED.completed_at,
            executed_amount = EXCLUDED.executed_amount,
            executed_rate = EXCLUDED.executed_rate
        RETURNING id;
        """
        params = (
            order.order_id, order.symbol, order.amount, order.rate, order.period, 
            order.status.value, order.created_at, order.executed_at, 
            order.cancelled_at, order.completed_at, order.executed_amount, 
            order.executed_rate, order.strategy_name, 
            order.strategy_params and str(order.strategy_params)
        )
        
        result = self.db_manager.execute_query(query, params, fetch='one')
        
        if result:
            order.id = result[0]
            log.info(f"Saved LendingOrder with order_id: {order.order_id}")
            return order
        else:
            log.warning(f"Failed to save LendingOrder with order_id: {order.order_id}")
            return None
