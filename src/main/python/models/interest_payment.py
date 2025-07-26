from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
import re

@dataclass
class InterestPayment:
    """代表從 Bitfinex API 獲取的單筆利息收入記錄，作為一個純粹的數據容器。"""
    
    # 核心數據欄位
    ledger_id: int
    currency: str
    amount: Decimal
    paid_at: datetime
    description: str
    
    # 關聯ID (可選)
    order_id: Optional[int] = None
    
    # 資料庫主鍵
    id: Optional[int] = None
    
    @classmethod
    def from_ledger_entry(cls, entry: dict) -> 'InterestPayment':
        """
        從 Bitfinex Ledger 條目字典創建 InterestPayment 實例。
        
        Args:
            entry: 從 bfxapi 的 get_ledgers 返回的單個條目，已轉換為字典。
            
        Returns:
            一個 InterestPayment 實例。
            
        Raises:
            ValueError: 如果 'id' 或 'mts' 欄位缺失。
        """
        
        # 驗證必要欄位
        ledger_id = entry.get('id')
        if not ledger_id:
            raise ValueError("Ledger entry must have an 'id'")
            
        paid_at_ms = entry.get('mts')
        if not paid_at_ms:
            raise ValueError("Ledger entry must have 'mts' (timestamp)")

        # 創建實例
        instance = cls(
            ledger_id=ledger_id,
            currency=entry.get('currency', 'UNKNOWN'),
            amount=Decimal(str(entry.get('amount', '0.0'))),
            paid_at=datetime.fromtimestamp(paid_at_ms / 1000.0),
            description=entry.get('description', '')
        )
        
        # 從描述中提取 Order ID
        match = re.search(r'#(\d+)', instance.description)
        if match:
            instance.order_id = int(match.group(1))
            
        return instance 