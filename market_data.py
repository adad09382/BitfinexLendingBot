#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SimpleLendingBot - 市場數據獲取模塊
專注於從 Bitfinex API 獲取和預處理市場放貸數據
職責：純數據獲取、緩存、基礎清理
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal
import time

logger = logging.getLogger(__name__)

class MarketDataFetcher:
    """簡單的市場數據獲取器"""
    
    def __init__(self, api_client):
        """
        初始化市場數據獲取器
        
        Args:
            api_client: SimpleBitfinexAPI 實例
        """
        self.api = api_client
        self._cache = {}  # 簡單緩存，避免頻繁API調用
        self._cache_duration = 300  # 5分鐘緩存
    
    def get_recent_funding_rates(self, currency: str, limit: int = 10) -> List[float]:
        """
        獲取最近放貸成交利率
        
        Args:
            currency: 幣種 (如 'USD')
            limit: 獲取數量，預設10筆
            
        Returns:
            List[float]: 最近成交的日利率列表 (如 [0.00021, 0.00022, 0.00020])
        """
        cache_key = f"recent_rates_{currency}"
        
        # 檢查緩存
        if self._is_cache_valid(cache_key):
            logger.debug(f"使用緩存的 {currency} 最近利率數據")
            return self._cache[cache_key]['data']
        
        try:
            logger.info(f"獲取 {currency} 最近 {limit} 筆放貸成交數據")
            
            # 使用新的API方法獲取成交數據
            trades = self.api.get_funding_trades(currency, limit=limit)
            
            if not trades:
                logger.warning(f"未獲取到 {currency} 成交數據")
                return []
            
            # 解析成交數據，提取利率
            rates = []
            for trade in trades:
                if len(trade) >= 4:
                    # trade 格式: [ID, MTS, AMOUNT, RATE]
                    # RATE 是日利率 (decimal)，例如 0.0002 表示 0.02% 日利率
                    rate = abs(float(trade[3]))  # 取絕對值，避免負值
                    if 0.00001 <= rate <= 2.0:  # 合理範圍過濾 (0.001% ~ 200% 日利率)
                        rates.append(rate)
            
            # 更新緩存
            self._update_cache(cache_key, rates)
            
            logger.info(f"成功獲取 {len(rates)} 個有效 {currency} 利率數據: {rates[:3]}...")
            return rates
            
        except Exception as e:
            logger.error(f"獲取 {currency} 最近利率失敗: {e}")
            return []
    
    def get_funding_book_rates(self, currency: str, precision: str = 'P0', depth: int = 25) -> Dict[str, any]:
        """
        從資金簿獲取當前 bid 和 offer 利率數據
        
        Args:
            currency: 幣種 (如 'USD')
            precision: 精度 (如 'P0')
            depth: 分析深度，預設取前25檔
            
        Returns:
            Dict: {
                'bids': [...],  # 放貸方數據 (提供資金)
                'asks': [...],  # 借貸方數據 (需要資金) 
                'bid_rates': [...],  # 提取的 bid 利率
                'ask_rates': [...],  # 提取的 ask 利率
                'analysis': {...}    # 分析結果
            }
        """
        cache_key = f"book_rates_{currency}_{precision}"
        
        # 檢查緩存
        if self._is_cache_valid(cache_key):
            logger.debug(f"使用緩存的 {currency} 資金簿數據")
            return self._cache[cache_key]['data']
        
        try:
            logger.info(f"獲取 {currency} 資金簿數據 (精度: {precision}, 深度: {depth})")
            
            # 使用新的API方法獲取資金簿
            funding_book_data = self.api.get_funding_book(currency, precision=precision, depth=depth)
            
            if not funding_book_data:
                logger.warning(f"未獲取到 {currency} 資金簿數據")
                return {}
            
            # 解析資金簿數據 
            # Bitfinex 資金簿格式: [RATE (日利率, decimal), PERIOD, COUNT, AMOUNT]
            # AMOUNT > 0: bids (放貸方，提供資金)
            # AMOUNT < 0: asks (借貸方，需要資金)
            
            bids = []  # 放貸方 (正金額)
            asks = []  # 借貸方 (負金額)
            
            for entry in funding_book_data:
                if len(entry) >= 4:
                    rate, period, count, amount = entry[0], entry[1], entry[2], entry[3]
                    
                    entry_data = {
                        'rate': float(rate),
                        'period': int(period), 
                        'count': int(count),
                        'amount': float(amount)
                    }
                    
                    if float(amount) > 0:
                        bids.append(entry_data)  # 放貸方 (提供資金)
                    else:
                        entry_data['amount'] = abs(float(amount))  # 轉為正數便於理解
                        asks.append(entry_data)  # 借貸方 (需要資金)
            
            # 提取利率數據用於分析
            bid_rates = []
            ask_rates = []
            
            # 分析 bids (放貸方利率)
            for bid in bids:
                rate = bid['rate']
                if 0.00001 <= rate <= 5.0:  # 合理範圍過濾 (0.001% ~ 500% 日利率)
                    bid_rates.append(rate)
            
            # 分析 asks (借貸方願付利率)
            for ask in asks:
                rate = ask['rate']
                if 0.00001 <= rate <= 5.0:  # 合理範圍過濾
                    ask_rates.append(rate)
            
            # 生成分析結果
            analysis = {}
            
            if bid_rates:
                analysis['bid_avg'] = sum(bid_rates) / len(bid_rates)
                analysis['bid_best'] = max(bid_rates)  # 最高放貸利率
                analysis['bid_worst'] = min(bid_rates)  # 最低放貸利率
                analysis['bid_count'] = len(bid_rates)
                analysis['bid_total_amount'] = sum(bid['amount'] for bid in bids)
            
            if ask_rates:
                analysis['ask_avg'] = sum(ask_rates) / len(ask_rates)
                analysis['ask_best'] = max(ask_rates)  # 最高借貸願付利率
                analysis['ask_worst'] = min(ask_rates)  # 最低借貸願付利率
                analysis['ask_count'] = len(ask_rates)
                analysis['ask_total_amount'] = sum(ask['amount'] for ask in asks)
            
            # 市場分析
            if bid_rates and ask_rates:
                analysis['spread'] = analysis['ask_avg'] - analysis['bid_avg']
                analysis['market_balance'] = 'supply_heavy' if len(bids) > len(asks) else 'demand_heavy'
            
            result = {
                'bids': bids,
                'asks': asks, 
                'bid_rates': bid_rates,
                'ask_rates': ask_rates,
                'analysis': analysis,
                'timestamp': time.time()
            }
            
            # 更新緩存
            self._update_cache(cache_key, result)
            
            logger.info(f"資金簿分析完成:")
            logger.info(f"  Bids (放貸方): {len(bids)} 檔, 利率 {analysis.get('bid_worst', 0)*365*100:.3f}%-{analysis.get('bid_best', 0)*365*100:.3f}%")
            logger.info(f"  Asks (借貸方): {len(asks)} 檔, 利率 {analysis.get('ask_worst', 0)*365*100:.3f}%-{analysis.get('ask_best', 0)*365*100:.3f}%") 
            
            return result
            
        except Exception as e:
            logger.error(f"獲取 {currency} 資金簿失敗: {e}")
            return {}
    
    def get_funding_stats(self, currency: str) -> Dict[str, float]:
        """
        獲取放貸統計數據 (如果API支持)
        
        Args:
            currency: 幣種
            
        Returns:
            Dict: 統計數據 {'avg_rate': 0.08, 'volume': 1000000}
        """
        try:
            logger.info(f"獲取 {currency} 放貸統計數據")
            
            # 使用新的API方法獲取統計數據
            stats_response = self.api.get_funding_stats(currency)
            
            if stats_response:
                return stats_response
                
        except Exception as e:
            logger.debug(f"獲取 {currency} 統計數據失敗 (非關鍵功能): {e}")
        
        return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """檢查緩存是否有效"""
        if cache_key not in self._cache:
            return False
        
        cache_time = self._cache[cache_key]['timestamp']
        return (time.time() - cache_time) < self._cache_duration
    
    def _update_cache(self, cache_key: str, data):
        """更新緩存"""
        self._cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear_cache(self):
        """清空緩存"""
        self._cache.clear()
        logger.info("市場數據緩存已清空")

    def get_market_summary(self, currency: str) -> Dict[str, any]:
        """
        獲取市場數據摘要 (整合最近成交和資金簿)
        
        Args:
            currency: 幣種 (如 'USD')
            
        Returns:
            Dict: 整合的市場數據摘要
        """
        try:
            logger.info(f"獲取 {currency} 市場數據摘要")
            
            # 獲取最近成交和資金簿
            recent_rates = self.get_recent_funding_rates(currency, limit=10)
            book_data = self.get_funding_book_rates(currency, precision='P0', depth=25)
            
            summary = {
                'currency': currency,
                'timestamp': time.time(),
                'recent_trades': {
                    'rates': recent_rates,
                    'count': len(recent_rates),
                    'avg_daily_rate': sum(recent_rates) / len(recent_rates) if recent_rates else 0
                },
                'order_book': book_data.get('analysis', {}),
                'data_quality': {
                    'has_recent_trades': len(recent_rates) > 0,
                    'has_order_book': 'analysis' in book_data,
                    'cache_age_seconds': 0  # 可以添加緩存年齡信息
                }
            }
            
            logger.info(f"市場摘要生成完成: 成交{len(recent_rates)}筆, 訂單簿{len(book_data.get('bids', []))}檔")
            return summary
            
        except Exception as e:
            logger.error(f"獲取市場摘要失敗: {e}")
            return {}

def main():
    """直接運行市場數據獲取的主函數"""
    import sys
    
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 SimpleLendingBot - 市場數據獲取工具")
    print("=" * 50)
    
    # 檢查是否使用模擬模式
    use_mock = len(sys.argv) > 1 and sys.argv[1] == '--mock'
    if use_mock:
        print("🎭 使用模擬模式 (演示數據結構)")
        return run_mock_mode()
    else:
        print("🌐 使用實時API模式")
        return run_live_mode()

def run_mock_mode():
    """運行模擬模式，展示數據結構"""
    print("\n🎭 模擬市場數據 (僅供演示)")
    
    # 模擬資金簿數據
    mock_book_data = {
        'bids': [
            {'rate': 0.08, 'period': 7, 'count': 3, 'amount': 50000},
            {'rate': 0.085, 'period': 14, 'count': 2, 'amount': 30000},
            {'rate': 0.09, 'period': 7, 'count': 1, 'amount': 20000},
            {'rate': 0.075, 'period': 30, 'count': 5, 'amount': 100000},
            {'rate': 0.095, 'period': 7, 'count': 1, 'amount': 15000},
        ],
        'asks': [
            {'rate': 0.12, 'period': 7, 'count': 2, 'amount': 80000},
            {'rate': 0.11, 'period': 14, 'count': 1, 'amount': 40000},
            {'rate': 0.13, 'period': 30, 'count': 3, 'amount': 60000},
        ],
        'analysis': {
            'bid_avg': 0.086,
            'bid_best': 0.095,
            'bid_worst': 0.075,
            'bid_count': 5,
            'bid_total_amount': 215000,
            'ask_avg': 0.12,
            'ask_best': 0.13,
            'ask_worst': 0.11,
            'ask_count': 3,
            'ask_total_amount': 180000,
            'spread': 0.034,
            'market_balance': 'supply_heavy'
        }
    }
    
    # 模擬最近成交
    mock_recent_rates = [0.088, 0.092, 0.084, 0.087, 0.091]
    
    # 顯示數據
    analysis = mock_book_data['analysis']
    
    print(f"\n📊 模擬市場概況:")
    print(f"   Bids (放貸方): {analysis['bid_count']} 檔")
    print(f"   Asks (借貸方): {analysis['ask_count']} 檔")
    print(f"   放貸平均利率: {analysis['bid_avg']*100:.3f}%")
    print(f"   放貸最佳利率: {analysis['bid_best']*100:.3f}%")
    print(f"   放貸總金額: {analysis['bid_total_amount']:,.0f} USD")
    print(f"   借貸平均利率: {analysis['ask_avg']*100:.3f}%")
    print(f"   借貸需求總額: {analysis['ask_total_amount']:,.0f} USD")
    print(f"   市場狀況: 供給過剩")
    
    # 顯示 Bids
    print(f"\n💰 模擬 Bids (放貸方競爭對手):")
    print("   檔位 |   年化利率   |  期限  |    金額     ")
    print("   -----|--------------|--------|-------------")
    for i, bid in enumerate(mock_book_data['bids'], 1):
        print(f"   {i:2d}.  | {bid['rate']*100:10.3f}% | {bid['period']:4d}天 | {bid['amount']:10,.0f}")
    
    # 顯示 Asks
    print(f"\n🏦 模擬 Asks (借貸需求):")
    print("   檔位 |   年化利率   |  期限  |    需求金額  ")
    print("   -----|--------------|--------|-------------")
    for i, ask in enumerate(mock_book_data['asks'], 1):
        print(f"   {i:2d}.  | {ask['rate']*100:10.3f}% | {ask['period']:4d}天 | {ask['amount']:10,.0f}")
    
    # 顯示最近成交
    print(f"\n📈 模擬最近成交:")
    for i, rate in enumerate(mock_recent_rates, 1):
        print(f"   {i}. {rate*100:.3f}%")
    
    avg_rate = sum(mock_recent_rates) / len(mock_recent_rates)
    print(f"   平均: {avg_rate*100:.3f}%")
    
    # 競爭建議
    bid_avg = analysis['bid_avg']
    print(f"\n💡 模擬利率建議:")
    print(f"   保守策略: {bid_avg * 1.01 * 100:.3f}% (略高於平均)")
    print(f"   積極策略: {analysis['bid_best'] * 0.98 * 100:.3f}% (接近最佳)")
    
    market_avg = avg_rate
    combined = bid_avg * 0.6 + market_avg * 0.4
    print(f"   綜合建議: {combined * 100:.3f}% (60%訂單簿+40%成交)")
    
    print(f"\n✅ 模擬演示完成")
    print("💡 提示: 使用 'python market_data.py' 獲取實時數據")
    return True

def run_live_mode():
    """運行實時API模式 - 簡化版本"""
    
    try:
        # 導入API客戶端
        from bitfinex_api import BitfinexAPI
        
        # 創建API客戶端和數據獲取器
        print("📡 初始化 Bitfinex API 客戶端...")
        api_client = BitfinexAPI()
        
        print("📊 創建市場數據獲取器...")
        fetcher = MarketDataFetcher(api_client)
        
        # 獲取市場數據摘要
        currency = 'USD'
        print(f"\n💰 獲取 {currency} 市場數據摘要...")
        
        summary = fetcher.get_market_summary(currency)
        
        if summary and summary.get('data_quality', {}).get('has_order_book'):
            analysis = summary['order_book']
            recent_trades = summary['recent_trades']
            
            print("✅ 市場數據獲取成功!")
            print(f"\n📊 市場概況:")
            print(f"   最近成交: {recent_trades['count']} 筆")
            print(f"   成交平均利率: {recent_trades.get('avg_daily_rate', 0)*365*100:.3f}% (年化)")
            
            if 'bid_avg' in analysis:
                print(f"   放貸競爭: {analysis['bid_count']} 檔")
                print(f"   競爭平均利率: {analysis['bid_avg']*365*100:.3f}% (年化)")
                print(f"   競爭最佳利率: {analysis['bid_best']*365*100:.3f}% (年化)")
                
            if 'market_balance' in analysis:
                balance_text = "供給過剩" if analysis['market_balance'] == 'supply_heavy' else "需求旺盛"
                print(f"   市場狀況: {balance_text}")
            
            print(f"\n💡 數據品質:")
            quality = summary['data_quality']
            print(f"   成交數據: {'✅' if quality['has_recent_trades'] else '❌'}")
            print(f"   訂單簿數據: {'✅' if quality['has_order_book'] else '❌'}")
        else:
            print("❌ 無法獲取完整市場數據")
            print("💡 提示: 可以嘗試 'python market_data.py --mock' 查看演示")
        
        print(f"\n✅ 市場數據測試完成")
        print("💡 提示: 實際利率計算請使用 rate_calculator.py")
        return True
        
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        print("💡 提示: 可以嘗試 'python market_data.py --mock' 查看演示")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)