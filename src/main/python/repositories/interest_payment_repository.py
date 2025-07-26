import logging
from typing import List, Optional
import psycopg2.extras

from src.main.python.services.database_manager import DatabaseManager, handle_database_errors
from src.main.python.models.interest_payment import InterestPayment

log = logging.getLogger(__name__)

class InterestPaymentRepository:
    """
    管理 InterestPayment 對象的數據庫操作，專為 PostgreSQL 設計。
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._create_table_if_not_exists()

    @handle_database_errors
    def _create_table_if_not_exists(self):
        """
        如果 interest_payments 表不存在，則創建它。
        此方法是私有的，應在初始化時調用。
        """
        query = """
        CREATE TABLE IF NOT EXISTS interest_payments (
            id SERIAL PRIMARY KEY,
            ledger_id BIGINT UNIQUE NOT NULL,
            order_id BIGINT,
            currency VARCHAR(10) NOT NULL,
            amount NUMERIC(20, 10) NOT NULL,
            paid_at TIMESTAMPTZ NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        self.db_manager.execute_query(query)
        log.info("Table 'interest_payments' is ready.")

    @handle_database_errors
    def save_payment(self, payment: InterestPayment) -> Optional[InterestPayment]:
        """
        保存單個利息支付記錄。如果記錄已存在（基於 ledger_id），則不執行任何操作。
        
        Args:
            payment: 要保存的 InterestPayment 對象。
            
        Returns:
            如果插入成功，返回帶有數據庫 id 的 InterestPayment 對象，否則返回 None。
        """
        if not payment.ledger_id:
            log.warning("Cannot save payment without a ledger_id.")
            return None

        query = """
        INSERT INTO interest_payments 
        (ledger_id, order_id, currency, amount, paid_at, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (ledger_id) DO NOTHING
        RETURNING id;
        """
        params = (
            payment.ledger_id,
            payment.order_id,
            payment.currency,
            payment.amount,
            payment.paid_at,
            payment.description
        )
        
        result = self.db_manager.execute_query(query, params, fetch='one')
        
        if result:
            payment.id = result[0]
            log.info(f"Saved new interest payment with ledger_id: {payment.ledger_id}")
            return payment
        else:
            log.debug(f"Interest payment with ledger_id {payment.ledger_id} already exists. Skipping.")
            return None

    @handle_database_errors
    def save_payments_batch(self, payments: List[InterestPayment]) -> tuple[int, int]:
        """
        批量保存利息支付記錄列表，並跳過已存在的記錄。
        
        Args:
            payments: InterestPayment 對象的列表。
            
        Returns:
            一個元組 (inserted_count, skipped_count)。
        """
        if not payments:
            return 0, 0

        query = """
        INSERT INTO interest_payments 
        (ledger_id, order_id, currency, amount, paid_at, description)
        VALUES %s
        ON CONFLICT (ledger_id) DO NOTHING;
        """
        
        data_to_insert = [
            (
                p.ledger_id, p.order_id, p.currency, p.amount, 
                p.paid_at, p.description
            )
            for p in payments if p.ledger_id
        ]
        
        if not data_to_insert:
            return 0, len(payments)

        inserted_count = 0
        with self.db_manager.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_values(
                        cur,
                        query,
                        data_to_insert,
                        template=None,
                        page_size=100
                    )
                    inserted_count = cur.rowcount
                conn.commit() # <--- 關鍵修復：提交交易
            except Exception as e:
                log.error(f"Batch insert failed, rolling back transaction: {e}")
                conn.rollback() # <--- 關鍵修復：錯誤時回滾
                raise # 重新拋出異常，讓上層知道出錯了

        skipped_count = len(payments) - inserted_count
        log.info(f"Batch insert complete. Inserted: {inserted_count}, Skipped: {skipped_count}")
        return inserted_count, skipped_count
