"""
優化版帳戶狀態管理器
替代複雜的訂單追蹤，聚焦用戶關心的核心指標
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json

from src.main.python.services.database_manager import DatabaseManager
from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.core.config import AppConfig

log = logging.getLogger(__name__)

class AccountStatusManagerV2:
    """
    優化版帳戶狀態管理器
    
    核心理念：
    1. 實時API查詢 + 每日聚合存儲
    2. 聚焦用戶關心的核心指標
    3. 大幅減少數據庫寫入量
    4. 智能緩存提高查詢效率
    """
    
    def __init__(self, config: AppConfig, db_manager: DatabaseManager, api_client: BitfinexApiClient):
        self.config = config
        self.db = db_manager
        self.api = api_client
        self.cache = {}  # 簡單內存緩存
        self.cache_ttl = 300  # 5分鐘緩存
        
    def get_current_status(self) -> Dict:
        """
        獲取當前實時狀態 (用戶最關心的數據)
        
        Returns:
            Dict: {
                'total_balance': Decimal,      # 總資金
                'money_working': Decimal,      # 放貸中金額 
                'money_idle': Decimal,         # 閒置金額
                'utilization_rate': Decimal,   # 資金利用率 %
                'daily_earnings': Decimal,     # 今日收益
                'annual_rate': Decimal,        # 年化收益率 %
                'active_orders_count': int,    # 活躍訂單數
                'avg_lending_rate': Decimal    # 平均放貸利率
            }
        """
        
        cache_key = 'current_status'
        
        # 檢查緩存
        if self._is_cache_valid(cache_key):
            log.debug("返回緩存的狀態數據")
            return self.cache[cache_key]['data']
        
        try:
            # 實時獲取 API 數據
            api_data = self._fetch_realtime_data()
            
            # 計算核心指標
            status = self._calculate_core_metrics(api_data)
            
            # 更新緩存
            self._update_cache(cache_key, status)
            
            log.info(f"實時狀態更新 - 利用率: {status['utilization_rate']:.1f}%, "
                    f"年化收益: {status['annual_rate']:.2f}%")
            
            return status
            
        except Exception as e:
            log.error(f"獲取帳戶狀態失敗: {e}")
            # 返回緩存數據或默認值
            return self._get_fallback_status()
    
    def _fetch_realtime_data(self) -> Dict:
        """從 Bitfinex API 獲取實時數據"""
        
        log.debug("從 Bitfinex API 獲取實時數據...")
        
        # 並行獲取多個API端點數據
        wallet_data = self.api.get_wallet_balances()
        active_orders = self.api.get_active_funding_offers()
        today_history = self.api.get_funding_history(
            since=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        
        return {
            'wallets': wallet_data,
            'active_orders': active_orders,
            'today_history': today_history
        }
    
    def _calculate_core_metrics(self, api_data: Dict) -> Dict:
        """計算用戶關心的核心指標"""
        
        currency = self.config.trading.lending_currency
        
        # 1. 資金分佈計算
        wallet_info = api_data['wallets'].get('funding', {}).get(currency, {})
        total_balance = Decimal(str(wallet_info.get('balance', 0)))
        
        # 計算放貸中金額 (活躍訂單總額)
        money_working = sum(
            Decimal(str(order.get('amount', 0))) 
            for order in api_data['active_orders']
        )
        
        money_idle = total_balance - money_working
        utilization_rate = (money_working / total_balance * 100) if total_balance > 0 else Decimal('0')
        
        # 2. 收益計算
        daily_earnings = self._calculate_daily_earnings(api_data['today_history'])
        
        # 3. 年化收益率計算
        if money_working > 0 and daily_earnings > 0:
            daily_roi = (daily_earnings / money_working) * 100
            annual_rate = daily_roi * 365
        else:
            annual_rate = Decimal('0')
        
        # 4. 訂單統計
        active_orders_count = len(api_data['active_orders'])
        avg_lending_rate = (
            sum(Decimal(str(order.get('rate', 0))) for order in api_data['active_orders']) / 
            active_orders_count
        ) if active_orders_count > 0 else Decimal('0')
        
        return {
            'total_balance': total_balance,
            'money_working': money_working,
            'money_idle': money_idle,
            'utilization_rate': utilization_rate,
            'daily_earnings': daily_earnings,
            'annual_rate': annual_rate,
            'active_orders_count': active_orders_count,
            'avg_lending_rate': avg_lending_rate * 100,  # 轉換為百分比
            'last_updated': datetime.now()
        }
    
    def _calculate_daily_earnings(self, today_history: List) -> Decimal:
        """計算今日收益"""
        
        daily_earnings = Decimal('0')
        
        for transaction in today_history:
            if transaction.get('type') == 'interest_payment':
                amount = Decimal(str(transaction.get('amount', 0)))
                if amount > 0:
                    daily_earnings += amount
        
        return daily_earnings
    
    def save_daily_snapshot(self) -> bool:
        """
        保存每日快照 (替代大量訂單記錄)
        只在每日結算時調用一次
        """
        
        try:
            current_status = self.get_current_status()
            today = datetime.now().date()
            
            # 獲取累積利息 (需要計算歷史總和)
            cumulative_interest = self._calculate_cumulative_interest()
            
            # 插入或更新每日快照
            query = """
            INSERT INTO account_status_v2 (
                date, total_balance, lending_amount, available_amount, utilization_rate,
                daily_interest, cumulative_interest, daily_roi, annualized_roi,
                active_orders_count, avg_lending_rate
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (date) DO UPDATE SET
                total_balance = EXCLUDED.total_balance,
                lending_amount = EXCLUDED.lending_amount,
                available_amount = EXCLUDED.available_amount,
                utilization_rate = EXCLUDED.utilization_rate,
                daily_interest = EXCLUDED.daily_interest,
                cumulative_interest = EXCLUDED.cumulative_interest,
                daily_roi = EXCLUDED.daily_roi,
                annualized_roi = EXCLUDED.annualized_roi,
                active_orders_count = EXCLUDED.active_orders_count,
                avg_lending_rate = EXCLUDED.avg_lending_rate,
                updated_at = NOW()
            """
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        today,
                        float(current_status['total_balance']),
                        float(current_status['money_working']),
                        float(current_status['money_idle']),
                        float(current_status['utilization_rate']),
                        float(current_status['daily_earnings']),
                        float(cumulative_interest),
                        float(current_status['daily_earnings'] / current_status['money_working'] * 100) if current_status['money_working'] > 0 else 0,
                        float(current_status['annual_rate']),
                        current_status['active_orders_count'],
                        float(current_status['avg_lending_rate'])
                    ))
                    conn.commit()
            
            log.info(f"每日快照已保存 - {today}")
            return True
            
        except Exception as e:
            log.error(f"保存每日快照失敗: {e}")
            return False
    
    def get_performance_summary(self, days: int = 7) -> Dict:
        """
        獲取績效總結 (用戶關心的歷史表現)
        
        Args:
            days: 查詢天數
            
        Returns:
            Dict: 績效總結數據
        """
        
        cache_key = f'performance_summary_{days}'
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            query = """
            SELECT 
                SUM(daily_interest) as total_earnings,
                AVG(annualized_roi) as avg_annual_rate,
                MAX(daily_interest) as best_day,
                MIN(daily_interest) as worst_day,
                AVG(utilization_rate) as avg_utilization,
                STDDEV(daily_interest) as earnings_volatility,
                COUNT(*) as active_days
            FROM account_status_v2 
            WHERE date >= CURRENT_DATE - INTERVAL '%s days'
            """
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (days,))
                    result = cursor.fetchone()
                    
                    if result:
                        summary = {
                            'period_days': days,
                            'total_earnings': float(result[0]) if result[0] else 0,
                            'avg_annual_rate': float(result[1]) if result[1] else 0,
                            'best_day_earnings': float(result[2]) if result[2] else 0,
                            'worst_day_earnings': float(result[3]) if result[3] else 0,
                            'avg_utilization': float(result[4]) if result[4] else 0,
                            'consistency_score': self._calculate_consistency_score(result[5]),
                            'active_days': result[6] or 0
                        }
                        
                        # 計算日均收益
                        if summary['active_days'] > 0:
                            summary['daily_avg_earnings'] = summary['total_earnings'] / summary['active_days']
                        else:
                            summary['daily_avg_earnings'] = 0
                        
                        self._update_cache(cache_key, summary)
                        return summary
            
            return self._get_default_performance_summary()
            
        except Exception as e:
            log.error(f"獲取績效總結失敗: {e}")
            return self._get_default_performance_summary()
    
    def get_optimization_suggestions(self) -> List[Dict]:
        """
        生成優化建議 (基於當前狀態分析)
        
        Returns:
            List[Dict]: 優化建議列表
        """
        
        suggestions = []
        current_status = self.get_current_status()
        
        # 1. 資金利用率建議
        if current_status['utilization_rate'] < 95:
            idle_amount = current_status['money_idle']
            potential_daily_gain = idle_amount * current_status['avg_lending_rate'] / 365 / 100
            
            suggestions.append({
                'type': 'utilization',
                'priority': 'high',
                'title': '提高資金利用率',
                'message': f'您有 ${idle_amount:.2f} 閒置資金',
                'potential_gain': f'每日可增加收益 ${potential_daily_gain:.2f}',
                'action': '調整策略參數，提高資金利用率至95%以上'
            })
        
        # 2. 收益率建議
        market_benchmark = self._get_market_benchmark()
        if current_status['annual_rate'] < market_benchmark * 0.95:
            suggestions.append({
                'type': 'performance',
                'priority': 'medium', 
                'title': '收益率優化',
                'message': f'當前年化收益率 {current_status["annual_rate"]:.2f}% 低於市場水平',
                'potential_gain': f'優化後可提升至 {market_benchmark:.2f}%',
                'action': '考慮調整利率設置或切換策略'
            })
        
        # 3. 策略分散建議
        if current_status['active_orders_count'] < 5:
            suggestions.append({
                'type': 'diversification',
                'priority': 'low',
                'title': '增加策略分散度',
                'message': f'當前只有 {current_status["active_orders_count"]} 個活躍訂單',
                'potential_gain': '分散投資可降低風險',
                'action': '考慮增加階梯數量或使用多策略組合'
            })
        
        return suggestions
    
    def _calculate_cumulative_interest(self) -> Decimal:
        """計算累積利息收入"""
        
        query = """
        SELECT COALESCE(SUM(daily_interest), 0) as total
        FROM account_status_v2
        WHERE date <= CURRENT_DATE
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return Decimal(str(result[0])) if result else Decimal('0')
    
    def _calculate_consistency_score(self, volatility: Optional[float]) -> float:
        """計算收益一致性評分 (0-100)"""
        
        if volatility is None or volatility == 0:
            return 100.0
        
        # 波動性越低，一致性越高
        consistency = max(0, 100 - (volatility * 10))
        return min(100, consistency)
    
    def _get_market_benchmark(self) -> float:
        """獲取市場基準收益率"""
        
        # 這裡可以從市場數據或配置中獲取基準
        return 8.5  # 假設市場基準年化收益率 8.5%
    
    def _is_cache_valid(self, key: str) -> bool:
        """檢查緩存是否有效"""
        
        if key not in self.cache:
            return False
        
        cache_time = self.cache[key]['timestamp']
        return (datetime.now() - cache_time).seconds < self.cache_ttl
    
    def _update_cache(self, key: str, data: Dict):
        """更新緩存"""
        
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def _get_fallback_status(self) -> Dict:
        """獲取後備狀態數據"""
        
        # 從數據庫獲取最近的快照
        try:
            query = """
            SELECT * FROM account_status_v2 
            ORDER BY date DESC LIMIT 1
            """
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            'total_balance': Decimal(str(result[2])),
                            'money_working': Decimal(str(result[3])),
                            'money_idle': Decimal(str(result[4])),
                            'utilization_rate': Decimal(str(result[5])),
                            'daily_earnings': Decimal(str(result[6])),
                            'annual_rate': Decimal(str(result[9])),
                            'active_orders_count': result[10],
                            'avg_lending_rate': Decimal(str(result[11])),
                            'last_updated': result[1]
                        }
        except Exception as e:
            log.error(f"獲取後備數據失敗: {e}")
        
        # 返回默認值
        return {
            'total_balance': Decimal('0'),
            'money_working': Decimal('0'),
            'money_idle': Decimal('0'),
            'utilization_rate': Decimal('0'),
            'daily_earnings': Decimal('0'),
            'annual_rate': Decimal('0'),
            'active_orders_count': 0,
            'avg_lending_rate': Decimal('0'),
            'last_updated': datetime.now()
        }
    
    def _get_default_performance_summary(self) -> Dict:
        """獲取默認績效總結"""
        
        return {
            'period_days': 7,
            'total_earnings': 0,
            'avg_annual_rate': 0,
            'best_day_earnings': 0,
            'worst_day_earnings': 0,
            'avg_utilization': 0,
            'consistency_score': 0,
            'active_days': 0,
            'daily_avg_earnings': 0
        }