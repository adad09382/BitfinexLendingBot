import os
import asyncio
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

bot = Client(api_key=API_KEY, api_secret=API_SECRET)

# --- Function to Test ---
async def get_available_balance(currency: str):
    """Fetches the available balance for lending from the funding wallet."""
    try:
        wallets = await asyncio.to_thread(bot.rest.auth.get_wallets)
        for wallet in wallets:
            if wallet.wallet_type == "funding" and wallet.currency == currency:
                return float(wallet.available_balance)
        return 0.0
    except Exception as e:
        print(f"[ERROR] Error fetching wallets: {e}")
        return 0.0

# --- Main Execution ---
async def main():
    """Main function to execute the test."""
    print(f"Attempting to fetch available balance for {LENDING_CURRENCY}...")
    
    balance = await get_available_balance(LENDING_CURRENCY)
    
    print("\n--- Test Result ---")
    print(f"Available Balance for {LENDING_CURRENCY}: {balance}")
    print("-------------------")

if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
    else:
        asyncio.run(main())
