import logging
from typing import Any, Dict, Optional, Type, Union
from dataclasses import dataclass, field
from decimal import Decimal
from decouple import Config, RepositoryEnv
from pathlib import Path
import os

log = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """數據庫配置"""
    host: str
    port: int
    name: str
    user: str
    password: str
    
    def __post_init__(self):
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"Invalid database port: {self.port}")


@dataclass
class ApiConfig:
    """API 配置"""
    key: str
    secret: str
    
    def __post_init__(self):
        if not self.key or not self.secret:
            raise ValueError("API key and secret are required")


@dataclass
class TradingConfig:
    """交易配置"""
    lending_currency: str
    lending_duration_days: int
    min_interest_rate: Decimal
    check_interval_seconds: int
    min_order_amount: Decimal = Decimal('150.0')  # Bitfinex 最低訂單金額
    max_loan_amount: Decimal = Decimal('10000.0')
    
    def __post_init__(self):
        if self.lending_duration_days <= 0:
            raise ValueError(f"Invalid lending duration: {self.lending_duration_days}")
        if self.min_interest_rate < 0:
            raise ValueError(f"Invalid minimum interest rate: {self.min_interest_rate}")
        if self.check_interval_seconds < 10:
            raise ValueError(f"Check interval too short: {self.check_interval_seconds}")
        if self.min_order_amount <= 0:
            raise ValueError(f"Invalid minimum order amount: {self.min_order_amount}")


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_name: str = 'laddering'
    
    # Laddering Strategy
    laddering_ladders: int = 3
    laddering_rate_spread: Decimal = Decimal('0.0001')
    
    # Adaptive Laddering Strategy
    al_lookback_period_hours: int = 24
    al_volatility_spread_multiplier: Decimal = Decimal('1.5')
    
    # Spread Filler Strategy
    sf_spread_position_ratio: Decimal = Decimal('0.5')
    sf_min_spread_threshold: Decimal = Decimal('0.0001')
    
    # Market Taker Strategy
    mt_amount_percentage: Decimal = Decimal('0.995')
    
    def __post_init__(self):
        valid_strategies = ['laddering', 'adaptive_laddering', 'spread_filler', 'market_taker']
        if self.strategy_name not in valid_strategies:
            raise ValueError(f"Invalid strategy: {self.strategy_name}. Valid options: {valid_strategies}")
        
        if self.laddering_ladders <= 0:
            raise ValueError(f"Invalid ladder count: {self.laddering_ladders}")
        
        if not (0 < self.mt_amount_percentage <= 1):
            raise ValueError(f"Invalid amount percentage: {self.mt_amount_percentage}")


@dataclass
class LoggingConfig:
    """日誌配置"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_enabled: bool = False
    file_path: Optional[str] = None
    
    def __post_init__(self):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.level not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}. Valid options: {valid_levels}")


@dataclass
class AppConfig:
    """應用程序總配置"""
    database: DatabaseConfig
    api: ApiConfig
    trading: TradingConfig
    strategy: StrategyConfig
    logging: LoggingConfig


class ConfigManager:
    """統一配置管理器"""
    
    def __init__(self, env_file_path: Optional[str] = None):
        self._config: Optional[AppConfig] = None
        self._raw_config: Optional[Config] = None
        self._env_file_path = env_file_path or self._find_env_file()
        self._load_config()
    
    def _find_env_file(self) -> str:
        """自動尋找 .env 文件"""
        current_dir = Path.cwd()
        for _ in range(5):  # 最多向上查找 5 層目錄
            env_file = current_dir / '.env'
            if env_file.exists():
                return str(env_file)
            current_dir = current_dir.parent
        
        # 如果找不到，返回當前目錄的 .env
        return '.env'
    
    def _load_config(self):
        """加載配置"""
        try:
            self._raw_config = Config(RepositoryEnv(self._env_file_path))
            log.info(f"Loaded configuration from: {self._env_file_path}")
            
            # 加載各個配置部分
            database_config = self._load_database_config()
            api_config = self._load_api_config()
            trading_config = self._load_trading_config()
            strategy_config = self._load_strategy_config()
            logging_config = self._load_logging_config()
            
            self._config = AppConfig(
                database=database_config,
                api=api_config,
                trading=trading_config,
                strategy=strategy_config,
                logging=logging_config
            )
            
            log.info("Configuration loaded and validated successfully")
            
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_database_config(self) -> DatabaseConfig:
        """加載數據庫配置"""
        return DatabaseConfig(
            host=self._raw_config('DB_HOST', default='localhost'),
            port=self._raw_config('DB_PORT', cast=int, default=5432),
            name=self._raw_config('DB_NAME'),
            user=self._raw_config('DB_USER'),
            password=self._raw_config('DB_PASSWORD')
        )
    
    def _load_api_config(self) -> ApiConfig:
        """加載 API 配置"""
        return ApiConfig(
            key=self._raw_config('API_KEY'),
            secret=self._raw_config('API_SECRET')
        )
    
    def _load_trading_config(self) -> TradingConfig:
        """加載交易配置"""
        return TradingConfig(
            lending_currency=self._raw_config('LENDING_CURRENCY', default='USD'),
            lending_duration_days=self._raw_config('LENDING_DURATION_DAYS', cast=int, default=2),
            min_interest_rate=Decimal(self._raw_config('MIN_INTEREST_RATE', default='0.000165')),
            check_interval_seconds=self._raw_config('CHECK_INTERVAL_SECONDS', cast=int, default=60),
            min_order_amount=Decimal(self._raw_config('MIN_ORDER_AMOUNT', default='150.0')),
            max_loan_amount=Decimal(self._raw_config('MAX_LOAN_AMOUNT', default='10000.0'))
        )
    
    def _load_strategy_config(self) -> StrategyConfig:
        """加載策略配置"""
        return StrategyConfig(
            strategy_name=self._raw_config('STRATEGY_NAME', default='laddering'),
            laddering_ladders=self._raw_config('LADDERING_LADDERS', cast=int, default=3),
            laddering_rate_spread=Decimal(self._raw_config('LADDERING_RATE_SPREAD', default='0.0001')),
            al_lookback_period_hours=self._raw_config('AL_LOOKBACK_PERIOD_HOURS', cast=int, default=24),
            al_volatility_spread_multiplier=Decimal(self._raw_config('AL_VOLATILITY_SPREAD_MULTIPLIER', default='1.5')),
            sf_spread_position_ratio=Decimal(self._raw_config('SF_SPREAD_POSITION_RATIO', default='0.5')),
            sf_min_spread_threshold=Decimal(self._raw_config('SF_MIN_SPREAD_THRESHOLD', default='0.0001')),
            mt_amount_percentage=Decimal(self._raw_config('MT_AMOUNT_PERCENTAGE', default='0.995'))
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """加載日誌配置"""
        return LoggingConfig(
            level=self._raw_config('LOG_LEVEL', default='INFO'),
            format=self._raw_config('LOG_FORMAT', default='%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_enabled=self._raw_config('LOG_FILE_ENABLED', cast=bool, default=False),
            file_path=self._raw_config('LOG_FILE_PATH', default=None)
        )
    
    @property
    def config(self) -> AppConfig:
        """獲取配置對象"""
        if self._config is None:
            raise RuntimeError("Configuration not loaded")
        return self._config
    
    def get_raw_config(self, key: str, default=None, cast=None):
        """獲取原始配置值（用於向後兼容）"""
        if self._raw_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._raw_config(key, default=default, cast=cast)
    
    def reload(self):
        """重新加載配置"""
        log.info("Reloading configuration...")
        self._load_config()
    
    def validate_config(self) -> bool:
        """驗證配置的完整性"""
        try:
            # 基本驗證已在 dataclass 的 __post_init__ 中完成
            # 這裡可以添加更複雜的業務邏輯驗證
            
            # 驗證策略與相關參數的一致性
            strategy = self.config.strategy
            if strategy.strategy_name == 'laddering' and strategy.laddering_ladders <= 0:
                raise ValueError("Laddering strategy requires positive ladder count")
            
            # 驗證最小訂單金額與策略參數的一致性
            trading = self.config.trading
            if strategy.laddering_ladders > 0:
                min_balance_needed = strategy.laddering_ladders * trading.min_order_amount
                if min_balance_needed > trading.max_loan_amount:
                    log.warning(f"Ladder configuration may require more balance ({min_balance_needed}) than max loan amount ({trading.max_loan_amount})")
            
            log.info("Configuration validation passed")
            return True
            
        except Exception as e:
            log.error(f"Configuration validation failed: {e}")
            return False


# 全局配置管理器實例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(env_file_path: Optional[str] = None) -> ConfigManager:
    """獲取全局配置管理器實例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(env_file_path)
    return _config_manager


def get_config() -> AppConfig:
    """快捷方式獲取配置"""
    return get_config_manager().config 