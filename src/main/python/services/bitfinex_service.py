import requests
from typing import List, Dict, Any

from src.main.python.models.daily_profit import DailyProfit
from src.main.python.repositories.daily_profit_repository import DailyProfitRepository

class BitfinexService:
    def __init__(self, api_key: str, api_secret: str, db_manager):
        self.base_url = "https://api.bitfinex.com/v2/"
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.daily_profit_repository = DailyProfitRepository(db_manager)

    def _get_auth_headers(self, nonce: str, path: str, body: str = '') -> Dict[str, str]:
        signature_payload = f'/api/{path}{nonce}{body}'
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_payload.encode('utf-8'),
            hashlib.sha384
        ).hexdigest()

        return {
            'bfx-nonce': nonce,
            'bfx-apikey': self.api_key,
            'bfx-signature': signature
        }

    def get_daily_profits(self) -> List[DailyProfit]:
        path = 'v2/auth/r/summary'
        nonce = str(int(time.time() * 1000))
        headers = self._get_auth_headers(nonce, path)
        response = self.session.post(f'{self.base_url}{path}', headers=headers)
        response.raise_for_status()
        data = response.json()

        daily_profits = []
        if data and data.get('summary') and data.get('summary').get('daily_profit'):
            for item in data['summary']['daily_profit']:
                daily_profits.append(DailyProfit(
                    currency=item['currency'],
                    interest_income=Decimal(item['interest_income']),
                    total_loan=Decimal(item['total_loan']),
                    type=item['type'],
                    date=datetime.fromtimestamp(item['timestamp'] / 1000).date()
                ))
        return daily_profits

    def save_daily_profits(self, daily_profits: List[DailyProfit]):
        for profit in daily_profits:
            self.daily_profit_repository.save_daily_profit(profit)
