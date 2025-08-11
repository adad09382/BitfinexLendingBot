from datetime import date, datetime as dt
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class SettlementStatus(str, Enum):
    """結算狀態"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DailyEarnings(BaseModel):
    """每日收益模型 - 用戶最關心的核心數據"""
    
    id: Optional[int] = None
    date: date = Field(..., description="結算日期")
    currency: str = Field(..., max_length=6, description="貨幣類型")
    
    # 用戶關心的核心數據
    total_interest: Decimal = Field(..., description="當日總利息收入")
    deployed_amount: Decimal = Field(..., description="當日平均部署金額")
    available_amount: Decimal = Field(..., description="當日平均可用金額")
    weighted_avg_rate: Decimal = Field(..., description="當日加權平均利率")
    
    # 效果指標
    utilization_rate: Decimal = Field(..., description="資金利用率 (%)")
    daily_return_rate: Decimal = Field(..., description="日收益率")
    annualized_return: Decimal = Field(..., description="年化收益率 (%)")
    
    # 策略信息
    primary_strategy: str = Field(..., max_length=20, description="主要使用策略")
    total_orders_placed: int = Field(..., description="當日下單數")
    orders_success_rate: Decimal = Field(..., description="訂單成功率 (%)")
    
    # 市場環境
    market_avg_rate: Optional[Decimal] = Field(None, description="市場平均利率")
    market_competitiveness: Optional[Decimal] = Field(None, description="競爭力指標")
    
    # 元數據
    settlement_status: SettlementStatus = Field(default=SettlementStatus.PENDING)
    settlement_timestamp: Optional[dt] = Field(None, description="結算完成時間")
    created_at: dt = Field(default_factory=dt.now, description="創建時間")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            Decimal: str,
            date: lambda v: v.isoformat(),
            dt: lambda v: v.isoformat()
        }
    )


class DailyEarningsCreate(BaseModel):
    """創建每日收益的輸入模型"""
    date: date
    currency: str
    total_interest: Decimal
    deployed_amount: Decimal
    available_amount: Decimal
    weighted_avg_rate: Decimal
    utilization_rate: Decimal
    daily_return_rate: Decimal
    annualized_return: Decimal
    primary_strategy: str
    total_orders_placed: int
    orders_success_rate: Decimal
    market_avg_rate: Optional[Decimal] = None
    market_competitiveness: Optional[Decimal] = None


class DailyEarningsSummary(BaseModel):
    """每日收益摘要 - 用於Dashboard顯示"""
    date: date
    currency: str
    total_interest: Decimal
    daily_return_rate: Decimal
    annualized_return: Decimal
    utilization_rate: Decimal
    market_competitiveness: Optional[Decimal] = None
    
    # 趨勢指標
    vs_yesterday: Optional[Decimal] = Field(None, description="與昨日對比")
    vs_last_week: Optional[Decimal] = Field(None, description="與上週對比")
    vs_last_month: Optional[Decimal] = Field(None, description="與上月對比")


class WeeklyEarningsSummary(BaseModel):
    """週收益摘要"""
    week_start: date
    week_end: date
    currency: str
    total_interest: Decimal
    avg_daily_return: Decimal
    avg_utilization_rate: Decimal
    total_orders: int
    best_day: date
    best_day_return: Decimal


class MonthlyEarningsSummary(BaseModel):
    """月收益摘要"""
    month: int
    year: int
    currency: str
    total_interest: Decimal
    avg_daily_return: Decimal
    avg_utilization_rate: Decimal
    total_orders: int
    best_strategy: str
    worst_day: date
    best_day: date