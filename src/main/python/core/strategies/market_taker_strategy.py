import logging
from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class MarketTakerStrategy(BaseStrategy):
    """
    A passive strategy that takes the best available bid rate to ensure high fund utilization.
    """
    def __init__(self, api_client, config, db_manager):
        super().__init__(api_client, config, db_manager)
        # Load strategy-specific parameters from config
        self.lending_duration = self.config('LENDING_DURATION_DAYS', cast=int)
        self.amount_percentage = self.config('MT_AMOUNT_PERCENTAGE', cast=float, default=0.995)

    async def generate_offers(self, available_balance, market_data):
        """
        Generates a single funding offer at the best current bid rate.
        """
        log.info("Executing Market Taker Strategy.")

        if not market_data or self.lending_duration not in market_data or market_data[self.lending_duration].get('bid') is None:
            log.warning(f"No bid rate available for the {self.lending_duration}-day period. Cannot place an offer.")
            return []

        best_bid_rate = market_data[self.lending_duration]['bid']
        log.info(f"Found best bid rate of {best_bid_rate * 100:.4f}% for {self.lending_duration}-day period.")

        if best_bid_rate <= 0:
            log.warning(f"Best bid rate {best_bid_rate} is zero or negative. No offer will be placed.")
            return []

        offer_amount = available_balance * self.amount_percentage
        
        # Bitfinex minimum order size is 150 USD equivalent
        if offer_amount < 150.0:
            log.warning(f"Available balance ({available_balance:.2f}) is too low to place a minimum offer of 150. Amount to place: {offer_amount:.2f}")
            return []

        offer = {
            'rate': best_bid_rate,
            'amount': offer_amount,
            'period': self.lending_duration
        }
        
        log.info(f"Generated Taker Offer: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%")

        return [offer]
