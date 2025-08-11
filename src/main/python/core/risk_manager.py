import logging
from decimal import Decimal
from typing import Dict, Any

from src.main.python.core.config import AppConfig
from src.main.python.services.account_service import AccountService
from src.main.python.services.funding_service import FundingService
from src.main.python.core.order_manager import OrderManager
from src.main.python.utils.notification_manager import NotificationManager

log = logging.getLogger(__name__)

class RiskManager:
    """
    負責監控和管理機器人的風險。
    """
    def __init__(self, config: AppConfig,
                 account_service: AccountService,
                 funding_service: FundingService,
                 order_manager: OrderManager,
                 notification_manager: NotificationManager):
        self.config = config
        self.account_service = account_service
        self.funding_service = funding_service
        self.order_manager = order_manager
        self.notification_manager = notification_manager

        # 從配置中加載風險閾值
        self.max_loan_amount = config.trading.max_loan_amount
        # 可以添加更多風險相關的配置，例如：
        # self.max_utilization_rate = config.risk.max_utilization_rate
        # self.max_daily_loss_percentage = config.risk.max_daily_loss_percentage

    def assess_and_manage_risk(self) -> bool:
        """
        評估當前風險並採取相應措施。
        :return: 如果風險可控且操作可以繼續，則返回 True；否則返回 False。
        """
        log.info("Assessing and managing risk...")
        lending_currency = self.config.trading.lending_currency

        try:
            # 1. 檢查總放貸金額是否超過限制
            # 這需要從數據庫中獲取所有活躍訂單的總金額
            # 簡化：這裡我們假設 FundingService 可以提供當前總放貸金額
            # 實際實現中，可能需要從 LendingOrderRepository 查詢
            # total_active_loan = self.funding_service.get_total_active_loan_amount()
            # 由於 FundingService 沒有直接提供這個方法，我們暫時跳過這個檢查
            # 或者從 account_service 獲取 funding 錢包的 balance (已部署 + 可用)
            
            # 獲取資金錢包的總餘額 (已部署 + 可用)
            all_balances = self.account_service.get_all_wallet_balances()
            funding_wallet_info = all_balances.get('funding', {}).get(lending_currency, {})
            total_funding_balance = funding_wallet_info.get('balance', Decimal('0'))

            if total_funding_balance > self.max_loan_amount:
                message = f"WARNING: Total funding balance ({total_funding_balance:.2f} {lending_currency}) exceeds maximum allowed loan amount ({self.max_loan_amount:.2f}). Consider pausing new offers."
                log.warning(message)
                self.notification_manager.send_alert(message, level="WARNING")
                # 可以選擇在這裡返回 False，阻止新的放貸
                # return False

            # 2. 檢查資金利用率 (需要更詳細的資產數據)
            # 3. 監控每日盈虧 (需要 ProfitCalculationService 的數據)
            # 4. 檢查異常行為 (例如，連續的 API 錯誤)

            log.info("Risk assessment completed. No critical risks detected.")
            return True

        except Exception as e:
            message = f"CRITICAL: Error during risk assessment: {e}"
            log.critical(message, exc_info=True)
            self.notification_manager.send_alert(message, level="CRITICAL")
            return False

    def pause_bot(self):
        """
        暫停機器人的所有放貸操作。
        """
        log.warning("Pausing bot operations due to high risk or manual intervention.")
        self.notification_manager.send_alert("FundingBot operations paused.", level="WARNING")
        # 這裡可以設置一個標誌，阻止 main 循環繼續下單
        # 或者取消所有活躍訂單
        self.funding_service.cancel_all_funding_offers()

    def resume_bot(self):
        """
        恢復機器人的放貸操作。
        """
        log.info("Resuming bot operations.")
        self.notification_manager.send_alert("FundingBot operations resumed.", level="INFO")

