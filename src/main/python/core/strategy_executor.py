import logging
from typing import Dict, Any, List, Type
from decimal import Decimal

from src.main.python.core.config import AppConfig
from src.main.python.core.strategies.base_strategy import BaseStrategy
from src.main.python.core.strategies.laddering_strategy import LadderingStrategy
from src.main.python.core.strategies.adaptive_laddering_strategy import AdaptiveLadderingStrategy
from src.main.python.core.strategies.market_taker_strategy import MarketTakerStrategy
from src.main.python.core.strategies.spread_filler_strategy import SpreadFillerStrategy
from src.main.python.core.exceptions import StrategyError

log = logging.getLogger(__name__)

class StrategyExecutor:
    """
    負責根據配置選擇和執行放貸策略。
    """
    def __init__(self, config: AppConfig):
        self.config = config
        self.strategies: Dict[str, Type[BaseStrategy]] = {
            "laddering": LadderingStrategy,
            "adaptive_laddering": AdaptiveLadderingStrategy,
            "market_taker": MarketTakerStrategy,
            "spread_filler": SpreadFillerStrategy
        }
        self.active_strategy: Optional[BaseStrategy] = None
        self._initialize_strategy()

    def _initialize_strategy(self):
        """
        根據配置初始化活動策略。
        """
        strategy_name = self.config.strategy.strategy_name
        strategy_class = self.strategies.get(strategy_name)

        if not strategy_class:
            raise StrategyError(f"Unknown strategy specified in config: {strategy_name}")
        
        try:
            self.active_strategy = strategy_class(self.config)
            log.info(f"Active strategy initialized: {strategy_name}")
        except Exception as e:
            raise StrategyError(f"Failed to initialize strategy {strategy_name}: {e}") from e

    def execute_strategy(self, available_balance: Decimal, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        執行當前活動策略，生成建議的放貸訂單。
        :param available_balance: 可用餘額
        :param market_data: 市場數據 (例如資金簿)
        :return: 建議的放貸訂單列表
        """
        if not self.active_strategy:
            raise StrategyError("No active strategy initialized.")
        
        log.info(f"Executing strategy: {self.active_strategy.get_strategy_name()}")
        try:
            offers = self.active_strategy.generate_offers(available_balance, market_data)
            log.info(f"Strategy {self.active_strategy.get_strategy_name()} generated {len(offers)} offers.")
            return offers
        except Exception as e:
            raise StrategyError(f"Error executing strategy {self.active_strategy.get_strategy_name()}: {e}") from e

    def get_active_strategy_name(self) -> str:
        """
        獲取當前活動策略的名稱。
        """
        if self.active_strategy:
            return self.active_strategy.get_strategy_name()
        return "None"
