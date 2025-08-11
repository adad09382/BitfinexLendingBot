import logging
from typing import Dict, Any, List
from decimal import Decimal

from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.core.exceptions import BitfinexAPIError

log = logging.getLogger(__name__)

class AccountService:
    """
    負責獲取和管理 Bitfinex 賬戶的餘額和資產信息。
    """
    def __init__(self, api_client: BitfinexApiClient):
        self.api_client = api_client

    def get_all_wallet_balances(self) -> Dict[str, Dict[str, Decimal]]:
        """
        獲取所有錢包的餘額信息。
        :return: 字典，鍵為錢包類型，值為另一個字典 (貨幣 -> 餘額)
        """
        balances: Dict[str, Dict[str, Decimal]] = {}
        try:
            wallet_data = self.api_client.get_wallet_balances()
            if not wallet_data:
                log.warning("No wallet balance data received from Bitfinex.")
                return balances

            for wallet in wallet_data:
                # 錢包數據格式: [wallet_type, currency, balance, unsettled_interest, available_balance]
                wallet_type = wallet[0]
                currency = wallet[1]
                balance = Decimal(str(wallet[2]))
                available_balance = Decimal(str(wallet[4]))

                if wallet_type not in balances:
                    balances[wallet_type] = {}
                
                balances[wallet_type][currency] = {
                    "balance": balance,
                    "available_balance": available_balance
                }
            log.info("Successfully fetched all wallet balances.")
        except BitfinexAPIError as e:
            log.error(f"Failed to fetch wallet balances from Bitfinex: {e}")
        except Exception as e:
            log.error(f"An unexpected error occurred while fetching wallet balances: {e}")
        return balances

    def get_funding_balance(self, currency: str) -> Decimal:
        """
        獲取指定貨幣的資金錢包可用餘額。
        :param currency: 貨幣符號 (例如 'USD')
        :return: 可用餘額，如果未找到則為 0
        """
        balances = self.get_all_wallet_balances()
        funding_wallet = balances.get('funding', {})
        currency_info = funding_wallet.get(currency, {})
        available_balance = currency_info.get("available_balance", Decimal('0'))
        log.debug(f"Funding wallet available balance for {currency}: {available_balance}")
        return available_balance

    def get_exchange_balance(self, currency: str) -> Decimal:
        """
        獲取指定貨幣的交易錢包可用餘額。
        :param currency: 貨幣符號 (例如 'USD')
        :return: 可用餘額，如果未找到則為 0
        """
        balances = self.get_all_wallet_balances()
        exchange_wallet = balances.get('exchange', {})
        currency_info = exchange_wallet.get(currency, {})
        available_balance = currency_info.get("available_balance", Decimal('0'))
        log.debug(f"Exchange wallet available balance for {currency}: {available_balance}")
        return available_balance

    def get_total_balance(self, currency: str) -> Decimal:
        """
        獲取指定貨幣的總餘額 (所有錢包類型)。
        :param currency: 貨幣符號 (例如 'USD')
        :return: 總餘額，如果未找到則為 0
        """
        total_balance = Decimal('0')
        balances = self.get_all_wallet_balances()
        for wallet_type, currencies in balances.items():
            if currency in currencies:
                total_balance += currencies[currency]["balance"]
        log.debug(f"Total balance for {currency}: {total_balance}")
        return total_balance
