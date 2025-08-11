import hmac
import hashlib
import time
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal

from src.main.python.core.config import ApiConfig
from src.main.python.core.exceptions import BitfinexAPIError, BitfinexAuthError, BitfinexRateLimitError

log = logging.getLogger(__name__)

class BitfinexApiClient:
    """
    Bitfinex API 客戶端，負責底層 API 請求、簽名和錯誤處理。
    """
    BASE_URL = "https://api.bitfinex.com/v2/"

    def __init__(self, api_config: ApiConfig):
        self.api_key = api_config.key
        self.api_secret = api_config.secret
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _get_auth_headers(self, path: str, body: str = '') -> Dict[str, str]:
        """
        生成 Bitfinex API 請求所需的認證頭。
        """
        nonce = str(int(time.time() * 1000))
        signature_payload = f'/api/{path}{nonce}{body}'
        
        # 確保 secret 是 bytes
        api_secret_bytes = self.api_secret.encode('utf-8')
        
        signature = hmac.new(
            api_secret_bytes,
            signature_payload.encode('utf-8'),
            hashlib.sha384
        ).hexdigest()

        return {
            'bfx-nonce': nonce,
            'bfx-apikey': self.api_key,
            'bfx-signature': signature
        }

    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None, authenticated: bool = False) -> Any:
        """
        執行實際的 HTTP 請求並處理響應。
        """
        url = f"{self.BASE_URL}{endpoint}"
        body = json.dumps(payload) if payload else ''
        
        headers = {}
        if authenticated:
            headers = self._get_auth_headers(endpoint, body)
        
        try:
            if method.upper() == 'POST':
                response = self.session.post(url, headers=headers, data=body)
            elif method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=payload)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status() # 檢查 HTTP 錯誤狀態碼

            data = response.json()

            # Bitfinex API 錯誤處理
            if isinstance(data, list) and len(data) > 0 and data[0] == 'error':
                error_code = data[1]
                error_message = data[2]
                log.error(f"Bitfinex API Error: Code={error_code}, Message={error_message}")
                if error_code == 10001: # "API key not authorized" or similar auth issues
                    raise BitfinexAuthError(f"Authentication failed: {error_message}")
                elif error_code == 10020: # "Rate limit exceeded"
                    raise BitfinexRateLimitError(f"Rate limit exceeded: {error_message}")
                else:
                    raise BitfinexAPIError(f"Bitfinex API Error [{error_code}]: {error_message}")
            
            return data

        except requests.exceptions.HTTPError as e:
            log.error(f"HTTP Error for {url}: {e.response.status_code} - {e.response.text}")
            raise BitfinexAPIError(f"HTTP Error: {e.response.status_code} - {e.response.text}") from e
        except requests.exceptions.ConnectionError as e:
            log.error(f"Connection Error for {url}: {e}")
            raise BitfinexAPIError(f"Connection Error: {e}") from e
        except requests.exceptions.Timeout as e:
            log.error(f"Timeout Error for {url}: {e}")
            raise BitfinexAPIError(f"Timeout Error: {e}") from e
        except json.JSONDecodeError as e:
            log.error(f"JSON Decode Error for {url}: {e}. Response text: {response.text}")
            raise BitfinexAPIError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            log.error(f"An unexpected error occurred during API request to {url}: {e}")
            raise BitfinexAPIError(f"Unexpected error: {e}") from e

    # --- 公共端點 (無需認證) ---

    def get_funding_book(self, symbol: str, precision: str = 'P0', limit: int = 50) -> Dict[str, List[List[Union[Decimal, int]]]]:
        """
        獲取指定資金對的資金簿。
        :param symbol: 資金對符號 (例如 'fUSD')
        :param precision: 精度 (例如 'P0', 'P1')
        :param limit: 限制返回的條目數量
        :return: 資金簿數據
        """
        endpoint = f"book/{symbol}/f/{precision}"
        params = {'len': limit}
        log.debug(f"Fetching funding book for {symbol} with precision {precision} and limit {limit}")
        return self._make_request('GET', endpoint, payload=params)

    def get_tickers(self, symbols: List[str]) -> List[List[Any]]:
        """
        獲取指定交易對的 ticker 信息。
        :param symbols: 交易對符號列表 (例如 ['tBTCUSD', 'fUSD'])
        :return: ticker 數據
        """
        endpoint = f"tickers"
        params = {'symbols': ','.join(symbols)}
        log.debug(f"Fetching tickers for symbols: {symbols}")
        return self._make_request('GET', endpoint, payload=params)

    # --- 認證端點 (需要 API Key 和 Secret) ---

    def get_ledgers(self, currency: str, start: Optional[int] = None, end: Optional[int] = None, limit: Optional[int] = None) -> List[List[Any]]:
        """
        獲取賬本歷史記錄。
        :param currency: 貨幣符號 (例如 'USD')
        :param start: 開始時間戳 (毫秒)
        :param end: 結束時間戳 (毫秒)
        :param limit: 限制返回的條目數量
        :return: 賬本記錄列表
        """
        endpoint = f"auth/r/ledgers/{currency}/hist"
        payload = {}
        if start:
            payload['start'] = start
        if end:
            payload['end'] = end
        if limit:
            payload['limit'] = limit
        log.debug(f"Fetching ledgers for {currency} from {start} to {end} with limit {limit}")
        return self._make_request('POST', endpoint, payload=payload, authenticated=True)

    def get_funding_offers(self, symbol: str = 'ALL') -> List[List[Any]]:
        """
        獲取當前活躍的資金報價。
        :param symbol: 資金對符號 (例如 'fUSD' 或 'ALL' for all)
        :return: 資金報價列表
        """
        endpoint = f"auth/r/funding/offers/{symbol}"
        log.debug(f"Fetching funding offers for {symbol}")
        return self._make_request('POST', endpoint, authenticated=True)

    def submit_funding_offer(self, symbol: str, amount: Decimal, rate: Decimal, period: int, type: str = 'FRR') -> List[Any]:
        """
        提交一個資金報價。
        :param symbol: 資金對符號 (例如 'fUSD')
        :param amount: 金額
        :param rate: 日利率
        :param period: 期限 (天)
        :param type: 報價類型 (例如 'FRR', 'FIXED')
        :return: 報價響應
        """
        endpoint = "auth/w/funding/offer/submit"
        payload = {
            'symbol': symbol,
            'amount': str(amount), # API expects string for Decimal
            'rate': str(rate),     # API expects string for Decimal
            'period': period,
            'type': type
        }
        log.info(f"Submitting funding offer: {payload}")
        return self._make_request('POST', endpoint, payload=payload, authenticated=True)

    def cancel_funding_offer(self, order_id: int) -> List[Any]:
        """
        取消一個資金報價。
        :param order_id: 報價 ID
        :return: 取消響應
        """
        endpoint = "auth/w/funding/offer/cancel"
        payload = {
            'id': order_id
        }
        log.info(f"Cancelling funding offer with ID: {order_id}")
        return self._make_request('POST', endpoint, payload=payload, authenticated=True)

    def get_wallet_balances(self) -> List[List[Any]]:
        """
        獲取錢包餘額。
        :return: 錢包餘額列表
        """
        endpoint = "auth/r/wallets"
        log.debug("Fetching wallet balances")
        return self._make_request('POST', endpoint, authenticated=True)

    def get_summary(self) -> Dict[str, Any]:
        """
        獲取賬戶摘要信息，包括每日利潤。
        :return: 賬戶摘要數據
        """
        endpoint = "auth/r/summary"
        log.debug("Fetching account summary")
        return self._make_request('POST', endpoint, authenticated=True)
