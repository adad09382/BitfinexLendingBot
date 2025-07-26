import os
import asyncio
from dotenv import load_dotenv

from typing import Optional

# --- Setup ---
# Construct the absolute path to the .env file to ensure it's always found
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

from bfxapi import Client

API_KEY = os.getenv("BFX_API_KEY")
API_SECRET = os.getenv("BFX_API_SECRET")
LENDING_CURRENCY = "USD"

bot = Client(api_key=API_KEY, api_secret=API_SECRET)

# --- Function to Test ---
async def analyze_funding_market(currency: str) -> dict[int, dict[str, Optional[float]]]:
    """
    Analyzes the funding book and returns a dictionary with the best bid and offer rates for each period.
    """
    market_rates = {} # {period: {'bid': rate, 'offer': rate}}
    try:
        symbol = f"f{currency}"
        book = await asyncio.to_thread(bot.rest.public.get_f_book, currency=symbol, precision="P0", len=100)
        if book and len(book) > 0:
            for entry in book:
                period = entry.period
                rate = entry.rate
                amount = entry.amount

                if period not in market_rates:
                    market_rates[period] = {'bid': 0.0, 'offer': float('inf')} # Initialize with extreme values

                if amount < 0: # It's a bid (borrower wants to borrow)
                    if rate > market_rates[period]['bid']:
                        market_rates[period]['bid'] = rate
                elif amount > 0: # It's an offer (lender wants to lend)
                    if rate < market_rates[period]['offer']:
                        market_rates[period]['offer'] = rate
    except Exception as e:
        print(f"[ERROR] Error analyzing funding market for {currency}: {e}")

    # Clean up periods where no bids or offers were found, or set to None
    for period in list(market_rates.keys()):
        if market_rates[period]['bid'] == 0.0 and market_rates[period]['offer'] == float('inf'):
            del market_rates[period] # Remove if no bids or offers for this period
        else:
            if market_rates[period]['bid'] == 0.0:
                market_rates[period]['bid'] = None # No bids found for this period
            if market_rates[period]['offer'] == float('inf'):
                market_rates[period]['offer'] = None # No offers found for this period

    return market_rates

# --- Main Execution ---
async def main():
    """Main function to execute the test."""
    print(f"Attempting to analyze funding market for {LENDING_CURRENCY}...")
    
    rates_data = await analyze_funding_market(LENDING_CURRENCY)
    
    print("\n--- Test Result ---")
    if rates_data:
        print(f"Best bid/offer rates per period for {LENDING_CURRENCY}:")
        for period, data in sorted(rates_data.items()):
            bid_rate_str = f"{data['bid']*100:.4f}%" if data['bid'] is not None else "N/A"
            offer_rate_str = f"{data['offer']*100:.4f}%" if data['offer'] is not None else "N/A"
            print(f"  - {period} days: Bid: {bid_rate_str}, Offer: {offer_rate_str}")
    else:
        print("Could not retrieve any market rates.")
    print("-------------------")

if __name__ == "__main__":
    asyncio.run(main())
