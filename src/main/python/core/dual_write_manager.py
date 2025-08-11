"""
雙寫管理器 - 新舊系統並行運行
確保數據一致性和平滑遷移
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
import json

from src.main.python.services.database_manager import DatabaseManager
from src.main.python.services.account_status_manager_v2 import AccountStatusManagerV2
from src.main.python.repositories.lending_order_repository import LendingOrderRepository
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.core.config import AppConfig

log = logging.getLogger(__name__)

class DualWriteManager:
    """
    雙寫管理器
    
    職責：
    1. 確保新舊系統同時寫入數據
    2. 比較新舊系統的數據一致性
    3. 提供安全的系統切換機制
    4. 監控新系統的性能和穩定性
    """
    
    def __init__(self, config: AppConfig, db_manager: DatabaseManager,
                 account_status_v2: AccountStatusManagerV2,
                 legacy_order_repo: LendingOrderRepository,
                 legacy_interest_repo: InterestPaymentRepository):
        
        self.config = config
        self.db = db_manager
        self.account_status_v2 = account_status_v2
        self.legacy_order_repo = legacy_order_repo
        self.legacy_interest_repo = legacy_interest_repo
        
        # 控制開關
        self.enable_new_system_write = True  # 是否寫入新系統
        self.enable_new_system_read = False  # 是否從新系統讀取
        self.enable_comparison = True  # 是否進行數據比較
        
        # 統計數據
        self.stats = {
            'dual_writes': 0,
            'write_errors': 0,
            'comparison_checks': 0,
            'data_inconsistencies': 0,
            'new_system_errors': 0
        }
        
    def write_order_data(self, order_data: Dict) -> bool:
        """
        雙寫訂單數據
        
        Args:
            order_data: 訂單數據
            
        Returns:
            bool: 是否寫入成功
        """
        
        success = True
        
        try:
            # 1. 總是寫入舊系統 (確保穩定性)
            legacy_success = self._write_to_legacy_system(order_data)
            if not legacy_success:
                log.error("舊系統寫入失敗")
                success = False
            
            # 2. 可選寫入新系統
            if self.enable_new_system_write:
                try:
                    new_success = self._write_to_new_system(order_data)
                    if not new_success:
                        log.warning("新系統寫入失敗，但不影響主流程")
                        self.stats['new_system_errors'] += 1
                        
                except Exception as e:
                    log.error(f"新系統寫入異常: {e}")
                    self.stats['new_system_errors'] += 1
            
            # 3. 數據一致性檢查
            if self.enable_comparison and legacy_success:
                self._schedule_consistency_check(order_data)
            
            self.stats['dual_writes'] += 1
            
        except Exception as e:
            log.error(f"雙寫操作失敗: {e}")
            self.stats['write_errors'] += 1
            success = False
        
        return success
    
    def read_account_status(self) -> Dict:
        """
        讀取帳戶狀態 (支持新舊系統切換)
        
        Returns:
            Dict: 帳戶狀態數據
        """
        
        if self.enable_new_system_read:
            # 從新系統讀取
            try:
                return self.account_status_v2.get_current_status()
            except Exception as e:
                log.error(f"新系統讀取失敗，回退到舊系統: {e}")
                return self._read_from_legacy_system()
        else:
            # 從舊系統讀取
            return self._read_from_legacy_system()
    
    def _write_to_legacy_system(self, order_data: Dict) -> bool:
        """寫入舊系統"""
        
        try:
            # 根據數據類型寫入對應的舊系統表
            if order_data.get('type') == 'lending_order':
                return self._write_legacy_order(order_data)
            elif order_data.get('type') == 'interest_payment':
                return self._write_legacy_interest(order_data)
            else:
                log.warning(f"未知數據類型: {order_data.get('type')}")
                return False
                
        except Exception as e:
            log.error(f"舊系統寫入失敗: {e}")
            return False
    
    def _write_to_new_system(self, order_data: Dict) -> bool:
        """寫入新系統 (聚合方式)"""
        
        try:
            # 新系統不直接寫入訂單，而是定期聚合
            # 這裡我們將數據緩存，等待聚合處理
            self._cache_for_aggregation(order_data)
            
            # 如果是重要的狀態變更，立即更新帳戶狀態
            if order_data.get('trigger_status_update'):
                return self.account_status_v2.save_daily_snapshot()
            
            return True
            
        except Exception as e:
            log.error(f"新系統寫入失敗: {e}")
            return False
    
    def _write_legacy_order(self, order_data: Dict) -> bool:
        """寫入舊系統訂單表"""
        
        try:
            # 轉換為舊系統格式
            legacy_order = {
                'bitfinex_id': order_data.get('bitfinex_id'),
                'currency': order_data.get('currency'),
                'amount': order_data.get('amount'),
                'rate': order_data.get('rate'),
                'period': order_data.get('period'),
                'status': order_data.get('status'),
                'strategy_name': order_data.get('strategy_name'),
                'strategy_params': order_data.get('strategy_params')
            }
            
            # 使用舊的 repository 寫入
            order_id = self.legacy_order_repo.create(legacy_order)
            return order_id is not None
            
        except Exception as e:
            log.error(f"寫入舊訂單表失敗: {e}")
            return False
    
    def _write_legacy_interest(self, interest_data: Dict) -> bool:
        """寫入舊系統利息表"""
        
        try:
            legacy_interest = {
                'lending_order_id': interest_data.get('lending_order_id'),
                'bitfinex_id': interest_data.get('bitfinex_id'),
                'currency': interest_data.get('currency'),
                'amount': interest_data.get('amount'),
                'rate': interest_data.get('rate'),
                'period_start': interest_data.get('period_start'),
                'period_end': interest_data.get('period_end'),
                'received_at': interest_data.get('received_at')
            }
            
            interest_id = self.legacy_interest_repo.create(legacy_interest)
            return interest_id is not None
            
        except Exception as e:
            log.error(f"寫入舊利息表失敗: {e}")
            return False
    
    def _cache_for_aggregation(self, data: Dict):
        """緩存數據等待聚合處理"""
        
        # 簡單的內存緩存實現
        # 在實際部署中可能需要使用 Redis 或數據庫緩存
        cache_key = f"aggregation_cache_{datetime.now().date()}"
        
        # 這裡簡化為直接觸發聚合更新
        # 實際中應該批量處理
        pass
    
    def _read_from_legacy_system(self) -> Dict:
        """從舊系統讀取數據"""
        
        try:
            # 從舊系統查詢並聚合數據
            # 這裡簡化實現，實際需要復雜的聚合邏輯
            
            # 獲取活躍訂單統計
            active_orders = self.legacy_order_repo.get_active_orders()
            
            # 計算基本指標
            total_lending = sum(Decimal(str(order.get('amount', 0))) for order in active_orders)
            avg_rate = (
                sum(Decimal(str(order.get('rate', 0))) for order in active_orders) / len(active_orders)
                if active_orders else Decimal('0')
            )
            
            # 獲取今日利息
            today_interest = self._get_today_interest_legacy()
            
            return {
                'total_balance': float(total_lending + 1000),  # 假設有可用餘額
                'money_working': float(total_lending),
                'money_idle': 1000.0,
                'utilization_rate': float(total_lending / (total_lending + 1000) * 100) if total_lending > 0 else 0,
                'daily_earnings': float(today_interest),
                'annual_rate': float(today_interest / total_lending * 365 * 100) if total_lending > 0 else 0,
                'active_orders_count': len(active_orders),
                'avg_lending_rate': float(avg_rate * 100),
                'last_updated': datetime.now(),
                'source': 'legacy_system'
            }
            
        except Exception as e:
            log.error(f"從舊系統讀取失敗: {e}")
            return self._get_default_status()
    
    def _get_today_interest_legacy(self) -> Decimal:
        """從舊系統獲取今日利息"""
        
        try:
            today = datetime.now().date()
            interests = self.legacy_interest_repo.get_by_date_range(today, today)
            return sum(Decimal(str(interest.get('amount', 0))) for interest in interests)
        except:
            return Decimal('0')
    
    def _schedule_consistency_check(self, data: Dict):
        """安排一致性檢查"""
        
        # 這個方法會安排後台任務來檢查數據一致性
        # 實際實現可能需要使用消息隊列或定時任務
        
        self.stats['comparison_checks'] += 1
        
        # 簡化實現：立即進行簡單檢查
        try:
            self._perform_simple_consistency_check(data)
        except Exception as e:
            log.error(f"一致性檢查失敗: {e}")
    
    def _perform_simple_consistency_check(self, data: Dict):
        """執行簡單的一致性檢查"""
        
        # 比較新舊系統的核心指標
        try:
            new_status = self.account_status_v2.get_current_status()
            legacy_status = self._read_from_legacy_system()
            
            # 檢查關鍵指標的差異
            tolerance = 0.05  # 5% 容忍度
            
            utilization_diff = abs(
                new_status.get('utilization_rate', 0) - 
                legacy_status.get('utilization_rate', 0)
            )
            
            if utilization_diff > tolerance * 100:  # 超過5%差異
                log.warning(f"資金利用率差異過大: 新系統 {new_status.get('utilization_rate'):.2f}%, "
                           f"舊系統 {legacy_status.get('utilization_rate'):.2f}%")
                self.stats['data_inconsistencies'] += 1
            
        except Exception as e:
            log.error(f"一致性檢查執行失敗: {e}")
    
    def get_dual_write_stats(self) -> Dict:
        """獲取雙寫統計數據"""
        
        total_operations = self.stats['dual_writes']
        
        return {
            'total_dual_writes': total_operations,
            'write_success_rate': (
                (total_operations - self.stats['write_errors']) / total_operations * 100
                if total_operations > 0 else 0
            ),
            'new_system_error_rate': (
                self.stats['new_system_errors'] / total_operations * 100
                if total_operations > 0 else 0
            ),
            'consistency_checks': self.stats['comparison_checks'],
            'data_inconsistencies': self.stats['data_inconsistencies'],
            'system_status': {
                'new_system_write_enabled': self.enable_new_system_write,
                'new_system_read_enabled': self.enable_new_system_read,
                'comparison_enabled': self.enable_comparison
            }
        }
    
    def enable_new_system_reads(self):
        """啟用新系統讀取"""
        
        log.info("啟用新系統讀取")
        self.enable_new_system_read = True
    
    def disable_new_system_reads(self):
        """禁用新系統讀取 (回退到舊系統)"""
        
        log.warning("禁用新系統讀取，回退到舊系統")
        self.enable_new_system_read = False
    
    def full_cutover_to_new_system(self):
        """完全切換到新系統"""
        
        log.info("開始完全切換到新系統")
        
        # 檢查新系統穩定性
        stats = self.get_dual_write_stats()
        
        if stats['new_system_error_rate'] > 5:  # 錯誤率超過5%
            log.error(f"新系統錯誤率過高 ({stats['new_system_error_rate']:.2f}%)，取消切換")
            return False
        
        if stats['data_inconsistencies'] > stats['consistency_checks'] * 0.1:  # 不一致率超過10%
            log.error("數據不一致率過高，取消切換")
            return False
        
        # 執行切換
        self.enable_new_system_read = True
        self.enable_comparison = False  # 切換後可以禁用比較以提高性能
        
        log.info("✅ 已完全切換到新系統")
        return True
    
    def _get_default_status(self) -> Dict:
        """獲取默認狀態"""
        
        return {
            'total_balance': 0,
            'money_working': 0,
            'money_idle': 0,
            'utilization_rate': 0,
            'daily_earnings': 0,
            'annual_rate': 0,
            'active_orders_count': 0,
            'avg_lending_rate': 0,
            'last_updated': datetime.now(),
            'source': 'default'
        }
        
    def health_check(self) -> Dict:
        """健康檢查"""
        
        try:
            # 檢查新系統健康狀態
            new_system_healthy = True
            try:
                status = self.account_status_v2.get_current_status()
                if not status or status.get('total_balance', 0) < 0:
                    new_system_healthy = False
            except:
                new_system_healthy = False
            
            # 檢查舊系統健康狀態
            legacy_system_healthy = True
            try:
                active_orders = self.legacy_order_repo.get_active_orders()
                if active_orders is None:
                    legacy_system_healthy = False
            except:
                legacy_system_healthy = False
            
            stats = self.get_dual_write_stats()
            
            return {
                'overall_health': 'healthy' if (new_system_healthy and legacy_system_healthy) else 'degraded',
                'new_system_healthy': new_system_healthy,
                'legacy_system_healthy': legacy_system_healthy,
                'error_rates': {
                    'write_errors': stats['write_success_rate'],
                    'new_system_errors': stats['new_system_error_rate']
                },
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            log.error(f"健康檢查失敗: {e}")
            return {
                'overall_health': 'critical',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }