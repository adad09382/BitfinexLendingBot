import time
import logging
import schedule # New import
from decimal import Decimal
from dotenv import load_dotenv
from typing import Optional, Dict, Any

from src.main.python.core.config import get_config_manager, AppConfig
from src.main.python.core.exceptions import (
    FundingBotError, ConfigurationError, StrategyLoadError, 
    InsufficientBalanceError, InvalidOrderError, create_strategy_load_error,
    create_insufficient_balance_error, create_invalid_order_error
)
from src.main.python.services.database_manager import DatabaseManager
from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.repositories.market_log_repository import MarketLogRepository
from src.main.python.repositories.lending_order_repository import LendingOrderRepository
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.repositories.daily_earnings_repository import DailyEarningsRepository
from src.main.python.services.market_data_service import MarketDataService
from src.main.python.services.account_service import AccountService
from src.main.python.services.funding_service import FundingService
from src.main.python.services.daily_settlement_service import DailySettlementService
from src.main.python.core.order_manager import OrderManager
from src.main.python.core.strategy_executor import StrategyExecutor
from src.main.python.core.risk_manager import RiskManager # New import
from src.main.python.utils.notification_manager import NotificationManager

log = logging.getLogger('FundingBot')

class FundingBot:
    """
    基於策略驅動的資金借貸機器人
    
    特性：
    - 統一配置管理
    - 分層異常處理
    - 自動化策略執行
    - 完善的資源管理
    """
    
    def __init__(self, app_config: AppConfig):
        log.info("Initializing FundingBot...")
        self.config = app_config
        
        # 初始化日誌系統
        self._setup_logging()
        
        # --- Initialize Services & Repositories ---
        try:
            self.db_manager = DatabaseManager(self.config.database)
            self.api_client = BitfinexApiClient(self.config.api)

            self.market_log_repo = MarketLogRepository(self.db_manager)
            self.lending_order_repo = LendingOrderRepository(self.db_manager)
            self.interest_payment_repo = InterestPaymentRepository(self.db_manager)
            self.daily_earnings_repo = DailyEarningsRepository(self.db_manager)

            self.market_data_service = MarketDataService(self.api_client, self.market_log_repo)
            self.account_service = AccountService(self.api_client)
            self.funding_service = FundingService(self.api_client, self.config, self.lending_order_repo)
            self.daily_settlement_service = DailySettlementService(
                self.daily_earnings_repo, 
                self.interest_payment_repo, 
                self.api_client
            )
            self.order_manager = OrderManager(self.api_client, self.lending_order_repo, self.interest_payment_repo)
            self.strategy_executor = StrategyExecutor(self.config)
            self.notification_manager = NotificationManager(
                telegram_bot_token=self.config.api.telegram_bot_token,
                telegram_chat_id=self.config.api.telegram_chat_id
            )
            self.risk_manager = RiskManager(
                config=self.config,
                account_service=self.account_service,
                funding_service=self.funding_service,
                order_manager=self.order_manager,
                notification_manager=self.notification_manager
            )
            
            log.info("FundingBot initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize FundingBot: {e}")
            self.notification_manager.send_alert(f"FundingBot initialization failed: {e}", level="CRITICAL")
            self._cleanup()
            raise
    
    def _setup_logging(self):
        """設置日誌系統"""
        logging_config = self.config.logging
        
        # 設置日誌級別
        log_level = getattr(logging, logging_config.level.upper())
        logging.getLogger().setLevel(log_level)
        
        # 設置格式
        formatter = logging.Formatter(logging_config.format)
        
        # 更新現有的處理器
        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
        
        # 文件日誌（如果啟用）
        if logging_config.file_enabled and logging_config.file_path:
            file_handler = logging.FileHandler(logging_config.file_path)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logging.getLogger().addHandler(file_handler)
            log.info(f"File logging enabled: {logging_config.file_path}")
    
    def _cleanup(self):
        """清理資源"""
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close()

    def run(self):
        """
        機器人主運行循環，使用 schedule 庫進行任務調度。
        """
        log.info("FundingBot is running")
        
        # 定義調度任務
        schedule.every(self.config.trading.check_interval_seconds).seconds.do(self._run_cycle)
        
        # 每日結算任務 (每天 00:05 執行)
        schedule.every().day.at("00:05").do(self._run_daily_settlement)

        # 首次運行
        self._run_cycle()

        while True:
            schedule.run_pending()
            time.sleep(1)

    def _run_cycle(self):
        """
        機器人單次運行週期。
        """
        cycle_start_time = time.time()
        lending_currency = self.config.trading.lending_currency
        min_order_amount = self.config.trading.min_order_amount

        log.info(f"
{'='*50}
Starting new cycle at {time.ctime()}
{'='*50}")

        try:
            # 0. 風險評估
            if not self.risk_manager.assess_and_manage_risk():
                log.warning("Risk assessment failed or indicated high risk. Skipping offer placement this cycle.")
                return

            # 1. 取消所有活躍訂單
            self.funding_service.cancel_all_funding_offers()
            time.sleep(2) # 給 API 一些時間處理取消操作

            # 2. 同步訂單狀態和處理利息支付
            self.order_manager.sync_order_statuses(lending_currency)
            self.order_manager.process_interest_payments(lending_currency)

            # 3. 獲取可用餘額
            available_balance = self.account_service.get_funding_balance(lending_currency)
            log.info(f"Available funding balance: {available_balance:.2f} {lending_currency}")

            # 4. 獲取市場數據
            market_data = self.market_data_service.fetch_and_store_funding_book(f'f{lending_currency}')
            if not market_data:
                log.warning("No market data available. Skipping offer generation this cycle.")
                return

            # 5. 檢查餘額是否足夠
            if available_balance < min_order_amount:
                raise create_insufficient_balance_error(
                    float(available_balance),
                    float(min_order_amount),
                    lending_currency
                )

            # 6. 生成訂單
            offers_to_place = self.strategy_executor.execute_strategy(available_balance, market_data.rates_data)

            if offers_to_place:
                log.info(f"Strategy generated {len(offers_to_place)} offer(s) to place")

                # 7. 下達訂單
                successful_orders = 0
                strategy_name = self.strategy_executor.get_active_strategy_name()
                # strategy_params 可以在策略內部獲取，或者從 config 中傳遞
                strategy_params = self.config.strategy.__dict__ # 傳遞所有策略配置

                for i, offer in enumerate(offers_to_place):
                    try:
                        self.funding_service.place_funding_offer(
                            offer['rate'],
                            offer['amount'],
                            offer['period'],
                            strategy_name=strategy_name,
                            strategy_params=strategy_params
                        )
                        successful_orders += 1

                        # 避免 API 速率限制
                        if i < len(offers_to_place) - 1:
                            time.sleep(1)

                    except Exception as e:
                        log.error(f"Failed to place offer {i+1}: {e}")

                log.info(f"Order placement complete: {successful_orders}/{len(offers_to_place)} successful")
            else:
                log.info("Strategy did not generate any offers in this cycle")

        except InsufficientBalanceError as e:
            log.warning(f"Insufficient balance: {e.message}")
            self.notification_manager.send_alert(f"Insufficient balance: {e.message}", level="WARNING")
            log.info("Skipping offer placement this cycle")

        except FundingBotError as e:
            log.error(f"Bot error in main loop: {e.message}")
            self.notification_manager.send_alert(f"Bot error: {e.message}", level="ERROR")
            if e.details:
                log.debug(f"Error details: {e.details}")

        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}", exc_info=True)
            self.notification_manager.send_alert(f"Unexpected error in main loop: {e}", level="CRITICAL")

        finally:
            # 計算週期時間
            cycle_time = time.time() - cycle_start_time
            log.info(f"Cycle completed in {cycle_time:.2f} seconds")
            log.info(f"Next cycle in {self.config.trading.check_interval_seconds} seconds")
            
    def _run_daily_settlement(self):
        """執行每日結算任務"""
        try:
            import asyncio
            from datetime import date, timedelta
            
            # 結算前一天的數據
            settlement_date = date.today() - timedelta(days=1)
            currency = self.config.trading.lending_currency
            
            log.info(f"開始每日結算: {settlement_date} {currency}")
            
            # 在同步環境中運行異步任務
            result = asyncio.run(
                self.daily_settlement_service.perform_daily_settlement(settlement_date, currency)
            )
            
            if result.success:
                log.info(f"每日結算成功: {settlement_date} {currency}")
                log.info(f"總收益: {result.daily_earnings.total_interest} {currency}")
                log.info(f"年化收益率: {result.daily_earnings.annualized_return:.2f}%")
                
                # 發送成功通知
                self.notification_manager.send_alert(
                    f"📊 每日結算完成\n"
                    f"日期: {settlement_date}\n"
                    f"收益: {result.daily_earnings.total_interest} {currency}\n"
                    f"年化收益率: {result.daily_earnings.annualized_return:.2f}%\n"
                    f"資金利用率: {result.daily_earnings.utilization_rate:.2f}%",
                    level="INFO"
                )
            else:
                log.error(f"每日結算失敗: {result.error_message}")
                self.notification_manager.send_alert(
                    f"❌ 每日結算失敗\n"
                    f"日期: {settlement_date}\n"
                    f"錯誤: {result.error_message}",
                    level="ERROR"
                )
                
        except Exception as e:
            log.error(f"每日結算異常: {e}", exc_info=True)
            self.notification_manager.send_alert(
                f"❌ 每日結算異常: {e}",
                level="CRITICAL"
            )

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._cleanup()

def main():
    """
    主函數，負責初始化和運行機器人。
    """
    config_manager = None
    bot = None
    
    try:
        # 初始化配置管理器
        config_manager = get_config_manager()
        app_config = config_manager.config
        
        # 驗證配置
        if not config_manager.validate_config():
            raise ConfigurationError("Configuration validation failed")
        
        # 設置基本日誌配置（在配置加載之前）
        logging.basicConfig(
            level=getattr(logging, app_config.logging.level),
            format=app_config.logging.format
        )
        
        log.info("Starting Bitfinex Funding Bot")
        log.info(f"Strategy: {app_config.strategy.strategy_name}")
        log.info(f"Currency: {app_config.trading.lending_currency}")
        log.info(f"Check interval: {app_config.trading.check_interval_seconds}s")
        
        # 初始化並運行機器人
        with FundingBot(app_config) as bot:
            bot.run()
            
    except ConfigurationError as e:
        log.critical(f"Configuration error: {e.message}")
        if bot and bot.notification_manager:
            bot.notification_manager.send_alert(f"Configuration error: {e.message}", level="CRITICAL")
        if e.details:
            log.debug(f"Configuration details: {e.details}")
        
    except FundingBotError as e:
        log.critical(f"Bot error: {e.message}")
        if bot and bot.notification_manager:
            bot.notification_manager.send_alert(f"Bot error: {e.message}", level="CRITICAL")
        if e.details:
            log.debug(f"Error details: {e.details}")
        
    except KeyboardInterrupt:
        log.info("Received interrupt signal, shutting down gracefully...")
        if bot and bot.notification_manager:
            bot.notification_manager.send_alert("FundingBot received interrupt signal, shutting down.", level="INFO")
        
    except Exception as e:
        log.critical(f"Critical error occurred: {e}", exc_info=True)
        if bot and bot.notification_manager:
            bot.notification_manager.send_alert(f"Critical error occurred: {e}", level="CRITICAL")
        
    finally:
        # 清理資源
        if bot:
            bot._cleanup()
        log.info("Shutdown complete")


if __name__ == "__main__":
    import os
    
    # 設置工作目錄到項目根目錄
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    os.chdir(project_root)
    
    # 加載環境變量
    load_dotenv(dotenv_path=os.path.join(project_root, '.env'), override=True)
    
    # 運行主程序
    main()