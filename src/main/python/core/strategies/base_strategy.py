from abc import ABC, abstractmethod
import logging
import asyncio
from decimal import Decimal
from typing import List, Dict, Any, Optional

from src.main.python.core.config import AppConfig
from src.main.python.core.exceptions import (
    MarketDataError, create_market_data_unavailable_error, handle_api_errors
)
from src.main.python.models.market_log import MarketLog

log = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    所有資金借貸策略的抽象基類
    
    提供策略的通用功能和接口定義
    """
    
    def __init__(self, api_client, config: AppConfig, market_log_repo):
        self.api_client = api_client
        self.config = config
        self.market_log_repo = market_log_repo
        self.lending_currency = config.trading.lending_currency
        self.min_order_amount = config.trading.min_order_amount

    @abstractmethod
    async def generate_offers(self, available_balance: Decimal, market_data: Dict[int, Dict[str, Optional[float]]]) -> List[Dict[str, Any]]:
        """
        根據策略生成資金借貸訂單列表
        
        Args:
            available_balance: 可用餘額
            market_data: 市場數據
            
        Returns:
            訂單列表，每個訂單包含 rate, amount, period 字段
        """
        pass

    @handle_api_errors
    async def analyze_and_log_market(self) -> Optional[Dict[int, Dict[str, Optional[float]]]]:
        """
        分析資金借貸市場，記錄數據並返回市場利率
        
        Returns:
            市場數據字典，格式為 {period: {'bid': rate, 'offer': rate}}
        """
        symbol = f"f{self.lending_currency}"
        log.info(f"Analyzing funding market for {symbol}")
        
        try:
            # 獲取資金訂單簿
            book = await asyncio.to_thread(
                self.api_client.rest.public.get_f_book, 
                symbol, 
                precision="P0", 
                len=100
            )
            
            if not book:
                raise create_market_data_unavailable_error(symbol)
            
            market_rates = {}
            
            # 分析訂單簿數據
            for entry in book:
                period = entry.period
                rate = entry.rate
                amount = entry.amount

                if period not in market_rates:
                    market_rates[period] = {'bid': 0.0, 'offer': float('inf')}

                if amount < 0:  # Bid (借入方)
                    if rate > market_rates[period]['bid']:
                        market_rates[period]['bid'] = rate
                elif amount > 0:  # Offer (借出方)
                    if rate < market_rates[period]['offer']:
                        market_rates[period]['offer'] = rate

            # 清理無效數據
            for period in list(market_rates.keys()):
                if market_rates[period]['bid'] == 0.0:
                    market_rates[period]['bid'] = None
                if market_rates[period]['offer'] == float('inf'):
                    market_rates[period]['offer'] = None

            # 記錄市場數據
            if self.market_log_repo:
                try:
                    market_log = MarketLog(currency=self.lending_currency, rates_data=market_rates)
                    self.market_log_repo.log_market_data(market_log)
                    log.debug(f"Market data logged for {self.lending_currency}")
                except Exception as e:
                    log.warning(f"Failed to log market data: {e}")
            else:
                log.warning("Market log repository not available, data will not be logged")

            # 記錄市場摘要
            periods = sorted(market_rates.keys())
            log.info(f"Market analysis complete for {len(periods)} periods: {periods}")
            
            return market_rates

        except Exception as e:
            log.error(f"Error analyzing funding market for {symbol}: {e}")
            raise MarketDataError(f"Failed to analyze market for {symbol}: {e}") from e
    
    def validate_order_amount(self, amount: Decimal) -> bool:
        """驗證訂單金額是否符合最低要求"""
        return amount >= self.min_order_amount
    
    def get_strategy_name(self) -> str:
        """獲取策略名稱"""
        return self.__class__.__name__
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略信息"""
        return {
            'name': self.get_strategy_name(),
            'currency': self.lending_currency,
            'min_order_amount': float(self.min_order_amount)
        }
