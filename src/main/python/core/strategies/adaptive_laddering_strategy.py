import logging
from .base_strategy import BaseStrategy
import pandas as pd

log = logging.getLogger(__name__)

class AdaptiveLadderingStrategy(BaseStrategy):
    """
    An adaptive strategy that adjusts its parameters based on recent market conditions.
    """
    def __init__(self, api_client, config, db_manager):
        super().__init__(api_client, config, db_manager)
        self.lending_duration = self.config('LENDING_DURATION_DAYS', cast=int)
        self.lookback_period_hours = self.config('AL_LOOKBACK_PERIOD_HOURS', cast=int, default=24)
        self.volatility_spread_multiplier = self.config('AL_VOLATILITY_SPREAD_MULTIPLIER', cast=float, default=1.5)
        self.num_ladders = self.config('LADDERING_LADDERS', cast=int)

    async def generate_offers(self, available_balance, market_data):
        """
        Generates laddered offers with dynamically adjusted rate and spread.
        """
        log.info("Executing Adaptive Laddering Strategy.")

        if not self.db_manager:
            log.error("Database manager is required for Adaptive Laddering Strategy, but it is not available.")
            return []

        # 1. Get historical data
        historical_data = self.db_manager.get_historical_market_data(self.lending_currency, self.lookback_period_hours)
        if historical_data.empty:
            log.warning("No historical market data available. Cannot execute adaptive strategy.")
            return []

        # 2. Analyze historical data
        avg_rate, volatility = self._analyze_historical_data(historical_data)
        log.info(f"Historical analysis ({self.lookback_period_hours}h): Avg. Rate: {avg_rate*100:.4f}%, Volatility: {volatility*100:.4f}%")

        # 3. Determine base rate
        current_best_bid = market_data.get(self.lending_duration, {}).get('bid')
        if current_best_bid is None:
            log.warning(f"No current best bid rate available for {self.lending_duration}-day period. Using historical average.")
            base_rate = avg_rate
        else:
            base_rate = max(current_best_bid, avg_rate) # Use the higher of the two
        
        log.info(f"Determined base rate: {base_rate*100:.4f}%")

        # 4. Determine dynamic rate spread
        dynamic_rate_spread = volatility * self.volatility_spread_multiplier
        log.info(f"Calculated dynamic rate spread: {dynamic_rate_spread*100:.4f}%")

        # 5. Generate offers
        offers = []
        amount_per_ladder = available_balance / self.num_ladders
        if amount_per_ladder < 150.0:
            log.warning(f"Calculated amount per ladder ({amount_per_ladder:.2f}) is below the 150 minimum. Adjusting number of ladders.")
            self.num_ladders = int(available_balance // 150)
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
            log.info(f"Generated adaptive ladder {i+1}/{self.num_ladders}: Amount={offer['amount']:.2f}, Rate={offer['rate']*100:.4f}%")

        return offers

    def _analyze_historical_data(self, historical_data):
        """Analyzes historical market data to determine average rate and volatility."""
        # For simplicity, we'll focus on the bid rates for the specified lending duration
        # In a more advanced implementation, you might consider all periods
        bid_rates = historical_data[f'p{self.lending_duration}_bid'].dropna()
        
        if len(bid_rates) < 2:
            log.warning("Not enough historical data points to calculate volatility. Returning 0 for volatility.")
            return bid_rates.mean() if not bid_rates.empty else 0.0, 0.0

        avg_rate = bid_rates.mean()
        volatility = bid_rates.std()
        return avg_rate, volatility
