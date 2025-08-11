from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PositionStatus(str, Enum):
    """頭寸狀態"""
    ACTIVE = "ACTIVE"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class PositionType(str, Enum):
    """頭寸類型"""
    LENDING = "LENDING"
    BORROWING = "BORROWING"


class ActivePosition(BaseModel):
    """當前活躍頭寸 - 運行時狀態追蹤"""
    
    id: Optional[int] = None
    position_id: str = Field(..., description="頭寸唯一標識")
    currency: str = Field(..., max_length=6, description="貨幣類型")
    position_type: PositionType = Field(default=PositionType.LENDING)
    
    # 基本信息
    amount: Decimal = Field(..., description="頭寸金額")
    rate: Decimal = Field(..., description="利率")
    period: int = Field(..., description="期限（天）")
    
    # 時間信息
    opened_at: datetime = Field(..., description="開倉時間")
    expected_close_at: Optional[datetime] = Field(None, description="預期平倉時間")
    actual_close_at: Optional[datetime] = Field(None, description="實際平倉時間")
    
    # 收益信息
    expected_return: Decimal = Field(..., description="預期收益")
    actual_return: Optional[Decimal] = Field(None, description="實際收益")
    
    # 策略信息
    strategy_name: str = Field(..., max_length=20, description="使用的策略")
    order_reference: Optional[str] = Field(None, description="關聯的訂單引用")
    
    # 狀態
    status: PositionStatus = Field(default=PositionStatus.ACTIVE)
    
    # 元數據
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class PositionSummary(BaseModel):
    """頭寸摘要"""
    currency: str
    total_positions: int
    total_amount: Decimal
    weighted_avg_rate: Decimal
    total_expected_return: Decimal
    avg_period: Decimal
    
    # 按狀態分組
    active_count: int
    closing_count: int
    
    # 按策略分組
    strategy_distribution: Dict[str, int]


class PositionCreate(BaseModel):
    """創建頭寸的輸入模型"""
    position_id: str
    currency: str
    amount: Decimal
    rate: Decimal
    period: int
    opened_at: datetime
    expected_return: Decimal
    strategy_name: str
    order_reference: Optional[str] = None


class PositionUpdate(BaseModel):
    """更新頭寸的輸入模型"""
    status: Optional[PositionStatus] = None
    actual_close_at: Optional[datetime] = None
    actual_return: Optional[Decimal] = None
    updated_at: datetime = Field(default_factory=datetime.now)