import logging
from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class SpreadFillerStrategy(BaseStrategy):
    """
    A strategy that places an offer within the bid-ask spread.
    """
    def __init__(self, api_client, config, db_manager):
        super().__init__(api_client, config, db_manager)
        self.lending_duration = self.config('LENDING_DURATION_DAYS', cast=int)
        self.spread_position_ratio = self.config('SF_SPREAD_POSITION_RATIO', cast=float, default=0.5)
        self.min_spread_threshold = self.config('SF_MIN_SPREAD_THRESHOLD', cast=float, default=0.0001)

    async def generate_offers(self, available_balance, market_data):
        """
        Generates an offer placed within the current bid-ask spread.
        """
        log.info("Executing Spread Filler Strategy.")

        if not market_data or self.lending_duration not in market_data:
            log.warning(f"Market data for the {self.lending_duration}-day period is not available.")
            return []

        market_period_data = market_data[self.lending_duration]
        best_bid = market_period_data.get('bid')
        best_ask = market_period_data.get('offer')

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

        if available_balance < 150.0:
            log.warning(f"Available balance ({available_balance:.2f}) is too low to place a minimum offer of 150.")
            return []

        offer = {
            'rate': offer_rate,
            'amount': available_balance,
            'period': self.lending_duration
        }
        
        log.info(f"Generated Spread Filler Offer: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%")

        return [offer]
