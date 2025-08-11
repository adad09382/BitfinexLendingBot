import logging
import asyncio
from src.main.python.core.config import AppConfig
from src.main.python.models.interest_payment import InterestPayment
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.repositories.lending_order_repository import LendingOrderRepository

log = logging.getLogger(__name__)

class SyncService:
    def __init__(self, bfx_client, config: AppConfig, 
                 interest_payment_repo: InterestPaymentRepository, 
                 lending_order_repo: LendingOrderRepository):
        self.bfx = bfx_client
        self.config = config
        self.interest_payment_repo = interest_payment_repo
        self.lending_order_repo = lending_order_repo

    async def sync_order_status(self):
        log.info("Syncing order status from Bitfinex...")
        symbol = f"f{self.config.trading.lending_currency}"
        offers = await asyncio.to_thread(self.bfx.rest.auth.get_funding_offers, symbol=symbol)
        log.info(f"Found {len(offers)} active funding offers")
        # TODO: Implement order status sync logic

    async def sync_interest_payments(self):
        log.info("Syncing interest payments from Bitfinex ledger...")
        currency = self.config.trading.lending_currency
        ledgers = await asyncio.to_thread(
            self.bfx.rest.auth.get_ledgers,
            currency=currency,
            limit=250
        )
        funding_payments = [
            ledger for ledger in ledgers 
            if hasattr(ledger, 'description') and ledger.description and             any(keyword in ledger.description.lower() for keyword in ['funding', 'interest', 'lending'])
        ]
        log.info(f"Found {len(funding_payments)} potential interest payment records from API.")
        for ledger in funding_payments:
            interest_payment = InterestPayment.from_ledger_entry({
                'id': ledger.id,
                'currency': ledger.currency,
                'amount': ledger.amount,
                'mts': ledger.mts,
                'description': ledger.description
            })
            self.interest_payment_repo.save_payment(interest_payment)
