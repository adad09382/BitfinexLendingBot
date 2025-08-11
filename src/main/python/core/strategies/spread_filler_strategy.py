import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class SpreadFillerStrategy(BaseStrategy):
    """
    A strategy that places an offer within the bid-ask spread.
    """
    def __init__(self, config):
        super().__init__(config)
        self.lending_duration = config.trading.lending_duration_days
        self.spread_position_ratio = config.strategy.sf_spread_position_ratio
        self.min_spread_threshold = config.strategy.sf_min_spread_threshold

    def generate_offers(self, available_balance: Decimal, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates an offer placed within the current bid-ask spread.
        """
        log.info("Executing Spread Filler Strategy.")

        best_bid = None
        if 'bids' in market_data and market_data['bids']:
            for entry in market_data['bids']:
                # entry format: [RATE, AMOUNT, PERIOD]
                rate = Decimal(str(entry[0]))
                period = int(entry[2])
                if period == self.lending_duration:
                    if best_bid is None or rate > best_bid:
                        best_bid = rate
        
        best_ask = None
        if 'asks' in market_data and market_data['asks']:
            for entry in market_data['asks']:
                # entry format: [RATE, AMOUNT, PERIOD]
                rate = Decimal(str(entry[0]))
                period = int(entry[2])
                if period == self.lending_duration:
                    if best_ask is None or rate < best_ask:
                        best_ask = rate

        if best_bid is None or best_ask is None:
            log.warning(f"Best bid or ask rate is not available for the {self.lending_duration}-day period. Cannot place an offer.")
            return []

        spread = best_ask - best_bid
        log.info(f"Market spread for {self.lending_duration}-day period: {spread*100:.4f}%. Best Bid: {best_bid*100:.4f}%, Best Ask: {best_ask*100:.4f}%")

        if spread < self.min_spread_threshold:
            log.warning(f"Spread {spread:.6f} is below the minimum threshold of {self.min_spread_threshold:.6f}. Placing offer at best bid rate instead.")
            offer_rate = best_bid
        else:
            offer_rate = best_bid + (spread * self.spread_position_ratio)

        if offer_rate <= 0:
            log.warning(f"Calculated offer rate {offer_rate} is zero or negative. No offer will be placed.")
            return []

        if available_balance < self.min_order_amount:
            log.warning(f"Available balance ({available_balance:.2f}) is too low to place a minimum offer of {self.min_order_amount}.")
            return []

        offer = {
            'rate': offer_rate,
            'amount': available_balance,
            'period': self.lending_duration
        }
        
        log.info(f"Generated Spread Filler Offer: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%, Period={offer['period']}")

        return [offer]
