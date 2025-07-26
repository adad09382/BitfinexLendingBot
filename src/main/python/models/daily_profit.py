from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

@dataclass
class DailyProfit:
    """
    每日收益數據
    """
    id: Optional[int] = None
    currency: str
    interest_income: Decimal
    total_loan: Decimal
    type: str
    date: date
