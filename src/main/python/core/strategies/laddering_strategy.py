import logging
from .base_strategy import BaseStrategy

log = logging.getLogger(__name__)

class LadderingStrategy(BaseStrategy):
    """
    A strategy that places multiple funding offers at different rates, creating a ladder.
    """
    def __init__(self, api_client, config, db_manager):
        super().__init__(api_client, config, db_manager)
        # Load strategy-specific parameters from config
        self.num_ladders = self.config('LADDERING_LADDERS', cast=int)
        self.rate_spread = self.config('LADDERING_RATE_SPREAD', cast=float)
        self.lending_duration = self.config('LENDING_DURATION_DAYS', cast=int)

    async def generate_offers(self, available_balance, market_data):
        """
        Generates a list of laddered funding offers based on provided market data.
        """
        log.info(f"Executing Laddering Strategy with {self.num_ladders} ladders.")

        if not market_data or self.lending_duration not in market_data or market_data[self.lending_duration]['bid'] is None:
            log.error(f"No bid rate available for the {self.lending_duration}-day period. Aborting offer generation.")
            return []

        base_rate = market_data[self.lending_duration]['bid']
        log.info(f"Using base rate of {base_rate * 100:.4f}% for {self.lending_duration}-day period.")

        # Ensure the amount per offer is at least the Bitfinex minimum of 150
        amount_per_ladder = available_balance / self.num_ladders
        if amount_per_ladder < 150.0:
            log.warning(f"Calculated amount per ladder ({amount_per_ladder:.2f}) is below the 150 minimum. Adjusting number of ladders.")
            self.num_ladders = int(available_balance // 150)
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
            log.info(f"Generated ladder {i+1}/{self.num_ladders}: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%")

        return offers
