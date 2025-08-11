import logging
from typing import List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal

from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.repositories.market_log_repository import MarketLogRepository
from src.main.python.models.market_log import MarketLog
from src.main.python.core.exceptions import BitfinexAPIError, DatabaseError

log = logging.getLogger(__name__)

class MarketDataService:
    """
    負責從 Bitfinex 獲取市場數據並將其存儲到數據庫。
    """
    def __init__(self, bitfinex_api_client: BitfinexApiClient, market_log_repository: MarketLogRepository):
        self.api_client = bitfinex_api_client
        self.market_log_repository = market_log_repository

    def fetch_and_store_funding_book(self, symbol: str, precision: str = 'P0', limit: int = 50) -> Optional[MarketLog]:
        """
        獲取指定資金對的資金簿並存儲。
        :param symbol: 資金對符號 (例如 'fUSD')
        :param precision: 精度 (例如 'P0', 'P1')
        :param limit: 限制返回的條目數量
        :return: 存儲的 MarketLog 對象，如果失敗則為 None
        """
        try:
            log.info(f"Fetching funding book for {symbol}...")
            funding_book_data = self.api_client.get_funding_book(symbol, precision, limit)
            
            if not funding_book_data:
                log.warning(f"No funding book data received for {symbol}.")
                return None

            # 資金簿數據通常是 bids 和 asks 列表
            # 為了簡化存儲，我們將其作為 JSONB 存儲
            market_log = MarketLog(
                currency=symbol,
                rates_data=funding_book_data,
                timestamp=datetime.now()
            )
            
            self.market_log_repository.save_market_log(market_log)
            log.info(f"Successfully fetched and stored funding book for {symbol}.")
            return market_log
        except BitfinexAPIError as e:
            log.error(f"Failed to fetch funding book from Bitfinex for {symbol}: {e}")
            return None
        except DatabaseError as e:
            log.error(f"Failed to store funding book for {symbol} in database: {e}")
            return None
        except Exception as e:
            log.error(f"An unexpected error occurred while fetching/storing funding book for {symbol}: {e}")
            return None

    def fetch_and_store_tickers(self, symbols: List[str]) -> List[MarketLog]:
        """
        獲取指定交易對的 ticker 信息並存儲。
        :param symbols: 交易對符號列表 (例如 ['tBTCUSD', 'fUSD'])
        :return: 存儲的 MarketLog 對象列表
        """
        stored_logs = []
        try:
            log.info(f"Fetching tickers for symbols: {symbols}...")
            tickers_data = self.api_client.get_tickers(symbols)

            if not tickers_data:
                log.warning(f"No ticker data received for symbols: {symbols}.")
                return []

            for ticker_info in tickers_data:
                # Bitfinex ticker 響應是一個列表，需要解析
                # 示例: ['tBTCUSD', 123.4, 567.8, ..., 0.00123, 12345.6]
                # 假設第一個元素是符號
                symbol = ticker_info[0]
                
                market_log = MarketLog(
                    currency=symbol,
                    rates_data={"ticker": ticker_info}, # 將整個 ticker 數據作為 JSONB 存儲
                    timestamp=datetime.now()
                )
                try:
                    self.market_log_repository.save_market_log(market_log)
                    stored_logs.append(market_log)
                    log.debug(f"Stored ticker data for {symbol}.")
                except DatabaseError as e:
                    log.error(f"Failed to store ticker data for {symbol} in database: {e}")
        except BitfinexAPIError as e:
            log.error(f"Failed to fetch tickers from Bitfinex for {symbols}: {e}")
        except Exception as e:
            log.error(f"An unexpected error occurred while fetching/storing tickers for {symbols}: {e}")
        return stored_logs

    # 可以添加更多獲取和存儲其他市場數據的方法，例如歷史交易、蠟燭圖等
