import logging
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.repositories.lending_order_repository import LendingOrderRepository
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.models.lending_order import LendingOrder, OrderStatus
from src.main.python.models.interest_payment import InterestPayment
from src.main.python.core.exceptions import BitfinexAPIError, DatabaseError

log = logging.getLogger(__name__)

class OrderManager:
    """
    負責管理放貸訂單的生命週期，包括狀態同步、利息支付記錄和到期處理。
    """
    def __init__(self, api_client: BitfinexApiClient, 
                 lending_order_repo: LendingOrderRepository,
                 interest_payment_repo: InterestPaymentRepository):
        self.api_client = api_client
        self.lending_order_repo = lending_order_repo
        self.interest_payment_repo = interest_payment_repo

    def sync_order_statuses(self, currency: str):
        """
        從 Bitfinex API 同步所有活躍放貸訂單的狀態，並更新數據庫。
        """
        log.info(f"Syncing lending order statuses for {currency}...")
        try:
            # 從 Bitfinex 獲取所有活躍的資金報價
            bitfinex_offers = self.api_client.get_funding_offers(symbol=f'f{currency}')
            bitfinex_offer_ids = {offer[0] for offer in bitfinex_offers} # 提取 Bitfinex 訂單 ID

            # 從數據庫獲取所有活躍的放貸訂單
            db_active_orders = self.lending_order_repo.get_active_orders()
            
            for db_order in db_active_orders:
                if db_order.order_id in bitfinex_offer_ids:
                    # 訂單仍在 Bitfinex 上活躍，更新其狀態
                    # Bitfinex API 返回的 offer 數據格式: [ID, SYMBOL, MTS_CREATED, MTS_UPDATED, AMOUNT, FLAGS, STATUS, RATE, PERIOD, ...]
                    # 找到對應的 Bitfinex offer
                    bitfinex_offer = next((offer for offer in bitfinex_offers if offer[0] == db_order.order_id), None)
                    if bitfinex_offer:
                        # 更新訂單狀態和執行金額等
                        new_status_str = bitfinex_offer[6] # STATUS 字段
                        new_status = self._map_bitfinex_status(new_status_str)
                        
                        # 檢查是否從 PENDING 變為 ACTIVE 或 PARTIALLY_FILLED
                        if db_order.status == OrderStatus.PENDING and new_status in [OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]:
                            db_order.executed_at = datetime.fromtimestamp(bitfinex_offer[2] / 1000) # MTS_CREATED
                            db_order.executed_amount = Decimal(str(bitfinex_offer[4])) # AMOUNT
                            db_order.executed_rate = Decimal(str(bitfinex_offer[7])) # RATE
                            log.info(f"Order {db_order.order_id} changed from PENDING to {new_status.value}. Executed amount: {db_order.executed_amount}")

                        db_order.status = new_status
                        self.lending_order_repo.update(db_order)
                        log.debug(f"Updated order {db_order.order_id} to status: {db_order.status.value}")
                else:
                    # 訂單不在 Bitfinex 活躍列表中，可能已成交、取消或過期
                    # 嘗試從 Bitfinex 獲取該訂單的詳細信息以確認最終狀態
                    # Bitfinex API 沒有直接獲取單個歷史資金報價的接口，通常需要通過 ledgers 或 summary
                    # 這裡我們假設如果不在活躍列表中，且不是 PENDING，則已完成
                    if db_order.status not in [OrderStatus.EXECUTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED]:
                        db_order.status = OrderStatus.EXECUTED # 假設已成交，後續通過利息支付確認
                        db_order.completed_at = datetime.now()
                        self.lending_order_repo.update(db_order)
                        log.info(f"Order {db_order.order_id} not found on Bitfinex, marked as EXECUTED (assumed).")
            
            log.info(f"Finished syncing lending order statuses for {currency}.")

        except BitfinexAPIError as e:
            log.error(f"Failed to sync order statuses from Bitfinex: {e}")
        except DatabaseError as e:
            log.error(f"Failed to update order statuses in database: {e}")
        except Exception as e:
            log.error(f"An unexpected error occurred during order status sync: {e}")

    def _map_bitfinex_status(self, status_str: str) -> OrderStatus:
        """將 Bitfinex 的狀態字符串映射到內部 OrderStatus 枚舉。"""
        status_map = {
            'ACTIVE': OrderStatus.ACTIVE,
            'EXECUTED': OrderStatus.EXECUTED,
            'PARTIALLY FILLED': OrderStatus.PARTIALLY_FILLED,
            'CANCELED': OrderStatus.CANCELLED,
            'EXPIRED': OrderStatus.EXPIRED,
            'PENDING': OrderStatus.PENDING # Bitfinex 也可能返回 PENDING
        }
        return status_map.get(status_str.upper(), OrderStatus.PENDING) # 默認為 PENDING

    def process_interest_payments(self, currency: str, start_timestamp_ms: Optional[int] = None):
        """
        從 Bitfinex 獲取利息支付記錄並存儲，同時更新相關聯的 LendingOrder 狀態。
        :param currency: 貨幣符號 (例如 'USD')
        :param start_timestamp_ms: 從該時間戳開始獲取利息記錄 (毫秒)
        """
        log.info(f"Processing interest payments for {currency}...")
        try:
            # 獲取最新的利息支付記錄的時間戳，以便增量更新
            last_payment = self.interest_payment_repo.get_latest_payment(currency)
            if last_payment and not start_timestamp_ms:
                start_timestamp_ms = int(last_payment.paid_at.timestamp() * 1000) - (24 * 60 * 60 * 1000) # 往前推一天，確保不漏
                log.info(f"Fetching interest payments from {datetime.fromtimestamp(start_timestamp_ms / 1000)} onwards.")
            
            ledgers = self.api_client.get_ledgers(currency, start=start_timestamp_ms, category=28) # category=28 for interest payments
            
            if not ledgers:
                log.info(f"No new interest payments found for {currency}.")
                return

            new_payments_count = 0
            for entry in ledgers:
                # Bitfinex ledger entry 格式: [ID, WALLET, CURRENCY, AMOUNT, BALANCE, MTS, DESCRIPTION, ... CATEGORY]
                ledger_id = entry[0]
                # 檢查是否已存在，避免重複處理
                if self.interest_payment_repo.get_by_ledger_id(ledger_id):
                    continue

                try:
                    # 假設 InterestPayment.from_ledger_entry 能夠正確解析
                    payment = InterestPayment.from_ledger_entry({
                        'id': entry[0],
                        'currency': entry[2],
                        'amount': Decimal(str(entry[3])),
                        'mts': entry[5],
                        'description': entry[6]
                    })
                    self.interest_payment_repo.save(payment)
                    new_payments_count += 1

                    # 如果有利息支付，且關聯到某個 order_id，則更新對應的 LendingOrder 狀態
                    if payment.order_id:
                        lending_order = self.lending_order_repo.get_by_order_id(payment.order_id)
                        if lending_order and lending_order.status != OrderStatus.EXECUTED:
                            lending_order.status = OrderStatus.EXECUTED
                            lending_order.completed_at = datetime.now() # 標記為完成
                            self.lending_order_repo.update(lending_order)
                            log.info(f"Lending order {lending_order.order_id} marked as EXECUTED due to interest payment.")

                except ValueError as ve:
                    log.warning(f"Skipping ledger entry due to data parsing error: {ve} - Entry: {entry}")
                except DatabaseError as de:
                    log.error(f"Failed to save interest payment {ledger_id} to database: {de}")
            
            log.info(f"Processed {new_payments_count} new interest payments for {currency}.")

        except BitfinexAPIError as e:
            log.error(f"Failed to fetch ledgers from Bitfinex: {e}")
        except Exception as e:
            log.error(f"An unexpected error occurred during interest payment processing: {e}")

    def handle_expired_or_cancelled_orders(self):
        """
        處理數據庫中可能已過期或被取消但未更新狀態的訂單。
        這通常需要與 Bitfinex API 進行更複雜的交互來確認，
        或者依賴於 sync_order_statuses 的結果。
        """
        log.info("Checking for potentially expired or cancelled orders in DB...")
        # 獲取所有非 EXECUTED 狀態的訂單
        pending_active_orders = self.lending_order_repo.get_all_non_completed_orders()
        
        for order in pending_active_orders:
            # 如果訂單創建時間超過一定閾值（例如，超過其 period + 緩衝期），
            # 且 sync_order_statuses 未能將其標記為活躍或已完成，
            # 則可能需要進一步調查或手動標記為 EXPIRED/CANCELLED。
            # 這裡可以添加更複雜的邏輯，例如再次調用 API 查詢訂單狀態，
            # 但 Bitfinex API 沒有直接查詢歷史資金報價的接口。
            # 目前，我們主要依賴 sync_order_statuses 和 process_interest_payments 來更新狀態。
            # 這裡可以作為一個清理機制，例如，如果訂單長時間處於 PENDING 狀態，可以考慮取消。
            pass
        log.info("Finished checking for expired or cancelled orders.")

    def auto_renew_funding(self, currency: str):
        """
        自動續借到期的資金。
        這需要獲取已完成的訂單，並根據配置重新發布新的放貸訂單。
        此功能將在 FundingService 中實現，OrderManager 負責觸發。
        """
        log.info(f"Checking for auto-renewal opportunities for {currency}...")
        # 這裡的邏輯會比較複雜，需要：
        # 1. 識別哪些資金已經到期並回到資金錢包
        # 2. 根據預設策略或用戶配置，重新計算新的放貸參數
        # 3. 調用 FundingService.place_funding_offer 重新下單
        # 這部分邏輯更適合放在 FundingService 或一個更高層次的策略執行器中。
        # OrderManager 主要是狀態管理和數據同步。
        pass
