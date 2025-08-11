"""
用戶儀表板服務
提供用戶關心的核心數據和直觀展示
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import json

from src.main.python.services.account_status_manager_v2 import AccountStatusManagerV2
from src.main.python.services.database_manager import DatabaseManager
from src.main.python.core.config import AppConfig

log = logging.getLogger(__name__)

class UserDashboardService:
    """
    用戶儀表板服務
    
    專注於用戶關心的核心價值：
    1. 今天賺了多少錢
    2. 年化收益率多少
    3. 有多少錢在工作
    4. 資金利用率如何
    5. 哪個策略最賺錢
    6. 有什麼改善建議
    """
    
    def __init__(self, config: AppConfig, db_manager: DatabaseManager, 
                 account_status_manager: AccountStatusManagerV2):
        self.config = config
        self.db = db_manager
        self.account_manager = account_status_manager
        
    def get_user_dashboard(self) -> Dict:
        """
        獲取用戶儀表板完整數據
        
        Returns:
            Dict: 用戶儀表板數據
        """
        
        try:
            dashboard = {
                'overview': self._get_overview(),
                'performance': self._get_performance_summary(),
                'strategies': self._get_strategy_comparison(),
                'suggestions': self._get_optimization_suggestions(),
                'trends': self._get_trends_data(),
                'last_updated': datetime.now().isoformat()
            }
            
            log.info("用戶儀表板數據更新完成")
            return dashboard
            
        except Exception as e:
            log.error(f"獲取儀表板數據失敗: {e}")
            return self._get_fallback_dashboard()
    
    def _get_overview(self) -> Dict:
        """獲取概覽數據 - 用戶最關心的核心指標"""
        
        current_status = self.account_manager.get_current_status()
        
        # 計算今日vs昨日對比
        yesterday_data = self._get_yesterday_data()
        
        return {
            # 資金狀況
            'total_balance': {
                'value': float(current_status['total_balance']),
                'display': f"${current_status['total_balance']:,.2f}",
                'description': '總資金'
            },
            
            'money_working': {
                'value': float(current_status['money_working']),
                'display': f"${current_status['money_working']:,.2f}",
                'description': '錢在工作 💪',
                'percentage': float(current_status['utilization_rate'])
            },
            
            'money_idle': {
                'value': float(current_status['money_idle']),
                'display': f"${current_status['money_idle']:,.2f}",
                'description': '閒置資金 😴',
                'warning': current_status['money_idle'] > current_status['total_balance'] * Decimal('0.05')
            },
            
            # 收益數據
            'daily_earnings': {
                'value': float(current_status['daily_earnings']),
                'display': f"${current_status['daily_earnings']:.2f}",
                'description': '今日收益 🎉',
                'change': self._calculate_change(
                    float(current_status['daily_earnings']),
                    yesterday_data.get('daily_earnings', 0)
                )
            },
            
            'annual_rate': {
                'value': float(current_status['annual_rate']),
                'display': f"{current_status['annual_rate']:.2f}%",
                'description': '年化收益率 📈',
                'benchmark': self._get_market_benchmark(),
                'performance': self._get_rate_performance(float(current_status['annual_rate']))
            },
            
            # 運營狀況
            'utilization_rate': {
                'value': float(current_status['utilization_rate']),
                'display': f"{current_status['utilization_rate']:.1f}%",
                'description': '資金利用率',
                'status': self._get_utilization_status(float(current_status['utilization_rate']))
            },
            
            'active_orders': {
                'value': current_status['active_orders_count'],
                'display': f"{current_status['active_orders_count']} 筆",
                'description': '活躍訂單',
                'avg_rate': f"{current_status['avg_lending_rate']:.3f}%"
            }
        }
    
    def _get_performance_summary(self) -> Dict:
        """獲取績效總結"""
        
        # 獲取不同時間段的績效
        week_performance = self.account_manager.get_performance_summary(7)
        month_performance = self.account_manager.get_performance_summary(30)
        
        return {
            'week': {
                'total_earnings': week_performance['total_earnings'],
                'display': f"${week_performance['total_earnings']:.2f}",
                'description': '本周總收益',
                'daily_avg': week_performance['daily_avg_earnings'],
                'consistency': week_performance['consistency_score']
            },
            
            'month': {
                'total_earnings': month_performance['total_earnings'],
                'display': f"${month_performance['total_earnings']:.2f}",
                'description': '本月總收益',
                'daily_avg': month_performance['daily_avg_earnings'],
                'annual_rate': month_performance['avg_annual_rate']
            },
            
            'highlights': {
                'best_day': {
                    'amount': week_performance['best_day_earnings'],
                    'display': f"${week_performance['best_day_earnings']:.2f}",
                    'description': '最佳單日收益 🏆'
                },
                'consistency': {
                    'score': week_performance['consistency_score'],
                    'display': f"{week_performance['consistency_score']:.0f}/100",
                    'description': '收益穩定性',
                    'level': self._get_consistency_level(week_performance['consistency_score'])
                }
            }
        }
    
    def _get_strategy_comparison(self) -> List[Dict]:
        """獲取策略對比數據"""
        
        try:
            query = """
            SELECT 
                strategy_name,
                allocated_amount,
                roi_30d,
                utilization_rate,
                avg_fill_rate,
                orders_count
            FROM strategy_performance_v2 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY strategy_name, allocated_amount, roi_30d, utilization_rate, avg_fill_rate, orders_count
            ORDER BY roi_30d DESC
            """
            
            strategies = []
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    total_allocated = sum(float(row[1]) for row in results)
                    
                    for row in results:
                        strategy_name = row[0]
                        allocated_amount = float(row[1])
                        roi_30d = float(row[2])
                        
                        strategies.append({
                            'name': strategy_name,
                            'display_name': self._get_strategy_display_name(strategy_name),
                            'allocated_amount': allocated_amount,
                            'allocation_percentage': (allocated_amount / total_allocated * 100) if total_allocated > 0 else 0,
                            'roi_30d': roi_30d,
                            'utilization_rate': float(row[3]),
                            'avg_fill_rate': float(row[4]),
                            'orders_count': row[5],
                            'performance_rating': self._rate_strategy_performance(roi_30d),
                            'recommendation': self._get_strategy_recommendation(strategy_name, roi_30d)
                        })
            
            return strategies
            
        except Exception as e:
            log.error(f"獲取策略對比失敗: {e}")
            return self._get_default_strategy_comparison()
    
    def _get_optimization_suggestions(self) -> List[Dict]:
        """獲取優化建議"""
        
        suggestions = self.account_manager.get_optimization_suggestions()
        
        # 增強建議信息
        enhanced_suggestions = []
        for suggestion in suggestions:
            enhanced = suggestion.copy()
            enhanced.update({
                'icon': self._get_suggestion_icon(suggestion['type']),
                'estimated_time': self._get_implementation_time(suggestion['type']),
                'difficulty': self._get_implementation_difficulty(suggestion['type']),
                'impact_score': self._calculate_impact_score(suggestion)
            })
            enhanced_suggestions.append(enhanced)
        
        # 按影響程度排序
        enhanced_suggestions.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return enhanced_suggestions
    
    def _get_trends_data(self) -> Dict:
        """獲取趨勢數據"""
        
        try:
            # 獲取最近30天的趨勢數據
            query = """
            SELECT 
                date,
                daily_interest,
                annualized_roi,
                utilization_rate
            FROM account_status_v2 
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY date
            """
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    dates = [row[0].strftime('%Y-%m-%d') for row in results]
                    earnings = [float(row[1]) for row in results]
                    rates = [float(row[2]) for row in results]
                    utilization = [float(row[3]) for row in results]
                    
                    return {
                        'earnings_trend': {
                            'dates': dates,
                            'values': earnings,
                            'trend': self._calculate_trend(earnings),
                            'description': '每日收益趨勢'
                        },
                        'rate_trend': {
                            'dates': dates,
                            'values': rates,
                            'trend': self._calculate_trend(rates),
                            'description': '年化收益率趨勢'
                        },
                        'utilization_trend': {
                            'dates': dates,
                            'values': utilization,
                            'trend': self._calculate_trend(utilization),
                            'description': '資金利用率趨勢'
                        }
                    }
            
        except Exception as e:
            log.error(f"獲取趨勢數據失敗: {e}")
            return {'earnings_trend': {}, 'rate_trend': {}, 'utilization_trend': {}}
    
    def _get_yesterday_data(self) -> Dict:
        """獲取昨天的數據用於對比"""
        
        try:
            query = """
            SELECT daily_interest, annualized_roi, utilization_rate
            FROM account_status_v2 
            WHERE date = CURRENT_DATE - INTERVAL '1 day'
            """
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            'daily_earnings': float(result[0]),
                            'annual_rate': float(result[1]),
                            'utilization_rate': float(result[2])
                        }
            
        except Exception as e:
            log.error(f"獲取昨日數據失敗: {e}")
        
        return {'daily_earnings': 0, 'annual_rate': 0, 'utilization_rate': 0}
    
    def _calculate_change(self, current: float, previous: float) -> Dict:
        """計算變化百分比"""
        
        if previous == 0:
            return {'value': 0, 'percentage': 0, 'direction': 'neutral'}
        
        change = current - previous
        percentage = (change / previous) * 100
        
        return {
            'value': change,
            'percentage': percentage,
            'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral',
            'display': f"{'+' if change > 0 else ''}{change:.2f} ({percentage:+.1f}%)"
        }
    
    def _get_market_benchmark(self) -> Dict:
        """獲取市場基準"""
        
        benchmark_rate = 8.5  # 假設市場基準
        
        return {
            'rate': benchmark_rate,
            'display': f"{benchmark_rate:.1f}%",
            'description': '市場基準收益率'
        }
    
    def _get_rate_performance(self, current_rate: float) -> Dict:
        """評估收益率表現"""
        
        benchmark = 8.5
        
        if current_rate >= benchmark * 1.1:
            level = 'excellent'
            description = '優秀 🎉'
            color = '#10B981'
        elif current_rate >= benchmark:
            level = 'good'
            description = '良好 👍'
            color = '#059669'
        elif current_rate >= benchmark * 0.9:
            level = 'average'
            description = '一般 😐'
            color = '#D97706'
        else:
            level = 'poor'
            description = '需改善 😟'
            color = '#DC2626'
        
        return {
            'level': level,
            'description': description,
            'color': color,
            'vs_benchmark': current_rate - benchmark
        }
    
    def _get_utilization_status(self, utilization: float) -> Dict:
        """評估資金利用率狀態"""
        
        if utilization >= 95:
            return {'level': 'excellent', 'description': '優秀', 'color': '#10B981'}
        elif utilization >= 90:
            return {'level': 'good', 'description': '良好', 'color': '#059669'}
        elif utilization >= 80:
            return {'level': 'average', 'description': '一般', 'color': '#D97706'}
        else:
            return {'level': 'poor', 'description': '需改善', 'color': '#DC2626'}
    
    def _get_consistency_level(self, score: float) -> str:
        """獲取一致性等級"""
        
        if score >= 90:
            return '非常穩定'
        elif score >= 80:
            return '穩定'
        elif score >= 70:
            return '適中'
        else:
            return '波動較大'
    
    def _get_strategy_display_name(self, strategy_name: str) -> str:
        """獲取策略顯示名稱"""
        
        name_mapping = {
            'optimal_allocation': '最優分配',
            'adaptive_laddering': '自適應階梯',
            'laddering': '標準階梯',
            'market_taker': '市場跟隨',
            'spread_filler': '利差填充'
        }
        
        return name_mapping.get(strategy_name, strategy_name)
    
    def _rate_strategy_performance(self, roi: float) -> Dict:
        """評估策略表現"""
        
        if roi >= 10:
            return {'rating': 5, 'description': '卓越', 'color': '#10B981'}
        elif roi >= 8.5:
            return {'rating': 4, 'description': '優秀', 'color': '#059669'}
        elif roi >= 7:
            return {'rating': 3, 'description': '良好', 'color': '#D97706'}
        elif roi >= 5:
            return {'rating': 2, 'description': '一般', 'color': '#F59E0B'}
        else:
            return {'rating': 1, 'description': '待改善', 'color': '#DC2626'}
    
    def _get_strategy_recommendation(self, strategy_name: str, roi: float) -> str:
        """獲取策略建議"""
        
        if roi >= 9:
            return '表現優異，建議增加配置'
        elif roi >= 7:
            return '表現良好，可考慮調整參數優化'
        elif roi >= 5:
            return '表現一般，建議檢查配置'
        else:
            return '表現不佳，建議暫停使用'
    
    def _get_suggestion_icon(self, suggestion_type: str) -> str:
        """獲取建議圖標"""
        
        icons = {
            'utilization': '⚡',
            'performance': '📈',
            'diversification': '🎯',
            'risk': '🛡️'
        }
        
        return icons.get(suggestion_type, '💡')
    
    def _get_implementation_time(self, suggestion_type: str) -> str:
        """獲取實施時間估算"""
        
        times = {
            'utilization': '立即',
            'performance': '1-2天',
            'diversification': '1天',
            'risk': '立即'
        }
        
        return times.get(suggestion_type, '1天')
    
    def _get_implementation_difficulty(self, suggestion_type: str) -> str:
        """獲取實施難度"""
        
        difficulties = {
            'utilization': '簡單',
            'performance': '中等',
            'diversification': '簡單',
            'risk': '簡單'
        }
        
        return difficulties.get(suggestion_type, '中等')
    
    def _calculate_impact_score(self, suggestion: Dict) -> float:
        """計算建議的影響評分"""
        
        # 基於潛在收益和優先級計算影響評分
        priority_scores = {'high': 3, 'medium': 2, 'low': 1}
        priority_score = priority_scores.get(suggestion.get('priority', 'medium'), 2)
        
        # 提取潛在收益數值 (如果有)
        potential_gain = suggestion.get('potential_gain', '')
        gain_score = 1
        
        if '$' in potential_gain:
            try:
                # 提取美元數值
                import re
                amounts = re.findall(r'\$(\d+\.?\d*)', potential_gain)
                if amounts:
                    gain_score = min(3, float(amounts[0]) / 10)  # 標準化到1-3分
            except:
                pass
        
        return priority_score * gain_score
    
    def _calculate_trend(self, values: List[float]) -> str:
        """計算趨勢方向"""
        
        if len(values) < 2:
            return 'neutral'
        
        # 簡單的線性趨勢計算
        recent_avg = sum(values[-7:]) / len(values[-7:]) if len(values) >= 7 else sum(values) / len(values)
        earlier_avg = sum(values[:7]) / 7 if len(values) >= 14 else sum(values[:-7]) / len(values[:-7]) if len(values) > 7 else recent_avg
        
        if recent_avg > earlier_avg * 1.05:
            return 'up'
        elif recent_avg < earlier_avg * 0.95:
            return 'down'
        else:
            return 'neutral'
    
    def _get_default_strategy_comparison(self) -> List[Dict]:
        """獲取默認策略對比"""
        
        return [
            {
                'name': 'optimal_allocation',
                'display_name': '最優分配',
                'allocated_amount': 0,
                'allocation_percentage': 0,
                'roi_30d': 0,
                'utilization_rate': 0,
                'avg_fill_rate': 0,
                'orders_count': 0,
                'performance_rating': {'rating': 0, 'description': '無數據'},
                'recommendation': '等待數據'
            }
        ]
    
    def _get_fallback_dashboard(self) -> Dict:
        """獲取後備儀表板數據"""
        
        return {
            'overview': {
                'total_balance': {'value': 0, 'display': '$0.00'},
                'money_working': {'value': 0, 'display': '$0.00'},
                'daily_earnings': {'value': 0, 'display': '$0.00'},
                'annual_rate': {'value': 0, 'display': '0.00%'}
            },
            'performance': {'week': {}, 'month': {}, 'highlights': {}},
            'strategies': [],
            'suggestions': [],
            'trends': {},
            'last_updated': datetime.now().isoformat(),
            'error': '數據加載失敗，請稍後重試'
        }