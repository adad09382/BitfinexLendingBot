import os
import asyncio
import sys
from dotenv import load_dotenv
from typing import Optional
from bfxapi import Client

# --- Setup ---
# Construct the absolute path to the .env file to ensure it's always found
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv("BFX_API_KEY")
API_SECRET = os.getenv("BFX_API_SECRET")
LENDING_CURRENCY = os.getenv("LENDING_CURRENCY", "USD")
LENDING_DURATION_DAYS = int(os.getenv("LENDING_DURATION_DAYS", 2))
MIN_INTEREST_RATE = float(os.getenv("MIN_INTEREST_RATE", 0.0001))
MAX_LOAN_AMOUNT = float(os.getenv("MAX_LOAN_AMOUNT", 10000.0))

bot = Client(api_key=API_KEY, api_secret=API_SECRET)

# --- Functions to Test ---
async def analyze_funding_market(currency: str) -> dict[int, float]:
    market_rates = {}
    try:
        symbol = f"f{currency}"
        book = await asyncio.to_thread(bot.rest.public.get_f_book, currency=symbol, precision="P0", limit=100)
        if book and len(book) > 0:
            bids = [entry for entry in book if entry.amount < 0]
            for bid in bids:
                period = bid.period
                rate = bid.rate
                if period not in market_rates or rate > market_rates[period]:
                    market_rates[period] = rate
    except Exception as e:
        print(f"[ERROR] Error analyzing funding market for {currency}: {e}")
    return market_rates

async def get_available_balance(currency: str):
    try:
        wallets = await asyncio.to_thread(bot.rest.auth.get_wallets)
        for wallet in wallets:
            if wallet.wallet_type == "funding" and wallet.currency == currency:
                return float(wallet.available_balance)
        return 0.0
    except Exception as e:
        print(f"[ERROR] Error fetching wallets: {e}")
        return 0.0

async def place_lending_offer(currency: str, amount: float, rate: float, period: int):
    print(f"[INFO] Attempting to place lending offer: {amount} {currency} at {rate*100:.4f}% daily for {period} days...")
    try:
        offer = await asyncio.to_thread(bot.rest.auth.submit_funding_offer, type="LIMIT", symbol=f"f{currency}", amount=amount, rate=rate, period=period)
        print(f"[SUCCESS] Successfully placed offer: {offer}")
        return offer
    except Exception as e:
        print(f"[ERROR] Error placing lending offer: {e}")
        return None

async def execute_aggressive_strategy(available_balance, market_rates):
    target_period = LENDING_DURATION_DAYS
    best_market_bid = market_rates.get(target_period)

    if not best_market_bid:
        print(f"[WARNING] No market rate found for the target period of {target_period} days. Cannot execute aggressive strategy.")
        return

    print(f"[INFO] Best bid for {target_period} days is {best_market_bid*100:.4f}%. Placing aggressive offer.")
    amount_to_lend = min(available_balance, MAX_LOAN_AMOUNT)
    offer_rate = max(MIN_INTEREST_RATE, best_market_bid - 0.000001)
    if offer_rate < 0:
        offer_rate = MIN_INTEREST_RATE
    
    if amount_to_lend >= 150.0:
        await place_lending_offer(LENDING_CURRENCY, amount_to_lend, offer_rate, target_period)
    else:
        print(f"[WARNING] Amount to lend {amount_to_lend} is less than minimum 150.0 {LENDING_CURRENCY}. Skipping offer placement.")

# --- Main Execution ---
async def main():
    """Main function to execute the test."""
    print("--- Testing Aggressive Strategy ---")
    print("--- WARNING: This script may place a REAL lending offer. ---")

    available_balance = await get_available_balance(LENDING_CURRENCY)
    print(f"Available balance: {available_balance} {LENDING_CURRENCY}")

    if available_balance < 150.0:
        print("Insufficient balance to run test. Minimum 150 is required.")
        return

    market_rates = await analyze_funding_market(LENDING_CURRENCY)
    print(f"Market rates: {market_rates}")

    if not market_rates:
        print("Could not retrieve market rates. Aborting test.")
        return

    # Confirmation prompt
    if "-y" not in sys.argv:
        confirm = input("Are you sure you want to proceed with placing an aggressive offer? (y/n): ")
        if confirm.lower() != 'y':
            print("Test cancelled by user.")
            return

    await execute_aggressive_strategy(available_balance, market_rates)

if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
    else:
        asyncio.run(main())
