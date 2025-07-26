import os
import asyncio
from dotenv import load_dotenv
from bfxapi import Client
from typing import Optional

# --- Setup ---
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv("BFX_API_KEY")
API_SECRET = os.getenv("BFX_API_SECRET")

bot = Client(api_key=API_KEY, api_secret=API_SECRET)

async def get_historical_funding_offers(currency: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None, limit: int = 100):
    """Fetches historical funding offers for a given currency."""
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
        return []

    try:
        symbol = f"f{currency}"
        # Bitfinex API expects timestamps in milliseconds
        # Convert start/end to milliseconds if they are in seconds
        start_ms = start_timestamp * 1000 if start_timestamp else None
        end_ms = end_timestamp * 1000 if end_timestamp else None

        offers_hist = await asyncio.to_thread(bot.rest.auth.get_funding_offers_history,
                                               symbol=symbol,
                                               start=start_ms,
                                               end=end_ms,
                                               limit=limit)
        print(f"[INFO] Fetched {len(offers_hist)} historical funding offers for {currency}.")
        for offer in offers_hist:
            # You can customize the output format here
            # Note: The amount field in historical offers might represent the original amount or remaining amount.
            # For executed offers, the amount will be 0 as it's fully utilized.
            # The actual interest earned is in ledgers.
            print(f"  Offer ID: {offer.id}, Amount: {offer.amount}, Rate: {offer.rate*100:.4f}%, Period: {offer.period} days, Status: {offer.offer_status}, Created: {offer.mts_create}")
        return offers_hist
    except Exception as e:
        print(f"[ERROR] Error fetching historical funding offers: {e}")
        return []

async def get_funding_ledgers(currency: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None, limit: int = 100):
    """Fetches ledger entries related to funding earnings for a given currency."""
    if not API_KEY or not API_SECRET:
        print("[FATAL] API_KEY and API_SECRET must be set in the .env file.")
        return []

    try:
        # Bitfinex API expects timestamps in milliseconds
        start_ms = start_timestamp * 1000 if start_timestamp else None
        end_ms = end_timestamp * 1000 if end_timestamp else None

        # Fetch all ledgers for the currency
        ledgers = await asyncio.to_thread(bot.rest.auth.get_ledgers,
                                          currency=currency,
                                          start=start_ms,
                                          end=end_ms,
                                          limit=limit)
        
        print(f"[INFO] Fetched {len(ledgers)} ledger entries for {currency}.")
        funding_earnings = []
        for entry in ledgers:
            # Filter for entries related to funding interest payments
            # The description often contains keywords like 'Margin Funding Payment' or 'Funding Payment'
            if 'funding' in entry.description.lower() and 'payment' in entry.description.lower():
                funding_earnings.append(entry)
                print(f"  Ledger ID: {entry.id}, Currency: {entry.currency}, Amount: {entry.amount}, Balance: {entry.balance}, Description: {entry.description}, Created: {entry.mts}")
        
        print(f"[INFO] Found {len(funding_earnings)} funding earnings entries for {currency}.")
        return funding_earnings
    except Exception as e:
        print(f"[ERROR] Error fetching funding ledgers: {e}")
        return []

async def main():
    print("--- Bitfinex Historical Funding Data Tool ---")
    # Example usage: Get the last 10 historical UST funding offers
    await get_historical_funding_offers("UST", limit=10)

    print("\n--- Bitfinex Funding Earnings (Ledgers) ---")
    # Example usage: Get the last 100 UST funding ledger entries
    await get_funding_ledgers("UST", limit=100)