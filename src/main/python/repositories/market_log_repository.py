import logging
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List

from src.main.python.models.market_log import MarketLog
from src.main.python.services.database_manager import DatabaseManager

log = logging.getLogger(__name__)

class MarketLogRepository:
    """
    Handles all database operations related to the MarketLog model.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def log_market_data(self, market_log: MarketLog):
        """
        Logs a new market data point to the database.
        """
        if not market_log.rates_data:
            return

        log.info(f"Logging market data to database for {market_log.currency}")
        rates_data_json = json.dumps(market_log.rates_data)
        query = """
        INSERT INTO market_logs (currency, rates_data, timestamp)
        VALUES (%s, %s, %s);
        """
        self.db_manager.execute_query(query, (market_log.currency, rates_data_json, market_log.timestamp))

    def get_historical_market_data(self, currency: str, hours_ago: int) -> pd.DataFrame:
        """
        Retrieves historical market data and returns it as a pandas DataFrame.
        """
        log.info(f"Retrieving historical market data for {currency} from the last {hours_ago} hours.")
        time_threshold = datetime.now() - timedelta(hours=hours_ago)
        
        query = """
        SELECT timestamp, rates_data FROM market_logs
        WHERE currency = %s AND timestamp >= %s
        ORDER BY timestamp ASC;
        """
        
        results = self.db_manager.execute_query(query, (currency, time_threshold), fetch='all')

        if not results:
            return pd.DataFrame()

        processed_data = []
        for timestamp, rates_data in results:
            record = {'timestamp': timestamp}
            # The periods in rates_data are strings from JSON keys, convert them to int
            for period_str, rates in rates_data.items():
                period = int(period_str)
                record[f'p{period}_bid'] = rates.get('bid')
                record[f'p{period}_offer'] = rates.get('offer')
            processed_data.append(record)
            
        df = pd.DataFrame(processed_data)
        if not df.empty:
            df.set_index('timestamp', inplace=True)
        return df
