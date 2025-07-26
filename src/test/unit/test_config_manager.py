"""
配置管理器單元測試

測試新的統一配置系統的功能和驗證機制
"""

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from src.main.python.core.config import ConfigManager, get_config_manager, get_config
from src.main.python.core.exceptions import ConfigurationError


class TestConfigManager(unittest.TestCase):
    """配置管理器測試"""
    
    def setUp(self):
        """設置測試環境"""
        # 創建臨時 .env 文件
        self.temp_dir = tempfile.mkdtemp()
        self.env_file = os.path.join(self.temp_dir, '.env')
        
        # 基本配置內容
        self.basic_config = """
# API Configuration
API_KEY=test_api_key
API_SECRET=test_api_secret

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=test_db
DB_USER=test_user
DB_PASSWORD=test_password

# Trading Configuration
LENDING_CURRENCY=USD
LENDING_DURATION_DAYS=2
MIN_INTEREST_RATE=0.000165
CHECK_INTERVAL_SECONDS=60
MIN_ORDER_AMOUNT=150.0
MAX_LOAN_AMOUNT=10000.0

# Strategy Configuration
STRATEGY_NAME=laddering
LADDERING_LADDERS=3
LADDERING_RATE_SPREAD=0.0001

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE_ENABLED=false
"""
    
    def tearDown(self):
        """清理測試環境"""
        # 清理臨時文件
        if os.path.exists(self.env_file):
            os.remove(self.env_file)
        os.rmdir(self.temp_dir)
        
        # 重置全局配置管理器
        import src.main.python.core.config as config_module
        config_module._config_manager = None
    
    def create_env_file(self, content=None):
        """創建 .env 文件"""
        content = content or self.basic_config
        with open(self.env_file, 'w') as f:
            f.write(content)
    
    def test_basic_config_loading(self):
        """測試基本配置加載"""
        self.create_env_file()
        
        config_manager = ConfigManager(self.env_file)
        config = config_manager.config
        
        # 測試 API 配置
        self.assertEqual(config.api.key, "test_api_key")
        self.assertEqual(config.api.secret, "test_api_secret")
        
        # 測試數據庫配置
        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.database.port, 5432)
        self.assertEqual(config.database.name, "test_db")
        
        # 測試交易配置
        self.assertEqual(config.trading.lending_currency, "USD")
        self.assertEqual(config.trading.lending_duration_days, 2)
        self.assertEqual(config.trading.min_order_amount, Decimal('150.0'))
        
        # 測試策略配置
        self.assertEqual(config.strategy.strategy_name, "laddering")
        self.assertEqual(config.strategy.laddering_ladders, 3)
    
    def test_config_validation(self):
        """測試配置驗證"""
        self.create_env_file()
        
        config_manager = ConfigManager(self.env_file)
        
        # 基本配置應該通過驗證
        self.assertTrue(config_manager.validate_config())
    
    def test_invalid_strategy_name(self):
        """測試無效策略名稱"""
        invalid_config = self.basic_config.replace(
            "STRATEGY_NAME=laddering", 
            "STRATEGY_NAME=invalid_strategy"
        )
        self.create_env_file(invalid_config)
        
        with self.assertRaises(ValueError):
            ConfigManager(self.env_file)
    
    def test_invalid_database_port(self):
        """測試無效數據庫端口"""
        invalid_config = self.basic_config.replace(
            "DB_PORT=5432", 
            "DB_PORT=99999"
        )
        self.create_env_file(invalid_config)
        
        with self.assertRaises(ValueError):
            ConfigManager(self.env_file)
    
    def test_missing_required_config(self):
        """測試缺少必需配置"""
        incomplete_config = """
API_KEY=test_key
# Missing API_SECRET
DB_HOST=localhost
"""
        self.create_env_file(incomplete_config)
        
        with self.assertRaises(Exception):
            ConfigManager(self.env_file)
    
    def test_default_values(self):
        """測試默認值"""
        minimal_config = """
API_KEY=test_key
API_SECRET=test_secret
DB_NAME=test_db
DB_USER=test_user
DB_PASSWORD=test_password
"""
        self.create_env_file(minimal_config)
        
        config_manager = ConfigManager(self.env_file)
        config = config_manager.config
        
        # 測試默認值
        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.database.port, 5432)
        self.assertEqual(config.trading.lending_currency, "USD")
        self.assertEqual(config.strategy.strategy_name, "laddering")
        self.assertEqual(config.logging.level, "INFO")
    
    def test_config_reload(self):
        """測試配置重新加載"""
        self.create_env_file()
        
        config_manager = ConfigManager(self.env_file)
        original_currency = config_manager.config.trading.lending_currency
        
        # 修改配置文件
        updated_config = self.basic_config.replace(
            "LENDING_CURRENCY=USD", 
            "LENDING_CURRENCY=BTC"
        )
        self.create_env_file(updated_config)
        
        # 重新加載配置
        config_manager.reload()
        new_currency = config_manager.config.trading.lending_currency
        
        self.assertEqual(original_currency, "USD")
        self.assertEqual(new_currency, "BTC")
    
    def test_global_config_manager(self):
        """測試全局配置管理器"""
        self.create_env_file()
        
        # 第一次調用應該創建新實例
        manager1 = get_config_manager(self.env_file)
        
        # 第二次調用應該返回相同實例
        manager2 = get_config_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_decimal_precision(self):
        """測試 Decimal 精度處理"""
        precision_config = self.basic_config.replace(
            "MIN_INTEREST_RATE=0.000165",
            "MIN_INTEREST_RATE=0.000000001"
        )
        self.create_env_file(precision_config)
        
        config_manager = ConfigManager(self.env_file)
        config = config_manager.config
        
        # 確保高精度數值正確處理
        self.assertEqual(config.trading.min_interest_rate, Decimal('0.000000001'))
    
    def test_logging_config(self):
        """測試日誌配置"""
        logging_config = self.basic_config + """
LOG_FILE_ENABLED=true
LOG_FILE_PATH=/tmp/test.log
"""
        self.create_env_file(logging_config)
        
        config_manager = ConfigManager(self.env_file)
        config = config_manager.config
        
        self.assertTrue(config.logging.file_enabled)
        self.assertEqual(config.logging.file_path, "/tmp/test.log")


if __name__ == '__main__':
    # 運行測試
    unittest.main() 