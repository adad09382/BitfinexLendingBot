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
async def cancel_funding_offer(offer_id: int):
    """Cancels a specific funding offer by ID."""
    print(f"[INFO] Attempting to cancel offer with ID: {offer_id}")
    try:
        result = await asyncio.to_thread(bot.rest.auth.cancel_funding_offer, offer_id)
        print(f"[SUCCESS] Successfully cancelled offer: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Error cancelling offer {offer_id}: {e}")
        return None

# --- Main Execution ---
async def main():
    """Main function to execute the test."""
    if len(sys.argv) < 2:
        print("Usage: python test_cancel_funding_offer.py <OFFER_ID>")
        print("Example: python test_cancel_funding_offer.py 123456789")
        return

    try:
        offer_id_to_cancel = int(sys.argv[1])
    except ValueError:
        print("Error: <OFFER_ID> must be an integer.")
        return

    print(f"--- WARNING: This script will cancel the funding offer with ID: {offer_id_to_cancel} ---")
    
    # Confirmation prompt
    if "-y" not in sys.argv:
        confirm = input("Are you sure you want to proceed? (y/n): ")
        if confirm.lower() != 'y':
            print("Test cancelled by user.")
            return

    await cancel_funding_offer(offer_id_to_cancel)

if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
    else:
        asyncio.run(main())
