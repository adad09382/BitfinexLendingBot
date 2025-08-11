import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class LadderingStrategy(BaseStrategy):
    """
    A strategy that places multiple funding offers at different rates, creating a ladder.
    """
    def __init__(self, config):
        super().__init__(config)
        # Load strategy-specific parameters from config
        self.num_ladders = config.strategy.laddering_ladders
        self.rate_spread = config.strategy.laddering_rate_spread
        self.lending_duration = config.trading.lending_duration_days

    def generate_offers(self, available_balance: Decimal, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates a list of laddered funding offers based on provided market data.
        """
        log.info(f"Executing Laddering Strategy with {self.num_ladders} ladders.")

        # Extract the best bid rate for the lending duration from the raw funding book data
        best_bid_rate = None
        if 'bids' in market_data and market_data['bids']:
            for entry in market_data['bids']:
                # entry format: [RATE, AMOUNT, PERIOD]
                rate = Decimal(str(entry[0]))
                amount = Decimal(str(entry[1]))
                period = int(entry[2])
                
                if period == self.lending_duration:
                    if best_bid_rate is None or rate > best_bid_rate:
                        best_bid_rate = rate
        
        if best_bid_rate is None:
            log.error(f"No bid rate available for the {self.lending_duration}-day period. Aborting offer generation.")
            return []

        base_rate = best_bid_rate
        log.info(f"Using base rate of {base_rate * 100:.4f}% for {self.lending_duration}-day period.")

        # Ensure the amount per offer is at least the Bitfinex minimum of 150
        amount_per_ladder = available_balance / self.num_ladders
        if amount_per_ladder < self.min_order_amount:
            log.warning(f"Calculated amount per ladder ({amount_per_ladder:.2f}) is below the {self.min_order_amount} minimum. Adjusting number of ladders.")
            self.num_ladders = int(available_balance // self.min_order_amount)
            if self.num_ladders == 0:
                log.error("Available balance is too low to place even one offer.")
                return []
            amount_per_ladder = available_balance / self.num_ladders
            log.info(f"New number of ladders: {self.num_ladders}")

        offers = []
        for i in range(self.num_ladders):
            # Start from the best bid rate and create ladders with slightly higher rates
            rate = base_rate + (i * self.rate_spread)
            # Ensure rate is positive
            if rate <= 0:
                log.warning(f"Calculated rate {rate} is zero or negative. Skipping this ladder.")
                continue

            offer = {
                'rate': rate,
                'amount': amount_per_ladder,
                'period': self.lending_duration
            }
            offers.append(offer)
            log.info(f"Generated ladder {i+1}/{self.num_ladders}: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%, Period={offer['period']}")

        return offers
