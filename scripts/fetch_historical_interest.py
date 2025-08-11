import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

from dotenv import load_dotenv
from bfxapi import Client

# --路徑設置，確保能導入專案模組 --
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# --路徑設置結束 --

from src.main.python.core.config import get_config_manager, AppConfig
from src.main.python.services.database_manager import DatabaseManager
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.models.interest_payment import InterestPayment

# -- 日誌配置 --
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
log = logging.getLogger("FetchHistory")
# -- 日誌配置結束 --

class HistoricalFetcher:
    """一個用於獲取和存儲歷史利息支付記錄的類。"""

    # Bitfinex API 一次請求返回的最大記錄數
    API_LIMIT = 2500
    # 篩選帳本描述的關鍵字
    INTEREST_KEYWORDS = ["interest payment", "margin funding payment"]

    def __init__(self, config: AppConfig):
        self.config = config
        self.db_manager = DatabaseManager(config.database)
        self.payment_repo = InterestPaymentRepository(self.db_manager)
        self.bfx = Client(
            api_key=self.config.api.key,
            api_secret=self.config.api.secret
        )

    async def fetch_all_interest_payments(self, currency: str):
        """主函數，分頁獲取並存儲指定幣種的所有利息記錄。"""
        log.info(f"Starting historical interest fetch for currency: {currency}")
        
        total_inserted = 0
        total_skipped = 0
        end_mts = int(datetime.now().timestamp() * 1000)

        while True:
            log.info(f"Fetching ledger entries before: {datetime.fromtimestamp(end_mts / 1000)}")
            
            try:
                ledgers = await self._fetch_ledgers_page(currency, end_mts)
                if not ledgers:
                    log.info("No more ledger entries found. Fetch complete.")
                    break

                # 過濾和解析利息支付記錄
                interest_payments = self._filter_and_parse_payments(ledgers)
                log.info(f"Found {len(interest_payments)} interest payments in this batch of {len(ledgers)} ledgers.")

                if interest_payments:
                    # 批量保存到資料庫
                    inserted, skipped = self.payment_repo.save_payments_batch(interest_payments)
                    total_inserted += inserted
                    total_skipped += skipped
                    log.info(f"Batch saved. Inserted: {inserted}, Skipped: {skipped}")
                
                # 更新下一次請求的結束時間戳
                end_mts = ledgers[-1].mts - 1

                # 避免過於頻繁地請求 API
                await asyncio.sleep(2)

            except Exception as e:
                log.error(f"An error occurred during fetch: {e}", exc_info=True)
                break
        
        log.info("--- Historical Fetch Summary ---")
        log.info(f"Total new payments inserted: {total_inserted}")
        log.info(f"Total existing payments skipped: {total_skipped}")
        log.info("----------------------------------")

    async def _fetch_ledgers_page(self, currency: str, end_mts: int) -> List[Dict[str, Any]]:
        """異步獲取單頁的帳本記錄。"""
        return await asyncio.to_thread(
            self.bfx.rest.auth.get_ledgers,
            currency=currency,
            limit=self.API_LIMIT,
            end=end_mts
        )

    def _filter_and_parse_payments(self, ledgers: List[Any]) -> List[InterestPayment]:
        """從帳本記錄中過濾出利息支付並解析為 InterestPayment 對象。"""
        payments = []
        for entry in ledgers:
            # bfxapi 返回的是對象，而不是字典
            description = getattr(entry, 'description', '').lower()
            if any(keyword in description for keyword in self.INTEREST_KEYWORDS):
                try:
                    # 將對象轉換為字典以便 from_ledger_entry 處理
                    entry_dict = entry.__dict__
                    payment = InterestPayment.from_ledger_entry(entry_dict)
                    payments.append(payment)
                except ValueError as e:
                    log.warning(f"Skipping ledger entry due to parsing error: {e}. Entry: {entry}")
        return payments

    def close(self):
        """關閉資料庫連接。"""
        if self.db_manager:
            self.db_manager.close()
            log.info("Database connection closed.")

async def main():
    """腳本主入口。"""
    # 加載 .env 文件
    load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
    
    fetcher = None
    try:
        # 初始化配置和服務
        config = get_config_manager().config
        fetcher = HistoricalFetcher(config)
        
        # 從配置中獲取要查詢的幣種
        currency_to_fetch = config.trading.lending_currency
        
        # 執行獲取
        await fetcher.fetch_all_interest_payments(currency_to_fetch)

    except Exception as e:
        log.critical(f"A critical error occurred: {e}", exc_info=True)
    finally:
        if fetcher:
            fetcher.close()

if __name__ == "__main__":
    # 設置工作目錄到專案根目錄
    os.chdir(project_root)
    asyncio.run(main())
