#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BitfinexAPI - 純 HTTP 請求的統一客戶端
解決混合使用套件和直接請求的 nonce 衝突問題
"""

import logging
import time
import requests
import hmac
import hashlib
import json
from typing import Dict, List, Optional, Any
from decimal import Decimal
from decouple import config

logger = logging.getLogger(__name__)

class BitfinexAPIError(Exception):
    """Bitfinex API 基礎異常"""
    pass

class BitfinexAuthError(BitfinexAPIError):
    """Bitfinex 認證錯誤"""
    pass

class BitfinexRateLimitError(BitfinexAPIError):
    """Bitfinex 頻率限制錯誤"""
    pass

class BitfinexAPI:
    """
    純 HTTP 請求的統一 API 客戶端
    解決 nonce 管理問題
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        初始化 API 客戶端
        
        Args:
            api_key: API密鑰，為空時從環境變量讀取
            api_secret: API密鑰，為空時從環境變量讀取
        """
        # API 認證配置
        self.api_key = api_key or config('BITFINEX_API_KEY', default='')
        self.api_secret = api_secret or config('BITFINEX_API_SECRET', default='')
        
        # API 端點配置
        self.base_url = 'https://api.bitfinex.com'
        self.base_url_public = 'https://api-pub.bitfinex.com'
        
        # 請求配置
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Nonce 管理
        self._last_nonce = int(time.time() * 1000)
        
        # 重試配置
        self.max_retry_attempts = int(config('MAX_RETRY_ATTEMPTS', default='3'))
        self.retry_delay_seconds = int(config('RETRY_DELAY_SECONDS', default='5'))
        
        # 驗證配置
        self._has_credentials = bool(self.api_key and self.api_secret)
        
        if self._has_credentials:
            logger.info("Bitfinex API 客戶端初始化完成 (已配置認證)")
        else:
            logger.info("Bitfinex API 客戶端初始化完成 (僅公開API)")
    
    def _get_nonce(self):
        """生成遞增的 nonce"""
        current_time_ms = int(time.time() * 1000)
        if current_time_ms <= self._last_nonce:
            self._last_nonce += 1
        else:
            self._last_nonce = current_time_ms
        return str(self._last_nonce)
    
    def _generate_auth_headers(self, path: str, body: str = '') -> Dict[str, str]:
        """生成認證頭"""
        if not self._has_credentials:
            raise BitfinexAuthError("API密鑰未配置，無法執行認證請求")
        
        nonce = self._get_nonce()
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
    
    def _make_request(self, method: str, path: str, params: Dict = None, authenticated: bool = False) -> Optional[Any]:
        """執行 HTTP 請求"""
        if path.startswith('/'):
            path = path[1:]
        
        # 選擇端點
        if authenticated:
            url = f"{self.base_url}/{path}"
        else:
            url = f"{self.base_url_public}/{path}"
        
        headers = {}
        body = ''
        
        try:
            # 處理認證
            if authenticated:
                if params and method == 'POST':
                    body = json.dumps(params)
                headers.update(self._generate_auth_headers(path, body))
            
            # 執行請求
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"不支持的請求方法: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"請求失敗: HTTP {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"請求異常 {method} {url}: {e}")
            return None
    
    # ==================== 公開API方法 ====================
    
    def get_funding_trades(self, currency: str, limit: int = 10) -> List[Any]:
        """獲取放貸成交歷史"""
        try:
            path = f'v2/trades/f{currency}/hist'
            params = {'limit': limit}
            response = self._make_request('GET', path, params=params)
            return response or []
        except Exception as e:
            logger.error(f"獲取 {currency} 成交記錄失敗: {e}")
            return []
    
    def get_funding_book(self, currency: str, precision: str = 'P0', depth: int = 25) -> List[Any]:
        """獲取放貸訂單簿"""
        try:
            path = f'v2/book/f{currency}/{precision}'
            response = self._make_request('GET', path)
            if response and depth > 0:
                return response[:depth]
            return response or []
        except Exception as e:
            logger.error(f"獲取 {currency} 訂單簿失敗: {e}")
            return []
    
    def get_funding_stats(self, currency: str) -> Optional[Dict]:
        """獲取放貸統計數據"""
        try:
            path = f'v2/stats1/funding.size:1m:f{currency}:p30/last'
            response = self._make_request('GET', path)
            if response and len(response) >= 2:
                return {
                    'timestamp': response[0],
                    'total_funding': float(response[1])
                }
        except Exception as e:
            logger.debug(f"獲取 {currency} 統計數據失敗 (非關鍵): {e}")
        return None
    
    # ==================== 私有API方法 ====================
    
    def get_wallet_balances(self) -> Dict[str, Decimal]:
        """獲取 funding 錢包餘額（用於放貸）"""
        try:
            response = self._make_request('POST', 'v2/auth/r/wallets', authenticated=True)
            
            if not response:
                return {}
            
            balances = {}
            for wallet in response:
                if len(wallet) >= 3:
                    wallet_type, currency, balance = wallet[0], wallet[1], wallet[2]
                    if wallet_type == 'funding':  # 只關心 funding 錢包
                        balances[currency] = Decimal(str(balance))
            
            logger.info(f"獲取 funding 錢包餘額成功: {dict(balances)}")
            return balances
            
        except Exception as e:
            logger.error(f"獲取錢包餘額失敗: {e}")
            return {}
    
    def get_all_wallet_balances(self) -> Dict[str, Dict[str, Decimal]]:
        """獲取所有錢包類型的餘額"""
        try:
            response = self._make_request('POST', 'v2/auth/r/wallets', authenticated=True)
            
            if not response:
                return {}
            
            wallets = {}
            for wallet in response:
                if len(wallet) >= 3:
                    wallet_type, currency, balance = wallet[0], wallet[1], wallet[2]
                    if wallet_type not in wallets:
                        wallets[wallet_type] = {}
                    if balance > 0:  # 只顯示有餘額的
                        wallets[wallet_type][currency] = Decimal(str(balance))
            
            logger.info(f"所有錢包餘額: {dict(wallets)}")
            return wallets
            
        except Exception as e:
            logger.error(f"獲取錢包餘額失敗: {e}")
            return {}
    
    def transfer_between_wallets(self, currency: str, amount: Decimal, from_wallet: str, to_wallet: str) -> bool:
        """
        在錢包之間轉移資金
        
        Args:
            currency: 貨幣代碼 (例如 'USD')
            amount: 轉移金額
            from_wallet: 源錢包 ('exchange', 'margin', 'funding')
            to_wallet: 目標錢包 ('exchange', 'margin', 'funding')
        
        Returns:
            bool: 轉移是否成功
        """
        try:
            payload = {
                'from': from_wallet,
                'to': to_wallet,
                'currency': currency,
                'amount': str(amount)
            }
            
            response = self._make_request('POST', 'v2/auth/w/transfer', payload, authenticated=True)
            
            if response and len(response) > 0:
                logger.info(f"錢包轉帳成功: {amount} {currency} 從 {from_wallet} 轉移到 {to_wallet}")
                return True
            else:
                logger.error(f"錢包轉帳失敗: 無效響應")
                return False
                
        except Exception as e:
            logger.error(f"錢包轉帳失敗: {e}")
            return False
    
    def get_active_funding_offers(self, currency: str) -> List[Any]:
        """獲取活躍的放貸訂單"""
        try:
            response = self._make_request('POST', f'v2/auth/r/funding/offers/{currency}', authenticated=True)
            if not response:
                return []
            
            logger.info(f"獲取活躍訂單成功: {len(response)} 筆")
            return response
        except Exception as e:
            logger.error(f"獲取活躍訂單失敗: {e}")
            return []
    
    def cancel_funding_offer(self, offer_id: int) -> bool:
        """取消單個放貸訂單"""
        try:
            params = {'id': offer_id}
            response = self._make_request('POST', 'v2/auth/w/funding/offer/cancel', params, authenticated=True)
            
            if response:
                logger.info(f"成功取消訂單: {offer_id}")
                return True
            else:
                logger.warning(f"取消訂單失敗: {offer_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消訂單異常: {e}")
            return False
    
    def cancel_all_funding_offers(self, currency: str) -> bool:
        """取消所有活躍的放貸訂單"""
        try:
            active_offers = self.get_active_funding_offers(currency)
            
            if not active_offers:
                logger.info("沒有需要取消的訂單")
                return True
            
            cancelled_count = 0
            for offer in active_offers:
                if len(offer) >= 1:
                    offer_id = offer[0]
                    if self.cancel_funding_offer(offer_id):
                        cancelled_count += 1
                        time.sleep(0.1)  # 避免請求過快
            
            logger.info(f"成功取消 {cancelled_count}/{len(active_offers)} 個訂單")
            return cancelled_count > 0
            
        except Exception as e:
            logger.error(f"批量取消訂單失敗: {e}")
            return False
    
    def submit_funding_offer(self, currency: str, amount: Decimal, rate: Decimal, period: int) -> Optional[Any]:
        """提交放貸訂單"""
        try:
            # rate 已經是小數形式的日利率，直接使用
            daily_rate_decimal = float(rate)
            
            params = {
                'type': 'LIMIT',
                'symbol': f'f{currency}',
                'amount': str(amount),
                'rate': str(daily_rate_decimal),
                'period': period,
                'flags': 0
            }
            
            response = self._make_request('POST', 'v2/auth/w/funding/offer/submit', params, authenticated=True)
            
            if response and isinstance(response, list) and len(response) >= 7:
                logger.info(f"提交訂單成功: {amount} {currency} @ {daily_rate_decimal*100:.4f}% (日利率) for {period} days")
                return response
            else:
                logger.warning(f"訂單提交響應異常: {response}")
                return None
                
        except Exception as e:
            logger.error(f"提交訂單失敗: {e}")
            return None
    
    # ==================== 工具方法 ====================
    
    def test_connection(self) -> bool:
        """測試API連接"""
        try:
            # 測試公開API
            trades = self.get_funding_trades('USD', limit=1)
            
            if trades is not None:
                logger.info("API連接測試成功 (公開API)")
                
                # 如果有認證，測試私有API
                if self._has_credentials:
                    try:
                        balances = self.get_wallet_balances()
                        logger.info("API連接測試成功 (私有API)")
                        return True
                    except BitfinexAuthError:
                        logger.warning("私有API認證失敗，但公開API正常")
                        return True
                
                return True
            else:
                logger.error("API連接測試失敗")
                return False
                
        except Exception as e:
            logger.error(f"API連接測試異常: {e}")
            return False

# ==================== 工廠函數 ====================

def create_api_client(api_key: str = None, api_secret: str = None) -> BitfinexAPI:
    """創建 Bitfinex API 客戶端的工廠函數"""
    return BitfinexAPI(api_key=api_key, api_secret=api_secret)

if __name__ == "__main__":
    # 測試腳本
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Bitfinex HTTP API 客戶端測試")
    print("=" * 40)
    
    # 創建客戶端
    api = BitfinexAPI()
    
    # 測試連接
    if api.test_connection():
        print("✅ API連接正常")
        
        # 測試錢包餘額
        balances = api.get_wallet_balances()
        if balances:
            print("💰 Funding 錢包餘額:")
            for currency, balance in balances.items():
                if balance > 0:
                    print(f"   {currency}: {balance}")
        
    else:
        print("❌ API連接失敗")