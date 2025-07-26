from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, List
from decimal import Decimal

@dataclass
class CurrencyAllocation:
    """
    幣種配置信息
    """
    currency: str                               # 幣種
    total_amount: Decimal                       # 總金額
    deployed_amount: Decimal                    # 已部署金額
    available_amount: Decimal                   # 可用金額
    allocation_percentage: Decimal              # 配置百分比
    avg_rate: Decimal                          # 平均利率
    total_orders: int                          # 總訂單數

@dataclass  
class PeriodAllocation:
    """
    期限配置信息
    """
    period_days: int                           # 期限天數
    total_amount: Decimal                      # 投入金額
    allocation_percentage: Decimal             # 配置百分比
    avg_rate: Decimal                         # 平均利率
    order_count: int                          # 訂單數量
    expected_return: Decimal                  # 預期收益

@dataclass
class StrategyAllocation:
    """
    策略配置信息
    """
    strategy_name: str                         # 策略名稱
    total_amount: Decimal                      # 投入金額
    allocation_percentage: Decimal             # 配置百分比
    order_count: int                          # 訂單數量
    success_rate: Decimal                     # 成功率
    avg_return: Decimal                       # 平均收益率
    last_used: datetime                       # 最後使用時間

@dataclass
class RiskMetrics:
    """
    風險指標
    """
    # 集中度風險
    currency_concentration: Decimal = Decimal('0')    # 幣種集中度
    period_concentration: Decimal = Decimal('0')      # 期限集中度
    counterparty_concentration: Decimal = Decimal('0') # 交易對手集中度
    
    # 流動性風險
    avg_maturity_days: Decimal = Decimal('0')         # 平均到期天數
    liquidity_ratio: Decimal = Decimal('0')           # 流動性比率
    
    # 利率風險
    rate_sensitivity: Decimal = Decimal('0')          # 利率敏感性
    duration_risk: Decimal = Decimal('0')             # 久期風險
    
    # 整體風險
    portfolio_var: Optional[Decimal] = None           # 投資組合 VaR
    risk_score: Decimal = Decimal('0')                # 風險評分 (0-100)

@dataclass
class PortfolioStats:
    """
    投資組合統計快照
    
    提供某個時間點的完整投資組合分析
    """
    # 基本信息
    snapshot_date: date                               # 快照日期
    base_currency: str = "USD"                        # 基準幣種
    
    # 總體統計
    total_portfolio_value: Decimal = Decimal('0')     # 總投資組合價值
    total_deployed: Decimal = Decimal('0')            # 總部署金額
    total_available: Decimal = Decimal('0')           # 總可用金額
    total_pending: Decimal = Decimal('0')             # 總待執行金額
    
    # 利用率統計
    overall_utilization: Decimal = Decimal('0')       # 整體利用率
    target_utilization: Decimal = Decimal('95')       # 目標利用率
    utilization_efficiency: Decimal = Decimal('0')    # 利用效率
    
    # 收益統計
    current_daily_rate: Decimal = Decimal('0')        # 當前日收益率
    projected_annual_return: Decimal = Decimal('0')   # 預計年收益率
    ytd_return: Decimal = Decimal('0')                # 年初至今收益
    
    # 分配統計
    currency_allocations: List[CurrencyAllocation] = field(default_factory=list)
    period_allocations: List[PeriodAllocation] = field(default_factory=list)
    strategy_allocations: List[StrategyAllocation] = field(default_factory=list)
    
    # 風險分析
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    
    # 歷史比較
    prev_month_utilization: Optional[Decimal] = None  # 上月利用率
    prev_month_return: Optional[Decimal] = None       # 上月收益率
    utilization_trend: Optional[str] = None           # 利用率趨勢 (up/down/stable)
    
    # 元數據
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)  # 數據來源
    calculation_version: str = "1.0"                   # 計算版本
    
    # 數據庫字段
    id: Optional[int] = None                          # 數據庫主鍵
    
    def get_diversification_score(self) -> Decimal:
        """計算分散化評分 (0-100)"""
        if not self.currency_allocations:
            return Decimal('0')
        
        # 基於貨幣分散程度計算
        currency_count = len(self.currency_allocations)
        max_allocation = max(alloc.allocation_percentage for alloc in self.currency_allocations)
        
        # 分散化評分：貨幣種類越多、最大配置越小，分散化越好
        diversity_factor = min(currency_count * 10, 50)  # 最多50分
        concentration_penalty = max_allocation  # 最大配置作為懲罰
        
        score = diversity_factor + (50 - concentration_penalty)
        return min(max(score, Decimal('0')), Decimal('100'))
    
    def get_efficiency_score(self) -> Decimal:
        """計算效率評分 (0-100)"""
        if self.target_utilization == 0:
            return Decimal('0')
        
        # 基於利用率與目標的接近程度
        utilization_ratio = self.overall_utilization / self.target_utilization
        
        if utilization_ratio > 1:
            # 超過目標，適度懲罰
            score = 100 - (utilization_ratio - 1) * 20
        else:
            # 未達目標，按比例評分
            score = utilization_ratio * 100
        
        return min(max(score, Decimal('0')), Decimal('100'))
    
    def get_most_profitable_strategy(self) -> Optional[str]:
        """獲取最盈利的策略"""
        if not self.strategy_allocations:
            return None
        
        best_strategy = max(
            self.strategy_allocations, 
            key=lambda s: s.avg_return
        )
        return best_strategy.strategy_name
    
    def get_risk_level(self) -> str:
        """獲取風險級別描述"""
        score = self.risk_metrics.risk_score
        
        if score >= 80:
            return "High Risk"
        elif score >= 60:
            return "Medium-High Risk"
        elif score >= 40:
            return "Medium Risk"
        elif score >= 20:
            return "Low-Medium Risk"
        else:
            return "Low Risk"
    
    def needs_rebalancing(self) -> bool:
        """檢查是否需要重新平衡"""
        # 檢查利用率是否偏離目標太多
        utilization_deviation = abs(self.overall_utilization - self.target_utilization)
        
        # 檢查是否有過度集中的配置
        max_currency_allocation = max(
            (alloc.allocation_percentage for alloc in self.currency_allocations),
            default=Decimal('0')
        )
        
        return (utilization_deviation > 10 or 
                max_currency_allocation > 70 or
                self.risk_metrics.risk_score > 75) 