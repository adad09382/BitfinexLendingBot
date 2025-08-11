import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class AdaptiveLadderingStrategy(BaseStrategy):
    """
    An adaptive strategy that adjusts its parameters based on recent market conditions.
    """
    def __init__(self, config):
        super().__init__(config)
        self.lending_duration = config.trading.lending_duration_days
        self.lookback_period_hours = config.strategy.al_lookback_period_hours
        self.volatility_spread_multiplier = config.strategy.al_volatility_spread_multiplier
        self.num_ladders = config.strategy.laddering_ladders

    def generate_offers(self, available_balance: Decimal, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates laddered offers with dynamically adjusted rate and spread.
        
        Args:
            available_balance: 可用餘額
            market_data: 資金簿數據 (例如從 MarketDataService 獲取的原始資金簿數據)
            
        Returns:
            訂單列表，每個訂單包含 rate, amount, period 字段
        """
        log.info("Executing Adaptive Laddering Strategy.")

        # 從資金簿數據中提取最佳買入利率 (bid rate)
        best_bid_rate = None
        if 'bids' in market_data and market_data['bids']:
            for entry in market_data['bids']:
                # entry format: [RATE, AMOUNT, PERIOD]
                rate = Decimal(str(entry[0]))
                period = int(entry[2])
                
                if period == self.lending_duration:
                    if best_bid_rate is None or rate > best_bid_rate:
                        best_bid_rate = rate
        
        if best_bid_rate is None:
            log.error(f"No bid rate available for the {self.lending_duration}-day period. Aborting offer generation.")
            return []

        base_rate = best_bid_rate
        log.info(f"Determined base rate: {base_rate*100:.4f}%")

        # 簡化：使用配置中的乘數作為固定點差，因為策略不再直接處理歷史波動率
        dynamic_rate_spread = self.volatility_spread_multiplier * Decimal('0.00001') # 假設一個小的基礎點差
        log.info(f"Calculated dynamic rate spread: {dynamic_rate_spread*100:.4f}%")

        # 生成報價
        offers = []
        amount_per_ladder = available_balance / self.num_ladders
        if amount_per_ladder < self.min_order_amount:
            log.warning(f"Calculated amount per ladder ({amount_per_ladder:.2f}) is below the {self.min_order_amount} minimum. Adjusting number of ladders.")
            self.num_ladders = int(available_balance // self.min_order_amount)
            if self.num_ladders == 0:
                log.error("Available balance is too low to place even one offer.")
                return []
            amount_per_ladder = available_balance / self.num_ladders
            log.info(f"New number of ladders: {self.num_ladders}")

        for i in range(self.num_ladders):
            rate = base_rate + (i * dynamic_rate_spread)
            if rate <= 0:
                log.warning(f"Calculated rate {rate} is zero or negative. Skipping this ladder.")
                continue

            offer = {
                'rate': rate,
                'amount': amount_per_ladder,
                'period': self.lending_duration
            }
            offers.append(offer)
            log.info(f"Generated adaptive ladder {i+1}/{self.num_ladders}: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%, Period={offer['period']}")

        return offers
