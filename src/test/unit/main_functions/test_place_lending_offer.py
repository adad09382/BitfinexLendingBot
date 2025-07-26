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

bot = Client(api_key=API_KEY, api_secret=API_SECRET)

# --- Function to Test ---
async def place_lending_offer(currency: str, amount: float, rate: float, period: int):
    """Places a new lending offer."""
    print(f"[INFO] Attempting to place lending offer: {amount} {currency} at {rate*100:.4f}% daily for {period} days...")
    try:
        offer = await asyncio.to_thread(bot.rest.auth.submit_funding_offer,
            type="LIMIT",
            symbol=f"f{currency}",
            amount=amount,
            rate=rate,
            period=period
        )
        print(f"[SUCCESS] Successfully placed offer: {offer}")
        return offer
    except Exception as e:
        print(f"[ERROR] Error placing lending offer: {e}")
        return None

# --- Main Execution ---
async def main():
    """Main function to execute the test."""
    # WARNING: This will place a real order on the market.
    # For safety, we use a small amount and a low rate.
    TEST_CURRENCY = "USD"
    TEST_AMOUNT = 150.0
    TEST_RATE = 0.0001 # Corresponds to 0.01% daily
    TEST_PERIOD = 2

    print("--- WARNING: This script will place a REAL lending offer. ---")
    print(f"  Details: {TEST_AMOUNT} {TEST_CURRENCY} at {TEST_RATE*100:.4f}% for {TEST_PERIOD} days.")
    
    # Confirmation prompt
    if "-y" not in sys.argv:
        confirm = input("Are you sure you want to proceed? (y/n): ")
        if confirm.lower() != 'y':
            print("Test cancelled by user.")
            return

    await place_lending_offer(TEST_CURRENCY, TEST_AMOUNT, TEST_RATE, TEST_PERIOD)

if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
    else:
        asyncio.run(main())
