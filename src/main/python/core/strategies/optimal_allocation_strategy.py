"""
最優資金分配策略
專注於最大化資金利用率和收益率
"""

import logging
import statistics
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from src.main.python.core.strategies.base_strategy import BaseStrategy
from src.main.python.core.config import AppConfig

log = logging.getLogger(__name__)

class OptimalAllocationStrategy(BaseStrategy):
    """
    最優資金分配策略
    
    核心目標：
    1. 最大化資金利用率 (目標 >95%)
    2. 最大化年化收益率
    3. 最小化訂單管理成本
    4. 動態適應市場變化
    
    策略特點：
    - 智能訂單大小計算
    - 動態利率調整
    - 市場機會排序
    - 風險收益平衡
    """
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.strategy_name = "optimal_allocation"
        
        # 策略參數
        self.target_utilization = 0.96  # 目標資金利用率 96%
        self.max_single_order_ratio = 0.15  # 單筆訂單最大占比 15%
        self.min_order_amount = 100  # 最小訂單金額
        self.risk_tolerance = 0.02  # 風險容忍度
        
        # 動態參數 (會根據市場情況調整)
        self.current_market_conditions = {}
        self.performance_history = []
        
    def generate_offers(self, available_balance: Decimal, market_data: Dict) -> List[Dict]:
        """
        生成最優資金分配方案
        
        Args:
            available_balance: 可用資金
            market_data: 市場數據
            
        Returns:
            List[Dict]: 最優訂單列表
        """
        
        if available_balance < self.min_order_amount:
            log.warning(f"可用資金 ${available_balance} 不足最小訂單金額")
            return []
        
        try:
            # 1. 分析市場機會
            opportunities = self._analyze_market_opportunities(market_data)
            
            # 2. 計算最優資金分配
            allocation_plan = self._calculate_optimal_allocation(available_balance, opportunities)
            
            # 3. 生成優化訂單
            offers = self._generate_optimized_orders(allocation_plan)
            
            # 4. 驗證和調整
            offers = self._validate_and_adjust_offers(offers, available_balance)
            
            log.info(f"最優分配策略生成 {len(offers)} 個訂單，"
                    f"總金額 ${sum(Decimal(str(o['amount'])) for o in offers):.2f}，"
                    f"資金利用率 {sum(Decimal(str(o['amount'])) for o in offers) / available_balance * 100:.1f}%")
            
            return offers
            
        except Exception as e:
            log.error(f"生成最優分配方案失敗: {e}")
            # 回退到簡單策略
            return self._generate_fallback_orders(available_balance, market_data)
    
    def _analyze_market_opportunities(self, market_data: Dict) -> List[Dict]:
        """
        分析市場機會並排序
        
        Returns:
            List[Dict]: 按優先級排序的市場機會
        """
        
        rates_data = market_data.get('rates_data', {})
        bids = rates_data.get('bids', [])
        
        opportunities = []
        
        for i, bid in enumerate(bids[:20]):  # 只考慮前20個價位
            rate = Decimal(str(bid.get('rate', 0)))
            volume = Decimal(str(bid.get('amount', 0)))
            
            if rate > 0 and volume > 0:
                # 計算機會評分
                score = self._calculate_opportunity_score(rate, volume, i)
                
                # 估算成交概率
                fill_probability = self._estimate_fill_probability(rate, volume, market_data)
                
                opportunities.append({
                    'rate': rate,
                    'volume': volume,
                    'position': i,
                    'score': score,
                    'fill_probability': fill_probability,
                    'expected_return': rate * fill_probability,  # 期望收益
                    'risk_score': 1 - fill_probability  # 風險評分
                })
        
        # 按期望收益排序
        opportunities.sort(key=lambda x: x['expected_return'], reverse=True)
        
        log.debug(f"識別到 {len(opportunities)} 個市場機會，"
                 f"最佳機會利率 {opportunities[0]['rate']:.4f}%")
        
        return opportunities
    
    def _calculate_opportunity_score(self, rate: Decimal, volume: Decimal, position: int) -> float:
        """計算市場機會評分"""
        
        # 評分因素：
        # 1. 利率高低 (40%)
        # 2. 市場深度 (30%) 
        # 3. 位置優勢 (20%)
        # 4. 風險調整 (10%)
        
        base_rate = Decimal('0.08')  # 基準利率 8%
        rate_score = float(min(rate / base_rate, 1.5))  # 利率評分，最高1.5
        
        volume_score = float(min(volume / 10000, 1.0))  # 流動性評分，最高1.0
        
        position_score = max(0, 1 - position / 20)  # 位置評分，前面的位置更優
        
        risk_score = 0.8  # 固定風險評分
        
        total_score = (
            rate_score * 0.4 +
            volume_score * 0.3 +  
            position_score * 0.2 +
            risk_score * 0.1
        )
        
        return total_score
    
    def _estimate_fill_probability(self, rate: Decimal, volume: Decimal, market_data: Dict) -> float:
        """估算訂單成交概率"""
        
        # 基於歷史數據和市場條件估算
        avg_rate = Decimal(str(market_data.get('avg_rate', 0.08)))
        
        # 利率越接近市場平均，成交概率越高
        rate_diff = abs(rate - avg_rate) / avg_rate
        rate_factor = max(0.1, 1 - rate_diff * 2)
        
        # 流動性越高，成交概率越高
        volume_factor = min(1.0, float(volume / 5000))
        
        # 市場活躍度影響
        market_activity = 0.8  # 假設市場活躍度
        
        probability = rate_factor * 0.5 + volume_factor * 0.3 + market_activity * 0.2
        
        return max(0.1, min(0.95, probability))  # 限制在 10%-95% 範圍內
    
    def _calculate_optimal_allocation(self, total_balance: Decimal, opportunities: List[Dict]) -> List[Dict]:
        """
        計算最優資金分配
        使用動態規劃和風險約束優化
        """
        
        target_amount = total_balance * Decimal(str(self.target_utilization))
        remaining_balance = target_amount
        allocations = []
        
        # 按期望收益排序的機會列表
        sorted_opportunities = opportunities[:10]  # 只考慮前10個最佳機會
        
        for i, opp in enumerate(sorted_opportunities):
            if remaining_balance < self.min_order_amount:
                break
            
            # 計算該機會的最優投資額
            optimal_amount = self._calculate_optimal_order_size(
                remaining_balance, opp, i, len(sorted_opportunities)
            )
            
            if optimal_amount >= self.min_order_amount:
                allocations.append({
                    'rate': opp['rate'],
                    'amount': optimal_amount,
                    'expected_return': optimal_amount * opp['expected_return'] / 365,
                    'risk_score': opp['risk_score'],
                    'fill_probability': opp['fill_probability']
                })
                
                remaining_balance -= optimal_amount
        
        log.debug(f"資金分配完成，已分配 ${target_amount - remaining_balance:.2f}，"
                 f"剩餘 ${remaining_balance:.2f}")
        
        return allocations
    
    def _calculate_optimal_order_size(self, remaining_balance: Decimal, opportunity: Dict, 
                                    index: int, total_opportunities: int) -> Decimal:
        """計算單個訂單的最優大小"""
        
        # 基礎分配 (平均分配)
        base_allocation = remaining_balance / Decimal(str(total_opportunities - index))
        
        # 根據機會質量調整
        quality_multiplier = Decimal(str(opportunity['expected_return'] / 0.08))  # 基於8%基準
        quality_multiplier = max(Decimal('0.5'), min(Decimal('2.0'), quality_multiplier))
        
        # 根據風險調整
        risk_multiplier = Decimal(str(1 - opportunity['risk_score'] * 0.5))
        
        # 計算調整後的金額
        adjusted_amount = base_allocation * quality_multiplier * risk_multiplier
        
        # 應用約束
        max_single_amount = remaining_balance * Decimal(str(self.max_single_order_ratio))
        final_amount = min(adjusted_amount, max_single_amount)
        
        # 確保不小於最小訂單金額
        return max(Decimal(str(self.min_order_amount)), final_amount)
    
    def _generate_optimized_orders(self, allocation_plan: List[Dict]) -> List[Dict]:
        """根據分配計劃生成優化訂單"""
        
        orders = []
        
        for allocation in allocation_plan:
            # 獲取最優放貸期間
            optimal_period = self._get_optimal_period(allocation['rate'])
            
            order = {
                'rate': float(allocation['rate']),
                'amount': float(allocation['amount']),
                'period': optimal_period,
                'expected_return': float(allocation['expected_return']),
                'confidence': allocation['fill_probability']
            }
            
            orders.append(order)
        
        return orders
    
    def _get_optimal_period(self, rate: Decimal) -> int:
        """根據利率確定最優放貸期間"""
        
        # 高利率使用較短期間，低利率使用較長期間
        if rate >= Decimal('0.10'):  # 10%以上
            return 2
        elif rate >= Decimal('0.08'):  # 8%-10%
            return 7
        else:  # 8%以下
            return 30
    
    def _validate_and_adjust_offers(self, offers: List[Dict], available_balance: Decimal) -> List[Dict]:
        """驗證和調整訂單"""
        
        if not offers:
            return offers
        
        # 計算總金額
        total_amount = sum(Decimal(str(offer['amount'])) for offer in offers)
        
        # 如果超出可用餘額，按比例調整
        if total_amount > available_balance:
            adjustment_ratio = float(available_balance / total_amount)
            
            for offer in offers:
                offer['amount'] = float(Decimal(str(offer['amount'])) * Decimal(str(adjustment_ratio)))
            
            log.warning(f"訂單總額超出餘額，已按比例調整 (比例: {adjustment_ratio:.3f})")
        
        # 移除過小的訂單
        offers = [offer for offer in offers if offer['amount'] >= self.min_order_amount]
        
        # 按利率排序
        offers.sort(key=lambda x: x['rate'], reverse=True)
        
        return offers
    
    def _generate_fallback_orders(self, available_balance: Decimal, market_data: Dict) -> List[Dict]:
        """生成後備訂單 (簡化策略)"""
        
        log.info("使用後備策略生成訂單")
        
        # 簡單的等分策略
        order_count = min(5, int(available_balance / self.min_order_amount))
        if order_count == 0:
            return []
        
        amount_per_order = float(available_balance) / order_count
        base_rate = market_data.get('avg_rate', 0.08)
        
        orders = []
        for i in range(order_count):
            rate = base_rate + (i * 0.001)  # 遞增利率
            orders.append({
                'rate': rate,
                'amount': amount_per_order,
                'period': 7,
                'expected_return': amount_per_order * rate / 365,
                'confidence': 0.7
            })
        
        return orders
    
    def get_strategy_name(self) -> str:
        """獲取策略名稱"""
        return self.strategy_name
    
    def update_performance_history(self, performance_data: Dict):
        """更新策略表現歷史"""
        
        self.performance_history.append({
            'timestamp': datetime.now(),
            'data': performance_data
        })
        
        # 保留最近30天的數據
        cutoff_date = datetime.now() - timedelta(days=30)
        self.performance_history = [
            record for record in self.performance_history 
            if record['timestamp'] > cutoff_date
        ]
    
    def get_strategy_metrics(self) -> Dict:
        """獲取策略指標"""
        
        if not self.performance_history:
            return {
                'avg_roi': 0,
                'success_rate': 0,
                'total_trades': 0,
                'avg_utilization': 0
            }
        
        recent_data = self.performance_history[-7:]  # 最近7天
        
        roi_values = [d['data'].get('roi', 0) for d in recent_data]
        fill_rate_values = [d['data'].get('fill_rate', 0) for d in recent_data]
        utilization_values = [d['data'].get('utilization', 0) for d in recent_data]
        
        return {
            'avg_roi': statistics.mean(roi_values) if roi_values else 0,
            'success_rate': statistics.mean(fill_rate_values) if fill_rate_values else 0,
            'total_trades': sum(d['data'].get('order_count', 0) for d in recent_data),
            'avg_utilization': statistics.mean(utilization_values) if utilization_values else 0
        }