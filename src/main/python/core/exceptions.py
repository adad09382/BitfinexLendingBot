"""
自定義異常定義
提供分層的異常處理體系以支持更精確的錯誤處理
"""

import logging
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)


class FundingBotError(Exception):
    """
    Funding Bot 基礎異常類
    所有自定義異常的基類
    """
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        
        # 記錄異常
        log.error(f"[{self.error_code}] {self.message}", extra={'details': self.details})


class ConfigurationError(FundingBotError):
    """配置相關異常"""
    pass


class DatabaseError(FundingBotError):
    """數據庫相關異常"""
    pass


class DatabaseConnectionError(DatabaseError):
    """數據庫連接異常"""
    pass


class DatabaseQueryError(DatabaseError):
    """數據庫查詢異常"""
    pass


class ApiError(FundingBotError):
    """API 相關異常"""
    pass


class ApiConnectionError(ApiError):
    """API 連接異常"""
    pass


class ApiAuthenticationError(ApiError):
    """API 認證異常"""
    pass


class ApiRateLimitError(ApiError):
    """API 速率限制異常"""
    pass


class ApiInvalidResponseError(ApiError):
    """API 無效響應異常"""
    pass


class TradingError(FundingBotError):
    """交易相關異常"""
    pass


class InsufficientBalanceError(TradingError):
    """餘額不足異常"""
    pass


class InvalidOrderError(TradingError):
    """無效訂單異常"""
    pass


class OrderPlacementError(TradingError):
    """訂單下達異常"""
    pass


class OrderCancellationError(TradingError):
    """訂單取消異常"""
    pass


class StrategyError(FundingBotError):
    """策略相關異常"""
    pass


class StrategyLoadError(StrategyError):
    """策略加載異常"""
    pass


class StrategyExecutionError(StrategyError):
    """策略執行異常"""
    pass


class StrategyConfigurationError(StrategyError):
    """策略配置異常"""
    pass


class MarketDataError(FundingBotError):
    """市場數據相關異常"""
    pass


class MarketDataUnavailableError(MarketDataError):
    """市場數據不可用異常"""
    pass


class MarketDataParsingError(MarketDataError):
    """市場數據解析異常"""
    pass


# 異常工廠函數
def create_insufficient_balance_error(available: float, required: float, currency: str) -> InsufficientBalanceError:
    """創建餘額不足異常"""
    return InsufficientBalanceError(
        f"Insufficient balance: {available:.2f} {currency} available, {required:.2f} {currency} required",
        details={
            'available_balance': available,
            'required_balance': required,
            'currency': currency,
            'shortfall': required - available
        }
    )


def create_invalid_order_error(amount: float, min_amount: float, currency: str) -> InvalidOrderError:
    """創建無效訂單異常"""
    return InvalidOrderError(
        f"Order amount {amount:.2f} {currency} is below minimum {min_amount:.2f} {currency}",
        details={
            'order_amount': amount,
            'minimum_amount': min_amount,
            'currency': currency
        }
    )


def create_api_rate_limit_error(retry_after: Optional[int] = None) -> ApiRateLimitError:
    """創建 API 速率限制異常"""
    message = "API rate limit exceeded"
    if retry_after:
        message += f", retry after {retry_after} seconds"
    
    return ApiRateLimitError(
        message,
        details={'retry_after': retry_after}
    )


def create_strategy_load_error(strategy_name: str, error: Exception) -> StrategyLoadError:
    """創建策略加載異常"""
    return StrategyLoadError(
        f"Failed to load strategy '{strategy_name}': {str(error)}",
        details={
            'strategy_name': strategy_name,
            'original_error': str(error),
            'original_error_type': type(error).__name__
        }
    )


def create_market_data_unavailable_error(symbol: str, period: Optional[int] = None) -> MarketDataUnavailableError:
    """創建市場數據不可用異常"""
    message = f"Market data unavailable for {symbol}"
    details = {'symbol': symbol}
    
    if period:
        message += f" (period: {period} days)"
        details['period'] = period
    
    return MarketDataUnavailableError(message, details=details)


# 異常處理裝飾器
def handle_api_errors(func):
    """API 錯誤處理裝飾器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 根據異常類型轉換為對應的自定義異常
            error_message = str(e).lower()
            
            if 'rate limit' in error_message or 'too many requests' in error_message:
                raise create_api_rate_limit_error() from e
            elif 'authentication' in error_message or 'unauthorized' in error_message:
                raise ApiAuthenticationError(f"API authentication failed: {str(e)}") from e
            elif 'connection' in error_message or 'timeout' in error_message:
                raise ApiConnectionError(f"API connection failed: {str(e)}") from e
            else:
                raise ApiError(f"API error: {str(e)}") from e
    
    return wrapper


def handle_database_errors(func):
    """數據庫錯誤處理裝飾器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = str(e).lower()
            
            if 'connection' in error_message or 'connect' in error_message:
                raise DatabaseConnectionError(f"Database connection failed: {str(e)}") from e
            elif 'query' in error_message or 'syntax' in error_message:
                raise DatabaseQueryError(f"Database query failed: {str(e)}") from e
            else:
                raise DatabaseError(f"Database error: {str(e)}") from e
    
    return wrapper 