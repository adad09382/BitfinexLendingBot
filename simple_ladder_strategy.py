#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SimpleLendingBot - 簡單階梯策略
直接基於 market_data 的利率區間進行階梯下單
比複雜的 rate_calculator 更直接、可靠
"""

import logging
from typing import List, Dict, Optional
from market_data import MarketDataFetcher

logger = logging.getLogger(__name__)

class SimpleLadderStrategy:
    """基於市場數據的簡單階梯策略"""
    
    def __init__(self, config=None, api_client=None):
        """
        初始化階梯策略
        
        Args:
            config: 配置對象
            api_client: BitfinexAPI 客戶端 (可選，如果提供則內部創建 MarketDataFetcher)
        """
        self.config = config
        self.api_client = api_client
        
        # 策略參數
        self.competitive_buffer = getattr(config, 'competitive_buffer_percent', 2)  # 2% 競爭緩衝
        self.ladder_levels = getattr(config, 'ladder_levels', 10)  # 10檔階梯 (默認)
        self.min_rate_threshold = getattr(config, 'min_rate_threshold', 0.05)  # 5% 年化最低門檻
        self.fallback_increment = getattr(config, 'fallback_increment_percent', 0.05)  # 降級策略每檔遞增5%
        
        # 如果有API客戶端，創建市場數據獲取器
        self.market_data_fetcher = None
        if self.api_client:
            self.market_data_fetcher = MarketDataFetcher(self.api_client)
            logger.info(f"簡單階梯策略初始化: {self.ladder_levels}檔, 緩衝{self.competitive_buffer}% (含市場數據獲取)")
        else:
            logger.info(f"簡單階梯策略初始化: {self.ladder_levels}檔, 緩衝{self.competitive_buffer}% (僅策略邏輯)")
    
    def generate_ladder_rates(self, market_summary: Dict = None, currency: str = 'USD', target_levels: int = None) -> Dict[str, any]:
        """
        基於市場數據直接生成階梯利率
        
        Args:
            market_summary: 市場數據摘要 (可選，如果為空且有api_client會自動獲取)
            currency: 幣種 (當需要自動獲取市場數據時使用)
            target_levels: 目標階梯檔數 (可選，覆蓋預設配置)
            
        Returns:
            Dict: 階梯策略結果
        """
        # 如果沒有提供市場數據但有API客戶端，自動獲取
        if not market_summary and self.market_data_fetcher:
            logger.info(f"自動獲取 {currency} 市場數據...")
            market_summary = self.market_data_fetcher.get_market_summary(currency)
            
        try:
            # 決定實際使用的階梯檔數
            actual_levels = target_levels if target_levels is not None else self.ladder_levels
            logger.info(f"使用階梯檔數: {actual_levels} (目標: {target_levels}, 預設: {self.ladder_levels})")
            
            # 檢查數據品質
            if not market_summary or not market_summary.get('data_quality', {}).get('has_order_book'):
                return self._fallback_strategy(actual_levels)
            
            order_book = market_summary['order_book']
            recent_trades = market_summary['recent_trades']
            
            # 提取關鍵市場數據
            bid_avg = order_book.get('bid_avg', 0)  # 競爭對手平均利率
            bid_best = order_book.get('bid_best', 0)  # 最佳競爭利率
            bid_worst = order_book.get('bid_worst', 0)  # 最低競爭利率
            bid_count = order_book.get('bid_count', 0)  # 競爭檔數
            
            recent_avg = recent_trades.get('avg_daily_rate', 0)  # 最近成交平均
            
            logger.info(f"市場利率區間: {bid_worst*365*100:.3f}% - {bid_best*365*100:.3f}% (年化)")
            logger.info(f"競爭平均: {bid_avg*365*100:.3f}%, 最近成交: {recent_avg*365*100:.3f}%")
            
            # 決定我們的利率策略
            strategy_result = self._calculate_ladder_range(
                bid_avg, bid_best, bid_worst, recent_avg, bid_count
            )
            
            # 生成階梯 (使用動態檔數)
            ladder_rates = self._create_ladder_distribution(
                strategy_result['base_rate'], 
                strategy_result['top_rate'],
                actual_levels
            )
            
            return {
                'strategy_type': 'simple_ladder',
                'market_analysis': {
                    'bid_range': [bid_worst * 365 * 100, bid_best * 365 * 100],  # 年化%
                    'bid_avg': bid_avg * 365 * 100,
                    'recent_avg': recent_avg * 365 * 100,
                    'competition_level': 'high' if bid_count >= 15 else 'medium' if bid_count >= 8 else 'low',
                    'market_balance': order_book.get('market_balance', 'unknown')
                },
                'strategy_rates': {
                    'base_rate': strategy_result['base_rate'],
                    'top_rate': strategy_result['top_rate'],
                    'rate_range': strategy_result['top_rate'] - strategy_result['base_rate']
                },
                'ladder_rates': ladder_rates,
                'recommendation': self._generate_simple_recommendation(strategy_result, bid_count),
                'timestamp': market_summary.get('timestamp', 0)
            }
            
        except Exception as e:
            logger.error(f"生成階梯策略失敗: {e}")
            actual_levels = target_levels if target_levels is not None else self.ladder_levels
            return self._fallback_strategy(actual_levels)
    
    def _calculate_ladder_range(self, bid_avg, bid_best, bid_worst, recent_avg, bid_count):
        """計算階梯利率範圍"""
        
        # 基準利率：綜合考慮競爭對手和最近成交
        if bid_avg > 0 and recent_avg > 0:
            # 60% 競爭對手 + 40% 最近成交
            base_rate = bid_avg * 0.6 + recent_avg * 0.4
        elif bid_avg > 0:
            base_rate = bid_avg
        elif recent_avg > 0:
            base_rate = recent_avg
        else:
            base_rate = self.min_rate_threshold / 365  # 年化轉日利率
        
        # 應用競爭緩衝
        competitive_rate = base_rate * (1 + self.competitive_buffer / 100)
        
        # 決定階梯範圍
        if bid_count >= 15:
            # 競爭激烈：緊貼競爭對手，小幅度分佈
            ladder_base = competitive_rate
            ladder_top = competitive_rate * 1.05  # 只高5%
            strategy = 'conservative'
        elif bid_count >= 8:
            # 中等競爭：平衡策略
            ladder_base = competitive_rate
            ladder_top = competitive_rate * 1.1  # 高10%
            strategy = 'balanced'
        else:
            # 競爭較少：可以更積極
            ladder_base = competitive_rate
            ladder_top = competitive_rate * 1.15  # 高15%
            strategy = 'aggressive'
        
        logger.info(f"階梯策略 ({strategy}): {ladder_base*365*100:.3f}% - {ladder_top*365*100:.3f}% (年化)")
        
        return {
            'base_rate': ladder_base,
            'top_rate': ladder_top,
            'strategy': strategy
        }
    
    def _create_ladder_distribution(self, base_rate, top_rate, levels):
        """創建階梯分佈"""
        ladder_rates = []
        
        if levels <= 1:
            # 只有一檔
            ladder_rates.append({
                'level': 1,
                'daily_rate': base_rate,
                'annual_rate': base_rate * 365,
                'annual_percentage': base_rate * 365 * 100,
                'weight_suggestion': 1.0
            })
        else:
            # 多檔階梯
            rate_increment = (top_rate - base_rate) / (levels - 1)
            
            for i in range(levels):
                rate = base_rate + (rate_increment * i)
                ladder_rates.append({
                    'level': i + 1,
                    'daily_rate': rate,
                    'annual_rate': rate * 365,
                    'annual_percentage': rate * 365 * 100,
                    'weight_suggestion': 1.0 / levels  # 平均分配
                })
        
        return ladder_rates
    
    def _generate_simple_recommendation(self, strategy_result, bid_count):
        """生成簡單建議"""
        base_annual = strategy_result['base_rate'] * 365 * 100
        top_annual = strategy_result['top_rate'] * 365 * 100
        
        if bid_count >= 15:
            return f"競爭激烈 ({bid_count}檔)，建議保守策略 {base_annual:.2f}%-{top_annual:.2f}%"
        elif bid_count >= 8:
            return f"中等競爭 ({bid_count}檔)，建議平衡策略 {base_annual:.2f}%-{top_annual:.2f}%"
        else:
            return f"競爭較少 ({bid_count}檔)，建議積極策略 {base_annual:.2f}%-{top_annual:.2f}%"
    
    def _fallback_strategy(self, levels: int = None):
        """降級策略：無市場數據時使用"""
        actual_levels = levels if levels is not None else self.ladder_levels
        fallback_rate = self.min_rate_threshold / 365  # 年化轉日利率
        
        ladder_rates = []
        for i in range(actual_levels):
            rate = fallback_rate * (1 + 0.05 * i)  # 每檔遞增5%
            ladder_rates.append({
                'level': i + 1,
                'daily_rate': rate,
                'annual_rate': rate * 365,
                'annual_percentage': rate * 365 * 100,
                'weight_suggestion': 1.0 / actual_levels
            })
        
        return {
            'strategy_type': 'fallback',
            'ladder_rates': ladder_rates,
            'recommendation': f"無市場數據，使用降級策略 {self.min_rate_threshold:.1f}%+ 年化",
            'timestamp': 0
        }

def main():
    """演示簡單階梯策略"""
    import sys
    
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🪜 SimpleLendingBot - 簡單階梯策略測試")
    print("==" * 30)
    
    # 檢查是否使用模擬模式
    use_mock = len(sys.argv) > 1 and sys.argv[1] == '--mock'
    
    try:
        if use_mock:
            print("🎭 使用模擬數據測試")
            test_with_mock_data()
        else:
            print("🌐 使用實時API測試")
            test_with_live_data()
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

def test_with_mock_data():
    """使用模擬數據測試"""
    # 模擬市場摘要
    mock_summary = {
        'currency': 'USD',
        'timestamp': 1234567890,
        'recent_trades': {
            'rates': [0.00037, 0.00038, 0.00037, 0.00039],
            'count': 4,
            'avg_daily_rate': 0.000375  # 約13.7%年化
        },
        'order_book': {
            'bid_avg': 0.0004,     # 14.6%年化
            'bid_best': 0.000427,  # 15.6%年化
            'bid_worst': 0.000379, # 13.8%年化
            'bid_count': 12,
            'market_balance': 'demand_heavy'
        },
        'data_quality': {
            'has_recent_trades': True,
            'has_order_book': True
        }
    }
    
    # 創建策略
    class MockConfig:
        competitive_buffer_percent = 2
        ladder_levels = 10  # 設為10檔
        min_rate_threshold = 0.05
    
    strategy = SimpleLadderStrategy(MockConfig())
    
    # 生成階梯
    result = strategy.generate_ladder_rates(mock_summary)
    
    # 顯示結果
    print_strategy_result(result)

def test_with_live_data():
    """使用實時API測試"""
    from bitfinex_api import BitfinexAPI
    from decouple import config
    
    # 從配置獲取幣種
    test_currency = config('LENDING_CURRENCY', default='UST')
    
    # 創建API客戶端
    api = BitfinexAPI()
    
    # 創建策略 (傳入API客戶端，內部自動處理市場數據)
    class LiveConfig:
        competitive_buffer_percent = 2
        ladder_levels = 10  # 設為10檔
        min_rate_threshold = 0.05
    
    strategy = SimpleLadderStrategy(LiveConfig(), api_client=api)
    
    # 生成階梯 (使用配置的幣種)
    result = strategy.generate_ladder_rates(currency=test_currency)
    
    # 顯示結果
    print_strategy_result(result)

def print_strategy_result(result):
    """顯示策略結果"""
    if not result:
        print("❌ 策略生成失敗")
        return
    
    print(f"\n📊 策略類型: {result.get('strategy_type', 'unknown')}")
    print(f"📋 建議: {result.get('recommendation', 'N/A')}")
    
    if 'market_analysis' in result:
        analysis = result['market_analysis']
        print(f"\n📈 市場分析:")
        print(f"   競爭區間: {analysis['bid_range'][0]:.3f}% - {analysis['bid_range'][1]:.3f}% (年化)")
        print(f"   競爭平均: {analysis['bid_avg']:.3f}% (年化)")
        print(f"   成交平均: {analysis['recent_avg']:.3f}% (年化)")
        print(f"   競爭程度: {analysis['competition_level']}")
    
    if 'strategy_rates' in result:
        rates = result['strategy_rates']
        print(f"\n🎯 策略利率:")
        print(f"   基準利率: {rates['base_rate']*365*100:.3f}% (年化)")
        print(f"   最高利率: {rates['top_rate']*365*100:.3f}% (年化)")
        print(f"   利率範圍: {rates['rate_range']*365*100:.3f}%")
    
    print(f"\n🪜 階梯分佈:")
    print("   檔位 |   年化利率   |   日利率    |    權重")
    print("   -----|--------------|------------|--------")
    
    for ladder in result['ladder_rates']:
        daily_rate = ladder['daily_rate']
        print(f"   {ladder['level']:2d}.  | {ladder['annual_percentage']:10.3f}% | {daily_rate:.8f} | {ladder['weight_suggestion']:6.1%}")
    
    print(f"\n✅ 階梯策略生成完成!")
    print("💡 這個策略直接基於市場數據，比複雜的rate_calculator更簡單可靠")

if __name__ == "__main__":
    main()