
import asyncio
import logging
from src.main.python.core.config import DatabaseConfig
from src.main.python.services.database_manager import DatabaseManager

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def verify_data():
    """連接到資料庫並驗證 interest_payments 表中的數據。"""
    db_manager = None
    try:
        # 初始化 DatabaseManager
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        
        # 查詢總記錄數
        count_query = "SELECT COUNT(*) FROM interest_payments;"
        count_result = db_manager.execute_query(count_query, fetch='one')
        
        if count_result:
            count = count_result[0]
            logging.info(f"✅ Success! The 'interest_payments' table now contains {count} rows.")
            
            if count > 0:
                # 查詢並打印前 5 條記錄以供抽查
                logging.info("--- Sample of first 5 entries ---")
                sample_query = "SELECT ledger_id, currency, amount, paid_at FROM interest_payments ORDER BY paid_at DESC LIMIT 5;"
                sample_result = db_manager.execute_query(sample_query, fetch='all')
                if sample_result:
                    for row in sample_result:
                        logging.info(f"  Ledger ID: {row[0]}, Currency: {row[1]}, Amount: {row[2]:.8f}, Paid At: {row[3]}")
                logging.info("---------------------------------")
        else:
            logging.error("❌ Failed to get count from 'interest_payments' table.")

    except Exception as e:
        logging.error(f"An error occurred during verification: {e}", exc_info=True)
    finally:
        if db_manager:
            db_manager.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(verify_data())
