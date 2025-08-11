import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class MarketTakerStrategy(BaseStrategy):
    """
    A passive strategy that takes the best available bid rate to ensure high fund utilization.
    """
    def __init__(self, config):
        super().__init__(config)
        # Load strategy-specific parameters from config
        self.lending_duration = config.trading.lending_duration_days
        self.amount_percentage = config.strategy.mt_amount_percentage

    def generate_offers(self, available_balance: Decimal, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates a single funding offer at the best current bid rate.
        """
        log.info("Executing Market Taker Strategy.")

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
            log.warning(f"No bid rate available for the {self.lending_duration}-day period. Cannot place an offer.")
            return []

        best_bid_rate = best_bid_rate # Use the extracted best bid rate
        log.info(f"Found best bid rate of {best_bid_rate * 100:.4f}% for {self.lending_duration}-day period.")

        if best_bid_rate <= 0:
            log.warning(f"Best bid rate {best_bid_rate} is zero or negative. No offer will be placed.")
            return []

        offer_amount = available_balance * self.amount_percentage
        
        if offer_amount < self.min_order_amount:
            log.warning(f"Available balance ({available_balance:.2f}) is too low to place a minimum offer of {self.min_order_amount}. Amount to place: {offer_amount:.2f}")
            return []

        offer = {
            'rate': best_bid_rate,
            'amount': offer_amount,
            'period': self.lending_duration
        }
        
        log.info(f"Generated Taker Offer: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%, Period={offer['period']}")

        return [offer]
