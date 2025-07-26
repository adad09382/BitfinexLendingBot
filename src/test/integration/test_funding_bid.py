import os
import asyncio
from dotenv import load_dotenv
from bfxapi import Client

# --- Setup ---
# Load environment variables from .env file
load_dotenv()

# Retrieve API key and secret from environment variables
API_KEY = os.getenv("BFX_API_KEY")
API_SECRET = os.getenv("BFX_API_SECRET")

# Initialize Bitfinex API client
bot = Client(api_key=API_KEY, api_secret=API_SECRET)

# --- Function to Test ---
async def get_active_funding_offers():
    """Fetches all active funding offers from the Bitfinex API."""
    try:
        # Use asyncio.to_thread to run the synchronous bfxapi call in a separate thread
        offers = await asyncio.to_thread(bot.rest.auth.get_funding_offers)
        return offers
    except Exception as e:
        print(f"[ERROR] Error fetching active funding offers: {e}")
        return []

# --- Main Execution ---
async def main():
    """Main function to execute the test."""
    print("Attempting to fetch active funding offers...")
    
    active_offers = await get_active_funding_offers()
    
    if active_offers:
        print("\n--- Active Funding Offers ---")
        for offer in active_offers:
            print(f"  - ID: {offer.id}, Symbol: {offer.symbol}, Amount: {offer.amount}, Rate: {offer.rate*100:.4f}%, Period: {offer.period} days")
        print(f"\nTotal active offers: {len(active_offers)}")
    else:
        print("\n--- No active funding offers found. ---")

if __name__ == "__main__":
    # Check for API keys before running
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
    else:
        asyncio.run(main())