import asyncio
import time
import logging
import importlib
from decimal import Decimal
from dotenv import load_dotenv
from bfxapi import Client
from typing import Optional

from src.main.python.core.config import get_config_manager, AppConfig
from src.main.python.core.exceptions import (
    FundingBotError, ConfigurationError, StrategyLoadError, 
    InsufficientBalanceError, InvalidOrderError, create_strategy_load_error,
    create_insufficient_balance_error, create_invalid_order_error, handle_api_errors
)
from src.main.python.services.database_manager import DatabaseManager
from src.main.python.repositories.market_log_repository import MarketLogRepository
from src.main.python.models.market_log import MarketLog
from src.main.python.models.lending_order import LendingOrder, OrderStatus
from src.main.python.models.interest_payment import InterestPayment

import bfxapi
from datetime import datetime

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
            self.bfx = Client(
                api_key=self.config.api.key, 
                api_secret=self.config.api.secret
            )
            self.db_manager = DatabaseManager(self.config.database)
            self.market_log_repo = MarketLogRepository(self.db_manager)
            
            # --- Load Strategy ---
            self.strategy = self._load_strategy()
            
            log.info("FundingBot initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize FundingBot: {e}")
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

    def _load_strategy(self):
        """動態加載配置中指定的策略"""
        strategy_name = self.config.strategy.strategy_name
        log.info(f"Loading strategy: {strategy_name}")
        
        try:
            module_path = f"src.main.python.core.strategies.{strategy_name}_strategy"
            strategy_module = importlib.import_module(module_path)
            class_name = f"{strategy_name.replace('_', ' ').title().replace(' ', '')}Strategy"
            strategy_class = getattr(strategy_module, class_name)
            
            # 傳遞配置和服務到策略
            return strategy_class(self.bfx, self.config, self.market_log_repo)
            
        except (ImportError, AttributeError) as e:
            error = create_strategy_load_error(strategy_name, e)
            log.error(f"Failed to load strategy: {error}")
            raise error

    @handle_api_errors
    async def get_available_balance(self) -> Decimal:
        """獲取資金錢包中的可用餘額"""
        currency = self.config.trading.lending_currency
        
        try:
            wallets = await asyncio.to_thread(self.bfx.rest.auth.get_wallets)
            
            for wallet in wallets:
                if wallet.wallet_type == "funding" and wallet.currency == currency:
                    balance = Decimal(str(wallet.available_balance))
                    log.info(f"Available balance in funding wallet: {balance:.2f} {currency}")
                    return balance
            
            log.warning(f"No funding wallet found for {currency}")
            return Decimal('0.0')
            
        except Exception as e:
            log.error(f"Failed to get available balance: {e}")
            raise

    @handle_api_errors
    async def cancel_all_funding_offers(self):
        """獲取並取消所有活躍的資金借貸訂單"""
        currency = self.config.trading.lending_currency
        symbol = f"f{currency}"
        
        try:
            offers = await asyncio.to_thread(self.bfx.rest.auth.get_funding_offers, symbol=symbol)
            
            if not offers:
                log.info(f"No active offers found for {symbol}")
                return

            log.info(f"Found {len(offers)} active offers for {symbol}. Cancelling them...")
            
            cancelled_count = 0
            failed_count = 0
            
            for offer in offers:
                try:
                    await asyncio.to_thread(self.bfx.rest.auth.cancel_funding_offer, offer.id)
                    log.info(f"Successfully cancelled offer ID: {offer.id}")
                    cancelled_count += 1
                except Exception as e:
                    log.error(f"Failed to cancel offer ID: {offer.id}. Reason: {e}")
                    failed_count += 1
                    
            log.info(f"Cancellation complete: {cancelled_count} successful, {failed_count} failed")
            
        except Exception as e:
            log.error(f"Error fetching or cancelling funding offers: {e}")
            raise

    @handle_api_errors
    async def place_funding_offer(self, rate: Decimal, amount: Decimal, period: int, 
                                strategy_name: Optional[str] = None, 
                                strategy_params: Optional[dict] = None):
        """下達單個資金借貸訂單並記錄到資料庫"""
        currency = self.config.trading.lending_currency
        symbol = f"f{currency}"
        min_amount = self.config.trading.min_order_amount
        
        # 驗證訂單參數
        if amount < min_amount:
            raise create_invalid_order_error(float(amount), float(min_amount), currency)
        
        if rate <= 0:
            raise InvalidOrderError(f"Invalid rate: {rate}")
        
        if period <= 0:
            raise InvalidOrderError(f"Invalid period: {period}")
        
        try:
            log.info(f"Placing offer: {amount:.2f} {currency} at daily rate of {rate*100:.4f}% for {period} days")
            
            # 提交訂單到 Bitfinex
            response = await asyncio.to_thread(
                self.bfx.rest.auth.submit_funding_offer,
                type="LIMIT",
                symbol=symbol,
                amount=float(amount),
                rate=float(rate),
                period=period
            )
            
            log.info("Offer placed successfully")
            
            # 創建 LendingOrder 記錄
            await self._create_lending_order_record(
                response, symbol, amount, rate, period, strategy_name, strategy_params
            )
            
        except Exception as e:
            log.error(f"Error placing funding offer: {e}")
            raise
    
    async def _create_lending_order_record(self, api_response, symbol: str, amount: Decimal, 
                                         rate: Decimal, period: int, strategy_name: Optional[str], 
                                         strategy_params: Optional[dict]):
        """創建 LendingOrder 資料庫記錄"""
        try:
            # 從 API 響應中提取訂單 ID
            # 注意：Bitfinex API 響應格式可能需要根據實際情況調整
            order_id = None
            if hasattr(api_response, 'id'):
                order_id = api_response.id
            elif isinstance(api_response, dict) and 'id' in api_response:
                order_id = api_response['id']
            elif isinstance(api_response, list) and len(api_response) > 0:
                order_id = api_response[0]  # 有時 API 返回數組格式
            
            if not order_id:
                log.warning("Unable to extract order ID from API response, generating temporary ID")
                order_id = int(datetime.now().timestamp() * 1000000)  # 臨時 ID
            
            # 創建 LendingOrder 實例
            lending_order = LendingOrder(
                order_id=order_id,
                symbol=symbol,
                amount=amount,
                rate=rate,
                period=period,
                status=OrderStatus.PENDING,
                strategy_name=strategy_name,
                strategy_params=strategy_params
            )
            
            # 保存到資料庫（暫時記錄日誌，等 Repository 層實現）
            log.info(f"Created LendingOrder record: ID={order_id}, Amount={amount}, Rate={rate*100:.4f}%")
            
            # TODO: 實際保存到資料庫
            # await self.lending_order_repository.save(lending_order)
            
        except Exception as e:
            log.error(f"Error creating LendingOrder record: {e}")
            # 不拋出異常，避免影響主要的下單流程
    
    async def sync_order_status(self):
        """同步活躍訂單的狀態"""
        try:
            log.info("Syncing order status from Bitfinex...")
            
            # 獲取當前活躍的資金訂單
            symbol = f"f{self.config.trading.lending_currency}"
            offers = await asyncio.to_thread(self.bfx.rest.auth.get_funding_offers, symbol=symbol)
            
            log.info(f"Found {len(offers)} active funding offers")
            
            # TODO: 實現與資料庫中 LendingOrder 記錄的同步
            # 1. 從資料庫獲取狀態為 PENDING/ACTIVE 的訂單
            # 2. 比對 API 返回的活躍訂單
            # 3. 更新訂單狀態、執行金額等信息
            # 4. 標記不再活躍的訂單為已完成
            
            for offer in offers:
                log.info(f"Active offer: ID={offer.id}, Amount={offer.amount}, Rate={offer.rate*100:.4f}%")
            
        except Exception as e:
            log.error(f"Error syncing order status: {e}")
    
    async def sync_interest_payments(self):
        """同步利息支付記錄"""
        try:
            log.info("Syncing interest payments from Bitfinex ledger...")
            
            currency = self.config.trading.lending_currency
            
            # 獲取最近的 ledger 記錄
            ledgers = await asyncio.to_thread(
                self.bfx.rest.auth.get_ledgers,
                currency=currency,
                limit=250  # 增加獲取數量以確保覆蓋
            )
            
            # 過濾出資金相關的收益記錄
            funding_payments = [
                ledger for ledger in ledgers 
                if hasattr(ledger, 'description') and ledger.description and 
                any(keyword in ledger.description.lower() for keyword in ['funding', 'interest', 'lending'])
            ]
            
            log.info(f"Found {len(funding_payments)} potential interest payment records from API.")
            
            saved_count = 0
            skipped_count = 0
            
            for ledger in funding_payments:
                try:
                    interest_payment = InterestPayment.from_ledger_entry({
                        'id': ledger.id,
                        'currency': ledger.currency,
                        'amount': ledger.amount,
                        'mts': ledger.mts,
                        'description': ledger.description
                    })
                    
                    # 保存到資料庫，如果不存在
                    if self.interest_payment_repo.save_if_not_exists(interest_payment):
                        saved_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    log.warning(f"Error processing ledger entry {ledger.id}: {e}")
            
            log.info(f"Interest sync complete. Saved: {saved_count}, Skipped (already exist): {skipped_count}")
            
        except Exception as e:
            log.error(f"Error syncing interest payments: {e}")
    
    async def generate_basic_profit_report(self):
        """生成基本的收益報告"""
        try:
            log.info("Generating basic profit report...")
            
            # TODO: 實現基本收益報告
            # 1. 統計所有 LendingOrder 的預期收益
            # 2. 統計所有 InterestPayment 的實際收益
            # 3. 計算差異和收益率
            # 4. 輸出報告到日誌
            
            log.info("=== 收益報告 ===")
            log.info("預期收益: 待實現")
            log.info("實際收益: 待實現") 
            log.info("收益差異: 待實現")
            log.info("平均收益率: 待實現")
            log.info("===============")
            
        except Exception as e:
            log.error(f"Error generating profit report: {e}")

    async def run(self):
        """機器人主運行循環"""
        log.info("FundingBot is running")
        
        trading_config = self.config.trading
        min_balance = trading_config.min_order_amount
        currency = trading_config.lending_currency
        interval = trading_config.check_interval_seconds
        
        while True:
            cycle_start_time = time.time()
            
            try:
                log.info(f"\n{'='*50}\nStarting new cycle at {time.ctime()}\n{'='*50}")
                
                # 1. 取消現有訂單
                await self.cancel_all_funding_offers()
                await asyncio.sleep(5)  # 給 API 一些時間處理取消操作
                
                # 2. 獲取可用餘額
                available_balance = await self.get_available_balance()
                
                # 3. 獲取市場數據
                market_data = await self.strategy.analyze_and_log_market()
                
                # 4. 檢查餘額是否足夠
                if available_balance < min_balance:
                    raise create_insufficient_balance_error(
                        float(available_balance), 
                        float(min_balance), 
                        currency
                    )
                
                # 5. 生成訂單
                offers_to_place = await self.strategy.generate_offers(available_balance, market_data)
                
                if offers_to_place:
                    log.info(f"Strategy generated {len(offers_to_place)} offer(s) to place")
                    
                                    # 6. 下達訂單
                successful_orders = 0
                strategy_name = self.strategy.get_strategy_name()
                strategy_info = self.strategy.get_strategy_info()
                
                for i, offer in enumerate(offers_to_place):
                    try:
                        await self.place_funding_offer(
                            Decimal(str(offer['rate'])), 
                            Decimal(str(offer['amount'])), 
                            offer['period'],
                            strategy_name=strategy_name,
                            strategy_params=strategy_info
                        )
                        successful_orders += 1
                        
                        # 避免 API 速率限制
                        if i < len(offers_to_place) - 1:
                            await asyncio.sleep(1)
                            
                    except Exception as e:
                        log.error(f"Failed to place offer {i+1}: {e}")
                    
                    log.info(f"Order placement complete: {successful_orders}/{len(offers_to_place)} successful")
                else:
                    log.info("Strategy did not generate any offers in this cycle")

            except InsufficientBalanceError as e:
                log.warning(f"Insufficient balance: {e.message}")
                log.info("Skipping offer placement this cycle")
                
            except FundingBotError as e:
                log.error(f"Bot error in main loop: {e.message}")
                if e.details:
                    log.debug(f"Error details: {e.details}")
                
            except Exception as e:
                log.error(f"Unexpected error in main loop: {e}", exc_info=True)

            finally:
                # 計算週期時間
                cycle_time = time.time() - cycle_start_time
                log.info(f"Cycle completed in {cycle_time:.2f} seconds")
                log.info(f"Sleeping for {interval} seconds until next cycle")
                await asyncio.sleep(interval)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._cleanup()

async def main():
    """主函數"""
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
            await bot.run()
            
    except ConfigurationError as e:
        log.critical(f"Configuration error: {e.message}")
        if e.details:
            log.debug(f"Configuration details: {e.details}")
        
    except FundingBotError as e:
        log.critical(f"Bot error: {e.message}")
        if e.details:
            log.debug(f"Error details: {e.details}")
        
    except KeyboardInterrupt:
        log.info("Received interrupt signal, shutting down gracefully...")
        
    except Exception as e:
        log.critical(f"Critical error occurred: {e}", exc_info=True)
        
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
    asyncio.run(main())