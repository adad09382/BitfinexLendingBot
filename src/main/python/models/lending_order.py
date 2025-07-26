from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from decimal import Decimal
from enum import Enum

class OrderStatus(Enum):
    """訂單狀態枚舉"""
    PENDING = "PENDING"           # 等待執行
    ACTIVE = "ACTIVE"             # 活躍中
    EXECUTED = "EXECUTED"         # 已執行
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交
    CANCELLED = "CANCELLED"       # 已取消
    EXPIRED = "EXPIRED"           # 已過期

@dataclass
class LendingOrder:
    """
    代表單個放貸訂單的記錄
    
    包含訂單的完整生命週期信息：創建、執行、完成或取消
    """
    # 必需字段
    order_id: int                           # Bitfinex 訂單 ID
    symbol: str                             # 交易對符號 (如 "fUSD")
    amount: Decimal                         # 訂單金額
    rate: Decimal                           # 日利率
    period: int                             # 借貸期限（天）
    
    # 狀態和時間
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None   # 執行時間
    cancelled_at: Optional[datetime] = None  # 取消時間
    completed_at: Optional[datetime] = None  # 完成時間
    
    # 執行信息
    executed_amount: Optional[Decimal] = None # 實際執行金額
    executed_rate: Optional[Decimal] = None   # 實際執行利率
    
    # 策略信息
    strategy_name: Optional[str] = None      # 生成此訂單的策略
    strategy_params: Optional[dict] = None   # 策略參數快照
    
    # 數據庫字段
    id: Optional[int] = None                # 數據庫主鍵
    
    def is_active(self) -> bool:
        """檢查訂單是否處於活躍狀態"""
        return self.status in [OrderStatus.PENDING, OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]
    
    def is_completed(self) -> bool:
        """檢查訂單是否已完成（成功或失敗）"""
        return self.status in [OrderStatus.EXECUTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED]
    
    def get_duration_days(self) -> Optional[int]:
        """計算訂單持續天數"""
        if not self.executed_at or not self.completed_at:
            return None
        return (self.completed_at - self.executed_at).days
    
    def calculate_expected_interest(self) -> Decimal:
        """計算預期利息收入"""
        if not self.executed_amount:
            amount = self.amount
        else:
            amount = self.executed_amount
            
        rate = self.executed_rate or self.rate
        return amount * rate * self.period
    
    # === 新增：與 InterestPayment 關聯的方法 ===
    
    def get_related_interest_payments(self) -> List['InterestPayment']:
        """獲取與此訂單關聯的所有利息支付記錄"""
        # 這個方法將由 Repository 層實現，這裡先定義接口
        # 實際實現需要數據庫查詢
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from .interest_payment import InterestPayment
        # 暫時返回空列表，等 Repository 層實現
        return []
    
    def calculate_actual_total_interest(self) -> Decimal:
        """計算實際收到的總利息"""
        payments = self.get_related_interest_payments()
        return sum(payment.calculate_net_amount() for payment in payments)
    
    def calculate_interest_variance(self) -> Decimal:
        """計算預期與實際利息的差異"""
        expected = self.calculate_expected_interest()
        actual = self.calculate_actual_total_interest()
        return actual - expected
    
    def calculate_interest_variance_percentage(self) -> Optional[Decimal]:
        """計算利息差異百分比"""
        expected = self.calculate_expected_interest()
        if expected == 0:
            return None
        variance = self.calculate_interest_variance()
        return (variance / expected) * 100
    
    def get_actual_period_days(self) -> Optional[int]:
        """計算實際持有天數（基於 InterestPayment 的時間範圍）"""
        payments = self.get_related_interest_payments()
        if not payments:
            return self.get_duration_days()
        
        payment_dates = [payment.paid_at.date() for payment in payments]
        if len(payment_dates) < 2:
            return 1
        
        return (max(payment_dates) - min(payment_dates)).days + 1
    
    def is_early_repaid(self) -> bool:
        """判斷是否提前還款"""
        actual_days = self.get_actual_period_days()
        if actual_days is None:
            return False
        return actual_days < self.period
    
    def calculate_actual_daily_rate(self) -> Optional[Decimal]:
        """計算實際日利率"""
        actual_interest = self.calculate_actual_total_interest()
        actual_days = self.get_actual_period_days()
        actual_amount = self.executed_amount or self.amount
        
        if not actual_days or actual_days == 0 or actual_amount == 0:
            return None
        
        return actual_interest / (actual_amount * actual_days)
    
    def get_repayment_pattern(self) -> str:
        """獲取還款模式"""
        payments = self.get_related_interest_payments()
        if not payments:
            return "unknown"
        
        if self.is_early_repaid():
            return "early"
        elif len(payments) == 1:
            return "lump_sum"
        else:
            return "installment"
    
    def calculate_yield_efficiency(self) -> Optional[Decimal]:
        """計算收益效率（實際收益率/預期收益率）"""
        expected_rate = self.rate
        actual_rate = self.calculate_actual_daily_rate()
        
        if not actual_rate or expected_rate == 0:
            return None
        
        return actual_rate / expected_rate
    
    def get_interest_payment_timeline(self) -> Dict[str, Decimal]:
        """獲取利息支付時間線"""
        payments = self.get_related_interest_payments()
        timeline = {}
        
        for payment in payments:
            date_key = payment.paid_at.strftime('%Y-%m-%d')
            if date_key in timeline:
                timeline[date_key] += payment.calculate_net_amount()
            else:
                timeline[date_key] = payment.calculate_net_amount()
        
        return timeline
    
    def update_from_api_response(self, api_response: dict) -> None:
        """從 API 響應更新訂單信息"""
        # 更新執行信息
        if 'amount_executed' in api_response:
            self.executed_amount = Decimal(str(api_response['amount_executed']))
        
        if 'rate' in api_response and self.executed_rate is None:
            self.executed_rate = Decimal(str(api_response['rate']))
        
        # 更新狀態
        if 'status' in api_response:
            status_map = {
                'ACTIVE': OrderStatus.ACTIVE,
                'EXECUTED': OrderStatus.EXECUTED,
                'PARTIALLY FILLED': OrderStatus.PARTIALLY_FILLED,
                'CANCELED': OrderStatus.CANCELLED,
                'EXPIRED': OrderStatus.EXPIRED
            }
            if api_response['status'] in status_map:
                self.status = status_map[api_response['status']]
        
        # 更新時間戳
        if 'mts_created' in api_response and not self.executed_at:
            self.executed_at = datetime.fromtimestamp(api_response['mts_created'] / 1000)
    
    def mark_as_settled(self) -> None:
        """標記訂單為已結算"""
        if self.status == OrderStatus.EXECUTED:
            self.completed_at = datetime.now()
    
    def validate_completion(self) -> bool:
        """驗證訂單完成狀態的一致性"""
        if not self.is_completed():
            return True
        
        # 檢查時間戳一致性
        if self.status == OrderStatus.EXECUTED and not self.executed_at:
            return False
        
        if self.status == OrderStatus.CANCELLED and not self.cancelled_at:
            return False
        
        # 檢查執行金額
        if self.status == OrderStatus.EXECUTED and not self.executed_amount:
            return False
        
        return True 