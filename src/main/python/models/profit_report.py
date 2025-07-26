from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, List
from decimal import Decimal
from enum import Enum

class ReportPeriod(Enum):
    """報告周期類型"""
    DAILY = "DAILY"         # 日報
    WEEKLY = "WEEKLY"       # 週報  
    MONTHLY = "MONTHLY"     # 月報
    QUARTERLY = "QUARTERLY" # 季報
    YEARLY = "YEARLY"       # 年報
    CUSTOM = "CUSTOM"       # 自定義期間

@dataclass
class ProfitMetrics:
    """
    收益指標集合
    
    包含各種計算得出的收益和風險指標
    """
    # 基本收益指標
    total_interest: Decimal = Decimal('0')      # 總利息收入
    total_fees: Decimal = Decimal('0')          # 總手續費
    net_profit: Decimal = Decimal('0')          # 淨收益
    
    # 收益率指標
    total_return_rate: Decimal = Decimal('0')   # 總收益率
    annualized_return: Decimal = Decimal('0')   # 年化收益率
    daily_avg_return: Decimal = Decimal('0')    # 日均收益率
    
    # 資金利用指標
    avg_deployed_amount: Decimal = Decimal('0') # 平均部署金額
    max_deployed_amount: Decimal = Decimal('0') # 最大部署金額
    utilization_rate: Decimal = Decimal('0')    # 資金利用率
    
    # 利率指標
    avg_lending_rate: Decimal = Decimal('0')    # 平均放貸利率
    max_lending_rate: Decimal = Decimal('0')    # 最高放貸利率
    min_lending_rate: Decimal = Decimal('0')    # 最低放貸利率
    
    # 風險指標
    return_volatility: Decimal = Decimal('0')   # 收益波動率
    sharpe_ratio: Optional[Decimal] = None      # 夏普比率
    max_drawdown: Decimal = Decimal('0')        # 最大回撤
    
    # 交易統計
    total_orders: int = 0                       # 總訂單數
    successful_orders: int = 0                  # 成功訂單數
    cancelled_orders: int = 0                   # 取消訂單數
    avg_order_size: Decimal = Decimal('0')     # 平均訂單大小

@dataclass
class ProfitReport:
    """
    收益報告主體
    
    包含特定時間範圍內的完整收益分析
    """
    # 報告基本信息
    currency: str                               # 主要幣種
    period_type: ReportPeriod                   # 報告周期類型
    start_date: date                            # 開始日期
    end_date: date                              # 結束日期
    
    # 核心指標
    metrics: ProfitMetrics = field(default_factory=ProfitMetrics)
    
    # 分項數據
    daily_profits: Dict[str, Decimal] = field(default_factory=dict)  # 日收益明細
    rate_distribution: Dict[str, int] = field(default_factory=dict)  # 利率分布
    period_distribution: Dict[int, Decimal] = field(default_factory=dict)  # 期限分布
    
    # 比較數據
    benchmark_return: Optional[Decimal] = None   # 基準收益率
    previous_period_return: Optional[Decimal] = None  # 上期收益率
    market_avg_rate: Optional[Decimal] = None    # 市場平均利率
    
    # 策略分析
    strategy_performance: Dict[str, Decimal] = field(default_factory=dict)  # 各策略表現
    best_performing_strategy: Optional[str] = None
    worst_performing_strategy: Optional[str] = None
    
    # 元數據
    report_generated_at: datetime = field(default_factory=datetime.now)
    data_points_count: int = 0                  # 數據點數量
    data_completeness: Decimal = Decimal('100') # 數據完整度百分比
    
    # 數據庫字段
    id: Optional[int] = None                    # 數據庫主鍵
    
    def get_period_days(self) -> int:
        """計算報告期間的天數"""
        return (self.end_date - self.start_date).days + 1
    
    def calculate_daily_avg_profit(self) -> Decimal:
        """計算日均收益"""
        days = self.get_period_days()
        if days == 0:
            return Decimal('0')
        return self.metrics.net_profit / days
    
    def get_success_rate(self) -> Decimal:
        """計算訂單成功率"""
        if self.metrics.total_orders == 0:
            return Decimal('0')
        return Decimal(self.metrics.successful_orders) / Decimal(self.metrics.total_orders)
    
    def is_outperforming_benchmark(self) -> Optional[bool]:
        """檢查是否跑贏基準"""
        if self.benchmark_return is None:
            return None
        return self.metrics.annualized_return > self.benchmark_return
    
    def get_risk_adjusted_return(self) -> Optional[Decimal]:
        """獲取風險調整後收益"""
        if self.metrics.return_volatility == 0:
            return None
        return self.metrics.annualized_return / self.metrics.return_volatility 