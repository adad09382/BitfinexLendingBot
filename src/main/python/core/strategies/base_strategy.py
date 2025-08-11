import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from src.main.python.core.config import AppConfig

log = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    所有資金借貸策略的抽象基類
    
    提供策略的通用功能和接口定義
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.lending_currency = config.trading.lending_currency
        self.min_order_amount = config.trading.min_order_amount

    @abstractmethod
    def generate_offers(self, available_balance: Decimal, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根據策略生成資金借貸訂單列表
        
        Args:
            available_balance: 可用餘額
            market_data: 市場數據 (例如從 MarketDataService 獲取的資金簿數據)
            
        Returns:
            訂單列表，每個訂單包含 rate, amount, period 字段
        """
        pass
    
    def validate_order_amount(self, amount: Decimal) -> bool:
        """
        驗證訂單金額是否符合最低要求
        """
        return amount >= self.min_order_amount
    
    def get_strategy_name(self) -> str:
        """
        獲取策略名稱
        """
        return self.__class__.__name__
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        獲取策略信息
        """
        return {
            'name': self.get_strategy_name(),
            'currency': self.lending_currency,
            'min_order_amount': float(self.min_order_amount)
        }
