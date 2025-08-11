import os
import asyncio
from bfxapi import Client
from datetime import datetime, timedelta

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Bitfinex API credentials
BFX_API_KEY = os.getenv("BFX_API_KEY")
BFX_API_SECRET = os.getenv("BFX_API_SECRET")

# Create a client instance
bfx = Client(
    api_key=BFX_API_KEY,
    api_secret=BFX_API_SECRET
)

async def get_daily_profit():
    """
    Fetches and prints the daily funding profit summary by analyzing ledger entries.
    """
    try:
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        start_of_yesterday = int(yesterday.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        end_of_yesterday = int(yesterday.replace(hour=23, minute=59, second=59, microsecond=999).timestamp() * 1000)

        print(f"Fetching ledger entries for {yesterday.strftime('%Y-%m-%d')}...")
        ledgers = await asyncio.to_thread(bfx.rest.auth.get_ledgers,
            currency='USD',
            start=start_of_yesterday,
            end=end_of_yesterday,
            limit=2500 # Max limit, might need pagination for more data
        )
        print(f"Found {len(ledgers)} ledger entries.")

        daily_profit = {}
        for entry in ledgers:
            # Ledger entry format: [ID, CURRENCY, WALLET, MTS, AMOUNT, BALANCE, DESCRIPTION]
            currency = entry.currency
            amount = entry.amount
            description = entry.description

            # Filter for funding interest income. Adjust description as needed based on actual ledger entries.
            if "Funding" in description and amount > 0: # Assuming positive amount means income
                if currency not in daily_profit:
                    daily_profit[currency] = 0
                daily_profit[currency] += amount

        print("\nDaily Funding Profit Summary:")
        if daily_profit:
            for currency, profit in daily_profit.items():
                print(f"  Currency: {currency}, Profit: {profit:.8f}")
        else:
            print("No daily funding profit data found for yesterday.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_daily_profit())
