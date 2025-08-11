import logging
from decimal import Decimal
from typing import Optional
import asyncio

from src.main.python.core.config import AppConfig
from src.main.python.core.exceptions import (
    create_invalid_order_error, InvalidOrderError, handle_api_errors
)
from src.main.python.models.lending_order import LendingOrder, OrderStatus
from src.main.python.repositories.lending_order_repository import LendingOrderRepository

log = logging.getLogger(__name__)

class FundingService:
    from src.main.python.api.bitfinex_api_client import BitfinexApiClient

class FundingService:
    def __init__(self, api_client: BitfinexApiClient, config: AppConfig, lending_order_repo: LendingOrderRepository):
        self.api_client = api_client
        self.config = config
        self.lending_order_repo = lending_order_repo

    @handle_api_errors
    def get_available_balance(self) -> Decimal:
        currency = self.config.trading.lending_currency
        wallets = self.api_client.get_wallet_balances()
        for wallet in wallets:
            # 錢包數據格式: ['wallet_type', 'currency', 'balance', 'unsettled_interest', 'available_balance']
            if wallet[0] == "funding" and wallet[1] == currency:
                balance = Decimal(str(wallet[4])) # available_balance
                log.info(f"Available balance in funding wallet: {balance:.2f} {currency}")
                return balance
        log.warning(f"No funding wallet found for {currency}")
        return Decimal('0.0')

    @handle_api_errors
    def cancel_all_funding_offers(self):
        currency = self.config.trading.lending_currency
        symbol = f"f{currency}"
        offers = self.api_client.get_funding_offers(symbol=symbol)
        if not offers:
            log.info(f"No active offers found for {symbol}")
            return
        log.info(f"Found {len(offers)} active offers for {symbol}. Cancelling them...")
        for offer in offers:
            # offer 數據格式: [ID, SYMBOL, MTS_CREATED, MTS_UPDATED, AMOUNT, FLAGS, STATUS, RATE, PERIOD, ...]
            offer_id = offer[0]
            self.api_client.cancel_funding_offer(offer_id)
            log.info(f"Cancelled offer ID: {offer_id}")

    @handle_api_errors
    def place_funding_offer(self, rate: Decimal, amount: Decimal, period: int, 
                                strategy_name: Optional[str] = None, 
                                strategy_params: Optional[dict] = None):
        currency = self.config.trading.lending_currency
        symbol = f"f{currency}"
        min_amount = self.config.trading.min_order_amount

        if amount < min_amount:
            raise create_invalid_order_error(float(amount), float(min_amount), currency)
        if rate <= 0:
            raise InvalidOrderError(f"Invalid rate: {rate}")
        if period <= 0:
            raise InvalidOrderError(f"Invalid period: {period}")

        log.info(f"Placing offer: {amount:.2f} {currency} at daily rate of {rate*100:.4f}% for {period} days")
        
        # Bitfinex API 期望 amount 和 rate 為 Decimal 類型，並在內部轉換為字符串
        response = self.api_client.submit_funding_offer(
            symbol=symbol,
            amount=amount,
            rate=rate,
            period=period,
            type="FRR" # 默認為 FRR，可以根據需要調整
        )
        log.info("Offer placed successfully")
        self._create_lending_order_record(
            response, symbol, amount, rate, period, strategy_name, strategy_params
        )

    def _create_lending_order_record(self, api_response: List[Any], symbol: str, amount: Decimal, 
                                         rate: Decimal, period: int, strategy_name: Optional[str], 
                                         strategy_params: Optional[dict]):
        # Bitfinex API 提交訂單響應格式: [ID, SYMBOL, MTS_CREATED, MTS_UPDATED, AMOUNT, FLAGS, STATUS, RATE, PERIOD, ...]
        order_id = api_response[0]
        lending_order = LendingOrder(
            order_id=order_id,
            symbol=symbol,
            amount=amount,
            rate=rate,
            period=period,
            status=OrderStatus.PENDING, # 初始狀態為 PENDING
            strategy_name=strategy_name,
            strategy_params=strategy_params
        )
        self.lending_order_repo.save(lending_order)
