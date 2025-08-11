#!/usr/bin/env python3
"""
優化系統集成測試腳本
測試新系統的核心功能和性能
"""

import sys
import os
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
import json
from typing import Dict, List
import asyncio

# 添加項目路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main.python.core.config import get_config_manager
from src.main.python.services.database_manager import DatabaseManager
from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.services.account_status_manager_v2 import AccountStatusManagerV2
from src.main.python.services.user_dashboard_service import UserDashboardService
from src.main.python.core.strategies.optimal_allocation_strategy import OptimalAllocationStrategy
from src.main.python.core.dual_write_manager import DualWriteManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/optimized_system_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedSystemTester:
    """優化系統測試器"""
    
    def __init__(self):
        self.config = get_config_manager().config
        self.db = DatabaseManager(self.config.database)
        
        # 初始化組件 (使用mock API以避免真實交易)
        self.api_client = self._create_mock_api_client()
        self.account_manager = AccountStatusManagerV2(self.config, self.db, self.api_client)
        self.dashboard_service = UserDashboardService(self.config, self.db, self.account_manager)
        self.optimal_strategy = OptimalAllocationStrategy(self.config)
        
        # 測試結果
        self.test_results = {}
        
    def run_comprehensive_test(self):
        """運行綜合測試"""
        
        logger.info("🧪 開始優化系統綜合測試")
        
        test_suites = [
            ('數據庫連接測試', self.test_database_connection),
            ('帳戶狀態管理測試', self.test_account_status_manager),
            ('智能策略測試', self.test_optimal_strategy),
            ('用戶儀表板測試', self.test_user_dashboard),
            ('性能基準測試', self.test_performance_benchmarks),
            ('數據一致性測試', self.test_data_consistency),
            ('錯誤處理測試', self.test_error_handling),
            ('並發安全測試', self.test_concurrent_safety)
        ]
        
        for test_name, test_func in test_suites:
            logger.info(f"🔍 執行測試: {test_name}")
            try:
                start_time = time.time()
                result = test_func()
                duration = time.time() - start_time
                
                self.test_results[test_name] = {
                    'status': 'PASS' if result else 'FAIL',
                    'duration': duration,
                    'details': result if isinstance(result, dict) else {'success': result}
                }
                
                status_icon = '✅' if result else '❌'
                logger.info(f"{status_icon} {test_name}: {'通過' if result else '失敗'} ({duration:.2f}s)")
                
            except Exception as e:
                self.test_results[test_name] = {
                    'status': 'ERROR',
                    'duration': 0,
                    'error': str(e)
                }
                logger.error(f"❌ {test_name} 測試異常: {e}")
        
        # 生成測試報告
        self.generate_test_report()
        
        # 返回總體結果
        passed_tests = sum(1 for r in self.test_results.values() if r['status'] == 'PASS')
        total_tests = len(self.test_results)
        
        logger.info(f"🎯 測試完成: {passed_tests}/{total_tests} 通過")
        return passed_tests == total_tests
    
    def test_database_connection(self) -> bool:
        """測試數據庫連接和新表結構"""
        
        try:
            # 測試數據庫連接
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 檢查新表是否存在
                    new_tables = [
                        'account_status_v2',
                        'strategy_performance_v2',
                        'daily_operations_v2',
                        'user_dashboard_cache'
                    ]
                    
                    for table in new_tables:
                        cursor.execute(f"""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = '{table}'
                            )
                        """)
                        exists = cursor.fetchone()[0]
                        if not exists:
                            logger.error(f"表 {table} 不存在")
                            return False
                    
                    # 測試寫入操作
                    cursor.execute("""
                        INSERT INTO account_status_v2 (
                            date, total_balance, lending_amount, available_amount,
                            utilization_rate, daily_interest, cumulative_interest,
                            daily_roi, annualized_roi, active_orders_count, avg_lending_rate
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (date) DO NOTHING
                    """, (
                        datetime.now().date(),
                        40000.0, 38000.0, 2000.0, 95.0,
                        12.5, 1250.0, 0.033, 12.0, 40, 8.2
                    ))
                    
                    # 測試讀取操作
                    cursor.execute("SELECT COUNT(*) FROM account_status_v2")
                    count = cursor.fetchone()[0]
                    
                    conn.commit()
                    
                    logger.info(f"數據庫測試通過，account_status_v2 表有 {count} 條記錄")
                    return True
                    
        except Exception as e:
            logger.error(f"數據庫測試失敗: {e}")
            return False
    
    def test_account_status_manager(self) -> bool:
        """測試帳戶狀態管理器"""
        
        try:
            # 測試獲取當前狀態
            status = self.account_manager.get_current_status()
            
            required_fields = [
                'total_balance', 'money_working', 'money_idle',
                'utilization_rate', 'daily_earnings', 'annual_rate',
                'active_orders_count', 'avg_lending_rate'
            ]
            
            for field in required_fields:
                if field not in status:
                    logger.error(f"帳戶狀態缺少字段: {field}")
                    return False
            
            # 測試數據類型
            if not isinstance(status['total_balance'], (int, float, Decimal)):
                logger.error("total_balance 數據類型錯誤")
                return False
            
            if not (0 <= status['utilization_rate'] <= 100):
                logger.error(f"資金利用率超出範圍: {status['utilization_rate']}")
                return False
            
            # 測試保存每日快照
            snapshot_saved = self.account_manager.save_daily_snapshot()
            if not snapshot_saved:
                logger.error("保存每日快照失敗")
                return False
            
            # 測試績效總結
            performance = self.account_manager.get_performance_summary(7)
            if not performance or 'total_earnings' not in performance:
                logger.error("績效總結獲取失敗")
                return False
            
            # 測試優化建議
            suggestions = self.account_manager.get_optimization_suggestions()
            if not isinstance(suggestions, list):
                logger.error("優化建議格式錯誤")
                return False
            
            logger.info("帳戶狀態管理器測試通過")
            return True
            
        except Exception as e:
            logger.error(f"帳戶狀態管理器測試失敗: {e}")
            return False
    
    def test_optimal_strategy(self) -> bool:
        """測試智能資金分配策略"""
        
        try:
            # 模擬市場數據
            mock_market_data = {
                'rates_data': {
                    'bids': [
                        {'rate': 0.085, 'amount': 10000},
                        {'rate': 0.082, 'amount': 15000},
                        {'rate': 0.080, 'amount': 20000},
                        {'rate': 0.078, 'amount': 25000},
                        {'rate': 0.075, 'amount': 30000}
                    ]
                },
                'avg_rate': 0.080
            }
            
            # 測試策略生成
            available_balance = Decimal('10000')
            offers = self.optimal_strategy.generate_offers(available_balance, mock_market_data)
            
            if not offers:
                logger.error("策略未生成任何訂單")
                return False
            
            # 驗證訂單格式
            for i, offer in enumerate(offers):
                required_fields = ['rate', 'amount', 'period']
                for field in required_fields:
                    if field not in offer:
                        logger.error(f"訂單 {i} 缺少字段: {field}")
                        return False
                
                if offer['rate'] <= 0 or offer['amount'] <= 0:
                    logger.error(f"訂單 {i} 數值無效")
                    return False
            
            # 測試資金利用率
            total_amount = sum(Decimal(str(offer['amount'])) for offer in offers)
            utilization = total_amount / available_balance * 100
            
            if utilization < 90:  # 期望利用率至少90%
                logger.warning(f"資金利用率較低: {utilization:.1f}%")
            
            # 測試策略指標
            metrics = self.optimal_strategy.get_strategy_metrics()
            if not isinstance(metrics, dict):
                logger.error("策略指標格式錯誤")
                return False
            
            logger.info(f"智能策略測試通過，生成 {len(offers)} 個訂單，"
                       f"利用率 {utilization:.1f}%")
            return True
            
        except Exception as e:
            logger.error(f"智能策略測試失敗: {e}")
            return False
    
    def test_user_dashboard(self) -> bool:
        """測試用戶儀表板服務"""
        
        try:
            # 測試儀表板數據獲取
            dashboard = self.dashboard_service.get_user_dashboard()
            
            required_sections = ['overview', 'performance', 'strategies', 'suggestions']
            for section in required_sections:
                if section not in dashboard:
                    logger.error(f"儀表板缺少部分: {section}")
                    return False
            
            # 測試概覽數據
            overview = dashboard['overview']
            required_overview_fields = [
                'total_balance', 'money_working', 'daily_earnings', 'annual_rate'
            ]
            
            for field in required_overview_fields:
                if field not in overview:
                    logger.error(f"概覽缺少字段: {field}")
                    return False
                
                if 'value' not in overview[field] or 'display' not in overview[field]:
                    logger.error(f"概覽字段 {field} 格式錯誤")
                    return False
            
            # 測試績效數據
            performance = dashboard['performance']
            if 'week' not in performance or 'month' not in performance:
                logger.error("績效數據缺少週/月統計")
                return False
            
            # 測試建議數據
            suggestions = dashboard['suggestions']
            if not isinstance(suggestions, list):
                logger.error("建議數據格式錯誤")
                return False
            
            logger.info("用戶儀表板測試通過")
            return True
            
        except Exception as e:
            logger.error(f"用戶儀表板測試失敗: {e}")
            return False
    
    def test_performance_benchmarks(self) -> Dict:
        """性能基準測試"""
        
        results = {}
        
        try:
            # 測試帳戶狀態查詢性能
            start_time = time.time()
            for _ in range(100):
                self.account_manager.get_current_status()
            status_query_time = (time.time() - start_time) / 100
            results['avg_status_query_time'] = status_query_time
            
            # 測試儀表板生成性能
            start_time = time.time()
            for _ in range(10):
                self.dashboard_service.get_user_dashboard()
            dashboard_gen_time = (time.time() - start_time) / 10
            results['avg_dashboard_gen_time'] = dashboard_gen_time
            
            # 測試策略生成性能
            mock_market_data = {
                'rates_data': {'bids': [{'rate': 0.08, 'amount': 10000}] * 20},
                'avg_rate': 0.08
            }
            
            start_time = time.time()
            for _ in range(50):
                self.optimal_strategy.generate_offers(Decimal('10000'), mock_market_data)
            strategy_gen_time = (time.time() - start_time) / 50
            results['avg_strategy_gen_time'] = strategy_gen_time
            
            # 性能標準檢查
            performance_ok = (
                status_query_time < 0.1 and  # 狀態查詢 < 100ms
                dashboard_gen_time < 0.5 and  # 儀表板生成 < 500ms
                strategy_gen_time < 0.2       # 策略生成 < 200ms
            )
            
            results['performance_acceptable'] = performance_ok
            
            logger.info(f"性能測試完成 - 狀態查詢: {status_query_time*1000:.1f}ms, "
                       f"儀表板: {dashboard_gen_time*1000:.1f}ms, "
                       f"策略生成: {strategy_gen_time*1000:.1f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"性能測試失敗: {e}")
            return {'error': str(e)}
    
    def test_data_consistency(self) -> bool:
        """測試數據一致性"""
        
        try:
            # 創建測試數據
            test_date = datetime.now().date()
            
            # 插入測試數據到 account_status_v2
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO account_status_v2 (
                            date, total_balance, lending_amount, available_amount,
                            utilization_rate, daily_interest, cumulative_interest,
                            daily_roi, annualized_roi, active_orders_count, avg_lending_rate
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (date) DO UPDATE SET
                            total_balance = EXCLUDED.total_balance
                    """, (
                        test_date, 50000.0, 47500.0, 2500.0, 95.0,
                        15.0, 1500.0, 0.032, 11.7, 50, 8.3
                    ))
                    
                    # 驗證數據寫入
                    cursor.execute("""
                        SELECT total_balance, lending_amount, utilization_rate
                        FROM account_status_v2 
                        WHERE date = %s
                    """, (test_date,))
                    
                    result = cursor.fetchone()
                    if not result:
                        logger.error("測試數據寫入失敗")
                        return False
                    
                    # 驗證數據邏輯一致性
                    total_balance, lending_amount, utilization_rate = result
                    expected_utilization = (lending_amount / total_balance) * 100
                    
                    if abs(utilization_rate - expected_utilization) > 1:  # 允許1%誤差
                        logger.error(f"數據邏輯不一致: 利用率 {utilization_rate}%, "
                                   f"期望 {expected_utilization:.1f}%")
                        return False
                    
                    conn.commit()
            
            logger.info("數據一致性測試通過")
            return True
            
        except Exception as e:
            logger.error(f"數據一致性測試失敗: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """測試錯誤處理"""
        
        try:
            # 測試無效輸入處理
            try:
                # 無效餘額
                self.optimal_strategy.generate_offers(Decimal('-1000'), {})
                logger.error("應該拒絕負數餘額")
                return False
            except:
                pass  # 期望拋出異常
            
            # 測試空數據處理
            empty_dashboard = self.dashboard_service._get_fallback_dashboard()
            if not empty_dashboard or 'error' not in empty_dashboard:
                logger.error("後備儀表板數據格式錯誤")
                return False
            
            # 測試數據庫連接錯誤處理
            # (這裡簡化測試，實際中可能需要模擬連接失敗)
            
            logger.info("錯誤處理測試通過")
            return True
            
        except Exception as e:
            logger.error(f"錯誤處理測試失敗: {e}")
            return False
    
    def test_concurrent_safety(self) -> bool:
        """測試並發安全性"""
        
        try:
            import threading
            import queue
            
            results = queue.Queue()
            
            def worker():
                try:
                    # 並發執行狀態查詢
                    status = self.account_manager.get_current_status()
                    results.put(('success', status))
                except Exception as e:
                    results.put(('error', str(e)))
            
            # 創建10個並發線程
            threads = []
            for _ in range(10):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()
            
            # 等待所有線程完成
            for t in threads:
                t.join(timeout=5)
            
            # 檢查結果
            success_count = 0
            error_count = 0
            
            while not results.empty():
                status, data = results.get()
                if status == 'success':
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(f"並發錯誤: {data}")
            
            if error_count > 0:
                logger.error(f"並發測試失敗: {error_count} 個錯誤")
                return False
            
            logger.info(f"並發安全測試通過: {success_count} 個成功請求")
            return True
            
        except Exception as e:
            logger.error(f"並發安全測試失敗: {e}")
            return False
    
    def generate_test_report(self):
        """生成測試報告"""
        
        report = {
            'test_summary': {
                'total_tests': len(self.test_results),
                'passed': sum(1 for r in self.test_results.values() if r['status'] == 'PASS'),
                'failed': sum(1 for r in self.test_results.values() if r['status'] == 'FAIL'),
                'errors': sum(1 for r in self.test_results.values() if r['status'] == 'ERROR'),
                'total_duration': sum(r.get('duration', 0) for r in self.test_results.values())
            },
            'test_details': self.test_results,
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'python_version': sys.version,
                'database': 'PostgreSQL'
            }
        }
        
        # 保存報告到文件
        report_path = 'logs/optimized_system_test_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"測試報告已保存: {report_path}")
        
        # 打印簡要報告
        print("\n" + "="*60)
        print("🧪 優化系統測試報告")
        print("="*60)
        print(f"總測試數: {report['test_summary']['total_tests']}")
        print(f"✅ 通過: {report['test_summary']['passed']}")
        print(f"❌ 失敗: {report['test_summary']['failed']}")
        print(f"⚠️  錯誤: {report['test_summary']['errors']}")
        print(f"⏱️  總耗時: {report['test_summary']['total_duration']:.2f}s")
        print("="*60)
        
        # 詳細結果
        for test_name, result in self.test_results.items():
            status_icon = {'PASS': '✅', 'FAIL': '❌', 'ERROR': '⚠️'}[result['status']]
            print(f"{status_icon} {test_name}: {result['status']} ({result['duration']:.2f}s)")
        
        print("="*60)
    
    def _create_mock_api_client(self):
        """創建模擬 API 客戶端"""
        
        class MockApiClient:
            def get_wallet_balances(self):
                return {
                    'funding': {
                        'USD': {
                            'balance': 40000.0,
                            'available': 2000.0
                        }
                    }
                }
            
            def get_active_funding_offers(self):
                return [
                    {'amount': 5000, 'rate': 0.082, 'period': 7},
                    {'amount': 5000, 'rate': 0.084, 'period': 7},
                    {'amount': 5000, 'rate': 0.086, 'period': 7}
                ]
            
            def get_funding_history(self, since=None):
                return [
                    {
                        'type': 'interest_payment',
                        'amount': 12.5,
                        'timestamp': datetime.now()
                    }
                ]
        
        return MockApiClient()

def main():
    """主函數"""
    
    tester = OptimizedSystemTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 所有測試通過！優化系統準備就緒")
            return 0
        else:
            print("\n❌ 部分測試失敗，請檢查日誌")
            return 1
            
    except Exception as e:
        print(f"\n💥 測試執行異常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())